# Learning Guide Session 14: Relational Hierarchies, Async Notifications, Database Normalization, and N+1 Prevention

**Role:** Senior Staff Engineer Mentorship
**Objective:** Master building real-world hierarchical data models, non-blocking notification pipelines with feature flags, the N+1 query problem and its solutions, database normalization as a bug prevention technique, and understanding Python's async/sync boundary in FastAPI.

---

## 1. Overview of What Was Built in This Session

This session marked the transition from "toy MVP" to "structured application." Four major architectural changes:

**Feature A: Property Hierarchy System**
- Introduced three-tier data model: **Property Groups** → **Buildings** → **Units (Flats)**
- New tables: `properties_list`, `buildings` (extending existing `flats`)
- New routes: `GET/POST /property-groups`, `GET/POST /buildings`, `GET /property-groups/{id}/buildings`
- Unit count aggregation with 2-query strategy to avoid N+1

**Feature B: Asynchronous Manager Notifications**
- `notify_manager_appointment_scheduled()` — fires after appointment creation
- Sends both SMS (Twilio) and HTML email (SendGrid) with full complaint/flat/tenant details
- Feature-flagged per unit: `SMS_REMINDERS` and `EMAIL_REMINDERS` toggles in `unit_features` table
- Calls via `BackgroundTasks` so webhook returns instantly (no Vapi timeout)

**Feature C: Database Normalization — Appointments Detachment**
- Root cause fix for a 500 error: `appointment_date` was being sent to the `complaints` table which didn't have that column
- Separated appointments into their own table linked via `complaint_uuid` FK
- Prevents the 1NF violation of storing multiple appointment dates per complaint

**Feature D: Foreign Key Integrity Enforcement**
- Added explicit FK constraints between buildings and property groups, units and buildings
- Prevents orphaned units (units pointing to deleted buildings)

---

## 2. The Property Hierarchy System

### Why Hierarchies? The Scaling Problem

When you have 5 units, a flat list is fine. When you have 500 units across 10 buildings in 3 property groups, a flat list becomes unusable.

**Before (Flat List):**
```
Unit A101  ← "Where is this? Which building? Which portfolio?"
Unit B204
Unit C301
...
Unit Z999
```

**After (Hierarchy):**
```
Westside Portfolio (Property Group)
├── Ocean View Tower (Building)
│   ├── Apt 101 (Unit)
│   ├── Apt 102 (Unit)
│   └── Apt 103 (Unit)
└── Garden Court (Building)
    ├── Unit 1A (Unit)
    └── Unit 1B (Unit)

Downtown Holdings (Property Group)
└── Commerce Center (Building)
    ├── Suite 201 (Unit)
    └── Suite 202 (Unit)
```

### Database Schema: Three Tables, Two Foreign Keys

```sql
-- Top level: property groups (portfolios)
CREATE TABLE properties_list (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    image_url TEXT,
    property_type_id UUID REFERENCES property_types(id),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Middle level: buildings
CREATE TABLE buildings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    address TEXT,
    image_url TEXT,
    property_type_id UUID REFERENCES property_types(id),
    property_id UUID REFERENCES properties_list(id),  -- ← FK to property group
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Bottom level: units (existing flats table, extended)
ALTER TABLE flats ADD COLUMN building_id UUID REFERENCES buildings(id);
--                                                  ↑ FK to buildings
```

**Why Foreign Keys in the Database (Not Just Application Code)?**

A common beginner mistake is to only validate relationships in Python:
```python
# ❌ Application-only validation — fragile
async def create_flat(building_id: str, ...):
    building = db.table("buildings").select("*").eq("id", building_id).execute()
    if not building.data:
        raise HTTPException(404, "Building not found")
    # Insert flat...
```

This fails silently when:
- Two concurrent requests both check the building, both pass, then the building gets deleted between the check and the insert
- A different developer writes a script that bypasses your API entirely
- A bug causes the check to be skipped

**With a database FK constraint:**
```sql
ALTER TABLE flats ADD COLUMN building_id UUID REFERENCES buildings(id);
```

The database enforces it at the lowest level. No matter how the data gets inserted — API, script, SQL console — a flat with a non-existent `building_id` will be rejected with:
```
ERROR: insert or update on table "flats" violates foreign key constraint
"flats_building_id_fkey"
DETAIL: Key (building_id)=(fake-uuid-here) is not present in table "buildings".
```

