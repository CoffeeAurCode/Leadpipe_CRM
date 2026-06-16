# Implementation Plan — Edit Features + Agent Fix
**Date:** 2026-06-05  
**Status:** Ready for parallel implementation

---

## Context: What Was Already Fixed This Session

### Complaint Agent Startup Hang (DONE — already pushed to VAPI)

The complaint agent was interrupting its own greeting because `stop_speaking_plan.numWords: 2` treated
low-confidence carrier-noise artifacts at call-connect as "2 words of user speech", which fired the
stop-speaking logic and cut the TTS mid-stream. Three fixes applied in `vapi_agent_config.py`:

| Config key | Before | After | Reason |
|---|---|---|---|
| `first_message_mode` | missing → VAPI invoked LLM to generate greeting | `"assistant-speaks-first"` | Plays hardcoded `first_message` immediately; removes ~1.5 s LLM overhead |
| `stop_speaking_plan.numWords` | `2` | `5` | Carrier noise registers as ≤2 "words"; requires 5+ clear words before yielding |
| `confidenceThreshold` | `0.4` (shared) | `0.6` (complaint-only, via `COMPLAINT_TRANSCRIBER_CONFIG`) | Filters out low-confidence noise transcriptions |

**Why the lease agent doesn't need this:** Lease agent tests used inbound calls (Twilio → VAPI), which have
minimal carrier-layer noise at connect. Complaint agent tests used VAPI outbound calls, which emit a burst
of carrier artifacts at the moment of connection. The lease agent also lacks `first_message_mode` and uses
`numWords: 2` (line 1352 in `vapi_agent_config.py`) — these remain unchanged since lease tests pass.

**RLS SELECT policy for `call_logs` (DONE — applied to Supabase)**  
Migration `023_call_logs_rls_policy.sql` added `managers_read_own_call_logs` SELECT policy.
The pre-existing `manager_owns_call_logs` ALL policy filtered by `property_group_id` which the webhook
never sets, so every row was invisible to authenticated queries.

---

## Gap Analysis — What Is Missing

| Feature | Backend | Frontend | Note |
|---|---|---|---|
| Edit property group (name, address) | ❌ No PATCH `/properties/{uuid}` | ❌ No edit modal/button | New route + new modal |
| Edit building (name, address) | ✅ `PATCH /buildings/{id}` exists | ❌ No edit button wired in PropertiesPage | Wire existing endpoint |
| Edit unit/flat | ✅ `PATCH /flats/{uuid}` exists | ✅ `FlatEditModal.jsx` exists | Verify flow only |
| Edit listings (Leasing page) | ✅ `PATCH /leasing/listings/{uuid}` exists | ✅ Pencil button in LeasingTab wired to `AddListingModal` | Verify flow only |
| Edit tenant name + phone | ✅ `TenantUpdate` schema has `name`, `phone` | ❌ `TenantProfile` form only exposes email/dates/notes | Add fields to form |
| Auto-delist occupied unit | ❌ `assign-tenant` does not touch `lease_listings` | N/A — purely backend | One-liner in `flats.py` |

---

## Parallel Workstreams

The three implementation workstreams below have **zero shared files** and can be implemented, reviewed,
and tested independently. Part A is backend-only; Parts B and C each touch backend + frontend.

```
Part A (1 file, ~15 lines)  ──────────────────────── Auto-delist on assign
Part B (2 backend + 2 frontend files) ──────────────  Edit property/building
Part C (1 frontend file) ───────────────────────────  Full tenant edit
```

---

## Part A — Auto-Delist Listing When Tenant Assigned

**Scope:** `backend/app/routes/flats.py` only. No frontend change needed.

### Problem
When a tenant is assigned to a flat, `flats.assign-tenant` sets `occupied=True` but leaves any active
`lease_listing` row for that flat visible on the Leasing AI page. This means:
- The lease agent can quote units that are actually occupied
- The Leasing tab shows occupied units as available

### Fix — `flats.py:assign_tenant` (line 302)

After the flat update succeeds, add one deactivation call:

