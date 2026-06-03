# Plan: Complaint Agent → Manager Callback Scheduling

**Problem:** Two bugs + one product direction change.  
**Root cause bug:** `manager_id` missing from voice-created appointment inserts → RLS hides them.  
**Product change:** Agent stops booking maintenance visit appointments; instead schedules a manager **callback call** to the tenant.

---

## What Changes End-to-End

**Before:** Tenant calls → agent asks "when should the technician visit?" → stores appointment as a maintenance visit → manager sees visit schedule.

**After:** Tenant calls → agent collects the complaint → agent asks "when would you like the manager to call you back?" → stores a scheduled callback with the tenant's phone number → manager sees their callback queue → manager calls tenant at that time → marks it done.

---

## Phase 0 — DB Migration

**File to create:** `backend/migrations/017_appointments_callback_type.sql`

```sql
-- Add type column to distinguish maintenance visits from manager callbacks
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'callback'
    CHECK (type IN ('callback', 'visit'));

-- Add tenant_phone so manager knows who to call back
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS tenant_phone TEXT;

-- Backfill existing rows: anything created before this migration is a 'visit'
UPDATE appointments SET type = 'visit' WHERE type = 'callback' AND created_at < NOW();
```

Run this against Supabase before any code is deployed.

No new RLS policy needed — `manager_id` is already the RLS key. The fix to populate it (Phase 1) is what makes existing rows visible.

---

## Phase 1 — Backend: Root Cause Fix + New Fields

### 1.1 `backend/app/routes/voice.py`

**Location:** Lines 363–379 (the appointment_payload dict inside `voice_webhook`)

**Change:** Add `manager_id`, `type`, and `tenant_phone` to the appointment payload.

Current code:
```python
appointment_payload = {
    "flat_number": flat_no.strip().upper(),
    "complaint_uuid": complaint_uuid,
    "flat_uuid": flat_uuid,
    "appointment_date": appointment_date,
    "status": "scheduled"
}
```

New code:
```python
appointment_payload = {
    "flat_number": flat_no.strip().upper(),
    "complaint_uuid": complaint_uuid,
    "flat_uuid": flat_uuid,
    "appointment_date": appointment_date,
    "status": "scheduled",
    "type": "callback",
    "tenant_phone": caller_phone,   # already resolved at this point
    "manager_id": manager_id,       # ROOT CAUSE FIX — was missing entirely
}
```

`caller_phone` is already in scope (defined at line 311 as `caller_phone = (phone_number or "").strip()`).  
`manager_id` is already in scope (resolved at lines 311–321).  
This is the single-line fix that makes all existing and future voice-created appointments visible on the frontend.

### 1.2 `backend/app/schemas/appointment.py`

Add the two new fields to both request and response schemas.

**`AppointmentCreate` — add:**
```python
type: Optional[str] = Field("callback", description="'callback' or 'visit'")
tenant_phone: Optional[str] = Field(None, description="Tenant phone for callbacks")
```

**`AppointmentResponse` — add:**
```python
type: Optional[str] = None
tenant_phone: Optional[str] = None
```

Also add `complaint_category`, `complaint_description`, `complaint_priority` to `AppointmentResponse` since the GET handler already returns them at root level but the schema doesn't declare them (Pydantic silently drops them from the API response):
```python
complaint_category: Optional[str] = None
complaint_description: Optional[str] = None
complaint_priority: Optional[str] = None
```

### 1.3 `backend/app/routes/appointments.py`

**Availability check — fix DB client (secondary bug):**

Line 293 currently:
```python
db: Client = Depends(get_db),
```
Change to:
```python
db: Client = Depends(get_service_db),
```
Add `get_service_db` to the imports at the top. VAPI calls this endpoint without a user JWT — using the anon client means `auth.uid()` is NULL and RLS filters out all appointments, making every slot return "available" regardless of what is booked.

**The GET /appointments handler** — no logic changes needed. The `type` and `tenant_phone` fields will be returned automatically once the schema is updated.

---

## Phase 2 — VAPI Agent: System Prompt + Tool Schema

### 2.1 `backend/app/services/vapi_agent_config.py`

#### 2.1.1 System Prompt Update (`COMPLAINT_SYSTEM_PROMPT`, lines 644–717)

**Change the Maintenance Flow section (lines 702–710).** Replace all language about "visit", "technician", and "appointment" with callback language.

