from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from supabase import Client
from pydantic import BaseModel
import json
import re
from datetime import datetime, timezone

UUID_RE = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE,
)

from app.db.session import get_db, get_service_db
from app.config import settings
from app.ai.validator import validate_complaint
from app.services.notifications import notify_manager_appointment_scheduled
from app.dependencies.subscription import require_active_subscription

router = APIRouter()

# Tracks the ISO timestamp of the last end-of-call-report received.
# The frontend polls /voice/call-status and refreshes the dashboard when this changes.
# NOTE: module-level variable — resets on server restart, not shared across multiple workers.
_last_call_ended_at: str | None = None

@router.post("/voice/webhook")
async def voice_webhook(request: Request, background_tasks: BackgroundTasks, db: Client = Depends(get_service_db)):
    """
    Vapi webhook handler with proper event-type filtering.
    
    CRITICAL ARCHITECTURE:
    Vapi sends MANY webhook events per call (status-update, transcript, etc.)
    Most events do NOT contain call metadata.
    ONLY final events should be processed.
    
    Event filtering MUST happen FIRST before extracting call_id.
    
    Final Event Types:
    - tool-calls: User confirmed complaint via submit_complaint tool
    - end-of-call-report: Call ended (may or may not have complaint)
    
    Flow:
    1. Filter by message.type (FIRST - before call_id extraction)
    2. Extract call metadata (only for final events)
    3. Extract transcript (for audit)
    4. Detect user confirmation (tool-calls only)
    5. Create CallLog (always, for both event types)
    6. Create Complaint (only if confirmed via tool)
    """
    try:
        payload = await request.json()
        
        # ========== STEP 1: EVENT TYPE FILTERING (MUST BE FIRST) ==========
        # This MUST happen before any call_id extraction
        # Most webhook events do NOT contain call metadata
        
        message = payload.get("message", {})
        message_type = message.get("type")
        
        # Define allowed final event types
        FINAL_EVENT_TYPES = ["tool-calls", "end-of-call-report"]
        
        if message_type not in FINAL_EVENT_TYPES:
            # This is a streaming/status event - safely ignore
            # DO NOT log as error - this is normal Vapi behavior
            return {"status": "ignored", "reason": "non_final_event"}
        
        print("=" * 80)
        print(f"VAPI FINAL EVENT: {message_type}")
        print("=" * 80)
        
        # ========== STEP 2: EXTRACT CALL METADATA (ROBUST) ==========
        # Only execute after confirming this is a final event
        # Use priority-based fallback chain for different Vapi structures
        
        call_id = None
        phone_number = None
        
        # Priority 1: message.call (MOST COMMON)
        if "call" in message:
            call = message.get("call", {})
            call_id = call.get("id")
            phone_number = call.get("customer", {}).get("number")
        
        # Priority 2: message.callId (some final reports)
        if not call_id:
            call_id = message.get("callId")
        
        # Priority 3: payload.call (fallback)
        if not call_id:
            call = payload.get("call", {})
            call_id = call.get("id")
            phone_number = call.get("customer", {}).get("number")
        
        print(f"[CALL METADATA]")
        print(f"  call_id: {call_id}")
        print(f"  phone: {phone_number}")
        
        # If call_id is missing even in final event, log and return success
        # This prevents Vapi dashboard from marking call as failed
        if not call_id:
            print(f"[WARN] call_id missing in {message_type} event")
            print(f"  Returning success to prevent Vapi failure status")
            return {"status": "processed", "warning": "no_call_id"}
        
        # ========== STEP 3: EXTRACT TRANSCRIPT ==========
        # Use fallback chain - Vapi may use different structures
        artifact = message.get("artifact")
        transcript = ""
        
        if artifact:
            # Try messagesOpenAIFormatted first (most detailed)
            if "messagesOpenAIFormatted" in artifact:
                messages = artifact.get("messagesOpenAIFormatted", [])
                user_messages = [
                    msg.get("content", "")
                    for msg in messages
                    if msg.get("role") == "user"
                ]
                transcript = "\n".join(user_messages)
            
            # Fallback to direct transcript field
            elif "transcript" in artifact:
                transcript = artifact.get("transcript", "")
            
            # Fallback to messages array
            elif "messages" in artifact:
                transcript = "\n".join(
                    msg.get("content", "")
                    for msg in artifact["messages"]
                    if msg.get("role") == "user"
                )
        
        print(f"[TRANSCRIPT]")
        if transcript:
            preview = transcript[:100] + "..." if len(transcript) > 100 else transcript
            print(f"  {preview}")
        else:
            print(f"  (empty)")
        
        # ========== STEP 4: DETECT USER CONFIRMATION ==========
        # Complaints are created ONLY when message.type == "tool-calls"
        # AND submit_complaint tool exists
        
        is_tool_call_event = (message_type == "tool-calls")
        submit_tool = None
        
        if is_tool_call_event:
            # Check for submit_complaint tool in multiple locations
            tool_calls = []
            if artifact:
                tool_calls = artifact.get("toolCalls", [])
            if not tool_calls:
                tool_calls = message.get("toolCalls", [])
            
            for tool in tool_calls:
                # Harden tool name extraction - Vapi may use different structures
                tool_name = (
                    tool.get("function", {}).get("name") or  # Nested structure
                    tool.get("name")  # Direct field
                )
                
                if tool_name == "submit_complaint":
                    submit_tool = tool
                    break
        
        user_confirmed = submit_tool is not None
        
        if user_confirmed:
            print(f"[CONFIRMATION DETECTED]")
            print(f"  [OK] User confirmed complaint via submit_complaint")
        elif is_tool_call_event:
            print(f"[NO CONFIRMATION]")
            print(f"  Tool-calls event without submit_complaint (other tool called)")
        else:
            print(f"[END OF CALL]")
            print(f"  Call ended without submitting complaint (user hung up)")
        
        # ========== STEP 5: EXTRACT COMPLAINT DATA ==========
        complaint_data = None
        
        if user_confirmed:
            # Harden arguments extraction - handle different structures
            function_args = (
                submit_tool.get("function", {}).get("arguments") or  # Nested
                submit_tool.get("arguments")  # Direct
            )
            
            if isinstance(function_args, str):
                try:
                    complaint_data = json.loads(function_args)
                except:
                    complaint_data = {}
            else:
                complaint_data = function_args or {}
            
            print(f"[COMPLAINT DATA]")
            print(f"  flat_number: {complaint_data.get('flat_number')}")
            print(f"  category: {complaint_data.get('category')}")
            print(f"  appointment_date: {complaint_data.get('appointment_date')}")
        
        # ========== STEP 6: VALIDATE COMPLAINT DATA ==========
        is_valid = False
        
        if user_confirmed and complaint_data:
            validation = validate_complaint(complaint_data)
            is_valid = validation["is_complete"]
            missing = validation["missing_fields"]
            
            print(f"[VALIDATION]")
            print(f"  is_complete: {is_valid}")
            if not is_valid:
                print(f"  missing_fields: {missing}")
        
        # ========== STEP 7: IDEMPOTENCY CHECK ==========
        response = db.table("call_logs").select("*").eq("call_id", call_id).execute()
        existing_log = response.data[0] if response.data else None
        
        skip_complaint = False
        
        if existing_log:
            print(f"[IDEMPOTENCY]")
            print(f"  CallLog exists: ID={existing_log['id']}")
            
            if existing_log.get('complaint_id'):
                print(f"  Complaint already linked: ID={existing_log['complaint_id']}")
                skip_complaint = True
            else:
                print(f"  No complaint yet (retry allowed)")
        
        # ========== STEP 8: DETERMINE CALLLOG STATUS ==========
        # Status logic:
        # - "created": Complaint successfully created
        # - "pending": Confirmed + valid, about to create complaint
        # - "incomplete": Confirmed but missing required fields
        # - "abandoned": No confirmation (end-of-call-report or no tool)
        # - "failed": Complaint creation failed
        
        if user_confirmed and is_valid:
            status = "pending"
        elif user_confirmed and not is_valid:
            status = "incomplete"
        else:
            status = "abandoned"
        
        # ========== STEP 9: PERSIST CALLLOG (ALWAYS) ==========
        call_log = None
        call_log_id = None
        
        try:
            if existing_log:
                call_log = existing_log
                call_log_id = existing_log['id']
                print(f"[CALLLOG]")
                print(f"  Reusing existing: ID={call_log_id}")
            else:
                response = db.table("call_logs").insert({
                    "call_id": call_id,
                    "phone_number": phone_number,
                    "transcript": transcript,
                    "raw_event_type": message_type,
                    "complaint_status": status,
                    "complaint_id": None
                }).execute()
                
                if response.data:
                    call_log = response.data[0]
                    call_log_id = call_log['id']
                    print(f"[CALLLOG CREATED]")
                    print(f"  ID: {call_log_id}")
                    print(f"  status: {status}")
                else:
                    raise Exception("Failed to create call log")
        
        except Exception as e:
            print(f"[X] ERROR: CallLog creation failed: {e}")
            # Still return 200 to prevent Vapi failure
            return {"status": "error", "message": "calllog_failed"}
        
        # ========== STEP 10: CREATE COMPLAINT (ONLY IF CONFIRMED) ==========
        complaint_created = False
        complaint_id = None
        
        should_create = (
            user_confirmed and
            is_valid and
            not skip_complaint
        )
        
        if should_create:
            print(f"[COMPLAINT CREATION]")
            
            try:
                description = complaint_data.get("description")
                if not description or description.strip() == "":
                    description = transcript or "Voice complaint"
                
                # Fetch flat_uuid FIRST to check feature flags
                flat_no = complaint_data.get("flat_number")
                flat_response = db.table("flats").select("uuid, id").eq("flat_number", flat_no.strip().upper()).execute()
                
                if not flat_response.data:
                    raise Exception(f"Flat {flat_no} not found")
                    
                flat_uuid = flat_response.data[0]['uuid']
                flat_id = flat_response.data[0]['id']
                
                # Check voice_calls feature flag for this unit
                from app.services.feature_service import FeatureService
                from app.core.features import Feature
                feature_service = FeatureService(db)
                voice_enabled = await feature_service.is_feature_enabled(flat_id, Feature.VOICE_CALLS)
                
                if not voice_enabled:
                    print(f"  [BLOCKED] Voice calls feature is disabled for unit {flat_no}")
                    # Update call log to reflect blocked status
                    db.table("call_logs").update({
                        "complaint_status": "feature_disabled"
                    }).eq("id", call_log_id).execute()
                    return {"status": "processed", "message": "feature_disabled"}

                appointment_date = complaint_data.get("appointment_date")

                # Auto-assign tenant from flat
                tenant_resp = db.table("tenants").select("uuid").eq("flat_uuid", flat_uuid).execute()
                tenant_uuid = str(tenant_resp.data[0]["uuid"]) if tenant_resp.data else None

                complaint_dict = {
                    "flat_number": flat_no.strip().upper(),
                    "flat_uuid": flat_uuid,
                    "tenant_uuid": tenant_uuid,
                    "category": complaint_data.get("category"),
                    "priority": "medium",
                    "description": description[:1000],
                    "status": "pending",
                    "source": "voice"
                }

                complaint_resp = db.table("complaints").insert(complaint_dict).execute()

                if complaint_resp.data:
                    created = complaint_resp.data[0]
                    complaint_id = created.get("id")
                    complaint_uuid = created.get("uuid")

                    appointment_id = None
                    appointment_response = None
                    if appointment_date and complaint_uuid:
                        try:
                            appointment_payload = {
                                "flat_number": flat_no.strip().upper(),
                                "complaint_uuid": complaint_uuid,
                                "flat_uuid": flat_uuid,
                                "appointment_date": appointment_date,
                                "status": "scheduled"
                            }
                            appointment_response = db.table("appointments").insert(appointment_payload).execute()
                            if appointment_response.data:
                                appointment_id = appointment_response.data[0]["id"]
                                print(f"  [OK] Appointment created: ID={appointment_id} at {appointment_date}")
                        except Exception as e:
                            print(f"  [!] Appointment creation failed: {e}")

                    db.table("call_logs").update({
                        "complaint_id": complaint_id,
                        "complaint_status": "created"
                    }).eq("id", call_log_id).execute()

                    call_log['complaint_id'] = complaint_id
                    call_log['complaint_status'] = "created"

                    print(f"[AUTOMATION]")
                    print(f"  call_id:            {call_id}")
                    print(f"  Complaint Created:  Yes (ID={complaint_id})")
                    print(f"  Appointment Created: {'Yes (ID=' + str(appointment_id) + ')' if appointment_id else 'No (no date provided)'}")
                    if appointment_id and appointment_response and appointment_response.data:
                        print(f"  Triggering Notification: Yes")
                        background_tasks.add_task(
                            notify_manager_appointment_scheduled,
                            appointment_response.data[0]
                        )
                    else:
                        print(f"  Triggering Notification: No (no appointment)")

                    complaint_created = True
                    print(f"  [OK] Complaint created: ID={complaint_id}")

                else:
                    raise Exception("Complaint insert returned no data")
            
            except Exception as e:
                print(f"  [X] Error: {e}")
                print(f"[AUTOMATION]")
                print(f"  call_id:           {call_id}")
                print(f"  Complaint Created: No (exception)")
                print(f"  Triggering Notification: No")
                db.table("call_logs").update({
                    "complaint_status": "failed"
                }).eq("id", call_log_id).execute()
                call_log['complaint_status'] = "failed"
        
        elif skip_complaint and existing_log:
            complaint_id = existing_log.get('complaint_id')
            print(f"[COMPLAINT]")
            print(f"  Using existing: ID={complaint_id}")
        
        # ========== STEP 11: NO COMMIT NEEDED (Supabase auto-commits) ==========
        
        print(f"[FINAL STATE]")
        print(f"  CallLog: {call_log_id}")
        print(f"  Complaint: {complaint_id or 'None'}")
        print(f"  Status: {call_log.get('complaint_status')}")
        print("=" * 80)
        
        # Stamp end-of-call time so the frontend can poll and refresh
        if message_type == "end-of-call-report":
            global _last_call_ended_at
            _last_call_ended_at = datetime.now(timezone.utc).isoformat()

        # Always return 200 for valid final events
        # This prevents Vapi dashboard from showing "Failed"
        return {
            "status": "processed",
            "call_id": call_id,
            "call_log_id": call_log_id,
            "complaint_created": complaint_created,
            "complaint_id": complaint_id
        }
    
    except Exception as e:
        print(f"[X] UNHANDLED ERROR: {e}")
        import traceback
        traceback.print_exc()
        
        # Still return 200 to prevent Vapi failure
        return {"status": "error", "message": str(e)}


