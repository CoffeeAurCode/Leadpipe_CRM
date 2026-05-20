# Learning Guide Session 2: Event-Driven Architecture — Webhooks, Vapi Integration, and the 307 Redirect Trap

**Role:** Senior Staff Engineer Mentorship
**Objective:** Understand why webhooks are fundamentally different from REST APIs, how to correctly parse Vapi event payloads, and why HTTP redirects silently kill internal API calls. Every assumption from Session 1 gets stress-tested against production reality.

---

## 1. What Was Built in This Session

| Deliverable | What Changed |
|---|---|
| Vapi webhook handler | `backend/app/routes/voice.py` — filters event types, extracts call data, triggers complaint creation |
| CallLog model | `backend/app/db/models.py` — stores raw call metadata |
| Payload extraction logic | Priority-based fallback chain for `call_id` and transcript |
| Internal HTTP client | `httpx.AsyncClient` for calling internal `/complaints` endpoint |
| Event type filter | First line of webhook: ignore non-final events |
| Redirect fix | Changed `POST /complaints` → `POST /complaints/` (or redirected URL) |

---

## 2. The Mental Model Shift: Request-Response vs Event-Stream

Session 1 built a REST API. REST is synchronous and stateful at the request level:
- Client sends request
- Server processes it
- Server returns response
- Done

Webhooks are none of these things.

**REST API mental model:**
```
Client         Server
  |  POST /data  |
  |------------->|
  |              | (process)
  |  200 OK      |
  |<-------------|
```

**Webhook (event stream) mental model:**
```
External Service      Your Server
  |                        |
  |  POST /webhook (event 1 of 47) |
  |----------------------->|
  |  POST /webhook (event 2 of 47) |
  |----------------------->|
  |  POST /webhook (event 3 of 47) |
  |----------------------->|
  ... (47 total for one 2-minute call)
  |  POST /webhook (event 47 of 47)|
  |----------------------->|
```

Your webhook endpoint is a **subscriber to a real-time event stream**. Most events carry no useful data for complaint creation. Ignoring the wrong ones, or not ignoring at all, leads to:
- Database pollution (CallLog rows with all-null fields)
- False duplicate complaint creation
- Thousands of log lines per call

---

## 3. Vapi Event Architecture

### 3.1 How Many Events Does One Call Generate?

A 2-minute Vapi conversation generates roughly:

| Event Type | Count per call | Useful for us? |
|---|---|---|
| `status-update` | 10-20 | No |
| `conversation-update` | 5-10 | No |
| `transcript` | 10-20 | No |
| `speech-update` | 5-10 | No |
| `tool-calls` | 0-3 | Yes (during conversation) |
| `end-of-call-report` | 1 | Yes (final data) |

Total: 30-60 webhooks per call. Process only 1-4.

### 3.2 Event Type Filtering — Must Be First Line

```python
# backend/app/routes/voice.py

from fastapi import APIRouter, Request
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

PROCESSABLE_EVENT_TYPES = {"tool-calls", "end-of-call-report"}

@router.post("/webhook")
async def vapi_webhook(request: Request):
    payload = await request.json()
    message = payload.get("message", {})
    message_type = message.get("type")

    # STEP 1: Filter FIRST. This must be the very first check.
    # Any processing before this check wastes CPU on 95% of events.
    if message_type not in PROCESSABLE_EVENT_TYPES:
        return {"status": "ignored", "reason": f"non_final_event: {message_type}"}

    # STEP 2: Now process the event
    logger.info(f"Processing Vapi event type: {message_type}")
    # ... rest of processing
```

**Why not just log all events?** At 50 events per call and 100 calls per day: 5,000 log lines daily from one feature. Production logs become noise-only. Log after filtering.

---

## 4. Payload Structure Is Per-Event, Not Per-Endpoint

This is the most important insight of Session 2. REST API endpoints have predictable schemas. Webhook endpoints receive different schemas for each event type.

### 4.1 Where `call_id` Lives (It Moves)