Current language to replace (paraphrased from the agent):
- "When should the technician visit?"
- "I'll book a maintenance appointment for [date]"
- "A technician will visit flat [X] on [date]"

Replace with:
- "When would you like the manager to call you back?"
- "I'll schedule a manager callback for [date/time]"
- "The manager will call you at [phone] on [date] regarding your [category] complaint"

**Specific prompt section rewrite:**

```
CALLBACK SCHEDULING FLOW
After collecting the complaint details (flat number, category, description):
1. Ask: "When would you like the manager to call you back? Please give me a date and time."
2. Use the check_availability tool to confirm the manager is free at that time.
   - If unavailable, suggest the next available slot.
3. Confirm back to the caller: "I'll schedule a manager callback for [day] at [time]. 
   The manager will call you back on your registered phone number."
4. Call submit_complaint with all collected data.
5. After submission: "Your complaint has been logged and a callback is scheduled. 
   You'll receive an SMS confirmation shortly."
DO NOT use words like "technician", "visit", "maintenance appointment", or "engineer".
Always say "manager callback" or "call back from the manager".
```

**Also update the tool description reference in the prompt** to say `appointment_date` means the preferred callback time, not a visit time.

#### 2.1.2 `submit_complaint` Tool Schema Update (lines 884–923)

Change the `appointment_date` parameter description. **Do NOT rename the parameter** (VAPI dashboard uses the name as a key; renaming requires re-publishing the assistant). Only update the description:

Current:
```python
"appointment_date": {
    "type": "string",
    "description": "ISO 8601 visit datetime",
    "default": "",
},
```

New:
```python
"appointment_date": {
    "type": "string",
    "description": "ISO 8601 datetime for the manager callback call — when the tenant wants the manager to call them back. Format: YYYY-MM-DDTHH:MM:SS",
    "default": "",
},
```

#### 2.1.3 `build_complaint_config()` — Assistant-level instructions (lines 927–959)

Add to the `firstMessage` or `firstMessageMode` section to set the opening framing correctly. The agent should introduce itself as handling complaints and callbacks, not maintenance scheduling.

If there is a `firstMessage` string in `build_complaint_config()`, update it from anything that mentions "booking appointments" or "scheduling visits" to:
```
"Hi! I'm here to help log your complaint and schedule a callback from your property manager. How can I help you today?"
```

---

## Phase 3 — Backend: Notification Templates

### 3.1 `backend/app/services/notifications.py`

#### 3.1.1 `notify_manager_appointment_scheduled()` (lines 98–444)

This notifies the manager when an appointment is created. The manager now needs to know it's a callback — and crucially needs the **tenant's phone number** so they know who to call.

**SMS template change (lines 226–235):**

Current:
```
🔔 New Visit Scheduled

Flat: {flat_number}
Category: {complaint_category}
Priority: {complaint_priority.upper()}
Appointment: {formatted_date_short}

Tenant: {tenant_name}
```

New (check `appointment.get("type") == "callback"` to branch):
```
📞 Manager Callback Scheduled

Flat: {flat_number}
Call tenant at: {tenant_phone}
Tenant: {tenant_name}

Category: {complaint_category}
Priority: {complaint_priority.upper()}
Callback time: {formatted_date_short}
```

**Email HTML change (lines 238–410):**
- Change email subject from "New Maintenance Appointment" to "Manager Callback Scheduled — Flat {flat_number}"
- Change header title from "New Visit Scheduled" to "Callback Scheduled"
- In the "Appointment Details" section, add a row: **Tenant Phone:** `{tenant_phone}` — this is the most important field for the manager
- Change label "Appointment Date" → "Callback Time"
- Remove any language about "technician", "visit", "engineer"

**Implementation note:** The appointment dict passed to this function may not yet include `tenant_phone` if the appointment was fetched separately. Ensure the voice webhook passes the full appointment response dict (which will include `tenant_phone` after Phase 1).

#### 3.1.2 `notify_tenant_appointment()` (lines 16–96)

**Event type `"created"` SMS (line 62–65):**

Current:
```
Hi {name}, a new maintenance appointment has been scheduled for flat {flat_number}.
```

New:
```
Hi {name}, your complaint has been logged and a manager callback is scheduled for {formatted_date}. The manager will call you back on your registered number.
```

**Event type `"rescheduled"` (line 66–70):**