# ── Lease Lead Webhook ────────────────────────────────────────────────────────

@router.post("/voice/lease-lead-webhook")
async def lease_lead_webhook(request: Request, db: Client = Depends(get_service_db)):
    """
    VAPI function tool webhook — processes submit_lease_lead calls from the lease agent.
    Always returns HTTP 200 (async tool; VAPI does not wait for the result).
    """
    print("[DEPRECATED] lease_lead_webhook called — submit_lease_lead should use /voice/lease-lead-direct now")
    try:
        payload = await request.json()
        message = payload.get("message", {})
        call = message.get("call", {})

        print("=" * 60)
        print("[LEASE LEAD WEBHOOK] Incoming payload")
        print(f"  message.type:     {message.get('type')}")
        print(f"  call.id:          {call.get('id')}")
        print(f"  call.assistantId: {call.get('assistantId')}")
        print(f"  call.phoneNumberId: {call.get('phoneNumberId')}")
        print(f"  customer.number:  {call.get('customer', {}).get('number')}")

        tool_calls = message.get("toolCalls", [])
        if not tool_calls:
            tool_calls = (message.get("artifact") or {}).get("toolCalls", [])

        lead_tool = None
        for tool in tool_calls:
            name = tool.get("function", {}).get("name") or tool.get("name")
            if name == "submit_lease_lead":
                lead_tool = tool
                break

        if not lead_tool:
            print("  [IGNORED] No submit_lease_lead tool call found")
            print("=" * 60)
            return {"status": "ignored"}

        function_args = (
            lead_tool.get("function", {}).get("arguments") or
            lead_tool.get("arguments")
        )
        if isinstance(function_args, str):
            try:
                lead_data = json.loads(function_args)
            except Exception:
                lead_data = {}
        else:
            lead_data = function_args or {}

        print(f"  [submit_lease_lead args]")
        for k, v in lead_data.items():
            print(f"    {k}: {v}")

        phone = call.get("customer", {}).get("number", "")
        call_id = call.get("id")
        assistant_id = call.get("assistantId")
        phone_number_id = call.get("phoneNumberId")

        # Resolve property_group_id and manager_id via fallback paths
        property_group_id = None
        manager_id = None
        resolution_path = None

        # Path 1: listing_uuid → lease_listings.property_group_id
        raw_uuid = lead_data.get("listing_uuid") or ""
        listing_uuid = raw_uuid.strip() if UUID_RE.match(raw_uuid.strip()) else None
        if listing_uuid:
            row = db.table("lease_listings").select("property_group_id").eq("uuid", listing_uuid).limit(1).execute()
            if row.data:
                property_group_id = row.data[0].get("property_group_id")
                resolution_path = "listing_uuid"

        # Path 2: assistant_id → manager_vapi_config (per-manager assistant)
        if not manager_id and assistant_id:
            mvc_row = (
                db.table("manager_vapi_config")
                .select("manager_id")
                .eq("vapi_lease_assistant_id", assistant_id)
                .limit(1)
                .execute()
            )
            if mvc_row.data:
                manager_id = mvc_row.data[0].get("manager_id")
                resolution_path = "assistant_id→manager_vapi_config"

        # Path 3: phone_number_id → manager_vapi_config (per-manager number)
        if not manager_id and phone_number_id:
            mvc_row = (
                db.table("manager_vapi_config")
                .select("manager_id")
                .eq("vapi_phone_number_id", phone_number_id)
                .limit(1)
                .execute()
            )
            if mvc_row.data:
                manager_id = mvc_row.data[0].get("manager_id")
                resolution_path = "phone_number_id→manager_vapi_config"

        # Path 4: unresolved
        if not property_group_id and not manager_id:
            print(f"  [WARN] Could not resolve manager for assistant={assistant_id} phone_number_id={phone_number_id}")
            resolution_path = "unresolved"

        print(f"  [pg resolution] path={resolution_path} property_group_id={property_group_id}")

        # Resolve manager_id from property group if Path 1 was used and manager_id still unknown
        if property_group_id and not manager_id:
            pg_mgr = db.table("properties_list").select("manager_id").eq("id", str(property_group_id)).limit(1).execute()
            if pg_mgr.data:
                manager_id = pg_mgr.data[0].get("manager_id")

        print(f"  [manager resolution] manager_id={manager_id}")

        qualifying_answers = lead_data.get("qualifying_answers", "{}")
        if isinstance(qualifying_answers, str):
            try:
                qualifying_answers = json.loads(qualifying_answers)
            except Exception:
                qualifying_answers = {}

        address_preference = (lead_data.get("address_preference") or "").strip()
        if address_preference:
            qualifying_answers["address_preference"] = address_preference

        raw_interested = lead_data.get("interested_listing_ids") or []
        if not isinstance(raw_interested, list):
            raw_interested = []
        interested_ids = [i for i in raw_interested if isinstance(i, str) and UUID_RE.match(i.strip())]

        if call_id:
            dup = db.table("lease_leads").select("id").eq("call_id", call_id).limit(1).execute()
            if dup.data:
                print(f"  [DUPLICATE] call_id={call_id} already exists, skipping")
                print("=" * 60)
                return {"status": "duplicate"}

        lead_payload = {
            "property_group_id": str(property_group_id) if property_group_id else None,
            "manager_id": str(manager_id) if manager_id else None,
            "listing_uuid": str(listing_uuid) if listing_uuid else None,
            "interested_listing_ids": interested_ids,
            "caller_name": lead_data.get("caller_name") or "Unknown",
            "phone": phone,
            "email": lead_data.get("email"),
            "bedrooms": lead_data.get("bedrooms") or None,
            "budget_max": lead_data.get("budget_max") or None,
            "move_in_timeline": lead_data.get("move_in_timeline"),
            "occupants": lead_data.get("occupants") or None,
            "floor_preference": lead_data.get("floor_preference"),
            "qualification_status": lead_data.get("qualification_status") or "unmatched",
            "disqualifying_reason": lead_data.get("disqualifying_reason"),
            "qualifying_answers": qualifying_answers,
            "notes": lead_data.get("notes"),
            "source": "voice",
            "call_id": call_id,
        }

        result = db.table("lease_leads").insert(lead_payload).execute()
        print(f"  [SAVED] phone={phone} status={lead_payload['qualification_status']} property_group_id={property_group_id}")

        if result.data and lead_payload.get("qualification_status") == "qualified" and manager_id:
            try:
                saved_lead = result.data[0]
                caller_name = lead_payload.get("caller_name") or "Unknown caller"
                db.table("notifications").insert({
                    "manager_id": str(manager_id),
                    "title": "New Qualified Lead",
                    "body": f"{caller_name} is interested in leasing — review their details.",
                    "type": "lead",
                    "entity_id": str(saved_lead["uuid"]),
                    "is_read": False,
                }).execute()
                print(f"  [NOTIFICATION] Qualified lead notification created for manager {manager_id}")
            except Exception as notif_err:
                print(f"  [NOTIFICATION] Failed (non-fatal): {notif_err}")

        print("=" * 60)

    except Exception as e:
        print(f"[ERROR] lease_lead_webhook: {e}")

    return {"status": "processed"}


