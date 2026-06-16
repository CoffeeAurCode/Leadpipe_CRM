# Complaint Agent — Frontend Visibility Bug Report
**Date:** 2026-06-03  
**Test call:** `call_id: 019e8bab-6850-7337-b2a9-cbea96d80e45`  
**Outcome:** Complaint #62 created in DB, invisible on every frontend view.

---

## What the log confirmed worked

| Step | Result |
|---|---|
| Outbound call initiated | ✅ |
| Phone verify (S201 / +919998064026) | ✅ |
| Appointment availability check | ✅ |
| VAPI `tool-calls` webhook received | ✅ |
| CallLog #59 created | ✅ |
| Complaint #62 inserted to DB | ✅ |
| Appointment #52 created at 15:00 | ✅ |
| Notification triggered | ✅ |
| `POST /voice/webhook` → 200 | ✅ |
| `GET /complaints` (04:10:38, user navigated manually) | ✅ 200 — but returned empty of #62 |

---

## Bug 1 — Auto-refresh never fires after `tool-calls` event

### Root cause
`voice.py` only stamps `_last_call_ended_at` for `end-of-call-report` events:

```python
# voice.py:415-418
if message_type == "end-of-call-report":
    global _last_call_ended_at
    _last_call_ended_at = datetime.now(timezone.utc).isoformat()
```

But **complaints are created on `tool-calls` events**, not `end-of-call-report`.

`App.jsx:100-116` polls `/voice/call-status` every 10 s and calls `loadComplaints()` + `loadAppointments()` only when `last_call_ended_at` changes:

```js
const { last_call_ended_at } = await getCallStatus();
if (last_call_ended_at && last_call_ended_at !== lastSeen) {
    lastSeen = last_call_ended_at;
    loadComplaints();
    loadAppointments();
}
```

### Evidence from log
- Webhook fires `tool-calls` at **04:10:17** — complaint created
- Frontend polls at 04:10:17, 04:10:24, 04:10:34 — `last_call_ended_at` unchanged → **no refresh triggered**
- `GET /complaints` at 04:10:38 was the user navigating manually, not the poller

### Fix
Stamp `_last_call_ended_at` when a complaint is successfully created via `tool-calls`.

---

## Bug 2 — Complaint #62 invisible because `manager_id` is NULL → RLS hides it

### Root cause
The voice webhook builds `complaint_dict` without `manager_id`:

```python
# voice.py (after today's fix)
complaint_dict = {
    "flat_number": flat_no.strip().upper(),
    "flat_uuid": flat_uuid,
    "tenant_uuid": tenant_uuid,
    "category": ...,
    "priority": "medium",
    "description": ...,
    "status": "pending",
    "source": "voice"
    # manager_id: MISSING
}
db.table("complaints").insert(complaint_dict).execute()
```

The `complaints` table has an RLS policy `manager_id = auth.uid()`. The service-role client bypasses RLS at **insert time**, so the row goes in with `manager_id = NULL`. When the frontend queries with the manager's user JWT, RLS applies and **filters out every row where `manager_id` is NULL** — complaint #62 disappears.

### Evidence from log
- `GET /complaints` at **04:10:38** returned HTTP 200 — query succeeded
- Complaint #62 was in the DB but not in the response payload
- Same query via service client (e.g., Supabase dashboard) would show it

### Lookup chain — anchored on caller phone (verified identity)
```
phone_number (caller)
  → tenants.phone → tenant.flat_uuid
    → flats.building_id
      → buildings.property_id
        → properties_list.manager_id
```
The phone number is the identity that was cryptographically verified by `verify-phone`. Using the spoken flat number as the anchor would be weaker — the caller could say any flat. Starting from the phone ensures the manager assignment always follows the authenticated tenant.

### Fix
1. Look up tenant by `phone_number` → get `flat_uuid`
2. Walk: `flat_uuid → flats.building_id → buildings.property_id → properties_list.manager_id`
3. Include `manager_id` in `complaint_dict`

---

## Combined fix summary

| File | Change |
|---|---|
| `voice.py` | Add `building_id` to flat select |
| `voice.py` | Resolve `manager_id` via building → properties_list |
| `voice.py` | Add `manager_id` to `complaint_dict` |
| `voice.py` | Stamp `_last_call_ended_at` when complaint created via `tool-calls` |

---

## Why dashboard, calendar, and complaint tab were all blank

All three views read from the same data sources (`loadComplaints`, `loadAppointments`) that App.jsx controls. Since Bug 1 prevented the auto-refresh and the manually triggered `GET /complaints` was silenced by Bug 2 (RLS), **no view had the data to display**.