### Supabase-py: Joined Queries with `select("*, table(columns)")`

Supabase's PostgreSQL client supports PostgREST-style JOIN syntax in the `select()` call:

```python
# Single query that joins buildings with property_types
buildings_resp = (
    db.table("buildings")
    .select("*, property_types(name, icon_type)")  # ← JOIN syntax
    .order("name")
    .execute()
)
```

**What this returns:** Each building record has a nested `property_types` dict:
```json
{
    "id": "uuid",
    "name": "Ocean View Tower",
    "property_type_id": "uuid",
    "property_types": {
        "name": "Residential",
        "icon_type": "apartment"
    }
}
```

**The gotcha:** The nested key is the table name (`property_types`), not the FK column name (`property_type_id`). You extract it like:
```python
pt = building.get("property_types") or {}
property_type_name = pt.get("name")
```

**Why `or {}`?** If `property_type_id` is NULL, `property_types` will be `None` in the response. The `or {}` fallback prevents `NoneType is not subscriptable` errors when you call `.get()` on it.

---

## 3. The N+1 Query Problem (and the 2-Query Solution)

### What is N+1?

N+1 is one of the most common performance bugs in web applications. It happens when you make 1 query to get a list, then N more queries to fetch related data for each item.

**Scenario:** Display all buildings with their unit counts.

**N+1 approach (Wrong):**
```python
# ❌ N+1: 1 query for buildings + N queries for unit counts
buildings = db.table("buildings").select("*").execute().data  # Query 1

for building in buildings:  # N buildings = N more queries
    count = db.table("flats").select("*", count="exact").eq("building_id", building["id"]).execute()
    building["unit_count"] = count.count  # Query 2, 3, 4... N+1
```

If you have 50 buildings, this makes **51 HTTP requests** to your database. At 10ms each, that's 510ms just for the database calls.

**The 2-Query Solution (Correct):**
```python
# ✅ Only 2 queries regardless of how many buildings there are

# Query 1: All buildings
buildings_resp = db.table("buildings").select("*, property_types(name, icon_type)").order("name").execute()

# Query 2: All flats (just the fields we need for counting)
flats_resp = db.table("flats").select("building_id, tenant_uuid").execute()

# Build count maps in Python (pure CPU work, no I/O)
unit_counts: dict[str, int] = {}
occupied_counts: dict[str, int] = {}

for flat in flats_resp.data:
    bid = flat.get("building_id")
    if bid:
        unit_counts[bid] = unit_counts.get(bid, 0) + 1
        if flat.get("tenant_uuid"):
            occupied_counts[bid] = occupied_counts.get(bid, 0) + 1

# Merge counts into buildings
result = []
for b in buildings_resp.data:
    bid = str(b["id"])
    result.append({
        **b,
        "unit_count": unit_counts.get(bid, 0),
        "occupied_count": occupied_counts.get(bid, 0),
    })
```

**Why this is always 2 queries:**
- Query 1 fetches all buildings (1 HTTP request to Supabase)
- Query 2 fetches all flat IDs + tenant_uuids (1 HTTP request)
- The counting logic runs entirely in Python — no database trips

**Performance:** 50 buildings → same 2 queries. 500 buildings → still 2 queries.

**The trade-off:** Query 2 fetches ALL flats, even those not belonging to the queried buildings. For very large datasets (100,000+ units), you'd want to scope the query. But at typical property management scale (< 5,000 units), 2 queries is optimal.

---

## 4. FastAPI BackgroundTasks — Deep Dive

### The Core Problem

When VAPI calls your webhook to create an appointment, it expects a response within a few seconds. If your handler takes 5+ seconds (calling SendGrid, then Twilio, then maybe Supabase for complaint details), VAPI considers the webhook failed and retries — potentially creating duplicate appointments.

**Without BackgroundTasks (Blocking):**
```python
# ❌ BLOCKING — notification happens before response is sent
@router.post("/appointments")
async def create_appointment(data: AppointmentCreate, db: Client = Depends(get_db)):
    # Insert appointment — fast
    result = db.table("appointments").insert(data.dict()).execute()

    # Send SMS to manager — 2-3 seconds (Twilio API call)
    send_sms(manager_phone, "New appointment scheduled")

    # Send email to manager — 1-2 seconds (SendGrid API call)
    send_email(manager_email, "New appointment", email_html)

    return result.data[0]  # Response arrives 3-5 seconds AFTER the above
```

