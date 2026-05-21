from fastapi import APIRouter, Request, Depends, BackgroundTasks, HTTPException
from supabase import Client
from pydantic import BaseModel
import json
import httpx
from datetime import datetime, timezone

from app.db.session import get_db, get_service_db
from app.ai.validator import validate_complaint
from app.services.notifications import notify_manager_appointment_scheduled

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
                        "complaint_status": "blocked_by_feature_flag"
                    }).eq("id", call_log_id).execute()
                    return {"status": "processed", "message": "feature_disabled"}

                complaint_payload = {
                    "flat_number": flat_no.strip().upper(),
                    "category": complaint_data.get("category"),
                    "priority": "medium",  # Default priority for voice complaints
                    "description": description[:1000], # safe clip
                    "status": "pending",
                    "source": "voice"
                }
                
                # Store appointment date for later use
                appointment_date = complaint_data.get("appointment_date")
                
                # TODO: Future improvement - call service function directly instead of HTTP
                # This HTTP approach will break with gunicorn/multiple workers/Docker
                # For Day-3 MVP, this is acceptable
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://tenant-management-mvp.onrender.com/complaints",
                        # "http://localhost:8000/complaints",  # Use localhost for local dev
                        json=complaint_payload,
                        timeout=10.0
                    )
                
                if response.status_code == 201:
                    data = response.json()
                    complaint_id = data.get("id")
                    complaint_uuid = data.get("uuid")  # UUID for foreign key
                    
                    # Create appointment if datetime provided
                    appointment_id = None
                    if appointment_date and complaint_uuid:
                        try:
                            # Get flat_uuid for appointment
                            flat_no = complaint_data.get("flat_number")
                            flat_response = db.table("flats").select("uuid").eq("flat_number", flat_no.strip().upper()).execute()
                            
                            if flat_response.data:
                                flat_uuid = flat_response.data[0]['uuid']
                                
                                appointment_payload = {
                                    "flat_number": flat_no.strip().upper(),  # Required field
                                    "complaint_uuid": complaint_uuid,
                                    "flat_uuid": flat_uuid,
                                    "appointment_date": appointment_date,
                                    "status": "scheduled"
                                }
                                
                                appointment_response = db.table("appointments").insert(appointment_payload).execute()
                                if appointment_response.data:
                                    appointment_id = appointment_response.data[0]['id']
                                    print(f"  [OK] Appointment created: ID={appointment_id} at {appointment_date}")
                        except Exception as e:
                            print(f"  [!] Appointment creation failed: {e}")
                            # Don't fail the whole flow if appointment fails
                    
                    # Update call log with complaint linkage
                    db.table("call_logs").update({
                        "complaint_id": complaint_id,
                        "complaint_status": "created"
                    }).eq("id", call_log_id).execute()
                    
                    call_log['complaint_id'] = complaint_id
                    call_log['complaint_status'] = "created"
                    
                    # ========== AUTOMATION: NOTIFICATION TRIGGER ==========
                    print(f"[AUTOMATION]")
                    print(f"  call_id:            {call_id}")
                    print(f"  Complaint Created:  Yes (ID={complaint_id})")
                    print(f"  Appointment Created: {'Yes (ID=' + str(appointment_id) + ')' if appointment_id else 'No (no date provided)'}")
                    if appointment_id and appointment_response.data:
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
                    print(f"  [X] API returned {response.status_code}")
                    print(f"[AUTOMATION]")
                    print(f"  call_id:           {call_id}")
                    print(f"  Complaint Created: No (API {response.status_code})")
                    print(f"  Triggering Notification: No")
                    db.table("call_logs").update({
                        "complaint_status": "failed"
                    }).eq("id", call_log_id).execute()
                    call_log['complaint_status'] = "failed"
            
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
    try:
        payload = await request.json()
        message = payload.get("message", {})
        call = message.get("call", {})

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

        phone = call.get("customer", {}).get("number", "")
        call_id = call.get("id")
        assistant_id = call.get("assistantId")

        # Resolve property_group_id: listing → DB, then assistant_id → DB, then null
        property_group_id = None
        listing_uuid = lead_data.get("listing_uuid") or None
        if listing_uuid:
            row = db.table("lease_listings").select("property_group_id").eq("uuid", listing_uuid).limit(1).execute()
            if row.data:
                property_group_id = row.data[0].get("property_group_id")

        if not property_group_id and assistant_id:
            pg_row = (
                db.table("properties_list")
                .select("id")
                .eq("vapi_lease_assistant_id", assistant_id)
                .limit(1)
                .execute()
            )
            if pg_row.data:
                property_group_id = pg_row.data[0].get("id")

        qualifying_answers = lead_data.get("qualifying_answers", "{}")
        if isinstance(qualifying_answers, str):
            try:
                qualifying_answers = json.loads(qualifying_answers)
            except Exception:
                qualifying_answers = {}

        lead_payload = {
            "property_group_id": str(property_group_id) if property_group_id else None,
            "listing_uuid": str(listing_uuid) if listing_uuid else None,
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

        db.table("lease_leads").insert(lead_payload).execute()
        print(f"[LEASE LEAD] Captured: phone={phone} status={lead_payload['qualification_status']}")

    except Exception as e:
        print(f"[ERROR] lease_lead_webhook: {e}")

    return {"status": "processed"}


# ── Call status polling endpoint ──────────────────────────────────────────────

@router.get("/voice/call-status")
async def get_call_status():
    """
    Returns the timestamp of the last end-of-call-report received.
    Frontend polls this every 10s; when the timestamp changes it refreshes
    complaints and appointments.
    """
    return {"last_call_ended_at": _last_call_ended_at}


# ── Outbound call endpoint ────────────────────────────────────────────────────

class OutboundCallRequest(BaseModel):
    customer_number: str   # E.164 format, e.g. "+919876543210"
    first_message: str | None = None
    agent: str = "complaint"  # "complaint" or "lease"


@router.post("/voice/call/outbound")
async def make_outbound_call(req: OutboundCallRequest):
    """
    Initiate an outbound call using either the complaint or lease agent.
    agent="complaint" uses VAPI_ASSISTANT_ID + VAPI_NUMBER_ID (test group).
    agent="lease" uses VAPI_SHARED_LEASE_ASSISTANT_ID + VAPI_SHARED_LEASE_NUMBER_ID
                  (falls back to VAPI_NUMBER_ID if lease number not set).
    """
    from vapi import Vapi, CreateCustomerDto, AssistantOverrides
    from vapi.core.api_error import ApiError
    from app.config import settings

    if not settings.PRIVATE_VAPI_API:
        raise HTTPException(status_code=500, detail="PRIVATE_VAPI_API env var is not configured on the server")
    if not settings.VAPI_NUMBER_ID:
        raise HTTPException(status_code=500, detail="VAPI_NUMBER_ID env var is not configured on the server")

    if req.agent == "lease":
        assistant_id = settings.VAPI_SHARED_LEASE_ASSISTANT_ID
        phone_number_id = settings.VAPI_SHARED_LEASE_NUMBER_ID or settings.VAPI_NUMBER_ID
        if not assistant_id:
            raise HTTPException(status_code=500, detail="VAPI_SHARED_LEASE_ASSISTANT_ID env var is not configured on the server")
    else:
        assistant_id = settings.VAPI_ASSISTANT_ID
        phone_number_id = settings.VAPI_NUMBER_ID
        if not assistant_id:
            raise HTTPException(status_code=500, detail="VAPI_ASSISTANT_ID env var is not configured on the server")

    client = Vapi(token=settings.PRIVATE_VAPI_API)

    overrides = None
    if req.first_message:
        overrides = AssistantOverrides(first_message=req.first_message)

    try:
        call = client.calls.create(
            assistant_id=assistant_id,
            phone_number_id=phone_number_id,
            customer=CreateCustomerDto(number=req.customer_number),
            assistant_overrides=overrides,
        )
    except ApiError as e:
        detail = e.body.get("message", str(e)) if isinstance(e.body, dict) else str(e)
        raise HTTPException(status_code=e.status_code or 502, detail=detail)

    return {"call_id": call.id, "status": call.status, "agent": req.agent}