```python
# end-of-call-report: call_id is at message.callId
payload = {
    "message": {
        "type": "end-of-call-report",
        "callId": "call_abc123",     # <-- HERE
        "artifact": { ... }
    }
}

# tool-calls: call_id is at message.call.id
payload = {
    "message": {
        "type": "tool-calls",
        "call": {
            "id": "call_abc123",     # <-- HERE (nested)
            "customer": {"number": "+1234567890"}
        }
    }
}

# status-update: no call_id at all
payload = {
    "message": {
        "type": "status-update",
        "status": "ended"
        # No call_id anywhere
    }
}
```

### 4.2 Priority-Based Extraction Pattern

Never assume data is in one location. Always use a fallback chain:

```python
def extract_call_metadata(payload: dict) -> tuple[str | None, str | None]:
    """
    Extract call_id and phone_number from Vapi payload.
    Uses priority-based fallback because payload structure varies by event type.

    Returns: (call_id, phone_number)
    """
    message = payload.get("message", {})
    call_id = None
    phone_number = None

    # Priority 1: message.call.id (most common in tool-calls events)
    call_obj = message.get("call", {})
    if call_obj.get("id"):
        call_id = call_obj["id"]
        phone_number = call_obj.get("customer", {}).get("number")

    # Priority 2: message.callId (end-of-call-report)
    if not call_id:
        call_id = message.get("callId")

    # Priority 3: payload.call.id (legacy/older SDK versions)
    if not call_id:
        legacy_call = payload.get("call", {})
        call_id = legacy_call.get("id")
        if not phone_number:
            phone_number = legacy_call.get("customer", {}).get("number")

    return call_id, phone_number
```

**Why three fallback levels?** Vapi's SDK has evolved. v1 used `payload.call`, v2 moved to `message.call`, some event types use `message.callId`. You cannot know which version a specific deployment uses until you inspect the actual payload in production.

### 4.3 Transcript Extraction

```python
def extract_transcript(payload: dict) -> str | None:
    """
    Transcript location also varies by event type.
    end-of-call-report: message.artifact.transcript
    Some older events: payload.artifact.transcript
    """
    message = payload.get("message", {})

    # Primary: message.artifact.transcript
    artifact = message.get("artifact", {})
    if artifact.get("transcript"):
        return artifact["transcript"]

    # Fallback: payload.artifact.transcript
    artifact = payload.get("artifact", {})
    return artifact.get("transcript")
```

---

## 5. The Silent Killer: HTTP 307 Redirects

This was the most insidious bug in Session 2. It caused zero exceptions, zero error logs, and a `200 OK` response — while silently failing to create the complaint.

### 5.1 What Happened

The webhook handler called the internal complaints endpoint like this:

```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/complaints",  # No trailing slash
        json=complaint_payload
    )
print(f"Status: {response.status_code}")  # Printed: 200
```

The console showed `200 OK`. The database had no new complaint. No exception was raised.

### 5.2 Why This Happened

FastAPI by default adds a redirect rule: `POST /complaints` → `307 Temporary Redirect` → `GET /complaints/` ... except redirects change POST to GET.

Here is the exact flow:
```
1. Client sends: POST /complaints
2. FastAPI responds: 307 Redirect → Location: /complaints/
3. httpx FOLLOWS the redirect
4. httpx sends: GET /complaints/   ← Method changed from POST to GET!
5. FastAPI returns: 200 OK (the GET list endpoint)
6. No complaint created. No error. Silent failure.
```

### 5.3 Why httpx Changes POST to GET on Redirect

This is correct HTTP behavior. RFC 7231 says:
- `301 Moved Permanently`: User agents MAY change POST to GET
- `302 Found`: User agents MAY change POST to GET
- `307 Temporary Redirect`: Method MUST be preserved (POST stays POST)
- `308 Permanent Redirect`: Method MUST be preserved

But httpx (like most HTTP clients) does change the method for historical compatibility reasons. The `307` redirect from FastAPI becomes a GET redirect when followed by httpx.

### 5.4 The Fix: Three Options