**VAPI sees:** 5-second delay → timeout → retry → duplicate appointment.

**With BackgroundTasks (Non-Blocking):**
```python
# ✅ NON-BLOCKING — response returns immediately, notifications fire after
from fastapi import BackgroundTasks

@router.post("/appointments")
async def create_appointment(
    data: AppointmentCreate,
    background_tasks: BackgroundTasks,  # ← FastAPI injects this
    db: Client = Depends(get_db)
):
    # Insert appointment — fast
    result = db.table("appointments").insert(data.dict()).execute()
    appointment = result.data[0]

    # Queue the notification — does NOT block the response
    background_tasks.add_task(
        notify_manager_appointment_scheduled,  # Function to call
        appointment                             # Argument to pass
    )

    return appointment  # ← Response sent IMMEDIATELY (before notification runs)
    # notify_manager_appointment_scheduled() runs AFTER this response is delivered
```

**VAPI sees:** < 100ms response → success → no retry.

### How BackgroundTasks Actually Works

FastAPI's `BackgroundTasks` is backed by Starlette's background task runner. After the HTTP response is written to the socket, Starlette runs each queued task sequentially in the same process/thread.

**Mental Model:**
```
Request arrives
    ↓
Route handler executes
    ↓
background_tasks.add_task(fn, args...)  ← Just queues it, doesn't run yet
    ↓
Response is serialized and sent to client  ← Client receives response HERE
    ↓
Background tasks run sequentially
    ├── notify_manager_appointment_scheduled(appointment)
    └── (any other tasks queued)
```

### How to Write a Background Task Function

```python
# ✅ Background task rules:
# 1. Regular function (def), not async def — or if async, FastAPI awaits it
# 2. Must never raise exceptions (catch everything, log errors)
# 3. Cannot access request context (request object is gone after response)
# 4. Must be self-contained — create its own DB connection if needed

def notify_manager_appointment_scheduled(appointment: dict) -> None:
    try:
        # Create a new DB connection (the request's db connection may be closed)
        from supabase import create_client
        db = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

        # Do your work...
        flat_number = appointment.get('flat_number')
        # ...fetch complaint, tenant, send SMS, send email...

    except Exception as e:
        # CRITICAL: Never raise — this would crash silently and confuse debugging
        logger.error(f"notify_manager failed: {type(e).__name__} - {str(e)}")
        # log it, but return normally
```

**Why create a new DB connection inside background tasks?**
FastAPI's `Depends(get_db)` creates a connection tied to the request lifecycle. When the request completes and the response is sent, that connection may be closed or returned to the pool. Background tasks run after the request — so they need their own connection.

### The Sync-in-Async Problem (nest_asyncio)

**Scenario:** Your background task function is sync (`def`), but it needs to call an `async` function (like `FeatureService.is_feature_enabled`).

```python
# The background task function is sync
def notify_manager_appointment_scheduled(appointment: dict) -> None:
    # But we need to call this async method:
    is_enabled = await feature_service.is_feature_enabled(flat_id, Feature.SMS_REMINDERS)
    # ❌ ERROR: cannot use 'await' outside an async function
```

**The fix using `asyncio.get_event_loop()`:**
```python
import asyncio

def notify_manager_appointment_scheduled(appointment: dict) -> None:
    # ...
    async def get_feature_flags():
        sms = await feature_service.is_feature_enabled(flat_id, Feature.SMS_REMINDERS)
        email = await feature_service.is_feature_enabled(flat_id, Feature.EMAIL_REMINDERS)
        return sms, email

    # When running as a BackgroundTask inside FastAPI's event loop:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't use loop.run_until_complete() on a running loop!
            # nest_asyncio patches asyncio to allow nested event loops
            import nest_asyncio
            nest_asyncio.apply()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    sms_enabled, email_enabled = loop.run_until_complete(get_feature_flags())
```

**Why is `loop.run_until_complete()` normally forbidden inside an already-running loop?**
Python's asyncio event loop is single-threaded. If you call `run_until_complete()` from within a coroutine that's already running on the loop, you'd be asking the loop to run itself recursively — which would deadlock.