# ── Lease end-of-call-report fallback ────────────────────────────────────────

@router.post("/voice/lease-eoc-webhook")
async def lease_eoc_webhook(request: Request, db: Client = Depends(get_service_db)):
    """
    Fallback for the lease agent's end-of-call-report.
    If submit_lease_lead was never called during the call, creates a partial
    unmatched lead so the manager still sees that a call happened.
    """
    try:
        global _last_call_ended_at
        payload = await request.json()
        message = payload.get("message", {})
        msg_type = message.get("type")

        # For any tool-call events VAPI routes here, return a neutral tool result
        # so VAPI does not treat the tool as failed.
        if msg_type not in ("end-of-call-report", None):
            tool_calls = message.get("toolCalls") or []
            if tool_calls:
                results = [
                    {"toolCallId": tc.get("id", ""), "result": "ok"}
                    for tc in tool_calls
                ]
                return {"results": results}
            return {"status": "ok"}

        call = message.get("call", {})
        call_id = call.get("id")
        assistant_id = call.get("assistantId")
        phone_number_id = call.get("phoneNumberId")
        phone = call.get("customer", {}).get("number", "")

        if not call_id:
            return {"status": "ignored", "reason": "no_call_id"}

        _last_call_ended_at = datetime.now(timezone.utc).isoformat()

        existing = db.table("lease_leads").select("id").eq("call_id", call_id).limit(1).execute()
        if existing.data:
            return {"status": "ignored", "reason": "lead_already_exists"}

        artifact = message.get("artifact", {})
        transcript = artifact.get("transcript", "")

        manager_id = None
        if assistant_id:
            mvc_row = (
                db.table("manager_vapi_config")
                .select("manager_id")
                .eq("vapi_lease_assistant_id", assistant_id)
                .limit(1)
                .execute()
            )
            if mvc_row.data:
                manager_id = mvc_row.data[0].get("manager_id")

        if not manager_id and phone_number_id:
            mvc_row = (
                db.table("manager_vapi_config")
                .select("manager_id")
                .eq("vapi_phone_number_id", phone_number_id)
                .limit(1)
                .execute()
            )
            if mvc_row.data:
                manager_id = mvc_row.data[0].get("manager_id")

        notes = (
            "[Incomplete call — lead captured from end-of-call fallback]\n\nTranscript:\n"
            + transcript[:2000]
            if transcript
            else "[Incomplete call — no transcript available]"
        )

        lead_payload = {
            "manager_id": str(manager_id) if manager_id else None,
            "property_group_id": None,
            "listing_uuid": None,
            "interested_listing_ids": [],
            "caller_name": "Unknown",
            "phone": phone,
            "qualification_status": "unmatched",
            "source": "voice",
            "call_id": call_id,
            "notes": notes,
        }

        db.table("lease_leads").insert(lead_payload).execute()
        print(f"[LEASE EOC] Partial lead saved for call_id={call_id} phone={phone} manager={manager_id}")

    except Exception as e:
        print(f"[ERROR] lease_eoc_webhook: {e}")

    return {"status": "processed"}