**Option A — Add trailing slash to the URL (simplest):**
```python
response = await client.post(
    "http://localhost:8000/complaints/",  # Trailing slash matches route exactly
    json=complaint_payload
)
```

**Option B — Direct function call (no HTTP overhead):**
```python
from app.routes.complaints import create_complaint
from app.schemas.complaint import ComplaintCreate

# Call the route function directly instead of HTTP
complaint = ComplaintCreate(**complaint_payload)
result = await create_complaint(complaint, db=db_session)
```
This is the correct production pattern. No HTTP overhead, no redirect risk.

**Option C — Handle redirect manually:**
```python
response = await client.post(
    "http://localhost:8000/complaints",
    json=complaint_payload,
    follow_redirects=False  # Don't follow, detect redirect
)
if response.status_code in (301, 302, 307, 308):
    redirect_url = response.headers["location"]
    response = await client.post(redirect_url, json=complaint_payload)
```

**Recommended approach for this project:** Option B. If you are calling your own API from within the same process, you should call the function, not make an HTTP request to yourself.

### 5.5 How to Detect This Bug in the Future

```python
# Add explicit status code check
response = await client.post(url, json=payload)
if response.status_code not in (200, 201):
    logger.error(f"Unexpected status: {response.status_code}")
    logger.error(f"Response body: {response.text}")
    raise Exception(f"Internal API call failed: {response.status_code}")
```

**Never trust `response.status_code == 200` alone when POSTing.** A `200` on a POST that should return `201` means you hit a GET endpoint after a redirect.

---

## 6. Complete Webhook Handler

```python
# backend/app/routes/voice.py

from fastapi import APIRouter, Request, Depends, BackgroundTasks
from supabase import Client
from app.db.session import get_db
from app.ai.extractor import extract_fields
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["Voice"])

PROCESSABLE_EVENT_TYPES = {"tool-calls", "end-of-call-report"}


@router.post("/webhook")
async def vapi_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Client = Depends(get_db)
):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "error", "reason": "invalid_json"}

    message = payload.get("message", {})
    message_type = message.get("type")

    # STEP 1: Filter non-final events immediately
    if message_type not in PROCESSABLE_EVENT_TYPES:
        return {"status": "ignored", "reason": f"{message_type}"}

    # STEP 2: Extract call metadata with fallback chain
    call_id, phone_number = extract_call_metadata(payload)

    if not call_id:
        logger.warning("Vapi webhook received final event but no call_id found")
        return {"status": "skipped", "reason": "no_call_id"}

    # STEP 3: Extract transcript
    transcript = extract_transcript(payload)

    # STEP 4: Log the call attempt (fire-and-forget for speed)
    background_tasks.add_task(
        log_call_attempt,
        db=db,
        call_id=call_id,
        phone_number=phone_number,
        transcript=transcript,
        event_type=message_type
    )

    # STEP 5: Extract complaint fields from transcript
    if not transcript:
        return {"status": "success", "reason": "no_transcript_to_process"}

    extracted = extract_fields(transcript)

    # STEP 6: Create complaint if enough data present
    if extracted.get("category") and extracted.get("description"):
        background_tasks.add_task(
            create_complaint_from_call,
            db=db,
            call_id=call_id,
            phone_number=phone_number,
            extracted=extracted
        )

    return {"status": "success", "processed_event_type": message_type}


def extract_call_metadata(payload: dict) -> tuple[str | None, str | None]:
    message = payload.get("message", {})
    call_id = None
    phone_number = None

    call_obj = message.get("call", {})
    if call_obj.get("id"):
        call_id = call_obj["id"]
        phone_number = call_obj.get("customer", {}).get("number")

    if not call_id:
        call_id = message.get("callId")

    if not call_id:
        legacy_call = payload.get("call", {})
        call_id = legacy_call.get("id")
        if not phone_number:
            phone_number = legacy_call.get("customer", {}).get("number")

    return call_id, phone_number


def extract_transcript(payload: dict) -> str | None:
    message = payload.get("message", {})
    artifact = message.get("artifact", {})
    if artifact.get("transcript"):
        return artifact["transcript"]
    artifact = payload.get("artifact", {})
    return artifact.get("transcript")


async def log_call_attempt(db, call_id, phone_number, transcript, event_type):
    """Write call log. Runs in background so it doesn't delay the webhook response."""
    try:
        db.table("call_logs").insert({
            "call_id": call_id,
            "phone_number": phone_number,
            "transcript": transcript,
            "event_type": event_type
        }).execute()
    except Exception as e:
        logger.error(f"Failed to log call attempt: {e}")


async def create_complaint_from_call(db, call_id, phone_number, extracted):
    """Create complaint from extracted voice data. Runs in background."""
    try:
        # Find tenant by phone number
        tenant = None
        if phone_number:
            tenant_resp = db.table("tenants").select("uuid, flat_uuid").eq("phone", phone_number).execute()
            if tenant_resp.data:
                tenant = tenant_resp.data[0]

        complaint_data = {
            "description": extracted.get("description"),
            "category": extracted.get("category"),
            "priority": extracted.get("priority") or "medium",
            "status": "pending",
            "flat_number": extracted.get("flat_number"),
        }

        if tenant:
            complaint_data["tenant_uuid"] = tenant["uuid"]
            complaint_data["flat_uuid"] = tenant.get("flat_uuid")

        db.table("complaints").insert(complaint_data).execute()
        logger.info(f"Complaint created from voice call {call_id}")
    except Exception as e:
        logger.error(f"Failed to create complaint from call {call_id}: {e}")
```

