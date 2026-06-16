# Implementation Plan — CHANGE_SPECS.md Fixes

> Implement items **in the order listed**. Some items depend on earlier ones (e.g. #7 backend enrichment feeds into #8). After each item passes all of its verification steps, edit `CHANGE_SPECS.md` and check the box in the Summary checklist.

---

## How to check a box after completion

In `CHANGE_SPECS.md`, change:
```
- [ ] **N** — …
```
to:
```
- [x] **N** — …
```

---

## Fix 1 — Lead Detail: "Unit delisted" pill instead of raw UUID

### Files
- `frontend/src/components/LeadDetailModal.jsx` — lines 154–183

### What to change
`findListing(uuid)` returns `undefined` when the listing was deleted. Currently the fallback renders the raw UUID string.

**Primary listing (line ~160):**
```jsx
// BEFORE
{primary ? `${primary.flat_number}…` : lead.listing_uuid}

// AFTER
{primary
  ? `${primary.flat_number}${primary.monthly_rent ? ` — $${Number(primary.monthly_rent).toLocaleString('en-CA')}/mo` : ''}`
  : <span className="font-mono text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">Unit delisted</span>
}
```

**Also-interested chips (line ~175):**
```jsx
// BEFORE
{l ? l.flat_number : id}

// AFTER
{l
  ? l.flat_number
  : <span className="font-mono text-xs bg-muted text-muted-foreground px-2 py-0.5 rounded">Unit delisted</span>
}
```

### Verification steps
1. Open a lead whose listing still exists → flat number + rent shows normally.
2. Delete a listing from the Leasing tab, then re-open the lead that referenced it → pill shows "Unit delisted" (grey), no UUID, no crash.
3. Open a lead with `interested_listing_ids` containing a deleted listing → each deleted entry shows "Unit delisted" pill; existing ones still show flat numbers.
4. Open a lead with `listing_uuid = null` → Matched Listings section is hidden entirely (existing behaviour).

### Regression checks
- Other parts of `LeadDetailModal` (name, phone, qualification status, qualifying answers) render normally.
- No console errors.

---

## Fix 2 — Property group delete: cascade order + tenant-block warning

### Files
- `backend/app/routes/property_groups.py` — `delete_property_group` (~line 381) and `bulk_delete_property_groups` (~line 347)
- `frontend/src/components/PropertiesPage.jsx` (or wherever the delete button calls the API)
- `frontend/src/services/apiService.js` — ensure `deletePropertyGroup(id, force=false)` passes `?force=true`

### Backend changes

#### A. Fix cascade order in BOTH routes

Correct order for `delete_property_group` (single) — replaces the existing cascade block:
```
1. buildings query → building_ids
2. flats query → flat_uuids, tenant_uuids
3. listings query → listing_uuids
4. lease_leads.update(listing_uuid=NULL)  ← already done, keep it
5. lease_listings.delete by flat_uuid
6. rents.delete by flat_uuid
7. complaints.delete by tenant_uuid        ← NEW (missing step)
8. appointments.delete by tenant_uuid      ← NEW (missing step)
9. call_logs.delete by tenant_uuid         ← NEW (missing step, if FK exists)
10. tenants.delete by uuid
11. flats.delete by building_id
12. buildings.delete by property_id
13. properties_list.delete by id
```

Steps 7–9 must guard `if tenant_uuids:` before executing to avoid empty `IN ()` errors.

Replicate steps 3–9 into `bulk_delete_property_groups` (currently missing steps 3–4 for leads nullification and missing 7–9 entirely).

#### B. Tenant-block 409 warning

**In `delete_property_group`:** Before executing any destructive step, check `force` query param:
```python
@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_group(
    property_id: str,
    force: bool = Query(False),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
```
After gathering `tenant_uuids`, if `not force and tenant_uuids`:
```python
return JSONResponse(
    status_code=409,
    content={
        "detail": "tenant_block",
        "tenant_count": len(tenant_uuids),
        "message": f"This property contains {len(tenant_uuids)} active tenant(s). Confirm deletion.",
    }
)
```
`status_code=204` must become `status_code=200` when returning JSON on the 409 path — or use `Response` directly. The cleanest way: change the decorator to `status_code=200` and return `Response(status_code=204)` on success, or change `response_model` to `None` and return `JSONResponse` for the 409 only while keeping `return None` for 204.

**In `bulk_delete_property_groups`:** Same check per group — if any group has tenants and `force` is not set, return HTTP 409 with the same structure.

#### C. `apiService.js`

Add/update `deletePropertyGroup`:
```js
export async function deletePropertyGroup(groupId, force = false) {
  const qs = force ? '?force=true' : '';
  return authFetch(`/property-groups/${groupId}${qs}`, { method: 'DELETE' });
}
```

### Frontend changes

In `PropertiesPage.jsx` (wherever `deletePropertyGroup` is called):

```js
const handleDeleteGroup = async (groupId) => {
  try {
    await deletePropertyGroup(groupId);
    // success — refresh list
  } catch (err) {
    if (err?.detail === 'tenant_block') {
      const confirmed = window.confirm(
        `This property has ${err.tenant_count} active tenant(s). Delete them too?`
      );
      if (confirmed) {
        await deletePropertyGroup(groupId, true);
        // refresh list
      }
    } else {
      // show generic error
    }
  }
};
```

(If a dedicated `ConfirmModal` exists, use it instead of `window.confirm`.)

### Verification steps
1. Delete a property group with **no tenants** → deletes cleanly, no 409, no 500.
2. Delete a property group with **active tenants** → 409 dialog appears with correct tenant count.
3. Manager clicks **Cancel** on dialog → nothing is deleted.
4. Manager clicks **Confirm** → re-sends with `?force=true` → cascade deletes successfully, group disappears from list.
5. Bulk-delete a group with tenants → same 409 flow.
6. Verify that `complaints`, `appointments`, `call_logs` referencing those tenants are gone after force-delete (check Supabase table).

### Regression checks
- Deleting a group with no buildings → still works.
- Deleting a building directly (`DELETE /buildings/{id}`) → unaffected.
- Property group list refreshes after delete.

---

## Fix 3 — Stale unit / building count (DB cleanup)

### This is primarily a data fix, not a code change.

### Manual DB cleanup (run in Supabase SQL Editor)

```sql
-- Find orphaned property groups (no buildings reference them)
SELECT id, name FROM properties_list
WHERE id NOT IN (SELECT DISTINCT property_id FROM buildings WHERE property_id IS NOT NULL);

-- Find orphaned buildings (property group row deleted)
SELECT id, name FROM buildings
WHERE property_id NOT IN (SELECT id FROM properties_list);

-- Delete orphaned buildings first (FK order)
DELETE FROM buildings
WHERE property_id NOT IN (SELECT id FROM properties_list);

-- Then delete orphaned property groups if any
DELETE FROM properties_list
WHERE id NOT IN (SELECT DISTINCT property_id FROM buildings WHERE property_id IS NOT NULL)
  AND id NOT IN (SELECT DISTINCT property_group_id FROM flats WHERE property_group_id IS NOT NULL);
  -- Adjust the second condition to your schema if needed
```

### Code change (guard against future partial state)

In `delete_property_group` and `bulk_delete_property_groups`, the entire cascade already runs inside a `try/except`. No additional atomicity is possible without a Postgres function (RPC). At minimum, log each step failure clearly so partial state is detectable:

After each delete step, add:
```python
result = db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
# No error = good. PostgREST raises on FK violations.
```

Future improvement (out of scope for this sprint): wrap the cascade in a Supabase RPC stored procedure for true atomicity.

### Verification steps
1. After running the SQL cleanup, the Properties page shows correct building counts.
2. Each building shows correct unit counts.
3. No orphaned rows remain (run the SELECT queries again → 0 results).

---

## Fix 4 — Building modal: auto-fill `street_address` from property group

### Files
- `frontend/src/components/AddBuildingModal.jsx` — `useEffect` at line 52

### What to change

In the existing `useEffect` that copies `city`, `state`, `country`:
```js
// BEFORE (line ~56-62)
setForm(prev => ({
    ...prev,
    city: pg.city || prev.city,
    state: pg.state || prev.state,
    country: pg.country || prev.country,
}));

// AFTER
setForm(prev => ({
    ...prev,
    street_address: pg.street_address || prev.street_address,   // ← add this
    city: pg.city || prev.city,
    state: pg.state || prev.state,
    country: pg.country || prev.country,
}));
```

Also make `street_address` required:
- Change the label in the JSX from `"Street Address (optional)"` to `"Street Address *"`.
- In `handleSubmit`, add validation before the `try`:
  ```js
  if (!form.street_address.trim()) { setError('Street Address is required.'); setLoading(false); return; }
  ```
- Remove the conditional `if (form.street_address)` guard in the payload builder — always include it.

### Verification steps
1. Open "Add Building" for a property group that has a `street_address` → `street_address` field is pre-filled, city/state/country still auto-filled as before.
2. Open "Add Building" for a property group with no `street_address` → field is empty (no crash).
3. Try submitting with empty `street_address` → inline error "Street Address is required." appears.
4. Edit an existing building (edit mode) → auto-fill does NOT run (guarded by `!initialData`), existing values preserved.

### Regression checks
- City/state/country auto-fill still works.
- Edit mode (initialData present) still populates from `initialData`, not from parent property group.
- Building creation succeeds end-to-end with the street_address included in the payload.

---

## Fix 5 — Unit modal: auto-fill `street_address` from building

### Files
- `backend/app/routes/buildings.py` — `GET /buildings/{id}/units` (unit list endpoint)
- `frontend/src/components/FlatEditModal.jsx` — flat details tab

### Backend change

In the route that returns units for a building, join the `buildings` row to include `building_street_address` in each flat record:

```python
# In GET /buildings/{id}/units (or wherever units are fetched for a building)
# Current: returns raw flats rows
# Change: after fetching flats, fetch the building's street_address and attach it

building_resp = db.table("buildings").select("street_address").eq("id", building_id).execute()
building_street_address = building_resp.data[0].get("street_address", "") if building_resp.data else ""

units = flats_resp.data
for unit in units:
    unit["building_street_address"] = building_street_address
```

Alternatively, use PostgREST select to join:
```python
db.table("flats").select("*, buildings(street_address)").eq("building_id", building_id).execute()
```
Then flatten: `unit["building_street_address"] = unit.get("buildings", {}).get("street_address", "")`.

### Frontend change

In `FlatEditModal.jsx`, when the modal opens and `flatData.street_address` is empty, pre-fill from `flat.building_street_address`:

```js
useEffect(() => {
    if (isOpen && flat) {
        setFlatData(prev => ({
            ...prev,
            street_address: flat.street_address || flat.building_street_address || '',
            // address_line stays empty/optional
        }));
    }
}, [isOpen, flat]);
```

The `address_line` field stays optional with no auto-fill.

### Verification steps
1. Open `FlatEditModal` for a flat with no `street_address` whose building has a `street_address` → `street_address` field is pre-filled with the building's value.
2. Open `FlatEditModal` for a flat that already has its own `street_address` → existing value is preserved (not overwritten by building's).
3. `address_line` is always empty by default.
4. Saving the form persists the pre-filled `street_address` to the DB.

### Regression checks
- Unit list API still returns all existing flat fields (no regressions on other consumers).
- FlatEditModal edit form still works for all other fields.

---

## Fix 6 — Phone and email validation

### Files
- `frontend/src/components/AddTenantModal.jsx`
- `frontend/src/components/FlatEditModal.jsx`
- `frontend/src/components/TenantProfile.jsx` (already has E.164 validation per CODEBASE_CONTEXT — verify it matches the spec)

### Phone rule
Regex: `/^\+[1-9]\d{9,14}$/`
Error message: `"Enter a valid phone number with country code (e.g. +16135551234)"`

### Email rule (if collected)
Regex: `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
Error message: `"Enter a valid email address"`

### Implementation pattern (same in each modal)

```js
const PHONE_RE = /^\+[1-9]\d{9,14}$/;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function validatePhone(val) {
    return !val || PHONE_RE.test(val)
        ? null
        : 'Enter a valid phone number with country code (e.g. +16135551234)';
}
function validateEmail(val) {
    return !val || EMAIL_RE.test(val)
        ? null
        : 'Enter a valid email address';
}
```

In `handleSubmit`:
```js
const phoneErr = validatePhone(form.phone);
const emailErr = validateEmail(form.email);
if (phoneErr || emailErr) {
    setError(phoneErr || emailErr);
    return;
}
```

Display error inline below the field or via the existing `error` state.

### Backend (second layer — optional but recommended)

In `backend/app/schemas/tenant.py`, add Pydantic field_validator:
```python
from pydantic import field_validator
import re

PHONE_RE = re.compile(r'^\+[1-9]\d{9,14}$')

@field_validator('phone')
@classmethod
def validate_phone(cls, v):
    if v and not PHONE_RE.match(v):
        raise ValueError('Phone must be E.164 format, e.g. +16135551234')
    return v
```

### Verification steps
1. Submit `AddTenantModal` with phone `0612345678` → inline error, API not called.
2. Submit with phone `+16135551234` → succeeds.
3. Submit with phone left blank (if optional) → succeeds.
4. Submit with invalid email `foo@` → inline error, API not called.
5. Submit with valid email `foo@bar.com` → succeeds.
6. Same tests in `FlatEditModal` tenant phone field.

### Regression checks
- Existing tenants with valid E.164 phones can still be edited without error.
- `TenantProfile.jsx` existing validation unchanged (verify it already uses the same regex).

---

## Fix 7 — Listing dropdown: show building + property name for each vacant unit

### Files
- `backend/app/routes/flats.py` — `GET /flats?vacant=true` (~line 278)
- `frontend/src/components/AddListingModal.jsx` — unit dropdown (~line 167)
- `frontend/src/components/AddTenantModal.jsx` — unit dropdown (same pattern)

### Backend change

In `get_all_flats`, when `vacant=True`, join through `buildings` and `properties_list`:

```python
# Current
query = db.table("flats").select("*").order("address").order("flat_number")
if vacant:
    query = query.is_("tenant_uuid", "null")
response = query.execute()
return response.data

# Change: use PostgREST embed to join building name + property name
if vacant:
    query = (
        db.table("flats")
        .select("*, buildings(name, property_id, properties_list(name))")
        .is_("tenant_uuid", "null")
        .order("flat_number")
    )
    response = query.execute()
    rows = response.data
    for row in rows:
        b = row.pop("buildings", None) or {}
        row["building_name"] = b.get("name", "")
        pg = (b.get("properties_list") or {})
        row["property_name"] = pg.get("name", "") if isinstance(pg, dict) else ""
    return rows
```

If PostgREST nested join syntax causes issues, fall back to two separate queries (fetch flats, then building ids, then buildings+properties).

The `FlatResponse` schema will need `building_name: Optional[str] = None` and `property_name: Optional[str] = None` added so Pydantic doesn't strip these fields.

### Frontend change

In both `AddListingModal.jsx` and `AddTenantModal.jsx`, update the `<option>` / display label:

```jsx
// BEFORE
`${flat.flat_number} — ${flat.address || 'no address'}`

// AFTER
const location = [flat.building_name, flat.property_name].filter(Boolean).join(', ')
    || flat.street_address
    || 'No address';
`${flat.flat_number} — ${location}`
```

### Verification steps
1. Open "Add Listing" → unit dropdown shows `101 — Main Building, Maple Gardens` (building + property).
2. A flat with no building_name falls back to street_address or "No address".
3. Selecting a unit from the dropdown and saving the listing works normally.
4. Same in "Add Tenant" unit dropdown.

### Regression checks
- `GET /flats` without `?vacant=true` still returns the normal flat list (check the `if vacant:` guard).
- `FlatResponse` schema still validates for existing consumers that don't send `building_name`.
- No 500 errors on the flats list page.

---

## Fix 8 — Lease agent: unit full address in tool responses

### Files
- `backend/app/routes/leasing.py` — `GET /leasing/listings` and VAPI tool endpoints (`find-listing`, `search`)
- `backend/app/services/vapi_agent_config.py` — tool response schemas shown to the agent

### Backend change

#### `GET /leasing/find-listing` and `GET /leasing/search`

In both endpoints, after fetching the listing row, join to get building + property address:

```python
# For each listing, look up building address chain
flat_resp = db.table("flats").select("building_id, street_address, city, state").eq("uuid", listing["flat_uuid"]).execute()
flat = flat_resp.data[0] if flat_resp.data else {}
building_resp = db.table("buildings").select("name, street_address, city, state, properties_list(name)").eq("id", flat.get("building_id", "")).execute()
b = building_resp.data[0] if building_resp.data else {}
pg = (b.get("properties_list") or {})

address_parts = [
    listing.get("flat_number"),
    b.get("name", ""),
    b.get("street_address") or flat.get("street_address", ""),
    b.get("city") or flat.get("city", ""),
]
listing["address"] = ", ".join(p for p in address_parts if p)
listing["building_name"] = b.get("name", "")
listing["property_name"] = pg.get("name", "") if isinstance(pg, dict) else ""
```

Keep the existing `address` field name so the agent's existing prompt references still work. If `address` is not yet in the response, add it.

#### `vapi_agent_config.py` tool schemas

In `build_lease_config` and `build_lease_config_shared`, update the `search_available_listings` and `find_listing` tool result descriptions to mention that each listing now includes an `address` field:

```python
"description": "Returns listings matching search criteria. Each listing has: listing_uuid, flat_number, address (full human-readable address), bedrooms, monthly_rent, floor_number, available_from, title."
```

No change needed to agent system prompt — the existing rule ("only mention address if caller has location preferences") already handles this correctly.

### Verification steps
1. Call `GET /leasing/find-listing?query=101&property_group_id=...` → response includes `"address": "101, Main Building, 123 Oak St, Ottawa"`.
2. Call `GET /leasing/search?property_group_id=...` → each listing in `listings` array has `address` field.
3. Make an outbound lease agent call and ask "do you have anything on Oak Street?" → agent answers with address context.

### Regression checks
- `GET /leasing/listings` (manager CRUD endpoint) unaffected — it doesn't need address enrichment.
- Agent still only mentions address when caller asks location-specific questions.
- `find-listing` and `search` still return all existing fields (`listing_uuid`, `monthly_rent`, `available_from`, etc.).

---

## Fix 9 — Listing not refreshed after tenant assignment

### Files
- `frontend/src/components/LeasingTab.jsx`
- `frontend/src/components/AssignTenantModal.jsx`
- `frontend/src/components/AddTenantModal.jsx`

### Pattern (mirrors existing `refresh-appointments`)

#### `LeasingTab.jsx`

In the `useEffect` that mounts event listeners, add:
```js
const onRefreshListings = () => load();
window.addEventListener('refresh-listings', onRefreshListings);
return () => {
    window.removeEventListener('refresh-listings', onRefreshListings);
};
```

#### `AssignTenantModal.jsx` — after successful tenant assignment:
```js
window.dispatchEvent(new Event('refresh-listings'));
```

#### `AddTenantModal.jsx` — after successful tenant creation + flat assignment:
```js
window.dispatchEvent(new Event('refresh-listings'));
```

### Verification steps
1. Go to Leasing tab — a listing shows as Active.
2. Open a flat and assign a tenant via `AssignTenantModal` → without navigating away, check Leasing tab → listing now shows as inactive (no manual refresh needed).
3. Same test via `AddTenantModal` (create new tenant → listing deactivates in Leasing tab automatically).

### Regression checks
- Leasing tab's `load()` function still handles errors gracefully (existing try/catch).
- Other event listeners (`refresh-appointments`, etc.) in LeasingTab are unaffected.
- Assigning a tenant still works end-to-end (200 from backend, flat shows occupied in properties view).

---

---

## Fix 10 — Lease lead shows "Unknown" when no listings are available

### Root cause

`submit_lease_lead` is configured as `"async": True` in the VAPI tool definition (`vapi_agent_config.py` line 1275). VAPI fires the apiRequest to `/voice/lease-lead-direct` without waiting for a response, then immediately sends the end-of-call-report to `/voice/lease-eoc-webhook`.

**Race condition:**
1. Call ends — VAPI fires EOC to `lease-eoc-webhook` almost instantly.
2. `lease-eoc-webhook` checks `lease_leads` for `call_id` → finds nothing (the async apiRequest hasn't committed yet) → creates a fallback lead with `caller_name: "Unknown"`.
3. `lease_lead_direct` arrives with the real data (`caller_name: "Supah and Son"`) → finds the "Unknown" lead as a duplicate → returns `{"status": "duplicate"}` without saving.
4. Only the "Unknown" lead remains in the DB.

This hits specifically in the "no listings" scenario because the agent calls `submit_lease_lead` immediately before ending the call — leaving minimal time between the async request and the EOC.

### Files
- `backend/app/routes/voice.py` — `lease_lead_direct` function (~line 805)

### What to change

In `lease_lead_direct`, replace the current duplicate-bail-out with an **upsert**: if the existing record was created by the EOC fallback (`caller_name = "Unknown"`), update it with the real data.

```python
# BEFORE (line ~805)
if call_id:
    dup = db.table("lease_leads").select("id").eq("call_id", call_id).limit(1).execute()
    if dup.data:
        print(f"  [DUPLICATE] call_id={call_id} already exists")
        return {"status": "duplicate"}

# AFTER
if call_id:
    dup = db.table("lease_leads").select("id, caller_name").eq("call_id", call_id).limit(1).execute()
    if dup.data:
        existing_name = dup.data[0].get("caller_name", "Unknown")
        if existing_name == "Unknown" and lead_data.get("caller_name"):
            # EOC fallback beat us here — update the placeholder with real data
            update_payload = {
                "caller_name": lead_data.get("caller_name"),
                "qualification_status": lead_data.get("qualification_status") or "unmatched",
                "notes": lead_data.get("notes"),
                "bedrooms": lead_data.get("bedrooms") or None,
                "budget_max": lead_data.get("budget_max") or None,
                "move_in_timeline": lead_data.get("move_in_timeline"),
                "occupants": lead_data.get("occupants") or None,
                "floor_preference": lead_data.get("floor_preference"),
                "disqualifying_reason": lead_data.get("disqualifying_reason"),
                "qualifying_answers": qualifying_answers,
                "listing_uuid": listing_uuid,
                "interested_listing_ids": interested_ids,
                "property_group_id": str(property_group_id) if property_group_id else None,
                "manager_id": str(manager_id) if manager_id else None,
            }
            db.table("lease_leads").update(update_payload).eq("id", dup.data[0]["id"]).execute()
            print(f"  [UPDATED] Overwrote EOC placeholder with real caller_name={update_payload['caller_name']}")
        else:
            print(f"  [DUPLICATE] call_id={call_id} already exists with real name, skipping")
        return {"status": "duplicate"}
```

Note: the `qualifying_answers` variable is computed earlier in the function (lines ~823–832), so the update block can reference it directly. The `listing_uuid`, `property_group_id`, `manager_id`, and `interested_ids` variables are also computed before this block.

### Verification steps
1. Make a call to the lease agent when **no listings exist** → agent collects name, ends call.
2. Check the Leads list → caller name shows correctly (e.g., "Supah and Son"), not "Unknown".
3. Make a call when **listings exist** → full qualified/unmatched flow still works, name is correct.
4. Make two rapid calls with the same scenario → no duplicate "Unknown" leads created.
5. Check server logs: should see `[UPDATED] Overwrote EOC placeholder with real caller_name=...` in the no-listings scenario.

### Regression checks
- Normal calls (listings available, tool fires mid-conversation with time to spare) → EOC arrives after `lease_lead_direct` already committed → EOC ignores (existing behaviour unchanged).
- Calls where `submit_lease_lead` is genuinely never called (agent crashes, caller hangs up immediately) → `lease-eoc-webhook` still creates the "Unknown" fallback lead as before.
- `caller_name: "Unknown"` records created by other means are not accidentally overwritten (the update only fires when the apiRequest arrives for the same `call_id`).

---

## Completion workflow

After each fix is implemented and all verification steps pass:

1. Edit `CHANGE_SPECS.md` — change `- [ ] **N**` to `- [x] **N**` for that item.
2. Commit with message: `fix: [brief description] (spec N)`

Run a final smoke test after all 10 fixes:
- Create a property group → building auto-fills street_address.
- Create a listing → dropdown shows building + property name.
- Assign tenant → listing goes inactive in Leasing tab instantly.
- Delete a property group with tenants → 409 warning → confirm → cascade succeeds.
- Open a lead with a deleted listing → "Unit delisted" pill shown.
- Invalid phone in Add Tenant → inline error, no API call.
- Call lease agent with no listings → lead appears in list with correct caller name, not "Unknown".