# ── Lease lead direct (apiRequest version) ────────────────────────────────

@router.post("/voice/lease-lead-direct")
async def lease_lead_direct(
    request: Request,
    call_id: str | None = None,
    phone: str | None = None,
    db: Client = Depends(get_service_db),
):
    """
    apiRequest version of submit_lease_lead.
    VAPI posts the lead fields as a flat JSON body.
    Query params: call_id, phone (from VAPI template variables).
    Always returns HTTP 200.
    """
    try:
        lead_data = await request.json()
        print(f"[LEASE LEAD DIRECT] call_id={call_id} phone={phone} data={lead_data}")

        if call_id:
            dup = db.table("lease_leads").select("id").eq("call_id", call_id).limit(1).execute()
            if dup.data:
                print(f"  [DUPLICATE] call_id={call_id} already exists")
                return {"status": "duplicate"}

        raw_uuid = (lead_data.get("listing_uuid") or "").strip()
        listing_uuid = raw_uuid if UUID_RE.match(raw_uuid) else None

        manager_id = None
        property_group_id = None

        if listing_uuid:
            row = db.table("lease_listings").select("property_group_id, manager_id").eq("uuid", listing_uuid).limit(1).execute()
            if row.data:
                property_group_id = row.data[0].get("property_group_id")
                manager_id = row.data[0].get("manager_id")

        qualifying_answers = lead_data.get("qualifying_answers", "{}")
        if isinstance(qualifying_answers, str):
            try:
                qualifying_answers = json.loads(qualifying_answers)
            except Exception:
                qualifying_answers = {}

        address_preference = (lead_data.get("address_preference") or "").strip()
        if address_preference:
            qualifying_answers["address_preference"] = address_preference

        raw_interested = lead_data.get("interested_listing_ids") or []
        if not isinstance(raw_interested, list):
            raw_interested = []
        interested_ids = [i for i in raw_interested if isinstance(i, str) and UUID_RE.match(i.strip())]

        lead_payload = {
            "property_group_id": str(property_group_id) if property_group_id else None,
            "manager_id": str(manager_id) if manager_id else None,
            "listing_uuid": listing_uuid,
            "interested_listing_ids": interested_ids,
            "caller_name": lead_data.get("caller_name") or "Unknown",
            "phone": phone or "",
            "bedrooms": lead_data.get("bedrooms") or None,
            "budget_max": lead_data.get("budget_max") or None,
            "move_in_timeline": lead_data.get("move_in_timeline"),
            "occupants": lead_data.get("occupants") or None,
            "floor_preference": lead_data.get("floor_preference"),
            "qualification_status": lead_data.get("qualification_status") or "unmatched",
            "disqualifying_reason": lead_data.get("disqualifying_reason"),
            "qualifying_answers": qualifying_answers,
            "notes": lead_data.get("notes"),
            "source": "voice",
            "call_id": call_id,
        }

        result = db.table("lease_leads").insert(lead_payload).execute()
        print(f"  [SAVED] phone={phone} status={lead_payload['qualification_status']}")

        global _last_call_ended_at
        _last_call_ended_at = datetime.now(timezone.utc).isoformat()

        if result.data and lead_payload.get("qualification_status") == "qualified" and manager_id:
            try:
                saved_lead = result.data[0]
                caller_name = lead_payload.get("caller_name") or "Unknown caller"
                db.table("notifications").insert({
                    "manager_id": str(manager_id),
                    "title": "New Qualified Lead",
                    "body": f"{caller_name} is interested in leasing — review their details.",
                    "type": "lead",
                    "entity_id": str(saved_lead["uuid"]),
                    "is_read": False,
                }).execute()
            except Exception as notif_err:
                print(f"  [NOTIFICATION] Failed (non-fatal): {notif_err}")

        return {"status": "saved", "caller_name": lead_payload["caller_name"]}

    except Exception as e:
        print(f"[ERROR] lease_lead_direct: {e}")
        return {"status": "error"}