---

## 7. CallLog Model and Database Table

```python
# In backend/app/db/models.py (addition)

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(String(255), unique=True, nullable=False)
    phone_number = Column(String(20), nullable=True)
    transcript = Column(Text, nullable=True)
    event_type = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**Why unique constraint on `call_id`?** If the same `end-of-call-report` event is retried by Vapi (webhooks can be retried on timeout), you want idempotency. The unique constraint prevents duplicate rows for the same call.

---

## 8. Debugging Workflow for Webhook Issues

When a webhook "isn't working," follow this exact process:

```
Step 1: Is the webhook being hit at all?
  → Add: logger.info("WEBHOOK HIT") as the VERY FIRST LINE
  → If this does not appear, the URL is wrong or the service is not routing to you

Step 2: What event types are arriving?
  → Log: logger.info(f"Event type: {message.get('type')}")
  → This reveals whether you're getting final events at all

Step 3: What does the payload look like?
  → Log: logger.info(f"Full payload: {json.dumps(payload, indent=2)}")
  → Find where call_id actually is in THIS event type

Step 4: Is the DB write succeeding?
  → Query the DB directly after a test call
  → If not present: the background task failed silently

Step 5: Is the internal HTTP call working?
  → Log response.status_code AND response.text
  → If 200 but no data created: you hit a GET endpoint (redirect bug)
```

---

## 9. Errors You Will Encounter

### Error 1: Webhook fires 50 times, database has no entries

**Symptom:** Terminal shows `WEBHOOK HIT` 50 times. `call_logs` table has zero rows.

**Root cause:** All 50 events were filtered out before reaching the DB write, but the filter was misconfigured. Or the final event types had different names than expected.

**Debug:**
```python
# Temporarily log ALL event types without filtering
@router.post("/webhook")
async def vapi_webhook(request: Request):
    payload = await request.json()
    event_type = payload.get("message", {}).get("type")
    logger.info(f"RECEIVED EVENT TYPE: {event_type}")  # Log every type
    return {"status": "ok"}