Current:
```
Hi {name}, your maintenance appointment for flat {flat_number} has been rescheduled to {formatted_date}.
```

New:
```
Hi {name}, your manager callback for flat {flat_number} has been rescheduled to {formatted_date}.
```

**Event type `"cancelled"` (line 71–75):**

Current:
```
Hi {name}, your maintenance appointment for flat {flat_number} has been cancelled.
```

New:
```
Hi {name}, your manager callback for flat {flat_number} has been cancelled.
```

**Event type `"attended"` (line 76–80) — rename to `"completed"`:**

Current:
```
Hi {name}, your maintenance appointment for flat {flat_number} has been marked as attended.
```

New:
```
Hi {name}, your manager callback for flat {flat_number} has been completed. Thank you!
```

---

## Phase 4 — Frontend

### 4.1 `frontend/src/components/AppointmentDetailModal.jsx`

This is the modal that opens when a manager clicks an appointment in the calendar or list.

**Changes:**

1. **Title / header** — currently shows "Appointment" or similar. Add conditional logic:
   ```jsx
   const isCallback = appointment?.type === 'callback';
   const modalTitle = isCallback ? 'Scheduled Callback' : 'Maintenance Visit';
   ```

2. **Add tenant phone display** — add a new row in the details section:
   ```jsx
   {isCallback && appointment.tenant_phone && (
     <div className="flex items-center gap-2">
       <Phone className="w-4 h-4 text-blue-500" />
       <span className="font-medium">Call tenant at:</span>
       <a href={`tel:${appointment.tenant_phone}`} className="text-blue-600 underline">
         {appointment.tenant_phone}
       </a>
     </div>
   )}
   ```

3. **Status labels** — the status dropdown currently shows "Attended". For callbacks:
   - `scheduled` → "Scheduled"
   - `attended` → "Called" (label only, value stays `attended`)
   - `cancelled` → "Cancelled"
   - `completed` → "Completed"
   
   Add a helper:
   ```jsx
   const statusLabel = (s) => {
     if (isCallback && s === 'attended') return 'Called';
     return s.charAt(0).toUpperCase() + s.slice(1);
   };
   ```

4. **Date label** — change "Appointment Date" label to "Callback Time" when `type === 'callback'`.

5. **Icon** — if the appointment has `type === 'callback'`, show `<Phone />` icon in the modal header instead of a calendar/wrench icon.

### 4.2 `frontend/src/components/CalendarView.jsx`

Lines 88–100 (getEventsForDate) and lines 214–227 (mini-badge render).

**Changes:**

1. **Color coding** — add a new color for callback type:
   ```js
   // In MINI_STATUS / PANEL_BORDER / BADGE_CLASSES
   // Callbacks use a teal/cyan scheme to differentiate from other events
   callback_scheduled: 'border-teal-500 bg-teal-50 text-teal-700',
   ```

2. **Mini-badge label** — currently shows time + flat number. For callbacks, prepend a phone emoji or icon:
   ```jsx
   const label = apt.type === 'callback'
     ? `📞 ${timeStr} · ${apt.flat_number}`
     : `${timeStr} · ${apt.flat_number}`;
   ```

3. **Legend entry** — add "Manager Callback" to the legend with teal color.

### 4.3 `frontend/src/components/ComplaintsOverview.jsx` (and `ComplaintDetailModal.jsx`)

In `ComplaintDetailModal.jsx`, the linked appointment section (if present) currently labels the date as "Appointment". Change to:
```jsx
const apptLabel = linkedAppointment?.type === 'callback'
  ? 'Manager Callback'
  : 'Maintenance Appointment';
```

### 4.4 `frontend/src/components/dashboard/AppointmentsBar.jsx`

This chart shows appointments over time. Update the chart title/label from "Appointments" to "Scheduled Callbacks" (or "Callbacks & Visits" if both types exist in the system).

### 4.5 `frontend/src/services/apiService.js` (lines 555–584)

No logic changes needed. The existing `getAppointments`, `updateAppointment`, and `deleteAppointment` functions work with any shape. The new `type` and `tenant_phone` fields will come through automatically once the backend schema is updated.

---

## Phase 5 — In-App Notification (Bell Panel)

This mirrors exactly how lead notifications work: a row is inserted into the `notifications` table immediately after the appointment is created, and the manager sees it in the bell panel within 30 seconds (the panel polls every 30s).

