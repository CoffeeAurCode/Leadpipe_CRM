# Appointment Visibility Bug — Diagnosis

**Date:** 2026-06-03  
**Complaints tested:** IDs 63, 64 (flat S201) and 65 (flat C301)  
**Symptom:** Complaints visible in frontend. Appointments confirmed created in DB (IDs 53, 54, 55). Appointments invisible on every frontend view.

---

## 1. What the Logs Confirm

All three appointments were created successfully by the voice webhook:

| Complaint | Flat | Appointment ID | Scheduled At |
|---|---|---|---|
| 63 | S201 | 53 | 2026-06-03T13:52:34 |
| 64 | S201 | 54 | 2026-06-03T18:00:00 |
| 65 | C301 | 55 | 2026-06-05T10:00:00 |

Immediately after each webhook event, the frontend fires `GET /appointments?start_date=2026-03-05&end_date=2026-07-03` and receives HTTP 200. The 200 response is not proof of data — the query returned an empty array.

---

## 2. Root Cause — Missing `manager_id` in the Appointment Insert

### The appointments table schema (from CODEBASE_CONTEXT.md):

| Column | Type | Notes |
|---|---|---|
| `manager_id` | UUID | **RLS key** |
| `complaint_uuid` | UUID | FK → complaints |
| `flat_uuid` | UUID | FK → flats |
| `appointment_date` | timestamptz | |
| `status` | text | |

`manager_id` is the RLS key. The Supabase RLS policy on `appointments` evaluates to:
```sql
manager_id = auth.uid()
```

### The voice webhook appointment insert (`backend/app/routes/voice.py`, lines 367–374):

```python
appointment_payload = {
    "flat_number": flat_no.strip().upper(),
    "complaint_uuid": complaint_uuid,
    "flat_uuid": flat_uuid,
    "appointment_date": appointment_date,
    "status": "scheduled"
    # ← manager_id is NOT included
}
appointment_response = db.table("appointments").insert(appointment_payload).execute()
```

`manager_id` is resolved earlier in the function (lines 311–321) and stored in the local variable `manager_id`, but **it is never added to `appointment_payload`**.

The complaint insert — which runs just before this — does include `manager_id`:
```python
complaint_dict = {
    ...
    "manager_id": manager_id,   # ← present in complaints
    ...
}
```

This is why complaints are visible but appointments are not.

### Write vs. Read DB client mismatch:

The webhook uses `get_service_db` (service role — bypasses RLS) for the INSERT. The INSERT succeeds regardless of `manager_id`. But the frontend `GET /appointments` uses `get_authenticated_db` (RLS-enforced). The RLS policy filters every row where `manager_id != auth.uid()`. Since `manager_id` is `NULL` in all voice-created appointments, no rows pass the filter. The endpoint returns `[]`.

---

## 3. Evidence Trail

1. **Log line 71**: `[OK] Appointment created: ID=53 at 2026-06-03T13:52:34` — DB write succeeded.
2. **Log line 90**: `GET /appointments?start_date=2026-03-05&end_date=2026-07-03 HTTP/1.1 200 OK` — response is 200 but the payload is empty.
3. **Complaints CSV**: the `manager_id` column on all 3 complaints is `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` — confirmed the manager resolution step works. The same variable is never forwarded to the appointment payload.
4. **Complaints CSV**: the `appointment_date` column on all 3 complaints is empty — correct, because the appointment lives in the `appointments` table, not embedded in `complaints`. This is expected behaviour, not a bug.

---

## 4. Secondary Issue — `vapi_check_availability` Uses the Wrong DB Client

```python
# backend/app/routes/appointments.py, line 293
async def vapi_check_availability(
    appointment_date: str = ...,
    db: Client = Depends(get_db),      # ← anon client, respects RLS
):
```

VAPI calls this endpoint without a user JWT. Without a JWT, `auth.uid()` is `NULL`, and the RLS policy evaluates to `NULL` (falsy), so **no existing appointments are visible to this query**. Every slot returns `available` regardless of what is already booked.

This is a separate bug that makes the availability check unreliable, but it does not affect appointment visibility on the dashboard.

---

## 5. Why Nothing Shows on Any Frontend View

All frontend views that display appointments (CalendarView, ComplaintsOverview, AppointmentsBar, etc.) receive their data from a single `GET /appointments` call in the parent component. If that call returns `[]`, every child view is empty — calendar shows no events, dashboard charts show zero appointments, complaint detail modals show no linked appointment.

The JOIN in the GET handler also references `complaints!fk_appointments_complaint_uuid`. Even if the FK join were broken (wrong FK name), it would only lose the category/description/priority enrichment — the appointment rows themselves would still be returned if RLS passed. RLS failing entirely means the join never runs.

---

## 6. Summary

| Issue | Location | Severity |
|---|---|---|
| `manager_id` missing from appointment insert | `voice.py` lines 367–374 | **Critical — root cause** |
| `vapi_check_availability` uses `get_db` instead of `get_service_db` | `appointments.py` line 293 | Medium — availability checks always return "available" |

**Fix required:** Add `"manager_id": manager_id` to `appointment_payload` in `voice.py`. The `manager_id` variable is already resolved at that point in the function. The same variable that populates the complaint dict needs to be forwarded to the appointment dict.
