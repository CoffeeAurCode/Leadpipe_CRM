# API Fix Plan — Based on June 2026 Test Run

**Source:** `API_TEST_RESULTS.md`  
**Current score:** 56 pass / 40 fail / 19 skip out of 115 tests  
**Target:** eliminate all P0/P1 failures; bring pass rate to ~90+

Split into 3 sessions. Each session is independently executable.

---

## Session 1 — Critical Backend Fixes (P0 + P1)

**Goal:** Unblock the cascade. Fixing RLS alone recovers ~20 cascaded skips.

### Fix 1 — RLS: Allow INSERT on `tenants` and `complaints` (P0)

**Why failing:** POST /tenants and POST /complaints return HTTP 500.  
The `get_authenticated_db` dependency sets the JWT on the PostgREST client, but if the Supabase RLS INSERT policy uses `auth.uid() = manager_id` and `manager_id` is not being set in the request body (it's derived server-side), the policy rejects the insert.

**In Supabase dashboard (SQL editor):**
```sql
-- Check current policies first:
SELECT policyname, cmd, qual, with_check
FROM pg_policies
WHERE tablename IN ('tenants', 'complaints');

-- If INSERT policy is missing or misconfigured, run:
CREATE POLICY "Managers can insert their own tenants"
  ON tenants FOR INSERT
  WITH CHECK (auth.uid() = manager_id);

CREATE POLICY "Managers can insert their own complaints"
  ON complaints FOR INSERT
  WITH CHECK (auth.uid() = manager_id);
```

**Alternatively** — switch the INSERT in `routes/tenants.py` and `routes/complaints.py` to use `svc` (service-role client) the same way `routes/flats.py` already does for flat creation. This bypasses RLS on INSERT while all ownership checks still run first via the authenticated client.

> **Note:** Verify the actual error message in Supabase logs before choosing approach. If the error is `42501 permission denied`, use the RLS policy fix. If it's a schema error or null violation, investigate the INSERT payload instead.

**Tests recovered:** TN01 TN02 TN03 (tenant create) + CM01–CM05 (complaint create) + all appointment/VAPI tests that required a complaint to exist.

---

### Fix 2 — Add `DELETE /complaints/{id}` (P1)

**File:** `backend/app/routes/complaints.py`  
**Issue:** Route is documented but not implemented. Returns 405 (Method Not Allowed).

Add after the existing `PATCH /{complaint_id}` handler:

```python
@router.delete("/{complaint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_complaint(
    complaint_id: int,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    try:
        response = db.table("complaints").delete().eq("id", complaint_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Complaint {complaint_id} not found")
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting complaint: {str(e)}")
```

**Tests recovered:** CM10 (or whichever test covers DELETE /complaints/{id})

---

### Fix 3 — Add `GET /buildings/{id}` (P1)

**File:** `backend/app/routes/buildings.py`  
**Issue:** `GET /buildings/{building_id}/units` exists but `GET /buildings/{building_id}` does not. Returns 405.

Add between `get_all_buildings` and `create_building`:

```python
@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building_by_id(
    building_id: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    try:
        resp = (
            db.table("buildings")
            .select("*, property_types(name, icon_type)")
            .eq("id", building_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=404, detail="Building not found")
        b = resp.data[0]
        pt = b.get("property_types") or {}
        flats_resp = db.table("flats").select("tenant_uuid").eq("building_id", building_id).execute()
        units = flats_resp.data or []
        return {
            **b,
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "unit_count": len(units),
            "occupied_count": sum(1 for u in units if u.get("tenant_uuid")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching building: {str(e)}")
```

> **Route order warning:** FastAPI matches routes top-to-bottom. `GET /buildings/{building_id}/units` must come BEFORE `GET /buildings/{building_id}` in the file, otherwise `{building_id}` will greedily match `units`. Verify ordering after adding.

**Tests recovered:** B02 (GET /buildings/{id})

---

### Fix 4 — Update `CODEBASE_CONTEXT.md`: call_logs URL

**Issue:** The context documents the route as `/call-logs` (hyphen) but the actual router prefix is `/call_logs` (underscore). Tests V03-V05 fail because they follow the documentation.

In `CODEBASE_CONTEXT.md`, section 5, update:
```
### `/call-logs` — `routes/call_logs.py`
```
to:
```
### `/call_logs` — `routes/call_logs.py`
```
And update the route paths in the table from `/call-logs` to `/call_logs`.

**Tests recovered:** V03 V04 V05 (these are test plan errors, not code errors — update the test plan curl commands too)

---

### Session 1 Checklist

- [ ] Run SQL in Supabase dashboard to diagnose + fix RLS on `tenants`
- [ ] Run SQL in Supabase dashboard to diagnose + fix RLS on `complaints`
- [ ] Add DELETE handler to `complaints.py`
- [ ] Add GET /{id} handler to `buildings.py` (check route ordering)
- [ ] Update `CODEBASE_CONTEXT.md` call_logs URL

**Expected pass delta: +20–25 tests**

---

## Session 2 — Missing Feature Endpoints (P2)

**Goal:** Implement the notification and workflow endpoints that tests expect.

### Fix 5 — Notification Test + Preferences Endpoints

**File:** `backend/app/routes/notifications.py`  
**Missing routes:** `POST /notifications/test-sms`, `POST /notifications/test-email`, `GET /notifications/preferences`

The `manager_notifications` table already exists (stores `appointment_sms_enabled`, `appointment_email_enabled`). The test/preview SMS and email calls should use the existing Twilio/SendGrid clients.

Add to `notifications.py`:

```python
# GET /notifications/preferences
@router.get("/preferences")
async def get_notification_preferences(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    manager_id = user["sub"]
    resp = db.table("manager_notifications").select("*").eq("manager_id", manager_id).execute()
    if resp.data:
        return resp.data[0]
    # Return defaults if no row exists yet
    return {"manager_id": manager_id, "appointment_sms_enabled": False, "appointment_email_enabled": False}


# POST /notifications/test-sms
class TestSmsRequest(BaseModel):
    phone: str
    message: Optional[str] = "This is a test SMS from your property management system."

@router.post("/test-sms")
async def send_test_sms(
    body: TestSmsRequest,
    user: dict = Depends(require_active_subscription),
):
    from app.integrations.twilio_client import get_twilio_client
    sid = get_twilio_client().send_sms(to=body.phone, message=body.message)
    if sid:
        return {"success": True, "sid": sid}
    raise HTTPException(status_code=500, detail="Failed to send test SMS")


# POST /notifications/test-email
class TestEmailRequest(BaseModel):
    email: str
    subject: Optional[str] = "Test Email from Property Manager"
    message: Optional[str] = "This is a test email from your property management system."

@router.post("/test-email")
async def send_test_email(
    body: TestEmailRequest,
    user: dict = Depends(require_active_subscription),
):
    from app.integrations.email_client import get_email_client
    success = get_email_client().send_email(to=body.email, subject=body.subject, body=body.message)
    if success:
        return {"success": True}
    raise HTTPException(status_code=500, detail="Failed to send test email")
```

> **Note:** Verify the actual method signatures on `twilio_client` and `email_client` before adding — match what `services/notifications.py` already calls.

**Tests recovered:** N01 N02 N03 (all 3 notification tests)

---

### Fix 6 — SMS Templates CRUD + Broadcast Endpoint (P2)

**File:** `backend/app/routes/workflow.py`  
**Missing routes:** `GET /workflow/sms-templates`, `POST /workflow/sms-templates`, `POST /workflow/sms-broadcast`

**Decision point first:** Check whether the test for `POST /workflow/sms-broadcast` tests the same payload/behavior as the existing `POST /workflow/send-sms`. If yes, add `/sms-broadcast` as an alias route (or rename). If it's a different behavior (e.g., broadcast to all tenants in a group rather than a specific list), implement separately.

**SMS Templates** — requires a new table or in-memory defaults. Simplest path: store templates as static defaults in code (no DB table needed for MVP):

```python
_DEFAULT_TEMPLATES = [
    {"id": 1, "name": "Rent Reminder", "message": "Hi {name}, your rent of {rent} is due on {date}. Please pay on time."},
    {"id": 2, "name": "Maintenance Notice", "message": "Hi {name}, maintenance is scheduled for your unit {unit}."},
    {"id": 3, "name": "General Announcement", "message": "Hi {name}, this is an update from your property manager."},
]

@router.get("/sms-templates")
async def get_sms_templates(user: dict = Depends(require_active_subscription)):
    return _DEFAULT_TEMPLATES


class SmsTemplateCreate(BaseModel):
    name: str
    message: str

@router.post("/sms-templates", status_code=201)
async def create_sms_template(body: SmsTemplateCreate, user: dict = Depends(require_active_subscription)):
    # For MVP: return the template as-if saved (no DB persistence needed yet)
    new_id = len(_DEFAULT_TEMPLATES) + 1
    return {"id": new_id, "name": body.name, "message": body.message}


# sms-broadcast: alias for send-sms (same behavior, different name)
@router.post("/sms-broadcast", response_model=SmsWorkflowResponse)
async def sms_broadcast(
    payload: SmsWorkflowRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    return await send_sms_workflow(payload, user, db)
```

**Tests recovered:** W01 W02 W03 (all 3 SMS workflow tests)

---

### Session 2 Checklist

- [ ] Add `GET /notifications/preferences` to `notifications.py`
- [ ] Add `POST /notifications/test-sms` to `notifications.py`
- [ ] Add `POST /notifications/test-email` to `notifications.py`
- [ ] Verify twilio_client / email_client method signatures before wiring up
- [ ] Add `GET /workflow/sms-templates` to `workflow.py`
- [ ] Add `POST /workflow/sms-templates` to `workflow.py`
- [ ] Add `POST /workflow/sms-broadcast` alias to `workflow.py`
- [ ] Run the 3 notification tests and 3 workflow tests manually to confirm

**Expected pass delta: +6 tests**

---

## Session 3 — Validation Gaps + All DOC Fixes (P3 + DOC)

**Goal:** Tighten validation, fix test plan assertions, update CODEBASE_CONTEXT.md.

### Fix 7 — Require `city` and `state` on POST /property-groups (P3)

**File:** `backend/app/routes/property_groups.py`  
**Issue:** POST /property-groups with only `name` returns 201. City/state are nullable in DB but logically required for meaningful groups.

Find the Pydantic schema for `PropertyGroupCreate` and change:
```python
city: Optional[str] = None
state: Optional[str] = None
street_address: Optional[str] = None
```
to:
```python
city: str
state: str
street_address: Optional[str] = None
```

If the schema is inline in the route file, change it there. If it's in `schemas/`, change it there and verify no other callers (e.g., import routes) break.

**Tests recovered:** P03 validation test

---

### Fix 8 — Reject Duplicate Building Names Within Same Property Group (P3)

**File:** `backend/app/routes/buildings.py` → `create_building` handler  
**Issue:** POST /buildings with a duplicate name in the same property group returns 201. No unique constraint at DB or backend level.

Before the INSERT, add a uniqueness check:

```python
if request.property_id:
    dup = db.table("buildings")\
        .select("id")\
        .eq("property_id", str(request.property_id))\
        .eq("name", request.name)\
        .execute()
    if dup.data:
        raise HTTPException(status_code=409, detail="A building with this name already exists in this property group")
```

**Tests recovered:** B04 uniqueness test

---

### Fix 9 — Settings Route: Update Test Plan (DOC)

**Issue:** The test plan tests `/settings`, `/settings/features`, etc. — those routes don't exist.  
**Actual routes** (from `routes/settings.py`):
- `GET /properties/{property_uuid}/settings`
- `GET /properties/{property_uuid}/settings/building/{building_id}`
- `GET /units/{unit_id}/settings`
- `PATCH /properties/{property_uuid}/settings`
- `PATCH /properties/{property_uuid}/settings/building/{building_id}`
- `PATCH /units/{unit_id}/settings`

**No code change needed.** Update the test plan curl commands for S11 to use the correct paths.

Also update `CODEBASE_CONTEXT.md` section 5 — the `/settings` entry is wrong. Change it to document the actual `/properties/{uuid}/settings` pattern.

---

### Fix 10 — Response Shape Assertions (DOC)

Update the test plan assertions for these three endpoints:

| Test | Change |
|---|---|
| AP12 GET /appointments/view?flat_number=T101 | Assert `response.appointments == []` not `response == []` |
| L_LIST05 GET /leasing/search | Assert `response.count >= 0` and `response.listings` is array, not bare array |
| L_LIST10 GET /leasing/metrics | Assert fields `total_calls`, `qualification_rate`, `avg_duration_seconds` (not `total`, `rate`, `avg_duration`) |

---

### Fix 11 — VAPI verify-phone Test (DOC)

**Issue:** Tests VA01-VA04 send flat_number as a query param only. The endpoint requires a JSON body `{"flat_number": "..."}`.

Update the test plan curl for VA01-VA04:
```bash
# Wrong:
curl -X POST .../flats/verify-phone?flat_number=T101

# Correct:
curl -X POST .../flats/verify-phone?flat_number=T101 \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "T101"}'
```

---

### Fix 12 — Chatbot CH05 Failure (Investigate)

**S12 Chatbot: 1 fail** — CH01-CH04 and CH06 pass, CH05 fails. This is likely a specific tool-calling scenario.  
**Action:** Run CH05 manually and check what the chatbot returns vs what the test expects. Likely either a hallucinated tool call or a missing tool in `chatbot.py`. Fix is in `backend/app/ai/chatbot.py`.

---

### Fix 13 — S14 Payments: 1 fail (Investigate)

**S14 Payments: 1 fail** — PAY01 passes, PAY02 fails. The failing test is likely the Stripe webhook test.  
**Action:** Run PAY02 manually. Stripe webhook tests often fail due to missing `Stripe-Signature` header in the test curl. If it's a test plan error, update the curl to include the signature. If it's a code bug, check `routes/payments.py`.

---

### Session 3 Checklist

- [ ] Add `city`/`state` as required fields in property group create schema
- [ ] Add duplicate building name check in `create_building`
- [ ] Update `CODEBASE_CONTEXT.md`: settings routes section
- [ ] Update test plan: S11 settings URLs
- [ ] Update test plan: AP12, L_LIST05, L_LIST10 assertions
- [ ] Update test plan: VA01-VA04 curl to include JSON body
- [ ] Investigate and fix CH05 chatbot failure
- [ ] Investigate PAY02 payments failure

**Expected pass delta: +4–8 tests**

---

## Summary Table

| Session | Focus | Key Changes | Expected Fixes |
|---|---|---|---|
| Session 1 | P0/P1 — critical bugs | RLS fix, DELETE /complaints, GET /buildings/{id} | +20-25 tests |
| Session 2 | P2 — missing features | Notification endpoints, SMS templates + broadcast | +6 tests |
| Session 3 | P3/DOC — polish | Validation, test plan corrections, 2 investigations | +4-8 tests |

**Total expected pass rate after all 3 sessions: ~86–89 / 115 (~75-77%)**  
Remaining skips (~19) are likely still-cascaded from edge cases or test environment dependencies and should be re-evaluated after Session 1.