`nest_asyncio` patches asyncio to allow this, specifically for test environments and background tasks in frameworks like FastAPI. It's a pragmatic workaround, not a clean solution.

**The clean solution:** Make the background task itself `async`:
```python
# ✅ Better approach — async background task, no nest_asyncio needed
async def notify_manager_appointment_scheduled(appointment: dict) -> None:
    try:
        sms_enabled = await feature_service.is_feature_enabled(flat_id, Feature.SMS_REMINDERS)
        # ...
    except Exception as e:
        logger.error(...)
```

FastAPI's `BackgroundTasks.add_task()` supports both sync and async functions.

---

## 5. Feature Flags Per Unit

### What Are Feature Flags?

A feature flag is a boolean configuration that can enable or disable a feature without code changes. In this project, each unit (flat) has independent feature toggles stored in the `unit_features` table.

```
unit_features table:
| unit_id | feature_name       | enabled |
|---------|-------------------|---------|
| 1       | SMS_REMINDERS     | true    |
| 1       | EMAIL_REMINDERS   | false   |
| 2       | SMS_REMINDERS     | false   |
| 2       | EMAIL_REMINDERS   | true    |
```

**Why per-unit flags?** Some tenants prefer SMS, others email. Some properties are in demo mode (all notifications off). Feature flags allow granular control without conditional code changes.

### How Notifications Use Feature Flags

```python
# In notify_manager_appointment_scheduled()
sms_enabled = await feature_service.is_feature_enabled(flat_id, Feature.SMS_REMINDERS)
email_enabled = await feature_service.is_feature_enabled(flat_id, Feature.EMAIL_REMINDERS)

if sms_enabled:
    twilio_client.send_sms(to=manager_phone, message=sms_message)
else:
    logger.info(f"SMS notification skipped for flat {flat_number} (feature disabled)")

if email_enabled:
    email_client.send_email(subject=subject, html_content=email_html)
else:
    logger.info(f"Email notification skipped for flat {flat_number} (feature disabled)")
```

**Why log when skipping?** Without the log line, you'd spend hours wondering why no email was sent. The log makes it clear it's intentional (feature disabled), not a bug.

---

## 6. Sending HTML Email with SendGrid

### Why HTML Email (Not Plain Text)?

Plain text emails look unprofessional. HTML emails let you use branding, structured layouts, colored priority badges, and section dividers — all the things that make the notification actually readable at a glance.

### SendGrid Integration Pattern

```python
# backend/app/integrations/email_client.py

import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

class EmailClient:
    def __init__(self):
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@yourapp.com")
        self.to_email = os.getenv("MANAGER_EMAIL", "manager@yourapp.com")

    def send_email(self, subject: str, html_content: str) -> bool:
        """Returns True on success, False on failure. Never raises."""
        try:
            message = Mail(
                from_email=self.from_email,
                to_emails=self.to_email,
                subject=subject,
                html_content=html_content
            )
            sg = SendGridAPIClient(self.api_key)
            response = sg.client.mail.send.post(request_body=message.get())
            return response.status_code in (200, 202)
        except Exception as e:
            logger.error(f"SendGrid failed: {e}")
            return False

def get_email_client() -> EmailClient:
    return EmailClient()
```

**Required environment variables:**
```bash
SENDGRID_API_KEY=SG.xxxxxxxxx
SENDGRID_FROM_EMAIL=noreply@yourapp.com
MANAGER_EMAIL=manager@yourapp.com
```

**Common SendGrid errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `401 Unauthorized` | Wrong or missing API key | Check `SENDGRID_API_KEY` env var |
| `403 Forbidden` | From email not verified | Verify sender domain in SendGrid dashboard |
| `400 Bad Request` | Malformed HTML or invalid email address | Check `to_emails` and `html_content` |
| Email arrives in spam | From domain not authenticated | Set up DKIM/SPF records for your domain |

### HTML Email Template Pattern

The notification email uses inline CSS (no external stylesheets) because many email clients block external CSS:

```python
email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        /* Inline ALL styles — email clients strip external CSS */
        body {{ font-family: Arial, sans-serif; max-width: 650px; }}
        .header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 35px; }}
        .priority-high {{ color: #e74c3c; background: #fee; padding: 4px 12px; border-radius: 4px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>New Appointment: Flat {flat_number}</h1>
    </div>
    <div class="content">
        <p>Date: {formatted_date}</p>
        <p>Priority: <span class="priority-{complaint_priority.lower()}">{complaint_priority.upper()}</span></p>
    </div>
</body>
</html>
"""
```