# ── Call status polling endpoint ──────────────────────────────────────────────

@router.get("/voice/call-status")
async def get_call_status():
    """
    Returns the timestamp of the last end-of-call-report received.
    Frontend polls this every 10s; when the timestamp changes it refreshes
    complaints and appointments.
    """
    return {"last_call_ended_at": _last_call_ended_at}


# ── Agent info (phone numbers) ────────────────────────────────────────────────

@router.get("/voice/agent-info")
async def get_voice_agent_info(_: dict = Depends(require_active_subscription)):
    from app.config import settings
    return {
        "complaint_phone_number": settings.VAPI_COMPLAINT_PHONE_NUMBER or None,
    }


# ── Outbound call endpoint ────────────────────────────────────────────────────

class OutboundCallRequest(BaseModel):
    customer_number: str   # E.164 format, e.g. "+919876543210"
    first_message: str | None = None
    agent: str = "complaint"  # "complaint" or "lease"


@router.post("/voice/call/outbound")
async def make_outbound_call(
    req: OutboundCallRequest,
    user: dict = Depends(require_active_subscription),
    svc_db: Client = Depends(get_service_db),
):
    """
    Initiate an outbound call using either the complaint or lease agent.
    agent="complaint" uses VAPI_COMPLAINT_ASSISTANT_ID + VAPI_COMPLAINT_NUMBER_ID.
    agent="lease" uses the manager's per-group provisioned assistant; falls back to
                  VAPI_SHARED_LEASE_ASSISTANT_ID if no active provisioned group exists.
    """
    import asyncio
    import httpx
    from vapi import Vapi, CreateCustomerDto, AssistantOverrides
    from vapi.core.api_error import ApiError
    from app.config import settings

    if not settings.PRIVATE_VAPI_API:
        raise HTTPException(status_code=500, detail="PRIVATE_VAPI_API env var is not configured on the server")
    if req.agent == "complaint" and not settings.VAPI_COMPLAINT_NUMBER_ID:
        raise HTTPException(status_code=500, detail="VAPI_COMPLAINT_NUMBER_ID env var is not configured on the server")

    if req.agent == "lease":
        mvc_row = (
            svc_db.table("manager_vapi_config")
            .select("vapi_lease_assistant_id, vapi_phone_number_id")
            .eq("manager_id", user["sub"])
            .eq("vapi_provisioning_status", "active")
            .limit(1)
            .execute()
        )
        if mvc_row.data and mvc_row.data[0].get("vapi_lease_assistant_id"):
            assistant_id = mvc_row.data[0]["vapi_lease_assistant_id"]
            phone_number_id = mvc_row.data[0]["vapi_phone_number_id"]
        else:
            raise HTTPException(
                status_code=500,
                detail="No active lease agent found for this account. Check VAPI provisioning status."
            )
    else:
        assistant_id    = settings.VAPI_COMPLAINT_ASSISTANT_ID
        phone_number_id = settings.VAPI_COMPLAINT_NUMBER_ID or settings.VAPI_NUMBER_ID
        if not assistant_id:
            raise HTTPException(status_code=500, detail="VAPI_COMPLAINT_ASSISTANT_ID env var is not configured on the server")

    client = Vapi(token=settings.PRIVATE_VAPI_API)

    overrides = None
    if req.first_message:
        overrides = AssistantOverrides(first_message=req.first_message)

    try:
        call = await asyncio.to_thread(
            client.calls.create,
            assistant_id=assistant_id,
            phone_number_id=phone_number_id,
            customer=CreateCustomerDto(number=req.customer_number),
            assistant_overrides=overrides,
        )
    except ApiError as e:
        detail = e.body.get("message", str(e)) if isinstance(e.body, dict) else str(e)
        raise HTTPException(status_code=e.status_code or 502, detail=detail)
    except httpx.ReadTimeout:
        raise HTTPException(status_code=504, detail="VAPI timed out initiating the call. Check the VAPI dashboard — the call may still have been placed.")

    return {"call_id": call.id, "status": call.status, "agent": req.agent}