```python
@router.patch("/{flat_uuid}/assign-tenant")
async def assign_tenant(flat_uuid: str, body: AssignTenantBody, ...):
    ...
    db.table("flats").update({"tenant_uuid": body.tenant_uuid, "occupied": True}).eq("uuid", flat_uuid).execute()
    
    # NEW: deactivate any listing for this flat so it stops appearing to the lease agent
    db.table("lease_listings").update({"is_active": False}).eq("flat_uuid", flat_uuid).execute()
    ...
```

Also apply the same fix to the **CSV import path** in `flats.py` where tenant assignment happens inline
(around line 651 — search for `"occupied": True`).

### Logical checks
- Deactivating a listing that doesn't exist is a no-op (Supabase ignores updates with 0 rows matched)
- Unassigning a tenant (`unassign-tenant`) should NOT auto-reactivate the listing — the manager decides
  when to re-list. No change to `unassign_tenant`.
- Bulk import: same rule — if a CSV row assigns a tenant, the listing is deactivated

### Test (Part A)
1. Create a flat with an active listing in LeasingTab → verify it shows in listings
2. Go to PropertiesPage → assign a tenant to that flat
3. Return to LeasingTab → listing should be gone (is_active=False)
4. Call lease agent → agent should not mention the now-occupied unit
5. Unassign tenant → listing stays inactive (manager must manually re-enable)

---

## Part B — Edit Property Groups + Buildings

### B1 — Backend: Property Group PATCH

**File:** `backend/app/routes/properties.py`

Add a new Pydantic schema `PropertyGroupUpdate` (inline in the route file or in `schemas/`) and a
`PATCH /properties/{group_uuid}` route. The existing GET handler returns `PropertyResponse` — reuse it
for the response model.

```python
class PropertyGroupUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None  # or whatever fields are on properties_list

@router.patch("/{group_uuid}", response_model=PropertyResponse)
async def update_property_group(
    group_uuid: str,
    body: PropertyGroupUpdate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = db.table("properties_list").update(payload).eq("id", group_uuid).execute()
    if not response.data:
        raise HTTPException(status_code=404, detail="Property group not found")
    return response.data[0]
```

**What fields exist on `properties_list`:** Check schema — at minimum `name` and contact/address fields.
Run `SELECT column_name FROM information_schema.columns WHERE table_name = 'properties_list'` to enumerate.

### B2 — Frontend: Edit Property Group

**File:** `frontend/src/components/AddPropertyGroupModal.jsx`  
**Modify to accept an `initialData` prop** (same double-duty pattern used by `AddListingModal`).

When `initialData` is provided:
- Pre-populate all fields from `initialData`
- Change modal title to "Edit Property Group"  
- On submit, call `apiService.updatePropertyGroup(initialData.id, payload)` instead of create

**File:** `frontend/src/services/apiService.js`  
Add: `updatePropertyGroup(groupId, data)` → `PATCH /properties/${groupId}`

**File:** `frontend/src/components/PropertiesPage.jsx`  
- Add `editGroup` state  
- Pass `editGroup` + a pencil button on `PropertyGroupCard` / the group header
- Pencil → sets `editGroup` → opens `AddPropertyGroupModal` with `initialData={editGroup}`

### B3 — Frontend: Wire Building Edit

Building PATCH already exists. The `AddBuildingModal.jsx` likely just needs an `initialData` prop  
(same pattern as listings). Check if it already supports it — if not, add the same double-duty pattern.

**File:** `frontend/src/components/BuildingCard.jsx`  
Add a pencil/edit icon button. On click → open `AddBuildingModal` with `initialData={building}`.

**File:** `frontend/src/services/apiService.js`  
Add `updateBuilding(buildingId, data)` → `PATCH /buildings/${buildingId}` if not already present.

### B4 — Verify Unit/Flat Edit (already implemented — confirm only)

`FlatEditModal.jsx` exists and `PATCH /flats/{uuid}` exists. Confirm:
- The modal opens from `UnitListPanel.jsx` or `FlatDetailModal.jsx`
- Saves flat_number, rent_amount, floor, etc.
- Unit card refreshes after save

### Logical checks (Part B)
- Property group name uniqueness: if required by DB constraint, the PATCH should propagate the
  Supabase unique-violation error to the frontend with a user-visible message