### 5.1 `backend/app/routes/voice.py` — Insert notification after appointment is saved

**Location:** Right after the `print(f"  [OK] Appointment created: ...")` line (currently line 377), inside the `if appointment_response.data:` block.

**Pattern to follow** (lead notification at lines 636–646):
```python
db.table("notifications").insert({
    "manager_id": str(manager_id),
    "title": "New Qualified Lead",
    "body": f"{caller_name} is interested in leasing — review their details.",
    "type": "lead",
    "entity_id": str(saved_lead["uuid"]),
    "is_read": False,
}).execute()
```

**New callback notification block** — add it immediately after appointment creation succeeds:
```python
if appointment_response.data and manager_id:
    try:
        saved_apt = appointment_response.data[0]
        apt_uuid  = saved_apt.get("uuid", "")

        # Format the callback time for a human-readable body
        # appointment_date is ISO string e.g. "2026-06-05T10:00:00"
        try:
            from datetime import datetime as _dt
            dt_obj        = _dt.fromisoformat(appointment_date)
            readable_time = dt_obj.strftime("%a %b %-d at %-I:%M %p")  # e.g. "Thu Jun 5 at 10:00 AM"
        except Exception:
            readable_time = appointment_date

        category_label = (complaint_data.get("category") or "complaint").capitalize()
        display_phone  = caller_phone or "Unknown number"

        db.table("notifications").insert({
            "manager_id": str(manager_id),
            "title":      f"Callback Scheduled — Flat {flat_no.strip().upper()}",
            "body":       f"{display_phone} needs a callback on {readable_time} regarding a {category_label} issue.",
            "type":       "callback",
            "entity_id":  str(apt_uuid),
            "is_read":    False,
        }).execute()
        print(f"  [NOTIFICATION] Callback notification created for manager {manager_id}")
    except Exception as notif_err:
        print(f"  [NOTIFICATION] Failed (non-fatal): {notif_err}")
```

**Key details matching the lead pattern:**
- Wrapped in `try/except` — notification failure must never crash the webhook (VAPI would retry the call)
- `entity_id` is set to the appointment UUID so the frontend can later deep-link to it
- Uses `get_service_db` (already the active client in this webhook) — same as leads
- Inserted synchronously (not a background task) — small and fast, same as leads

### 5.2 `frontend/src/components/NotificationPanel.jsx` — Add `callback` type color

**Location:** `TYPE_COLORS` constant at lines 7–13.

Current:
```js
const TYPE_COLORS = {
    appointment: 'bg-blue-500/15 text-blue-400',
    complaint:   'bg-red-500/15 text-red-500',
    rent:        'bg-emerald-500/15 text-emerald-500',
    lead:        'bg-violet-500/15 text-violet-500',
    system:      'bg-secondary text-muted-foreground',
};
```

New — add `callback` entry:
```js
const TYPE_COLORS = {
    appointment: 'bg-blue-500/15 text-blue-400',
    complaint:   'bg-red-500/15 text-red-500',
    rent:        'bg-emerald-500/15 text-emerald-500',
    lead:        'bg-violet-500/15 text-violet-500',
    callback:    'bg-teal-500/15 text-teal-500',
    system:      'bg-secondary text-muted-foreground',
};
```

Teal matches the calendar color chosen in Phase 4 for callback events — the manager builds a visual association between teal = callback across both the calendar and the notification panel.

### 5.3 What the notification looks like in the panel

```
📞  [teal badge: callback]
Callback Scheduled — Flat S201          ← title
+919998064026 needs a callback on       ← body
Thu Jun 3 at 1:52 PM regarding a
Maintenance issue.
                                just now ← timeAgo
```

The unread red dot appears on the bell icon instantly (next poll cycle ≤ 30s). Clicking the row marks it read.

### 5.4 No new DB migration needed

The `notifications` table already has `manager_id`, `title`, `body`, `type`, `entity_id`, `is_read` columns. The new `"callback"` value in `type` is just a string — no schema change required.

---

## Phase 6 — Testing Checklist

### Backend / API

- [ ] Run DB migration `017_appointments_callback_type.sql` against Supabase
- [ ] Make a test voice call: confirm the webhook log shows `"type": "callback"` and `"manager_id": <uuid>` in the appointment insert
- [ ] `GET /appointments` with an authenticated token returns the newly created appointment (RLS fix verified)
- [ ] `GET /appointments/availability?appointment_date=...` returns correct availability (not always "available")
- [ ] Manager SMS contains tenant phone number
- [ ] Tenant SMS says "callback" not "maintenance appointment"