```

Run a test call. Look at what types you actually receive. Update `PROCESSABLE_EVENT_TYPES` accordingly.

---

### Error 2: `call_id` is always None

**Symptom:** `Extracted - Call ID: None` in every log line.

**Root cause:** Hardcoded `payload.get("call", {}).get("id")` but the event uses `message.get("call", {}).get("id")`.

**Debug:**
```python
import json
logger.info(f"Payload keys: {list(payload.keys())}")
logger.info(f"Message keys: {list(payload.get('message', {}).keys())}")
logger.info(f"Full payload: {json.dumps(payload, default=str)}")
```

Compare the actual payload structure to your extraction code.

---

### Error 3: Complaint created but no tenant linked (always null `tenant_uuid`)

**Symptom:** Complaints appear in DB but `tenant_uuid` is always null.

**Root cause:** Phone number extracted from payload does not match the format stored in the `tenants` table. Vapi sends `+91XXXXXXXXXX`, DB stores `91XXXXXXXXXX` or `XXXXXXXXXX`.

**Fix:**
```python
def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    # Remove +, spaces, dashes, parentheses
    digits_only = re.sub(r'[^\d]', '', phone)
    # Store last 10 digits (handles country code variations)
    return digits_only[-10:] if len(digits_only) >= 10 else digits_only
```

Apply normalization both when storing tenant phone and when looking up by phone from Vapi.

---

### Error 4: Background task runs after request but DB session is closed

**Exact error:**
```
sqlalchemy.exc.InvalidRequestError: Session is already closed
```

**Root cause:** FastAPI's `get_db` dependency closes the session after the route returns. Background tasks run after the route returns, so the session is already closed.

**Fix:** Pass a new DB session to background tasks, or use a separate session inside the task:

```python
async def log_call_attempt(call_id: str, phone_number: str):
    """Background task creates its own session."""
    async with AsyncSessionLocal() as session:
        session.add(CallLog(call_id=call_id, phone_number=phone_number))
        await session.commit()
```

Or if using Supabase client (as this project does), the client is stateless and does not have session lifecycle issues — you can safely pass it to background tasks.

---

## 10. Why Webhooks Must Always Return 200 Quickly

Vapi (and most webhook providers) will retry a webhook if it does not receive a `2xx` response within a timeout window (typically 10-30 seconds).

**Danger scenario:**
```
Vapi sends webhook
  → Your server takes 15 seconds (slow AI extraction + DB write)
  → Vapi times out, retries
  → You process the same event twice
  → Two complaints created for one call
```

**Correct pattern:**
```python
@router.post("/webhook")
async def vapi_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()

    # Filter: ~1ms
    if payload.get("message", {}).get("type") not in PROCESSABLE_EVENT_TYPES:
        return {"status": "ignored"}  # Return immediately

    # Queue heavy work as background task
    background_tasks.add_task(process_call_data, payload)

    # Return 200 immediately — processing happens after
    return {"status": "accepted"}
```

Return `200` in under 1 second. Do all heavy work (AI extraction, DB writes, notifications) in background tasks.

---

## 11. The Complete Error Map

| Assumption | Reality | Consequence | Fix |
|---|---|---|---|
| One webhook per call | 30-60 webhooks per call | DB pollution, log noise | Filter by event type first |
| `payload.call.id` always exists | Location varies by event type | `call_id = None` everywhere | Priority-based fallback chain |
| `payload.artifact.transcript` | It is `message.artifact.transcript` | `transcript = None` | Check message first |
| Internal `POST /complaints` works | 307 redirect → becomes GET | Silent failure, 200 but no record | Use trailing slash or direct function call |
| `response.status_code == 200` means success | GET returns 200, POST should return 201 | False success detection | Check for redirect, verify 201 |
| DB session available in background tasks | Session closes after route returns | `InvalidRequestError` | Create new session inside background task |

---

## 12. Session Completion Checklist

- [ ] Webhook handler filters event types as the very first operation
- [ ] `call_id` extraction uses a 3-level fallback chain
- [ ] Transcript extraction checks `message.artifact` before `payload.artifact`
- [ ] Internal API calls use trailing slash or direct function call (no redirect risk)
- [ ] All response status codes are explicitly checked after HTTP calls
- [ ] Background tasks use their own DB sessions (not the request's session)
- [ ] Webhook handler returns `200` in under 1 second by deferring work to background tasks
- [ ] All events are logged for debugging before filtering in development
- [ ] Idempotency enforced via unique constraint on `call_id` in `call_logs` table
- [ ] Phone number normalization applied consistently (store and lookup use same format)
- [ ] Added debug logging at entry point to confirm webhook is being hit