- Building: VAPI provisioning uses `properties_list.name` as the group label in the lease agent system
  prompt — if the group name changes, the lease agent will use the old name until
  `update_lease_agents.py` is re-run. Add a note in the edit modal: "VAPI agent will reflect the new
  name after the next provisioning update."
- Flat number uniqueness within a building: existing PATCH at `flats.py:696` should enforce this —
  verify it returns a 400 if a duplicate flat_number is attempted

### Tests (Part B)
1. Edit property group name → refresh page → verify new name shown
2. Edit building name → verify BuildingCard shows new name, no other buildings affected
3. Edit flat address/description → verify `FlatDetailModal` shows updated values
4. Try duplicate property group name → expect validation error (if DB constraint exists)
5. Ensure existing VAPI provisioning is not disrupted by a property group name change

---

## Part C — Full Tenant Edit (Name + Phone)

### The Gap

`TenantProfile.jsx` currently puts these fields in the edit form:
```
email, lease_start_date, lease_end_date, rent_status, payment_schedule, manager_notes, document_urls
```

**Missing:** `name` and `phone` — yet both exist in `TenantUpdate` schema and the PATCH endpoint
accepts them.

### Backend check — phone uniqueness

`PATCH /tenants/{tenant_uuid}` at `tenants.py:412` does NOT currently check for phone uniqueness
when updating. This is a logical bug: if Manager changes tenant A's phone to match tenant B's existing
phone, the DB unique constraint (if any) will throw an opaque 500-level error. Fix before exposing the
field in the UI:

```python
# Inside update_tenant, before the DB update:
if 'phone' in update_data and update_data['phone']:
    existing = db.table("tenants").select("uuid").eq("phone", update_data['phone']).neq("uuid", tenant_uuid).execute()
    if existing.data:
        raise HTTPException(status_code=400, detail="A tenant with this phone number already exists")
```

### Frontend change — TenantProfile.jsx

In `startEdit()`, add `name` and `phone` to the `form` initial state:

```javascript
const startEdit = () => {
    setForm({
        name: tenant.name || '',          // NEW
        phone: tenant.phone || '',        // NEW
        email: tenant.email || '',
        lease_start_date: tenant.lease_start_date || '',
        lease_end_date: tenant.lease_end_date || '',
        rent_status: tenant.rent_status || '',
        payment_schedule: tenant.payment_schedule || '',
        manager_notes: tenant.manager_notes || '',
        document_urls: tenant.document_urls || [],
    });
    ...
};
```

In the edit form JSX, add two new inputs in the Identity section:
- **Name field** — text input, required, max 100 chars
- **Phone field** — text input with E.164 hint (e.g. `+15145551234`), validated client-side

Format hint under phone field: `"Must be in E.164 format, e.g. +15145551234"`

### Downstream impact of phone change

When a tenant's phone number changes:
1. **VAPI verify-phone** — `POST /flats/verify-phone` looks up by phone + flat_number. Phone change
   takes effect immediately — the new number verifies; the old number no longer works. No VAPI config
   change needed.
2. **Twilio SMS** — SMS is sent to `tenant.phone` at send-time, so the new number gets future SMSes. ✓
3. **VAPI outbound calls** — `POST /voice/call/outbound` uses `tenant.phone` at call-time. ✓
4. **No stale references** — phone is not cached anywhere in VAPI config. ✓

### Logical checks (Part C)
- Empty name must be rejected (name is a required field in the DB)
- Phone must match E.164 pattern before the PATCH is sent; show inline error, not an alert
- If name changes, TenantManagement list should reflect immediately (state update via `onUpdate`)
- If phone changes, existing call_logs are NOT retroactively updated — acceptable, historical data

### Tests (Part C)
1. Edit tenant name → TenantManagement list shows new name, TenantProfile header shows new name
2. Edit phone to a valid new E.164 number → call the complaint agent with the new number → verify
   phone verification succeeds
3. Edit phone to the SAME number as another tenant → expect 400 "already exists" error shown inline
4. Try to save with empty name → expect validation error (do not send PATCH)
5. Edit email + name + phone in one save → all three fields updated in DB
6. Verify other tenant's data is not affected (isolation check)

---

## Integration Test Plan (run after all three parts pass unit tests)