### Agent

- [ ] Call the complaint line: agent should NOT say "technician" or "visit"
- [ ] Agent asks for preferred callback time
- [ ] Agent confirms "manager will call you back"
- [ ] `submit_complaint` fires with `appointment_date` set to callback time
- [ ] Webhook log shows: `Appointment Created: Yes (ID=XX)` with correct callback time

### In-App Notification

- [ ] After voice webhook completes, a row appears in the `notifications` table with `type = 'callback'`, `entity_id = <appointment_uuid>`, `is_read = false`
- [ ] Bell icon on the frontend shows a red unread count badge within 30 seconds of the call ending
- [ ] Opening the notification panel shows the new notification with the teal `callback` badge
- [ ] Notification title: `"Callback Scheduled — Flat <X>"`
- [ ] Notification body contains the tenant phone number and formatted callback time
- [ ] Clicking the notification row marks it as read (dot disappears)
- [ ] Notification failure (e.g. DB hiccup) does NOT crash the webhook — VAPI call still marked success

### Frontend

- [ ] Calendar shows the callback event on the correct date
- [ ] Callback events show phone icon / teal color (distinguishable from maintenance visits)
- [ ] Clicking the event opens `AppointmentDetailModal` showing tenant phone number
- [ ] "Callback Time" label appears instead of "Appointment Date"
- [ ] Status dropdown shows "Called" instead of "Attended" for callbacks
- [ ] Manager can mark a callback as "Called" (maps to `attended` status in DB)
- [ ] Complaint detail modal shows "Manager Callback" in linked appointment section

---

## File Change Summary

| File | Change Type | Description |
|---|---|---|
| `backend/migrations/017_appointments_callback_type.sql` | **NEW** | Add `type` and `tenant_phone` columns |
| `backend/app/routes/voice.py` | **EDIT** | Add `manager_id`, `type`, `tenant_phone` to appointment_payload (root fix) |
| `backend/app/routes/appointments.py` | **EDIT** | Switch `get_db` → `get_service_db` in availability check |
| `backend/app/schemas/appointment.py` | **EDIT** | Add `type`, `tenant_phone`, and complaint fields to schemas |
| `backend/app/services/vapi_agent_config.py` | **EDIT** | Update system prompt + tool description |
| `backend/app/services/notifications.py` | **EDIT** | Update SMS/email templates to callback language + tenant phone |
| `frontend/src/components/AppointmentDetailModal.jsx` | **EDIT** | Add tenant phone, conditional labels, phone icon |
| `frontend/src/components/CalendarView.jsx` | **EDIT** | Add callback color scheme, phone icon in mini-badge |
| `frontend/src/components/ComplaintDetailModal.jsx` | **EDIT** | Update linked appointment label |
| `frontend/src/components/dashboard/AppointmentsBar.jsx` | **EDIT** | Update chart title |
| `frontend/src/components/NotificationPanel.jsx` | **EDIT** | Add `callback` type color (teal) to `TYPE_COLORS` |

---

## Execution Order

1. **DB migration first** — deploy `017_appointments_callback_type.sql` before any code changes. Safe to run on live DB (ADD COLUMN, non-destructive).
2. **Backend Phase 1** — deploy `voice.py` fix + schema updates. This makes future voice calls produce visible appointments immediately.
3. **Backend Phase 3** — deploy notification changes. Purely cosmetic, safe at any point.
4. **Backend Phase 2** — update the VAPI agent config and republish the assistant in VAPI dashboard. Do this after backend is deployed so the new language matches the new backend behavior.
5. **Backend Phase 5 + Frontend Phase 5** — deploy notification changes together. The `notifications` table already has all the columns needed; no migration required. Deploy `voice.py` notification block and `NotificationPanel.jsx` color entry in the same release.
6. **Frontend Phase 4** — deploy remaining frontend changes (`AppointmentDetailModal`, `CalendarView`, etc.). The new fields (`type`, `tenant_phone`) will simply be `undefined` on older records (handled by null checks), so no backward-compat issues.
7. **Verify** existing appointments (IDs 53, 54, 55) are now visible after the `manager_id` fix. They will be, because the RLS fix only affects reads — the rows already exist in the DB.