**Why f-string and double braces `{{}}`?** In Python f-strings, `{` and `}` are special characters that denote interpolation. To include literal CSS braces, you must double them: `{{ }}` → produces `{ }` in the output.

---

## 7. Twilio SMS Integration

### Twilio Integration Pattern

```python
# backend/app/integrations/twilio_client.py

from twilio.rest import Client
import os

class TwilioClient:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_PHONE_NUMBER")

    def send_sms(self, to: str, message: str) -> bool:
        """Returns True on success, False on failure. Never raises."""
        try:
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to
            )
            logger.info(f"SMS sent: SID={msg.sid}")
            return True
        except Exception as e:
            logger.error(f"Twilio send_sms failed: {e}")
            return False

def get_twilio_client() -> TwilioClient:
    return TwilioClient()
```

**Required environment variables:**
```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+15551234567    # Your Twilio number
MANAGER_PHONE=+919998064026          # Where to send manager notifications
```

**Common Twilio errors:**

| Error | Cause | Fix |
|-------|-------|-----|
| `AuthenticationError` | Wrong credentials | Check `ACCOUNT_SID` and `AUTH_TOKEN` |
| `21408 - Permission to send an SMS` | Trial account restricted to verified numbers | Verify recipient number in Twilio console |
| `21610 - Message body is required` | Empty message string | Check `message` parameter |
| `21211 - Invalid 'To' Phone Number` | Bad phone format | Ensure E.164 format: `+1234567890` |

---

## 8. Database Normalization — The Appointments Detachment

### The Bug: Column Does Not Exist

**The 500 error that triggered this refactor:**
```
DETAIL: column "appointment_date" of relation "complaints" does not exist
```

**What happened:** The frontend form for creating a complaint also had an "appointment date" field. The handler naively passed the entire form payload to the complaints table insert:

```python
# ❌ The buggy code
@router.post("/complaints")
async def create_complaint(data: ComplaintCreate, ...):
    # data.dict() includes appointment_date, but complaints table doesn't have that column!
    result = db.table("complaints").insert(data.dict()).execute()
    # ↑ PostgreSQL rejects this: "column appointment_date does not exist"
```

### The Wrong Fix (Patching vs. Root Cause)

**Tempting but wrong:** Just add `appointment_date` as a column to `complaints`.

Why this is wrong:
- A complaint can have **multiple** follow-up appointments (rescheduled, then rescheduled again)
- Adding a single `appointment_date` column to `complaints` violates **First Normal Form (1NF)**: "Each column should contain only a single value"
- If the complaint has 3 appointments, which date do you store?

### The Correct Fix: Separate Table with FK

```python
# ✅ The correct normalized fix

@router.post("/complaints")
async def create_complaint(data: ComplaintCreate, ...):
    complaint_dict = data.dict()

    # 1. Pop appointment_date OUT of the dict BEFORE inserting into complaints
    appointment_date = complaint_dict.pop("appointment_date", None)

    # 2. Insert the complaint (now clean — no appointment_date field)
    result = db.table("complaints").insert(complaint_dict).execute()
    created_complaint = result.data[0]

    # 3. If we had an appointment_date, create a separate appointment record
    if appointment_date:
        db.table("appointments").insert({
            "complaint_uuid": created_complaint["uuid"],  # FK to complaints
            "appointment_date": appointment_date,
            "flat_number": created_complaint["flat_number"],
            "status": "scheduled"
        }).execute()

    return created_complaint
```

**The `dict.pop(key, default)` pattern:**
- `complaint_dict.pop("appointment_date", None)` removes `appointment_date` from the dict AND returns its value
- If the key doesn't exist, returns `None` (the default)
- This is the cleanest way to extract-and-remove a key from a dict in one line

### Normalization Mental Model

| Normalized | Not Normalized |
|-----------|----------------|
| Complaint has one or more Appointments (1:N) | Complaint has `appointment_date` column |
| Each appointment is its own row in `appointments` | Multiple appointments crammed into one row |
| Can add/cancel individual appointments | Must update the complaint row for every change |
| Appointment history preserved | Only current date stored |

---

## 9. Async vs Concurrency vs Background Processing — The Key Distinctions