These tests verify that the three workstreams don't break each other or existing features.

### I1 — Assign-delist + lease agent consistency
1. Add a listing for unit T2B01
2. Verify lease agent returns T2B01 when searching for 2-beds
3. Assign a tenant to T2B01 (Part A fix)
4. Call lease agent again — T2B01 must NOT appear in search results
5. Check LeasingTab → listing shows `inactive`
6. Unassign tenant → listing stays inactive → lease agent still doesn't offer T2B01 ✓

### I2 — Property group rename + building edit do not affect complaints
1. Rename property group to "New Name"
2. Rename its building to "New Building"
3. File a complaint call via the complaint agent
4. Verify complaint is created with correct `property_group_id` (UUID, not name — rename is safe) ✓

### I3 — Phone edit does not break existing call log linkage
1. Edit a tenant's phone number
2. Call the complaint agent from the NEW phone → verify verification passes
3. Confirm call_log is created with the new `manager_id`
4. Check VoiceStatsTab → call appears ✓

### I4 — CSV import still auto-deactivates listings
1. Have an active listing for a flat
2. Import a CSV with a tenant row that references that flat
3. Verify the listing is deactivated (Part A fix applied to import path)
4. Verify tenant is linked and flat is marked occupied

### I5 — Regression: existing edit flows still work
1. Edit a lease listing (already implemented) → confirm save works, no regression
2. Edit a flat/unit via FlatEditModal (already implemented) → confirm save works
3. Edit tenant lease dates via TenantProfile → confirm existing fields still save correctly

---

## Implementation Order & Parallelism

```
Sprint 1 (all parallel):
  Developer A → Part A (auto-delist)         ~30 min, 1 file
  Developer B → Part B (property/building)   ~2-3 hr, 4 files
  Developer C → Part C (tenant name/phone)   ~1 hr, 2 files

Sprint 2 (after Sprint 1 merges):
  All → Integration tests I1–I5
```

If solo developer:
1. Part A first (smallest, highest risk to data correctness if left out)
2. Part C next (self-contained frontend + small backend patch)
3. Part B last (most files, longest)

---

## Files Touched Summary

| Part | File | Change |
|---|---|---|
| A | `backend/app/routes/flats.py` | Add `lease_listings` deactivation in `assign_tenant` + CSV import path |
| B | `backend/app/routes/properties.py` | New `PATCH /properties/{group_uuid}` route |
| B | `frontend/src/components/AddPropertyGroupModal.jsx` | Add `initialData` prop for edit mode |
| B | `frontend/src/components/BuildingCard.jsx` | Add edit pencil → open `AddBuildingModal` |
| B | `frontend/src/services/apiService.js` | Add `updatePropertyGroup()`, `updateBuilding()` if missing |
| B | `frontend/src/components/PropertiesPage.jsx` | Wire `editGroup` state → `AddPropertyGroupModal` |
| C | `backend/app/routes/tenants.py` | Add phone-uniqueness check in `update_tenant` |
| C | `frontend/src/components/TenantProfile.jsx` | Add `name` + `phone` to edit form and JSX |

**No CODEBASE_CONTEXT.md update needed until implementation is complete.**

---

## Risks & Edge Cases

| Risk | Where | Mitigation |
|---|---|---|
| Property group name change breaks lease agent system prompt | VAPI agent config | System prompt uses group name for context only (not as a lookup key). Add UI note to re-run `update_lease_agents.py` |
| Tenant phone change confuses existing VAPI sessions | VAPI | No session continuity for already-ended calls. Only affects future calls — acceptable |
| Deactivating listing for a unit with multiple listings | Part A | `lease_listings.flat_uuid` is a foreign key and multiple rows can share it. The fix uses `.eq("flat_uuid", flat_uuid)` without `.limit(1)`, so ALL listings for that flat are deactivated — correct behaviour |
| Building edit clears VAPI provisioning fields | buildings table | `PATCH /buildings/{id}` only updates fields in `BuildingUpdate` schema. VAPI fields (`vapi_*`) are not in `BuildingUpdate` — safe |
| Phone change + Twilio number pool | Twilio pool | Twilio pool numbers are assigned to property groups, not tenants. Phone change is tenant-level only — no Twilio config impact |
