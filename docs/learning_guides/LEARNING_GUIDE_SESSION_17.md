# Learning Guide — Session 17
## Topic: Full-Stack Feature Engineering — Frontend Richness, Notification Architecture, Chatbot Depth, and Database Layer Bugs

> **Audience:** A junior developer or intern who has completed Session 16 and understands the basic project structure, chatbot tool calling, and VAPI design.
> **Goal:** By the end of this guide you should understand (a) how to render rich content in React, (b) how to extract a feature into its own page, (c) how status systems span three layers and can break at any one of them, (d) how Supabase RLS and storage work, (e) how to make notifications fire on every code path, (f) the mindset for building "complete" features rather than happy-path features, and (g) how every layer of the stack works in enough depth to build, debug, and extend any feature in this project independently.

> **This guide also serves as the permanent reference manual for the codebase.** Sections 12–19 are not session-specific — they document the foundational patterns, data model, and debugging approach that apply to all future work.

---

## Table of Contents

**Session-specific (new features built):**
1. [What We Built — Overview](#1-what-we-built)
2. [Rich Text in React — react-markdown](#2-rich-text-in-react)
3. [Extracting a Feature into Its Own Page](#3-extracting-a-feature-into-its-own-page)
4. [The Three-Layer Status System (and How It Breaks)](#4-the-three-layer-status-system)
5. [Supabase Storage, RLS, and the Service Role Key](#5-supabase-storage-rls-and-service-role-key)
6. [Notification Architecture — Firing SMS on Every Code Path](#6-notification-architecture)
7. [Chatbot Tool Design — Depth Patterns](#7-chatbot-tool-design)
8. [Stacked Modals — Drilling from List to Detail](#8-stacked-modals)
9. [Bug Catalogue — What Broke and How We Fixed It](#9-bug-catalogue)
10. [Architecture Intuitions and Senior Dev Mindset](#10-architecture-intuitions)
11. [Quick Reference](#11-quick-reference)

**Permanent reference (foundational knowledge):**
12. [The Data Model — Complete Table Reference](#12-the-data-model)
13. [FastAPI and Pydantic V2 in This Codebase](#13-fastapi-and-pydantic-v2)
14. [Supabase SDK Query Patterns](#14-supabase-sdk-query-patterns)
15. [React Architecture in This Project](#15-react-architecture)
16. [Date and Time Handling](#16-date-and-time-handling)
17. [End-to-End Request Traces](#17-end-to-end-request-traces)
18. [Debugging Playbook](#18-debugging-playbook)
19. [UUID vs Integer ID — Why Both Exist](#19-uuid-vs-integer-id)

---

## 1. What We Built — Overview

This session added significant depth across the whole stack. Here is what changed and why:

| Feature | Where | Why |
|---------|-------|-----|
| Markdown rendering in chatbot | Frontend | LLM outputs markdown syntax; users saw `**bold**` as raw text |
| Tenant lookup by unit number | Chatbot tool | Managers need to find tenants by flat number, not just by name |
| Separate Complaints page | Frontend | Dashboard was crowded; complaints deserve their own view |
| Calendar: opaque tooltip | Frontend | Hover text was invisible on transparent background |
| Calendar: click-to-detail | Frontend | Viewing an event in the side panel gave no way to edit it |
| "Attended" appointment status | Full stack | Three real states exist: scheduled, cancelled, attended |
| Image upload 403 fix | Backend | Storage bucket has RLS — anon key can't write |
| SMS on every appointment event | Backend | SMS was only wired to some code paths, not all |
| Chatbot: cancel/view/complaints | Chatbot | Users couldn't manage appointments or complaints via chat |
| Chatbot: update_appointment_status | Chatbot | No way to mark attended or reactivate via chat |
| Daily tasks KPI: click to detail | Frontend | List modal had no way to open appointment detail |
| Bell icon removed | Frontend | Unused UI element causing visual clutter |

Each of these involves patterns you'll reuse constantly. Let's go deep on each.

---

## 2. Rich Text in React — react-markdown

### The Problem

The AI chatbot backend returns text like this:

```
Here are your appointments:

**Today (2 appointments):**
- ID 14 | Flat 101 | Fix Plumbing Issue
- ID 22 | Flat 305 | Scheduled Visit
```

Without any processing, React renders this as a plain string — the `**` asterisks appear literally on screen. Users see `**Today**` instead of **Today**.

### Why This Happens

React's JSX renders strings as-is. It does not interpret markdown syntax — that is a deliberate security decision. If React silently processed all strings as markdown/HTML, it would be vulnerable to XSS (cross-site scripting) attacks.

### The Fix — react-markdown

Install the package:
```bash
cd frontend
npm install react-markdown
```

Then in `Chatbot.jsx`, render assistant messages through `ReactMarkdown` instead of directly:

```jsx
// Before — raw string, markdown symbols appear literally
<p className="whitespace-pre-wrap">{msg.content}</p>

// After — renders markdown as real HTML elements
import ReactMarkdown from 'react-markdown';

<ReactMarkdown components={{
    p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
    ul: ({ children }) => <ul className="list-disc list-inside space-y-0.5 my-1">{children}</ul>,
    li: ({ children }) => <li className="text-sm">{children}</li>,
    code: ({ children }) => <code className="bg-secondary/60 px-1 rounded text-xs font-mono">{children}</code>,
}}>{msg.content}</ReactMarkdown>
```

The `components` prop lets you override how each markdown element renders. This is where you apply your Tailwind classes — `ReactMarkdown` itself produces unstyled HTML elements.

### Important: Only Apply to Assistant Messages, Not User Messages

User messages are plain text typed by the user. You should NOT render those through `ReactMarkdown` for two reasons:
1. The user's text is not markdown — it would look wrong.
2. It's a minor security precaution — don't process user input through any HTML renderer.

```jsx
{msg.role === 'assistant' ? (
    <ReactMarkdown components={...}>{msg.content}</ReactMarkdown>
) : (
    <span className="whitespace-pre-wrap">{msg.content}</span>
)}
```

### Key Insight

Libraries like `react-markdown` exist specifically to bridge the gap between LLM output (which uses markdown) and React rendering (which doesn't). When you're working with AI features, this bridge is almost always needed. Add it early.

---

## 3. Extracting a Feature into Its Own Page

### The Pattern

The complaints list started inside `BentoDashboard.jsx`. As the app grew, the dashboard became overloaded. The right move was to extract complaints into `ComplaintsPage.jsx` and give it a sidebar link.

This is a very common refactor in growing apps. Here is the mental framework:

**When to extract a feature into its own page:**
1. The feature has its own filters/state that don't belong to the parent
2. The feature is "complete" — it has CRUD operations, not just viewing
3. The parent component is already complex
4. Users navigate to this feature intentionally, not as a side effect of something else

### The Steps

**Step 1: Create the new page component.**

`ComplaintsPage.jsx` receives the same `complaints` and `onComplaintUpdate` props that `BentoDashboard` used to receive, plus its own local state for filters:

```jsx
export default function ComplaintsPage({ complaints, onComplaintUpdate }) {
    const [filters, setFilters] = useState({ status: 'all', priority: 'all' });
    const [selectedComplaint, setSelectedComplaint] = useState(null);

    const filtered = useMemo(() =>
        complaints.filter(c =>
            (filters.status === 'all' || c.status === filters.status) &&
            (filters.priority === 'all' || c.priority === filters.priority)
        ), [complaints, filters]
    );
    // ...
}
```

**Step 2: Add the route in App.jsx.**

This project uses a `currentView` string (not React Router) to control which page is shown:

```jsx
{currentView === 'complaints' && (
    <ComplaintsPage
        complaints={complaints}
        onComplaintUpdate={handleComplaintUpdate}
    />
)}
```

**Step 3: Add the sidebar nav item.**

```jsx
{ id: 'complaints', icon: ClipboardList, label: 'Complaints' }
```

**Step 4: Remove from BentoDashboard.**

Delete the complaints section from `BentoDashboard.jsx` — the card list, filters, and related state. Leave the KPI count cards (they're summary analytics, appropriate for a dashboard).

### What to Keep vs What to Extract

The dashboard keeps:
- **KPI cards** (total, pending, in progress, daily tasks) — summary numbers belong on dashboards
- **Charts** (trends, donut, pie) — analytics overview belongs on dashboards

The complaints page takes:
- **The full list** with filters — operational views belong on dedicated pages
- **The detail modal** — editing belongs with the list

### The View-Based Routing Pattern

This project does not use React Router. Instead:

```jsx
// App.jsx
const [currentView, setCurrentView] = useState('dashboard');

// Sidebar passes setCurrentView via onNavigate
<Sidebar onNavigate={setCurrentView} currentView={currentView} />

// Main content area
{currentView === 'dashboard' && <BentoDashboard ... />}
{currentView === 'complaints' && <ComplaintsPage ... />}
{currentView === 'calendar' && <CalendarView ... />}
```

**Why not React Router?** For small apps with a fixed sidebar navigation, view-based routing is simpler. React Router adds complexity (URL management, history, lazy loading) that isn't needed until the app has public-facing pages or needs deep-linking.

---

## 4. The Three-Layer Status System (and How It Breaks)

### Understanding the Three Layers

Every status value in this app exists in THREE places, and all three must agree:

```
Layer 1: Database CHECK constraint  (PostgreSQL, lives in Supabase)
Layer 2: Pydantic Enum             (Python, lives in schemas/appointment.py)
Layer 3: Frontend constants        (JavaScript, lives in constants/status.js)
```

When you add a new status value, you MUST update all three. If any one of them is missing the new value, things break — but the error messages are very different depending on which layer is missing.

### Adding "attended" — What Happened

When we added the "attended" status:

1. ✅ `AppointmentStatus` enum in `schemas/appointment.py` had `ATTENDED = "attended"`
2. ✅ `APPOINTMENT_STATUS` in `constants/status.js` had `ATTENDED: 'attended'`
3. ❌ The PostgreSQL `appointments_status_check` constraint did NOT include `'attended'`

**What the user saw:**
```
INFO: "PATCH /appointments/30 HTTP/1.1" 500 Internal Server Error
```

A 500. No further explanation in the browser.

**Why is it a 500?**

When the frontend sends `PATCH /appointments/30` with `{ "status": "attended" }`:
1. FastAPI validates the request → passes (Pydantic enum accepts "attended")
2. Backend executes `db.table("appointments").update({"status": "attended"}).eq("id", 30).execute()`
3. Supabase sends this to PostgreSQL
4. PostgreSQL checks the constraint: `status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')`
5. "attended" is NOT in that list → PostgreSQL raises a constraint violation error
6. Supabase SDK propagates this as a Python exception
7. FastAPI catches an unhandled exception → returns HTTP 500

**The deceptive part:** Pydantic happily accepted "attended" — it looked valid all the way through to the DB. The failure was invisible until the DB rejected it.

### Diagnosing Which Layer is Missing

When you see a 500 on a status update, check in this order:

**Check Layer 2 first (Pydantic — easiest):**
```python
# schemas/appointment.py
class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    ATTENDED = "attended"   # ← is it here?
```

**Check Layer 3 (Frontend — second easiest):**
```javascript
// constants/status.js
export const APPOINTMENT_STATUS = {
    SCHEDULED: 'scheduled',
    ATTENDED: 'attended',   // ← is it here?
};
```

**Check Layer 1 (Database — requires running a query):**
```sql
-- Run this in Supabase SQL Editor
SELECT conname, consrc
FROM pg_constraint
WHERE conname LIKE '%appointment%';
```

Or just check the existing constraint by attempting to insert a test value and seeing the error.

### The Fix — Migration SQL

You cannot just "edit" a CHECK constraint — you have to drop it and recreate it:

```sql
-- File: backend/migrations/009_add_attended_status.sql
ALTER TABLE appointments
    DROP CONSTRAINT IF EXISTS appointments_status_check;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_status_check
    CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'attended'));
```

**Always save migrations as numbered SQL files** in `backend/migrations/`. This gives you:
- A history of every schema change
- Something to run on a fresh database to reproduce the schema
- Documentation for teammates

### Lesson: The Three-Layer Rule

> **Every time you add a new enum value anywhere in the stack, immediately update all three layers. Commit them together in the same git commit.**

If you add it to Pydantic but forget the DB constraint, you'll get a 500.
If you add it to the DB but forget the frontend, the UI won't show it or will show wrong styles.
If you add it to the frontend but forget Pydantic, the API will reject it with a 422.

The three layers are deliberately independent — that's good architecture. But independence means you must keep them in sync manually.

---

## 5. Supabase Storage, RLS, and the Service Role Key

### The Error

When a user uploaded a cover photo for a building, the server returned:

```json
{
    "statusCode": 403,
    "error": "Unauthorized",
    "message": "new row violates row-level security policy"
}
```

HTTP 403 Unauthorized. Upload failed.

### What is RLS?

**Row Level Security (RLS)** is a PostgreSQL feature that Supabase uses to control who can access which rows/objects. In Supabase:

- Every table and storage bucket can have RLS enabled
- When RLS is on, operations are rejected by default unless a matching policy exists
- Policies can be specific: "allow INSERT only if `auth.uid()` = `user_id`"

### Two Supabase Keys — What They Mean

Supabase gives you two API keys:

| Key | Name | What it can do |
|-----|------|----------------|
| `anon` key | Public / anonymous | Only what RLS policies explicitly allow |
| `service_role` key | Admin | Bypasses all RLS — full access |

The backend was using the `anon` key (`SUPABASE_KEY`) for everything. This is correct for database table reads/writes — RLS policies there are set up appropriately.

**But storage buckets have their own RLS.** The "Property Pics" bucket had RLS enabled with no INSERT policy for the anon role. So any upload attempt via the anon key was rejected.

### Why You Can't Just Disable RLS on Storage

RLS exists for security. Disabling it would allow anyone with the URL to upload files to your bucket. Don't disable it — use the service role key for storage operations instead.

### The Fix Pattern — Dual Client

```python
# backend/app/routes/upload.py
from supabase import create_client
from app.config import settings

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    db: Client = Depends(get_db)  # anon key — for DB table operations
):
    # Use service role key for storage operations only
    svc_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY  # fallback to anon
    storage_client = create_client(settings.SUPABASE_URL, svc_key)

    # All storage operations use storage_client (service role)
    response = storage_client.storage.from_("Property Pics").upload(path, file_bytes)

    # All DB table operations still use db (anon key via Depends)
    db.table("buildings").update({"cover_url": public_url}).eq("id", building_id).execute()
```

**Two clients. One purpose each.**

### Config Setup

```python
# backend/app/config.py
class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")           # anon key
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")  # service role key
```

```bash
# .env — add this line
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Find your service role key in: Supabase Dashboard → Project Settings → API → `service_role` (secret).

### Fallback Safety

```python
svc_key = settings.SUPABASE_SERVICE_KEY or settings.SUPABASE_KEY
```

If `SUPABASE_SERVICE_KEY` is not set in `.env`, it falls back to the anon key. This means the code won't crash with a missing-config error — it will fail gracefully with a 403 (same as before the fix), which is better than a startup crash.

### The Trailing Slash Warning

While debugging this, there was also a log warning:
```
WARNING: Storage endpoint URL should have a trailing slash
```

This is a **red herring** — it's a cosmetic warning from the Supabase SDK's URL normalizer. The Supabase client already handles it internally (`session.py` appends the slash). It was NOT the cause of the 403.

**Senior dev skill:** Learn to distinguish error messages from warning messages. A warning does not cause a failure. Always find the actual error — in this case, the `new row violates row-level security policy` message in the 403 body was the real clue.

### Key Mental Model

```
anon key → "what a logged-out user can do"   → appropriate for public read access
service_role key → "what an admin can do"     → appropriate for server-side writes
```

Your backend IS a server-side admin. For administrative operations (file uploads, bulk operations), use the service role key. For user-facing data operations, use the anon key so RLS policies remain active.

---

## 6. Notification Architecture — Firing SMS on Every Code Path

### The Problem

Appointments can be created, rescheduled, and cancelled through three different entry points:

```
┌──────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Calendar UI    │    │  VAPI (Voice)   │    │    Chatbot      │
│  (React + REST)  │    │  (Phone calls)  │    │ (AI assistant)  │
└────────┬─────────┘    └────────┬────────┘    └────────┬────────┘
         │                       │                      │
         ▼                       ▼                      ▼
  PATCH /appointments/  PATCH /appointments/   execute_tool() in
  {id}   (standard)     update  (VAPI)         chatbot.py
  DELETE /appointments/ PATCH /appointments/
  {id}                  cancel  (VAPI)
```

**Before this session:** SMS notifications were wired to some paths but not others. The chatbot's `cancel_appointment` and `reschedule_appointment` tools updated the DB but never sent any SMS. The `PATCH /appointments/{id}` endpoint sent SMS for date changes but not for status changes.

**Result:** Tenants only received SMS sometimes. Whether they got notified depended on which entry point was used — completely inconsistent.

### Auditing All Code Paths

When a feature must fire "no matter how an action is triggered," the first step is to **map every code path that performs that action**:

```
Appointment created:
  → POST /appointments ✅ (had SMS)

Appointment rescheduled:
  → PATCH /appointments/update (VAPI) ✅ (had SMS)
  → PATCH /appointments/{id} (standard) ✅ (had SMS — for date field only)
  → chatbot execute_tool("reschedule_appointment") ❌ (NO SMS)

Appointment cancelled:
  → PATCH /appointments/cancel (VAPI) ✅ (had SMS)
  → DELETE /appointments/{id} (standard) ✅ (had SMS)
  → chatbot execute_tool("cancel_appointment") ❌ (NO SMS)

Status changed to attended:
  → PATCH /appointments/{id} ❌ (date-only trigger — status changes missed)
  → chatbot execute_tool("update_appointment_status") ❌ (new tool, no SMS yet)
```

Once you have the map, the missing pieces are obvious.

### How notify_tenant_appointment() Works

The notification function is in `backend/app/services/notifications.py`:

```python
def notify_tenant_appointment(
    flat_uuid: str,
    event: str,     # "created" | "rescheduled" | "cancelled" | "attended" | "reactivated"
    flat_number: str,
    db: Client,
    new_date: Optional[str] = None,
) -> None:
    # 1. Look up tenant by flat_uuid
    tenant_resp = db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).maybe_single().execute()

    # 2. Build message based on event
    if event == "cancelled":
        message = f"Hi {name}, your appointment for flat {flat_number} has been cancelled."
    elif event == "attended":
        message = f"Hi {name}, your appointment for flat {flat_number} has been marked as attended."
    # ... etc

    # 3. Send SMS via Twilio
    get_twilio_client().send_sms(to=phone, message=message)
```

**It's a synchronous function** — it runs immediately when called. When called from FastAPI route handlers, it's wrapped in `background_tasks.add_task()` so the HTTP response goes out immediately and the SMS sends in the background. When called directly from the chatbot's `execute_tool()`, it runs synchronously (which is fine — the chatbot is already in a blocking context).

### Fix 1 — PATCH /{id}: Trigger SMS on Status Changes

The `update_appointment` endpoint was only checking `"appointment_date" in update_data`. It missed status changes:

```python
# BEFORE — only date changes triggered SMS
if "appointment_date" in update_data:
    background_tasks.add_task(notify_tenant_appointment, str(flat_uuid), "rescheduled", ...)

# AFTER — both date and status changes trigger SMS
if "appointment_date" in update_data and flat_uuid:
    background_tasks.add_task(notify_tenant_appointment, str(flat_uuid), "rescheduled", ...)

if "status" in update_data and flat_uuid:
    _status_event_map = {
        "cancelled":  "cancelled",
        "attended":   "attended",
        "scheduled":  "reactivated",   # cancelled → scheduled = reactivated
    }
    event = _status_event_map.get(update_data["status"])
    if event:
        background_tasks.add_task(notify_tenant_appointment, str(flat_uuid), event, ...)
```

The event map is a lookup table from DB status value to SMS event name. `"scheduled"` maps to `"reactivated"` because when you change an appointment FROM cancelled back TO scheduled, it's conceptually a reactivation — the message should say "reactivated" not "status updated to scheduled."

### Fix 2 — Chatbot Tools: Direct notify_tenant_appointment() Calls

The chatbot's `execute_tool()` is a regular Python function. You can import and call `notify_tenant_appointment()` directly from it — no background task needed:

```python
# chatbot.py — at the top
from app.services.notifications import notify_tenant_appointment

# Inside execute_tool(), after cancel_appointment DB update:
flat_uuid = apt.get("flat_uuid")
if flat_uuid:
    notify_tenant_appointment(str(flat_uuid), "cancelled", apt.get("flat_number", ""), db)
```

One import. One line. Done. But remember to also fetch `flat_uuid` in your DB query:

```python
# BEFORE — flat_uuid was not fetched
fetch = db.table("appointments").select("id, status, flat_number").eq("id", appointment_id).execute()

# AFTER — fetch flat_uuid so we can send SMS
fetch = db.table("appointments").select("id, status, flat_number, flat_uuid").eq("id", appointment_id).execute()
```

This is a common mistake — you fix the logic but forget to also fetch the data you need. Always trace through what data your new logic requires and ensure the DB query selects it.

### Adding New Events to the Notification Function

When you add a new status ("attended", "reactivated"), you also need to add corresponding message templates in `notify_tenant_appointment()`:

```python
elif event == "attended":
    message = (
        f"Hi {tenant_name}, your maintenance appointment for flat "
        f"{flat_number} has been marked as attended. Thank you!"
    )
elif event == "reactivated":
    message = (
        f"Hi {tenant_name}, your maintenance appointment for flat "
        f"{flat_number} has been reactivated and is now scheduled."
    )
```

The function has an `else` branch that logs a warning for unknown event names. If you forget to add a new event here, the notification is silently skipped with a log warning — not an error. That's the correct behavior (notifications should never crash the app) but it means you must watch the logs to notice it.

### The Background Task Pattern in FastAPI

```python
@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    background_tasks: BackgroundTasks,      # ← inject this
    db: Client = Depends(get_db)
):
    # ... do the DB update

    # This schedules SMS to send AFTER the HTTP response goes out
    background_tasks.add_task(
        notify_tenant_appointment,    # the function to call
        str(flat_uuid),               # arg 1
        "cancelled",                  # arg 2
        flat_number_val,              # arg 3
        db,                          # arg 4 — Supabase client
    )

    return updated  # ← HTTP response goes out NOW, before SMS sends
```

**Why background tasks?** SMS sending takes ~200-500ms. If you await it synchronously, the user's click takes half a second extra to respond. Background tasks decouple the response time from the notification time.

**Important:** The `db` client is passed as an argument to the background task. The task will run in the same request lifecycle, so the DB connection is still valid when it executes.

---

## 7. Chatbot Tool Design — Depth Patterns

### Pattern 1: One Tool, Two Modes

`get_appointment_details` does two things:

```python
# Mode 1: fetch a specific appointment by ID
# Mode 2: list all appointments for a flat

{
    "name": "get_appointment_details",
    "parameters": {
        "appointment_id": { "type": "integer" },  # optional
        "flat_number":    { "type": "string" },   # optional
        "required": []  # ← neither is required; LLM provides what it has
    }
}
```

Inside `execute_tool()`:

```python
elif tool_name == "get_appointment_details":
    appointment_id = args.get("appointment_id")
    flat_number = args.get("flat_number")

    if not appointment_id and not flat_number:
        return "Please provide either an appointment ID or a flat number."

    if appointment_id:
        # single appointment lookup
    else:
        # flat-number list lookup
```

**When to use this pattern:** When two operations are conceptually "get appointment info" from the user's perspective. If you split them into two tools, the LLM must choose between them — introducing a choice that adds complexity. One tool with two modes is cleaner when the difference is just "how specific is the lookup."

**When NOT to use this pattern:** When the operations are genuinely different actions (e.g., "get details" vs "cancel" are different enough to deserve separate tools).

### Pattern 2: Status Update Tool with Event Map

The `update_appointment_status` tool demonstrates the event map pattern:

```python
elif tool_name == "update_appointment_status":
    new_status = args.get("new_status", "").lower().strip()

    # 1. Validate against allowed values
    valid_statuses = {"scheduled", "attended", "cancelled"}
    if new_status not in valid_statuses:
        return f"Invalid status '{new_status}'. Valid options: scheduled, attended, cancelled."

    # 2. Guard against no-op
    current_status = apt.get("status", "")
    if current_status == new_status:
        return f"Appointment {appointment_id} is already '{new_status}'."

    # 3. Update DB
    db.table("appointments").update({"status": new_status}).eq("id", appointment_id).execute()

    # 4. Map status → notification event
    _event_map = {"cancelled": "cancelled", "attended": "attended", "scheduled": "reactivated"}
    event = _event_map.get(new_status)
    if flat_uuid and event:
        notify_tenant_appointment(str(flat_uuid), event, flat_number, db)

    return f"Status updated from '{current_status}' to '{new_status}'."
```

Notice the **no-op guard** — if the appointment is already in the requested status, return early rather than updating (which would send a duplicate SMS). This is important for idempotency.

### Pattern 3: Importing notify_tenant_appointment in chatbot.py

The chatbot module is inside `app/ai/`. The notification service is inside `app/services/`. The import:

```python
from app.services.notifications import notify_tenant_appointment
```

This works because the project runs with `backend/` as the root (uvicorn is started from `backend/`), so `app` is on the Python path. The circular import risk doesn't apply here — `notifications.py` doesn't import anything from `ai/chatbot.py`.

**Always think about import direction:** Can A import B without B also importing A? If yes, the import is safe. If it creates a circular chain, you need to restructure.

### Updating the System Prompt When Tools Change

Every time you add a new tool, update the first line of the system prompt:

```python
# BEFORE
"You can add/delete properties, ...check or reschedule appointments."

# AFTER (added cancel, view details, complaints, status update)
"You can add/delete properties, ...retrieve tenant/building/property/unit/appointment/complaint details, and check, reschedule, or cancel appointments."
```

**Why this matters:** The LLM uses the system prompt description to understand its own capabilities. If you add a `cancel_appointment` tool but the prompt says nothing about cancelling, the LLM may be uncertain about using it — or may tell the user "I can't cancel appointments" even though the tool exists.

---

## 8. Stacked Modals — Drilling from List to Detail

### The Pattern

The Daily Tasks KPI card shows a list of today's appointments. The user wants to click one appointment in that list and open the `AppointmentDetailModal` for it. This is "stacked modals" — a modal that opens another modal.

The implementation requires:

1. **State in the list modal** to track which item is selected
2. **Rendering the detail modal** outside or on top of the list modal
3. **Passing handlers** so the detail modal can update/delete

### Step 1: Propagate Handlers Down

The handlers (`onAppointmentUpdate`, `onAppointmentDelete`) live in `App.jsx`. The chain:

```
App.jsx (has handlers)
  └── BentoDashboard.jsx (passes through)
        └── DailyTasksModal.jsx (uses them)
              └── AppointmentDetailModal.jsx (receives them)
```

Each component in the chain must accept and forward the handlers:

```jsx
// App.jsx
<BentoDashboard
    onAppointmentUpdate={handleAppointmentUpdate}
    onAppointmentDelete={handleAppointmentDelete}
/>

// BentoDashboard.jsx — signature and forwarding
function BentoDashboard({ ..., onAppointmentUpdate, onAppointmentDelete }) {
    return <DailyTasksModal
        onAppointmentUpdate={onAppointmentUpdate}
        onAppointmentDelete={onAppointmentDelete}
    />;
}

// DailyTasksModal.jsx — uses them
function DailyTasksModal({ ..., onAppointmentUpdate, onAppointmentDelete }) {
    const [selectedAppointment, setSelectedAppointment] = useState(null);
    // ...
}
```

If you forget to add a prop to any component in the chain, the handler won't reach the bottom and clicks will silently do nothing.

### Step 2: Making List Items Clickable

Change the appointment card `<div>` to a `<button>`:

```jsx
// BEFORE — inert div
<div className="flex items-start gap-3 p-3 rounded-lg bg-secondary/50 border border-border">

// AFTER — clickable button with hover state
<button
    key={appt.id}
    onClick={() => setSelectedAppointment(appt)}
    className="w-full text-left flex items-start gap-3 p-3 rounded-lg
               bg-secondary/50 border border-border
               hover:bg-secondary hover:border-primary/30 transition-colors cursor-pointer"
>
```

Key details:
- `w-full text-left` — buttons are `inline` by default; make it block and left-aligned to look like a card
- `hover:bg-secondary hover:border-primary/30` — visual affordance that it's clickable
- `cursor-pointer` — the hand cursor confirms interactivity

### Step 3: Rendering the Detail Modal Outside the List Modal

The detail modal must appear ABOVE the list modal in the stacking context. This is achieved by rendering it as a sibling, not a child:

```jsx
// DailyTasksModal.jsx
return (
    <>
        {/* The list modal */}
        <div className="fixed inset-0 bg-black/60 ... z-50">
            ...appointment list...
        </div>

        {/* The detail modal — rendered as sibling, appears on top naturally */}
        <AnimatePresence>
            {selectedAppointment && (
                <AppointmentDetailModal
                    appointment={selectedAppointment}
                    isOpen={true}
                    onClose={() => setSelectedAppointment(null)}
                    onUpdate={handleUpdate}
                    onDelete={handleDelete}
                />
            )}
        </AnimatePresence>
    </>
);
```

Since both are `fixed` with `z-50`, the detail modal renders on top because it appears later in the DOM. This is simpler than trying to manage z-index manually.

### Step 4: Optimistic Local Updates

When the user changes a status in the detail modal, the list modal underneath should also reflect the change. Handle this in the wrapper:

```jsx
const handleUpdate = async (id, updates) => {
    if (onAppointmentUpdate) await onAppointmentUpdate(id, updates);
    // update the selected appointment locally so the detail modal reflects the change
    setSelectedAppointment(prev => prev ? { ...prev, ...updates } : prev);
};
```

This is an **optimistic update** — you update the local state immediately without waiting for a server refetch. If the API call fails, you'd revert it. In this case the `AppointmentDetailModal` already handles reversion on error, so the optimistic update here makes the UI feel responsive.

---

## 9. Bug Catalogue — What Broke and How We Fixed It

### Bug 1: Image Upload Returns 403

**Symptom:**
```json
{ "statusCode": 403, "error": "Unauthorized",
  "message": "new row violates row-level security policy" }
```

**Diagnosis:** The error message says "row-level security policy." This is always a Supabase RLS issue. Check which key is being used for the failing operation.

**Root cause:** Backend uses the anon key. Storage bucket "Property Pics" has RLS enabled. Anon key has no INSERT policy on the bucket.

**Fix:** Use the service role key for storage operations. Create a second Supabase client with `SUPABASE_SERVICE_KEY` and use it only for `storage.from_(bucket).upload(...)` calls.

**What NOT to do:** Don't disable RLS on the bucket. Don't use the service role key everywhere. Scope it narrowly to storage operations only.

---

### Bug 2: PATCH Appointment Status Returns 500

**Symptom:** `PATCH /appointments/30` with `{ "status": "attended" }` returns HTTP 500.

**Diagnosis:** FastAPI returns 500 when an unhandled Python exception occurs in a route handler. The most common causes are: DB query error, Pydantic validation failure on the response, or missing data.

Since the frontend was sending a valid status ("attended" is in the `AppointmentStatus` enum in Pydantic), the Pydantic layer accepted it. The failure must be deeper.

**Suspected causes (ranked by likelihood):**
1. DB CHECK constraint doesn't include "attended" → most likely
2. Response serialization fails (e.g., `uuid` field is null for old records)

**How to confirm:** Run the SQL directly in Supabase SQL Editor:
```sql
UPDATE appointments SET status = 'attended' WHERE id = 30;
```

If this also fails with a constraint violation error → confirmed, it's the CHECK constraint.

**Fix:** Migration SQL to drop and recreate the constraint including "attended":
```sql
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS appointments_status_check;
ALTER TABLE appointments ADD CONSTRAINT appointments_status_check
    CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'attended'));
```

---

### Bug 3: Status Styles Not Applying in DailyTasksModal

**Symptom:** Appointment cards in the Daily Tasks modal show no colored status badge — just a grey fallback.

**Root cause:** The `STATUS_STYLES` object used capitalized keys:
```javascript
// WRONG — keys are capitalized
const STATUS_STYLES = {
    Scheduled: 'bg-blue-500/10 text-blue-500',
    Cancelled:  'bg-red-500/10 text-red-500',
};
// appt.status from DB = "scheduled" (lowercase) → lookup returns undefined → fallback style
```

The database stores statuses in lowercase (`"scheduled"`, `"cancelled"`). The JavaScript lookup `STATUS_STYLES[appt.status]` was case-sensitive. "Scheduled" ≠ "scheduled".

**Fix:**
```javascript
// CORRECT — keys match what the DB actually returns
const STATUS_STYLES = {
    scheduled: 'bg-blue-500/10 text-blue-500',
    attended:  'bg-purple-500/10 text-purple-500',
    cancelled: 'bg-red-500/10 text-red-500',
};
```

**Lesson:** Object lookups in JavaScript are case-sensitive. Your lookup keys must exactly match the string values you're looking up. When values come from a DB, always check what format they're stored in.

---

### Bug 4: Chatbot Sends No SMS After Cancel/Reschedule

**Symptom:** Tenant does not receive SMS when an appointment is cancelled via chatbot, but does receive it when cancelled via the calendar UI.

**Root cause:** The chatbot's `execute_tool()` for `cancel_appointment` and `reschedule_appointment` performed the DB update but never called `notify_tenant_appointment()`. The SMS path was simply not wired in.

Additionally, the `select()` query in those tools only fetched `"id, status, flat_number"` — it didn't include `"flat_uuid"`, which `notify_tenant_appointment()` requires to look up the tenant.

**Fix:**
1. Add `from app.services.notifications import notify_tenant_appointment` at the top of `chatbot.py`
2. In the `select()` call, add `flat_uuid` to the fetched columns
3. After the DB update, call `notify_tenant_appointment(str(flat_uuid), event, flat_number, db)`

**Lesson:** When you add a new notification path to existing tools, always check what data those tools currently fetch. You need to audit the `select()` call and add any missing columns.

---

### Bug 5: Calendar Events Had Transparent Tooltip Background

**Symptom:** On the calendar, hovering over a date shows a tooltip/popup, but the text is hard to read because the popup has a transparent or semi-transparent background.

**Root cause:** The tooltip was using the CSS class `bg-popover`. In the app's dark theme, `bg-popover` was defined with transparency or as `transparent`. The intent was to use an opaque surface color.

**Fix:** Replace `bg-popover` with `bg-card`:
```jsx
// BEFORE
className="... bg-popover ..."

// AFTER
className="... bg-card ..."
```

`bg-card` is the project's opaque card surface color. `bg-popover` was meant for a different context. Lesson: always check what a CSS variable actually resolves to in your theme before using it — open DevTools and inspect the computed background.

---

## 10. Architecture Intuitions and Senior Dev Mindset

### Intuition 1: "Where is this feature allowed to live?"

Every new feature needs a home. Before writing a single line of code, ask:

- Is this a **display only** feature? → A component
- Is this a **page** that users navigate to? → A new view in App.jsx + sidebar link
- Is this a **modal** that appears on top of something? → A component rendered conditionally
- Is this a **background process**? → FastAPI background task or notification service
- Is this a **database change**? → SQL migration file

Getting this classification wrong creates technical debt. A "page" that lives inside a parent component's state becomes impossible to navigate to directly. A "background process" that's synchronous blocks the HTTP response.

### Intuition 2: "What are all the code paths?"

This is the most important habit for building complete features. Before implementing, draw the full map:

```
Action: "appointment status changes"
  Path 1: Calendar modal PATCH /appointments/{id}
  Path 2: VAPI phone call PATCH /appointments/cancel
  Path 3: Chatbot execute_tool("cancel_appointment")
  Path 4: Chatbot execute_tool("update_appointment_status")
```

Now audit: "Does my feature fire on ALL of these paths?" If not, you have a partial implementation. A notification that fires on 3 out of 4 paths is wrong — the user who uses path 4 gets a degraded experience.

**This is the biggest gap between junior and senior developers.** Juniors implement the happy path. Seniors implement all paths.

### Intuition 3: "What are the three layers?"

For any data field that has constrained values (a status, a category, a role):

```
Layer 1: DB CHECK constraint   — what PostgreSQL enforces
Layer 2: Pydantic enum         — what the API enforces
Layer 3: Frontend constants    — what the UI displays
```

A change to one layer that doesn't touch the others will silently break in production. Build the habit of checking all three every time.

### Intuition 4: "Who owns this operation?"

When a backend operation needs elevated access (like storage writes), ask: who is the right actor?

- A **logged-in user** uploading their own avatar → use their session token
- A **backend server** uploading files on behalf of any user → use the service role key

Backend services performing server-side operations are administrators. Use admin credentials for those operations. Don't confuse "backend code" (which has full access) with "user-facing code" (which should be appropriately restricted).

### Intuition 5: "Where does the notification logic belong?"

The `notify_tenant_appointment()` function is in `app/services/notifications.py`, not in the route handler or the chatbot. This is correct — it's a **service**.

**Why not in the route handler?**
The route handler handles HTTP concerns (request parsing, response formatting). Notification logic is business logic. Mixing them makes each harder to test and reason about.

**Why not in the chatbot?**
The chatbot is also a consumer of the notification service, not its owner. Multiple consumers (route handlers, chatbot) should all use the same service — not each have their own notification code.

**The mental model for services:** A service is a reusable piece of business logic with no HTTP concerns. Any part of the codebase can import and call it. This is why importing `notify_tenant_appointment` into `chatbot.py` was the right move — the chatbot is just another consumer.

### Intuition 6: "Is this a cosmetic change or a behavioral change?"

When removing the bell icon from the TopBar:

```jsx
// Remove the import (prevents dead code)
import { RefreshCw } from 'lucide-react';  // Bell removed

// Remove the JSX
// Notification Button — DELETED
```

Always remove both the import and the usage. An unused import is dead code — it still loads the module, wastes bundle space, and confuses future readers who see an import with no usage.

For cosmetic changes like this, the test is: "Did anything break after removing it?" If no — the feature was truly unused and can be safely deleted.

### Intuition 7: "What data do I need to fetch?"

Before writing any DB query, mentally list what the code will do with the result:

```
cancel_appointment needs:
  - apt["status"]     → to check if already cancelled
  - apt["flat_number"] → for the return message
  - apt["flat_uuid"]   → NEW: for the SMS notification
```

Every field that downstream code reads must be in the `select()`. Missing a field means `.get("flat_uuid")` returns `None` silently — no error, just no SMS. This class of bug is especially hard to notice because the code doesn't crash.

**Practice:** Before writing `db.table(...).select(...).execute()`, write the code that consumes the result first (or pseudocode it). Then work backwards to figure out what the select needs.

---

## 11. Quick Reference

### The Three-Layer Status Rule

| Layer | File | What to update |
|-------|------|----------------|
| Database | Supabase SQL Editor | DROP + recreate CHECK constraint |
| Backend | `schemas/appointment.py` | Add to `AppointmentStatus` enum |
| Frontend | `constants/status.js` | Add to `APPOINTMENT_STATUS` and `APPOINTMENT_STATUS_CONFIG` |

Always update all three in the same code change. Save the SQL as a migration file.

---

### Supabase Key Decision Tree

```
Do I need to read from a DB table?
  → Use anon key (db from Depends(get_db))

Do I need to write to a DB table?
  → Use anon key (RLS policies handle write access)

Do I need to upload a file to storage?
  → Use service role key (create separate client)

Do I need to bypass RLS entirely?
  → Use service role key (admin operations only)
```

---

### Notification Coverage Checklist

Before shipping a feature that triggers notifications, audit every code path:

```
For action X, find all entry points:
  □ Standard REST endpoint (calendar/UI)
  □ VAPI endpoint (voice calls)
  □ Chatbot tool (AI assistant)
  □ Any future entry points

For each entry point:
  □ Is notify_tenant_appointment() called?
  □ Is flat_uuid fetched in the select()?
  □ Is the correct event string used?
  □ Is the event string handled in notify_tenant_appointment()?
```

---

### SMS Event Reference

| DB status change | Event passed to notify_tenant_appointment |
|-----------------|------------------------------------------|
| Created new appointment | `"created"` |
| Changed `appointment_date` | `"rescheduled"` |
| Status → `"cancelled"` | `"cancelled"` |
| Status → `"attended"` | `"attended"` |
| Status → `"scheduled"` (from cancelled) | `"reactivated"` |

---

### Stacked Modal Checklist

```
To add "click card to open detail modal" to a list modal:
  □ Add selectedItem state to list modal
  □ Change item div → button with onClick={() => setSelectedItem(item)}
  □ Add hover styles to the button (hover:bg, hover:border, cursor-pointer)
  □ Render detail modal as sibling (not child) using Fragment <>
  □ Wrap detail modal in AnimatePresence for smooth entry/exit
  □ Pass onUpdate and onDelete handlers through the component chain
  □ Add optimistic local state update in the wrapper handler
```

---

### Common Mistakes and Their Symptoms

| Mistake | Symptom | Layer |
|---------|---------|-------|
| New status not in DB CHECK constraint | HTTP 500 on status update | DB |
| New status not in Pydantic enum | HTTP 422 Unprocessable Entity | API |
| New status not in frontend constants | Grey fallback styling, no label | UI |
| Anon key used for storage upload | HTTP 403 Unauthorized, RLS violation | Storage |
| `flat_uuid` not in chatbot select() | SMS never sends (no error) | Chatbot |
| Object keys capitalized but DB values are lowercase | Lookup returns undefined → fallback styling | UI |
| Notification imported as module but called directly without background_task | SMS blocks HTTP response by ~300ms | Performance |
| Missing prop in component chain | Handler arrives as undefined at bottom | React |
| `import { Bell }` not removed after deleting Bell JSX | Dead code in bundle | Frontend |

---

### Mindset Summary

> **Build complete features, not happy-path features.**
>
> A feature is "complete" when it:
> - Works across ALL code paths (UI, VAPI, chatbot, direct API)
> - Is consistent across ALL layers (DB, API, frontend)
> - Handles edge cases (already-cancelled, no tenant phone, missing flat_uuid)
> - Cleans up after itself (removes unused imports, updates all related files)
>
> Ask yourself after every feature: "What would break if someone used this in a way I didn't test?"

---

*Session content written March 19, 2026. Reference sections (12–19) are permanent.*

---

## 12. The Data Model — Complete Table Reference

Understanding the data model is prerequisite to everything else. Every query, every tool, every modal — they all read or write one of these tables.

### The Hierarchy

```
properties_list
    └── buildings          (property_id FK)
            └── flats      (building_id FK)
                    └── tenants   (flat_uuid FK — linked by UUID, not int ID)
```

Appointments and complaints are linked to flats — not to tenants directly:

```
flats ←── appointments    (flat_uuid FK + flat_number denorm)
flats ←── complaints      (flat_number — string match, not UUID FK)
appointments ←── complaints  (complaint_uuid FK — optional link)
```

### Table: `flats`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Auto-increment primary key |
| `uuid` | uuid | New-style unique identifier |
| `flat_number` | text | Human-readable, e.g. `"101"`, `"A-205"` — used in most queries |
| `building_id` | int | FK → buildings.id |
| `address` | text | Optional full address |
| `tenant_uuid` | uuid | FK → tenants.uuid (null if vacant) |
| `occupied` | bool | True if a tenant is currently assigned |

**Key pattern:** Most lookups use `flat_number` (human-readable) rather than `id` or `uuid`. Use `.ilike("flat_number", normalized)` because callers might type "101" or "A 101" or "a-101".

### Table: `tenants`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Auto-increment |
| `uuid` | uuid | Unique identifier |
| `name` | text | Full name |
| `phone` | text | E.164 format, e.g. `"+919876543210"` — used for SMS |
| `email` | text | Optional |
| `flat_uuid` | uuid | FK → flats.uuid (which flat they live in) |
| `lease_start` | date | Optional |
| `lease_end` | date | Optional |

**Key pattern:** To find a tenant for a flat, use `flat_uuid`:
```python
db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).maybe_single().execute()
```

### Table: `appointments`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Auto-increment |
| `uuid` | uuid | Unique identifier |
| `flat_number` | text | Denormalized copy of the flat number |
| `flat_uuid` | uuid | FK → flats.uuid — **required for SMS** |
| `appointment_date` | text | `"YYYY-MM-DDTHH:MM:SS"` — stored as string with T separator |
| `status` | text | One of: `scheduled`, `attended`, `cancelled`, `completed` |
| `notes` | text | Optional freeform notes |
| `complaint_id` | int | FK → complaints.id (legacy integer link) |
| `complaint_uuid` | uuid | FK → complaints.uuid (preferred UUID link) |

**Critical:** `flat_uuid` must be stored at creation time. Without it, you cannot send tenant SMS notifications. Check that any code path creating appointments sets this field.

### Table: `complaints`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Auto-increment |
| `uuid` | uuid | Unique identifier |
| `flat_number` | text | String match (no UUID FK) |
| `category` | text | e.g. `"Plumbing"`, `"Electrical"` |
| `description` | text | Freeform |
| `priority` | text | `"high"`, `"medium"`, `"low"` |
| `status` | text | `"pending"`, `"in-progress"`, `"resolved"` |
| `tenant_name` | text | Denormalized copy of tenant name at creation time |
| `created_at` | timestamptz | Auto-set by DB |

**Key pattern:** Complaints link to flats via `flat_number` (string), not a UUID FK. This means you filter with `.ilike("flat_number", flat_number)` — same normalization as elsewhere.

### Table: `buildings`

| Column | Type | Notes |
|--------|------|-------|
| `id` | int | Auto-increment |
| `uuid` | uuid | Unique identifier |
| `name` | text | e.g. `"Block A"` |
| `address` | text | Optional |
| `property_id` | uuid | FK → properties_list.id (optional link to property group) |
| `cover_url` | text | Public URL of cover photo in Supabase Storage |

### Table: `properties_list`

| Column | Type | Notes |
|--------|------|-------|
| `id` | uuid | UUID primary key (not int — this table uses UUID as PK) |
| `name` | text | Property name |
| `address` | text | Optional |
| `description` | text | Optional |

### Relationship Summary

```
To find a tenant's phone for a flat:
  flats.uuid → tenants.flat_uuid → tenants.phone

To find a building for a flat:
  flats.building_id → buildings.id

To find complaints for a flat:
  complaints.flat_number == flats.flat_number (ilike match)

To find appointments for a flat:
  appointments.flat_uuid == flats.uuid
  OR appointments.flat_number == flats.flat_number (ilike)

To find the complaint linked to an appointment:
  appointments.complaint_uuid → complaints.uuid
```

---

## 13. FastAPI and Pydantic V2 in This Codebase

### How Routes Are Structured

Every route file follows this pattern:

```python
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from supabase import Client
from app.db.session import get_db

router = APIRouter(prefix="/appointments", tags=["Appointments"])

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,   # request body — Pydantic validates this
    background_tasks: BackgroundTasks,     # inject background task runner
    db: Client = Depends(get_db)           # inject DB client
):
    ...
```

**`prefix="/appointments"`** — every route in this file gets this prefix. `@router.post("")` becomes `POST /appointments`. `@router.get("/{id}")` becomes `GET /appointments/{id}`.

**`response_model=AppointmentResponse`** — FastAPI validates the return value against this Pydantic schema before sending the response. If your return value has extra fields, they're stripped. If it's missing required fields, FastAPI raises a 500.

**`status_code=status.HTTP_201_CREATED`** — the HTTP status code for success. Defaults to 200 if omitted.

### Dependency Injection — `Depends(get_db)`

```python
# app/db/session.py
from supabase import create_client, Client
from app.config import settings

def get_db():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
```

`Depends(get_db)` tells FastAPI: "call `get_db()` and inject the result as the `db` parameter." This means:
- Every request gets a fresh Supabase client
- You never import `get_db` in chatbot.py or service files — only route handlers use `Depends`
- You pass `db` explicitly to any helper function that needs it: `execute_tool(tool_name, args, db)`

**Why not just `db = create_client(...)` at the top of each route?**
`Depends` is testable — in tests you can override the dependency with a mock client. It also handles cleanup (if `get_db` were a generator with `yield`, FastAPI would run the cleanup after the response).

### Pydantic V2 — What You Need to Know

**`model_dump(exclude_unset=True, mode='json')`**

Used in the PATCH endpoint:
```python
update_data = appointment_data.model_dump(exclude_unset=True, mode='json')
```

- `exclude_unset=True` — only includes fields the caller actually sent. If the PATCH body is `{"status": "attended"}`, update_data is `{"status": "attended"}` — not `{"status": "attended", "notes": null, "appointment_date": null}`.
- `mode='json'` — serializes Python types to JSON-compatible types. An `AppointmentStatus` enum value like `AppointmentStatus.ATTENDED` becomes the string `"attended"` rather than the Python enum object. This is what the Supabase SDK expects.

**`ConfigDict(from_attributes=True)`**

```python
class AppointmentResponse(AppointmentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

Tells Pydantic: "you can construct this model from an object's attributes, not just a dict." Needed when FastAPI returns ORM objects. In this project where Supabase returns plain dicts, it's harmless but keeps backward compat.

**`Optional[str] = None` vs `str`**

```python
class AppointmentUpdate(BaseModel):
    appointment_date: Optional[str] = None   # not required in PATCH
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    appointment_date: str = Field(...)   # REQUIRED in POST — no default
```

`Optional[X] = None` means "this field can be absent from the request." `str = Field(...)` means "this field is required." Get this wrong and you'll either reject valid requests (422 error) or allow invalid ones (null values in DB).

### HTTP Status Codes Used in This Project

| Code | Meaning | When this project uses it |
|------|---------|--------------------------|
| `200 OK` | Success | GET, PATCH returns |
| `201 Created` | Resource created | POST /appointments, POST /complaints |
| `204 No Content` | Success, no body | DELETE operations |
| `400 Bad Request` | Client sent invalid data | Business logic rejections ("already cancelled") |
| `404 Not Found` | Resource doesn't exist | `SELECT` returned empty |
| `422 Unprocessable Entity` | Pydantic validation failed | Wrong field type, missing required field |
| `500 Internal Server Error` | Unhandled Python exception | DB constraint violation, missing field, etc. |

**VAPI exception:** VAPI endpoints always return `200` even for "errors" — they use a boolean `exists` field instead. This is a deliberate design for voice AI compatibility.

### Background Tasks

```python
@router.patch("/{id}")
async def update_appointment(
    background_tasks: BackgroundTasks,
    db: Client = Depends(get_db)
):
    # ... do the DB update, get `updated` dict back

    background_tasks.add_task(
        notify_tenant_appointment,   # function to call
        str(flat_uuid),              # positional args...
        "attended",
        flat_number_val,
        db,
    )

    return updated   # ← HTTP response sent NOW
    # notify_tenant_appointment() runs AFTER this, in the background
```

`BackgroundTasks.add_task(fn, *args)` schedules `fn(*args)` to run after the response is sent. The DB connection `db` is valid for the duration of the background task because it's within the same request lifecycle.

**Warning:** background tasks still run in the same process/thread. They are NOT async workers — they block the event loop while running. For truly heavy operations, use a task queue (Celery, Redis). For SMS sending (~200ms), background tasks are appropriate.

---

## 14. Supabase SDK Query Patterns

This is the API you'll use for every DB operation. Memorize these patterns.

### Basic Select

```python
# Get all rows
result = db.table("buildings").select("*").execute()
rows = result.data   # list of dicts, empty list if no rows

# Get specific columns
result = db.table("buildings").select("id, name, address").execute()

# Get single row by PK
result = db.table("appointments").select("*").eq("id", 30).execute()
row = result.data[0] if result.data else None

# Get single row with .maybe_single() — returns dict or None, never raises
result = db.table("tenants").select("name, phone").eq("flat_uuid", uuid).maybe_single().execute()
tenant = result.data  # dict or None — no need for .data[0]
```

### Filters

```python
# Exact match (case-sensitive)
.eq("status", "scheduled")

# Case-insensitive match — USE THIS for user-supplied strings
.ilike("flat_number", "A-101")           # exact ilike
.ilike("name", f"%{user_input}%")        # contains match

# Comparisons
.gte("appointment_date", "2026-03-01")   # >=
.lte("appointment_date", "2026-03-31")   # <=
.gt("appointment_date", window_start)    # >
.lt("appointment_date", window_end)      # <

# Not equal
.neq("status", "cancelled")

# Chaining filters (AND logic)
.eq("status", "scheduled").gte("appointment_date", today)
```

### Insert

```python
result = db.table("buildings").insert({
    "name": "Block A",
    "address": "123 Main St",
    "property_id": some_uuid,
}).execute()

if result.data:
    new_id = result.data[0]["id"]
```

**Always check `result.data`** after insert. If the insert fails (constraint violation, duplicate key), `result.data` will be empty and an exception may be raised. Wrap in `try/except`.

### Update

```python
result = db.table("appointments")\
    .update({"status": "attended", "notes": "Completed on time"})\
    .eq("id", 30)\
    .execute()

updated_row = result.data[0] if result.data else None
```

`.update()` returns the updated rows. If the `.eq()` matches nothing, `result.data` is empty — not an error, just no rows matched.

### Delete

```python
result = db.table("buildings").delete().eq("id", building_id).execute()
# result.data contains the deleted rows
```

### Order and Limit

```python
.order("appointment_date", desc=True)   # newest first
.order("created_at")                    # oldest first (default asc)
.limit(10)                              # first 10 rows only
```

### Joins (Foreign Key Select)

Supabase allows you to fetch related table data in one query using foreign key names:

```python
# Get appointments with linked complaint data
result = db.table("appointments")\
    .select("*, complaints!fk_appointments_complaint_uuid(category, description, priority)")\
    .execute()

# Each row in result.data will have a "complaints" key with the linked complaint dict
for apt in result.data:
    complaint_data = apt.get("complaints")  # dict or None
    if complaint_data:
        category = complaint_data.get("category")
```

The `!fk_appointments_complaint_uuid` syntax tells Supabase which foreign key to use when there are multiple relationships between two tables. When there's only one FK, you can just use the table name: `.select("*, complaints(category)")`.

### Error Handling Pattern

```python
try:
    result = db.table("appointments").update({"status": "attended"}).eq("id", 30).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return result.data[0]
except HTTPException:
    raise   # let FastAPI handle it
except Exception as e:
    raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
```

**Always re-raise `HTTPException`** before the generic `except Exception` — otherwise your deliberate 404s get swallowed and become 500s.

### `.maybe_single()` vs `.execute()` with `[0]`

| Approach | Use when | Behavior on empty |
|----------|----------|-------------------|
| `.maybe_single().execute()` | Expecting 0 or 1 row | Returns `None` in `.data` — no exception |
| `.execute()` then `data[0]` | Expecting at least 1 row | `IndexError` if empty — wrap in `if result.data` |

Use `.maybe_single()` for lookups where "not found" is a valid expected outcome (e.g., finding a tenant — the flat might be vacant). Use the `[0]` pattern when you've already validated the row exists.

---

## 15. React Architecture in This Project

### The Component Tree

```
App.jsx
├── Sidebar.jsx           — navigation, sets currentView
├── TopBar.jsx            — refresh button, theme toggle
├── main content area
│   ├── BentoDashboard.jsx (currentView === 'dashboard')
│   │   ├── KPICard.jsx (×4)
│   │   ├── TrendsChart.jsx
│   │   ├── StatusDonut.jsx
│   │   ├── CategoriesPie.jsx
│   │   ├── AppointmentsBar.jsx
│   │   ├── DashboardListModal.jsx   (complaint detail)
│   │   └── DailyTasksModal.jsx      (today's appointments)
│   │       └── AppointmentDetailModal.jsx
│   ├── ComplaintsPage.jsx (currentView === 'complaints')
│   │   └── ComplaintModal.jsx
│   ├── CalendarView.jsx (currentView === 'calendar')
│   │   ├── AppointmentDetailModal.jsx
│   │   └── ComplaintModal.jsx
│   ├── PropertiesPage.jsx (currentView === 'properties')
│   ├── TenantManagement.jsx (currentView === 'tenants')
│   └── SettingsPage.jsx (currentView === 'settings')
└── Chatbot.jsx           — fixed position, always visible
```

### View-Based Routing (No React Router)

The app uses a single `currentView` state in `App.jsx` instead of React Router:

```jsx
// App.jsx
const [currentView, setCurrentView] = useState('dashboard');

// Sidebar navigation
<Sidebar currentView={currentView} onNavigate={setCurrentView} />

// Conditional rendering
{currentView === 'dashboard' && <BentoDashboard ... />}
{currentView === 'complaints' && <ComplaintsPage ... />}
```

**Why not React Router?** This is an internal management dashboard — no public URLs, no browser back button needed, no deep linking. React Router would add meaningful complexity with no benefit for this use case.

**Trade-off:** You can't bookmark a specific view. If that's ever needed, migrating to React Router is the right call.

### State Management — Where Data Lives

```
App.jsx owns:
  - complaints[]          — loaded from API, passed down as props
  - appointments[]        — loaded from API, passed down as props
  - handleComplaintUpdate — PATCH complaint, refreshes list
  - handleAppointmentUpdate — PATCH appointment, refreshes list
  - handleAppointmentDelete — DELETE appointment, refreshes list

Components own:
  - their own UI state (modal open/closed, selected item, filters)
  - they do NOT own data — they receive it as props
```

This is "lifting state up." All shared data lives at the root (`App.jsx`) so any component can access it. Components that modify data call handler functions passed down as props.

```jsx
// App.jsx
const handleAppointmentUpdate = async (id, updates) => {
    await updateAppointment(id, updates);  // apiService call
    await loadAppointments();              // reload from server
    window.dispatchEvent(new Event('refresh-appointments'));
};

// CalendarView receives the handler
<CalendarView
    appointments={appointments}
    onAppointmentUpdate={handleAppointmentUpdate}
/>
```

### Data Fetching Pattern

```jsx
// App.jsx
const [appointments, setAppointments] = useState([]);

const loadAppointments = useCallback(async () => {
    try {
        const data = await getAppointments();
        setAppointments(data);
    } catch (err) {
        console.error('Failed to load appointments:', err);
    }
}, []);

useEffect(() => {
    loadAppointments();
    // Listen for refresh signals from chatbot or other components
    window.addEventListener('refresh-appointments', loadAppointments);
    return () => window.removeEventListener('refresh-appointments', loadAppointments);
}, [loadAppointments]);
```

### `useMemo` for Derived Data

```jsx
// WRONG — recalculates on every render
const todayAppointments = appointments.filter(a => isToday(parseISO(a.appointment_date)));

// CORRECT — only recalculates when appointments changes
const todayAppointments = useMemo(
    () => appointments.filter(a => {
        try { return isToday(parseISO(a.appointment_date)); }
        catch { return false; }
    }),
    [appointments]
);
```

Use `useMemo` for any expensive calculation that depends on props or state. The `try/catch` is important — an appointment with a null or malformed date would crash without it.

### The `useRef` Pattern for Outside-Click Detection

```jsx
const dropdownRef = useRef(null);

useEffect(() => {
    const handleClickOutside = (e) => {
        if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
            setDropdownOpen(false);
        }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
}, []);

// In JSX:
<div ref={dropdownRef}>
    {/* dropdown content */}
</div>
```

Used in `AppointmentDetailModal` for the status dropdown. The cleanup `return () => removeEventListener(...)` is critical — without it, every render adds another listener and you get a memory leak.

### `AnimatePresence` for Enter/Exit Animations

```jsx
import { AnimatePresence, motion } from 'framer-motion';

<AnimatePresence>
    {isOpen && (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
        >
            {/* modal content */}
        </motion.div>
    )}
</AnimatePresence>
```

Without `AnimatePresence`, the `exit` animation never runs because React removes the element from the DOM immediately on condition becoming false. `AnimatePresence` keeps the element mounted until the `exit` animation completes.

### The `apiService.js` Rule

**Every single HTTP call goes through `frontend/src/services/apiService.js`.** No exceptions. No inline `fetch()` inside components.

```javascript
// apiService.js
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function updateAppointment(id, updates) {
    const response = await fetch(`${API_BASE_URL}/appointments/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(`Update failed: ${response.status}`);
    return await response.json();
}
```

**Why this matters:** If the backend URL changes (dev → staging → production), you change `API_BASE_URL` in one place. If you need to add auth headers, you add them in one place. If you need to add error logging, one place. Scattered inline fetches make all of this impossible to maintain.

### Status Constants — Single Source of Truth

```javascript
// constants/status.js — THE ONLY place these strings are defined
export const APPOINTMENT_STATUS = {
    SCHEDULED: 'scheduled',
    CANCELLED: 'cancelled',
    ATTENDED:  'attended',
};

export const APPOINTMENT_STATUS_CONFIG = {
    [APPOINTMENT_STATUS.SCHEDULED]: {
        label: 'Scheduled',
        bg: 'bg-blue-500/10',
        text: 'text-blue-400',
        border: 'border-blue-500/30',
    },
    // ...
};
```

Components import these constants instead of using raw strings:

```jsx
// WRONG — raw string, typo-prone
if (appointment.status === 'Scheduled') { ... }

// CORRECT — constant, catches typos at import time
import { APPOINTMENT_STATUS } from '../constants/status';
if (appointment.status === APPOINTMENT_STATUS.SCHEDULED) { ... }
```

---

## 16. Date and Time Handling

Date handling is where the most subtle bugs live in this project. Read this section carefully.

### The T Separator Rule

The frontend uses `date-fns` `parseISO()` to parse dates:

```javascript
import { parseISO, format, isToday } from 'date-fns';

parseISO("2026-03-19T14:30:00")   // ✅ valid — T separator
parseISO("2026-03-19 14:30:00")   // ❌ Invalid Date — space separator
```

`parseISO` is strict about ISO 8601 format. The T separator is mandatory.

**Rule: all dates in this project must be stored and returned with the T separator.** When the chatbot stores a rescheduled date, it uses `parsed.strftime("%Y-%m-%dT%H:%M:%S")`. When VAPI stores a date, it normalizes the space to T before saving.

### Where the Space Separator Creeps In

```python
# VAPI endpoint receives "2026-03-19 14:30:00" (space) from voice agent
# Must normalize before storing:
normalized_date = new_appointment_date.replace("T", " ")   # WRONG — this converts T→space
normalized_date = new_appointment_date.strip()             # Right idea, but incomplete
```

The VAPI update endpoint intentionally uses a space internally (PostgreSQL accepts both), but the chatbot must use T because the frontend `parseISO` requires it. This inconsistency exists because VAPI endpoints were written before the T-separator rule was established. If you modify VAPI endpoints, keep the space (they work); if you write new endpoints, use T.

### Backend Date Parsing

```python
# Parse a date string that might have T or space
from datetime import datetime

datetime.fromisoformat("2026-03-19T14:30:00")   # ✅
datetime.fromisoformat("2026-03-19 14:30:00")   # ✅ (Python accepts both)

# For flexible parsing from LLM output ("March 25 at 3pm", "tomorrow 10am"):
from dateutil import parser as dateparser
parsed = dateparser.parse("March 25 at 3pm")
normalized = parsed.strftime("%Y-%m-%dT%H:%M:%S")   # → "2026-03-25T15:00:00"
```

`dateutil.parser.parse()` is used in the chatbot's `reschedule_appointment` tool because LLMs output dates in natural language, not ISO format.

### IST Timezone

The project stores dates in IST (India Standard Time = UTC+5:30):

```python
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
current_time = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")
```

Supabase stores timestamps as `timestamptz` (with timezone) but the app treats all dates as IST. There is no UTC conversion in the frontend — `parseISO("2026-03-19T14:30:00")` is treated as local time.

**If you ever see times off by 5.5 hours** in the UI, it's a timezone issue — the browser is interpreting an IST timestamp as UTC and displaying the converted time. Fix by ensuring the backend always provides T-separated strings without a `+05:30` suffix (which triggers UTC conversion in `parseISO`).

### Frontend Date Display

```javascript
import { format, parseISO, isToday, subDays } from 'date-fns';

// Display formats used in this project
format(parseISO(date), 'EEEE, MMMM d, yyyy')  // "Wednesday, March 19, 2026"
format(parseISO(date), 'h:mm a')               // "2:30 PM"
format(parseISO(date), 'EEEE, MMMM d')         // "Wednesday, March 19"
format(today, 'MMMM yyyy')                     // "March 2026" (calendar header)

// Filtering
isToday(parseISO(appointment.appointment_date))          // for daily tasks
new Date(complaint.created_at) >= subDays(new Date(), 7) // last 7 days
```

Always wrap `parseISO` in a `try/catch` when iterating over DB data — a null or malformed date will throw and crash the whole component.

---

## 17. End-to-End Request Traces

Following a complete operation through the stack. Read these to understand how all the pieces connect.

### Trace 1: User Changes Appointment Status to "Attended" via Calendar Modal

```
1. User clicks the status dropdown in AppointmentDetailModal
   → handleStatusChange("attended") called

2. handleStatusChange calls onUpdate(appointment.id, { status: "attended" })
   → this is handleAppointmentUpdate in App.jsx

3. App.jsx calls updateAppointment(id, { status: "attended" }) from apiService.js
   → fetch("PATCH /appointments/30", body: {"status":"attended"})

4. FastAPI receives PATCH /appointments/30
   → AppointmentUpdate pydantic model validates: status "attended" is in enum ✅
   → update_data = {"status": "attended"}

5. Backend runs: db.table("appointments").update({"status":"attended"}).eq("id",30).execute()
   → PostgreSQL checks appointments_status_check constraint
   → "attended" IS in constraint ✅ (after migration 009)
   → Row updated, response.data[0] = full updated row

6. Backend checks "status" in update_data → True
   → event_map["attended"] → "attended"
   → background_tasks.add_task(notify_tenant_appointment, flat_uuid, "attended", flat_number, db)

7. FastAPI returns HTTP 200 with updated appointment dict

8. Background task runs:
   → looks up tenant by flat_uuid
   → gets phone number
   → builds message: "Hi [name], your appointment has been marked as attended."
   → calls twilio_client.send_sms(to=phone, message=message)
   → SMS delivered to tenant's phone

9. apiService returns response JSON
   → App.jsx calls loadAppointments() — re-fetches all appointments from /appointments
   → appointments state updates → all components re-render with new data

10. AppointmentDetailModal: useEffect sees appointment.status changed
    → setCurrentStatus("attended")
    → status badge updates to purple "Attended"
```

### Trace 2: Chatbot Cancels an Appointment

```
1. User types: "Cancel appointment 30"
   → Chatbot.jsx calls sendChatMessage([...messages, {role:"user", content:"Cancel..."}])
   → fetch("POST /chat", body: {messages: [...]})

2. FastAPI POST /chat route
   → validates request, calls chatbot.run_chat(messages, db)

3. run_chat() loop iteration 1:
   → builds system prompt with today's date
   → calls OpenAI gpt-4o-mini with messages + TOOLS schema
   → LLM responds: tool_call for "cancel_appointment" with args {appointment_id: 30}

4. execute_tool("cancel_appointment", {appointment_id: 30}, db)
   → SELECT id, status, flat_number, flat_uuid WHERE id=30
   → apt.status is "scheduled" — not already cancelled
   → UPDATE appointments SET status="cancelled" WHERE id=30
   → flat_uuid found → notify_tenant_appointment(flat_uuid, "cancelled", flat_number, db)
       → looks up tenant, sends SMS: "Hi [name], your appointment has been cancelled."
   → returns "Appointment 30 for flat 101 has been cancelled."

5. Tool result appended to messages as {role:"tool", content:"Appointment 30...cancelled."}

6. run_chat() loop iteration 2:
   → calls OpenAI with updated messages (including tool result)
   → LLM has no more tool calls to make
   → LLM responds: "Appointment #30 for flat 101 has been successfully cancelled."

7. run_chat() returns the string to POST /chat route
   → returns {"reply": "Appointment #30...cancelled."}

8. Chatbot.jsx receives reply
   → adds assistant message to chat
   → dispatches window.dispatchEvent(new Event('refresh-appointments'))

9. App.jsx hears 'refresh-appointments'
   → calls loadAppointments()
   → appointments state refreshes, calendar re-renders
```

### Trace 3: VAPI Voice Agent Creates an Appointment

```
1. Tenant calls the Vapi phone number
   → Vapi voice agent starts, calls POST /flats/verify-phone
   → Backend verifies flat exists, returns {exists: true, tenant_name: "...", ...}

2. Voice agent completes intake, confirms appointment details with tenant
   → Vapi calls POST /appointments (standard create endpoint)
   → body: {flat_number, flat_uuid, appointment_date, complaint_uuid, status: "scheduled"}

3. FastAPI POST /appointments
   → AppointmentCreate validated by Pydantic
   → DB insert into appointments table
   → response.data[0] = new appointment row

4. Background tasks added:
   → notify_manager_appointment_scheduled(appointment) — checks feature flags, sends SMS+email to manager
   → notify_tenant_appointment(flat_uuid, "created", flat_number, db) — SMS to tenant

5. HTTP 201 returned to Vapi
   → Voice agent confirms appointment to tenant: "Your appointment is booked for [date]"
```

---

## 18. Debugging Playbook

When something breaks, use this systematic approach. Never guess — trace.

### HTTP 500 Internal Server Error

A 500 means an unhandled Python exception occurred in a FastAPI route handler.

**Step 1: Read the server logs.** Run the backend with `--reload` and look at the terminal:
```
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "...", line 123, in update_appointment
    updated = response.data[0]
IndexError: list index out of range
```

The traceback tells you the exact file, line, and exception type. This is always where you start.

**Step 2: Reproduce with curl.** Isolate the failure to the backend:
```bash
curl -s -X PATCH http://127.0.0.1:8000/appointments/30 \
  -H "Content-Type: application/json" \
  -d '{"status": "attended"}'
```

If it fails here, the problem is in the backend, not the frontend.

**Step 3: Common 500 causes:**
- `IndexError: list index out of range` → `result.data[0]` when `.data` is empty — the row wasn't found or wasn't updated
- `KeyError: 'uuid'` → the DB response doesn't have a field you're accessing with `["uuid"]`
- `AttributeError: 'NoneType'` → called a method on `None` — a `.maybe_single()` returned `None` and you didn't check
- DB constraint violation → Pydantic accepted the value but PostgreSQL rejected it (check the constraint)

### HTTP 422 Unprocessable Entity

Pydantic validation failed. The request body doesn't match the schema.

```json
{
  "detail": [
    {
      "type": "enum",
      "loc": ["body", "status"],
      "msg": "Input should be 'scheduled', 'cancelled', 'attended' or 'completed'",
      "input": "done"
    }
  ]
}
```

The `detail` array tells you exactly which field failed and why. Fix the request to match what the schema expects.

### HTTP 403 Forbidden

Almost always a Supabase RLS issue.

1. Check the error body — it will say "row-level security policy" if it's RLS
2. Identify which operation failed (INSERT, SELECT, UPDATE, DELETE)
3. Check which Supabase client was used for that operation (anon key or service role)
4. Storage operations need service role. DB table writes use anon key but need matching RLS policies

### SMS Not Sending (Silent Failure)

SMS errors are caught and logged, never raised. Check logs for:
```
ERROR: notify_tenant_appointment failed: TwilioRestException - ...
WARNING: notify_tenant_appointment: no tenant for flat_uuid=...
WARNING: notify_tenant_appointment: tenant has no phone (flat_uuid=...)
```

**Checklist:**
1. Is `flat_uuid` being passed? Add a `print(flat_uuid)` before the call
2. Does the tenant record have a `phone` field?
3. Is the phone in E.164 format? (`+919876543210` not `9876543210`)
4. Is `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` set in `.env`?
5. Is the destination number verified in Twilio (if on trial account)?

### Calendar Not Refreshing After Chatbot Action

The chatbot dispatches a refresh event, but `App.jsx` must be listening:

```javascript
// App.jsx — must have this
useEffect(() => {
    window.addEventListener('refresh-appointments', loadAppointments);
    return () => window.removeEventListener('refresh-appointments', loadAppointments);
}, [loadAppointments]);
```

If the calendar isn't refreshing: open DevTools → Console → check if the event is dispatched (add `console.log` in `Chatbot.jsx` after the dispatch). If dispatched but not received, check that App.jsx has the listener.

### UI Shows No Data / Wrong Data

1. Open DevTools → Network tab → find the API request → check Response
2. If the API returns empty `[]`, the problem is in the backend query
3. If the API returns data but UI is wrong, the problem is in how the component processes the data (check `useMemo` dependencies, `filter` logic, prop names)
4. Check if `useMemo` has stale dependencies — if you added a new filter variable, add it to the dependency array

### LLM Claims Success But Nothing Changed in DB

This is the hallucinated-success failure mode (see Session 16 Bug 7).

1. Check server logs — if the tool was called, you'll see the DB operation in the logs
2. Call `execute_tool()` directly in Python to test it without the LLM (see Session 16 commands section)
3. Check if the tool has a missing `required` field that's blocking the call silently
4. Add a CRITICAL rule to the system prompt: "Never claim success without tool confirmation"

### "Could not find import" in VS Code (Linter Errors)

```
Import "fastapi" could not be resolved
Import "supabase" could not be resolved
```

These are **false positives** — the linter can't see the virtual environment. The code runs correctly. To fix the linter (optional): select your Python interpreter in VS Code (Ctrl+Shift+P → "Python: Select Interpreter" → choose the `.venv` one).

---

## 19. UUID vs Integer ID — Why Both Exist

Almost every table in this project has both:

```sql
id    INT  PRIMARY KEY  -- auto-increment integer
uuid  UUID DEFAULT gen_random_uuid()  -- universally unique identifier
```

### Why Integer IDs?

- **Simple, sequential, human-readable.** Appointment #30 is easy to say in conversation.
- **Fast joins.** Integer equality is faster than UUID equality in PostgreSQL.
- **Used in all original API endpoints** — the first version of the project used only integer IDs.

### Why UUIDs?

- **Non-guessable.** Integer IDs expose information: if you have appointment #30, you know there are at least 30 appointments. UUIDs reveal nothing.
- **Safe for external exposure.** VAPI and external callers receive UUIDs in responses.
- **Globally unique.** UUIDs are unique across all tables and systems — useful when events from different sources need to be correlated.
- **Relationships between tables.** The `flat_uuid → tenants.flat_uuid` link uses UUIDs because flat → tenant is a one-to-one relationship that was added after the initial integer-ID schema.

### When to Use Which in This Project

| Use integer `id` | Use UUID |
|-----------------|---------|
| Chatbot references ("appointment #30") | Inter-table foreign keys (flat_uuid, complaint_uuid) |
| Internal route params (`/appointments/30`) | External API responses to VAPI |
| Direct DB queries where you know the int | Anywhere the ID might be exposed publicly |
| Logs and debug messages | notification functions (flat_uuid for tenant lookup) |

**The critical one:** `notify_tenant_appointment()` takes `flat_uuid` (UUID), not `flat_id` (int). Always fetch `flat_uuid` from the appointments table when you need to send SMS.

### How the Transition Happened

The project originally used integer IDs everywhere. As it grew, UUIDs were added for security and cross-system linking (migration files `001_add_uuid_columns.sql` through `004_fix_all_uuid_relationships.sql`). This is why both exist — the integer IDs couldn't be removed without breaking existing queries, so both were kept.

**Practical rule:** When writing new code, prefer UUID foreign keys for inter-table links. Keep integer IDs for user-facing references (appointment numbers in chat, route params).