This is one of the most misunderstood areas in Python web development. Get this right.

### `async def` and `await` — Concurrency (NOT Parallelism)

```python
# async def means: "this function can yield control while waiting for I/O"
async def get_complaints():
    # While waiting for Supabase to respond, Python can handle other requests
    response = await db.table("complaints").select("*").execute()
    return response.data
```

**What happens during `await`:**
1. FastAPI is running on a single-threaded event loop
2. When `await` is hit, the event loop suspends this coroutine
3. The event loop picks up another waiting request/coroutine
4. When the I/O completes (Supabase responds), this coroutine resumes

**Mental Model:** A chef with multiple pots. While one pot boils (I/O wait), the chef stirs another pot. One chef (thread), multiple tasks (coroutines) — this is concurrency.

**This is NOT parallelism:** Parallelism would be multiple chefs (multiple threads/processes). Python's GIL and asyncio event loop both mean: still only one thing executes at a time.

### `BackgroundTasks` — Post-Response Execution

```python
background_tasks.add_task(send_notification, data)
return response  # ← Returned IMMEDIATELY, notification runs AFTER
```

**NOT async in the sense of "during the request"** — BackgroundTasks runs AFTER the response is sent. The client already has their answer; the server is now doing cleanup work.

**Use BackgroundTasks when:**
- Sending notifications (email, SMS) after an action
- Logging analytics events
- Triggering cache invalidation
- Any "fire and forget" side effect

### The Blocking Anti-Pattern

```python
# ❌ BLOCKING — using a synchronous library inside an async handler
import requests  # ← requests is synchronous, will BLOCK the event loop

async def get_data():
    # This blocks the entire event loop while waiting for the HTTP response!
    # No other requests can be handled during this time.
    result = requests.get("https://api.example.com/data")  # ← Blocks!
    return result.json()
```

**Fix:** Use `httpx` with `await` instead of `requests`:
```python
import httpx

async def get_data():
    async with httpx.AsyncClient() as client:
        result = await client.get("https://api.example.com/data")  # ← Non-blocking
    return result.json()
```

---

## 10. Technical Debt: supabase-py HTTP vs Direct Database Connection

### Current Architecture (MVP — supabase-py HTTP)

```
FastAPI App ──HTTP──> Supabase REST API ──TCP──> PostgreSQL
```

Every database operation makes an HTTP request from your backend to Supabase's REST API, which then translates it to a SQL query. Latency: ~10-50ms per query (network + HTTP overhead + REST translation).

### Better Architecture (Production — asyncpg Direct TCP)

```
FastAPI App ──TCP──> PostgreSQL (direct connection)
```

Using `asyncpg` + `SQLAlchemy` with `databases`:
```python
# This connects directly to PostgreSQL over TCP
# Latency: ~1-3ms per query
DATABASE_URL = "postgresql+asyncpg://user:pass@host:5432/dbname"

engine = create_async_engine(DATABASE_URL)
```

### When to Make the Switch

| Factor | Keep supabase-py | Switch to asyncpg |
|--------|-----------------|-------------------|
| Scale | < 100 concurrent users | > 100 concurrent users |
| Query complexity | Simple CRUD | Complex JOINs, CTEs |
| Latency requirements | > 100ms acceptable | < 10ms required |
| Development speed | Faster (less setup) | Slower (more boilerplate) |
| Real-time features | Built-in Supabase realtime | Manual implementation |

**At MVP scale (current project), supabase-py is fine.** The latency overhead is acceptable, and the built-in auth/RLS/storage integration is valuable.

---

## 11. Debugging Production Failures: Follow the Data

### The Systematic Debugging Framework

When a flat doesn't appear under the correct building, don't guess. Follow the data through every layer:

**Step 1: Check what the frontend sent**
```
Open browser → Network tab → Find the POST /flats request
Click it → Request tab → Payload
Did it include building_id?
```

**Step 2: Check what the backend received**
```python
# Add a temporary log in the route handler
print(f"[DEBUG] create_flat received building_id={building_id!r}")
```

**Step 3: Check what reached the database**
```sql
-- In Supabase SQL Editor or psql
SELECT building_id, flat_number, created_at
FROM flats
ORDER BY created_at DESC
LIMIT 5;
```

**Step 4: Check if the frontend is filtering correctly**
```javascript
// In browser console, on the Properties page
console.log("All units:", allUnits);
console.log("Building filter:", selectedBuildingId);
console.log("Filtered:", allUnits.filter(u => u.building_id === selectedBuildingId));
```

**The golden rule:** If you follow the data all the way from click → HTTP request → route handler → DB query → DB record → API response → frontend state → UI render, one of those steps will be wrong. Don't guess which one — verify each.

### The "Column Does Not Exist" 500 Error Pattern

**Symptom:** You add a new field to the frontend form and the backend starts throwing 500 errors.

**Diagnostic process:**
1. Check Render/uvicorn logs for the actual Python traceback
2. Look for: `DETAIL: column "field_name" of relation "table_name" does not exist`
3. This means your Python dict has a key that doesn't exist as a column in the DB table
4. Fix: Either add the column to the DB, or `pop()` the key from the dict before insert

```python
# The universal pattern for safe inserts when payload might have extra keys:
safe_payload = {k: v for k, v in full_payload.items() if k in ALLOWED_COLUMNS}
db.table("tablename").insert(safe_payload).execute()
```

---

## 12. Common Mistakes Checklist

| Mistake | Error/Symptom | Fix |
|---------|------------|-----|
| BackgroundTasks parameter after Query() params | `SyntaxError: parameter without a default follows parameter with a default` | Move `background_tasks: BackgroundTasks` to be the FIRST parameter |
| Not creating new DB connection in background task | `RuntimeError: Session is closed` or stale data | Create new `supabase.create_client()` inside the background function |
| Using `nest_asyncio` without importing it | `ModuleNotFoundError: No module named 'nest_asyncio'` | `pip install nest_asyncio` and add to requirements.txt |
| Missing `SENDGRID_FROM_EMAIL` verification | `403 Forbidden` from SendGrid | Verify sender in SendGrid → Settings → Sender Authentication |
| Twilio trial → unverified numbers | `21408 Error` | Verify recipient number at twilio.com/user/account/verified-numbers |
| Using `requests` in async handler | Event loop blocked, slow responses | Use `httpx.AsyncClient()` with `await` instead |
| N+1 queries for unit counts | Dashboard loads in 5-10+ seconds with many buildings | Use 2-query + Python map approach |
| Not checking `or {}` on joined property_types | `NoneType is not subscriptable` when property_type_id is NULL | `pt = building.get("property_types") or {}` |
| Storing appointment_date in complaints table | `500: column "appointment_date" does not exist` | Use `.pop()` and create separate appointments table record |

---

## 13. Implementation Checklist

### Property Hierarchy
- [ ] Create `properties_list` table in Supabase with UUID PK
- [ ] Create `buildings` table with `property_id UUID REFERENCES properties_list(id)`
- [ ] Add `building_id UUID REFERENCES buildings(id)` to `flats` table
- [ ] Build `GET /property-groups` with 2-query N+1-free pattern
- [ ] Build `GET /buildings` with 2-query N+1-free pattern
- [ ] Build `GET /property-groups/{id}/buildings` scoped to one group
- [ ] Include property_types join: `select("*, property_types(name, icon_type)")`
- [ ] Handle `None` joined object with `or {}` fallback

### Background Notifications
- [ ] Install `sendgrid`, `twilio`, `nest_asyncio` and add to requirements.txt
- [ ] Set all required env vars: `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `MANAGER_EMAIL`, `TWILIO_*`, `MANAGER_PHONE`
- [ ] Write `notify_manager_appointment_scheduled()` as a regular function that creates its own DB connection
- [ ] Wrap the entire function in `try/except Exception` — never raise
- [ ] Add `background_tasks: BackgroundTasks` as the FIRST parameter in routes that use it
- [ ] Test: `time.sleep(10)` inside the notification function, verify the API returns < 100ms

### Database Normalization
- [ ] Create `appointments` table with `complaint_uuid UUID REFERENCES complaints(uuid)`
- [ ] Use `complaint_dict.pop("appointment_date", None)` before insert
- [ ] Create appointment record only if `appointment_date` was provided

### Feature Flags
- [ ] Create `unit_features` table: `unit_id`, `feature_name`, `enabled`
- [ ] Initialize rows for all units on creation
- [ ] Check flags before sending SMS/email in notification service
- [ ] Log when skipping (not just when sending)
