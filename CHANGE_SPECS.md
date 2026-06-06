# Change Specs — Pending Fixes & Logic

All items below are scoped, unimplemented bugs or feature gaps identified on 2026-06-06.
No code has been changed yet. Implement each section in order (some have dependencies).

---

## 1. Lead Detail: UUID shown instead of unit name when listing is deleted

**Where:** `frontend/src/components/LeadDetailModal.jsx` — lines 154–183

**Root cause:** `findListing(uuid)` returns `undefined` when the listing no longer exists in
the `listings` array (listing was deleted). The current fallback is to display the raw UUID string.

**Fix:**
- Primary listing (`lead.listing_uuid`): if `findListing()` is undefined, show a pill with
  text `"Unit delisted"` (muted/grey styling) instead of the UUID.
- Also-interested IDs (`lead.interested_listing_ids`): same — each unresolved ID shows
  `"Unit delisted"` pill, not the raw UUID.

**No backend change needed.** The frontend already has `listings` passed as a prop.

---

## 2. Property group delete: warn about tenants, then cascade-delete everything

**Where:** `backend/app/routes/property_groups.py` — `delete_property_group` (line 381)
and `bulk_delete_property_groups` (line 347)

**Problem A — 500 error with tenants present:**
The cascade order is wrong. When flats contain tenants, `complaints` and `call_logs` tables
likely have FK constraints (`tenant_uuid → tenants.uuid`) with no `ON DELETE CASCADE` in
the DB. Deleting `tenants` rows while those FK rows still exist causes a PostgREST 409.

**Correct cascade order (for both `delete_property_group` and `bulk_delete_property_groups`):**
```
1. Gather flat_uuids and tenant_uuids for the group
2. Gather listing_uuids for those flat_uuids
3. lease_leads  → update listing_uuid = NULL  (already done for single-delete; replicate to bulk)
4. lease_listings → delete by flat_uuid
5. rents        → delete by flat_uuid
6. complaints   → delete by tenant_uuid (if tenant_uuids not empty)
7. appointments → delete by tenant_uuid (if tenant_uuids not empty)
8. call_logs    → delete by tenant_uuid  (check if FK exists; delete if so)
9. tenants      → delete by uuid
10. flats       → delete by building_id
11. buildings   → delete by property_id
12. properties_list → delete by id
```
Step 3 (leads nullification) is already in `delete_property_group` but missing from
`bulk_delete_property_groups` — add it there too.

**Problem B — should warn manager before deleting tenants:**
Before executing any destructive steps, the route should check if any tenant_uuids are
present. If yes, return HTTP 409 with a structured response:
```json
{
  "detail": "tenant_block",
  "tenant_count": 3,
  "message": "This property contains 3 active tenant(s). Confirm deletion."
}
```
The frontend shows a confirmation dialog ("This property has 3 active tenants. Delete them
too?"). If the manager confirms, the frontend re-sends the DELETE request with query param
`?force=true`. The backend skips the 409 check when `force=true` and proceeds with full
cascade.

**Frontend:** `PropertiesPage.jsx` (or wherever delete is triggered) — intercept the 409
`"tenant_block"` response, show confirmation modal, then re-call with `?force=true`.

---

## 3. Building shows stale unit count / property group shows stale building count

**Root cause:** Previous failed cascade deletes (before the FK fixes were deployed) left the
DB in a partial state — buildings or flats may have been deleted while the property group row
still exists, or vice versa. The counts are computed live from DB joins, so if the DB is
consistent, the counts should be correct.

**Immediate action:** Clean up orphaned records in Supabase directly:
- Run: `SELECT id FROM properties_list WHERE id NOT IN (SELECT DISTINCT property_id FROM buildings)`
  to find orphaned property groups.
- Run: `SELECT id FROM buildings WHERE property_id NOT IN (SELECT id FROM properties_list)`
  to find orphaned buildings.
- Delete orphaned rows manually.

**Code change (prevent future partial state):** The cascade delete route should wrap all
delete steps in a single Postgres function call (RPC) so they are atomic, OR use the service
client and catch any FK error at each step to roll back / report clearly. For now, at minimum
wrap the whole try block so that if any step fails the error is surfaced cleanly (the 500 is
already caught, but no partial-state cleanup happens).

---

## 4. Building address auto-fill from property street_address

**Where:** `frontend/src/components/AddBuildingModal.jsx` — `useEffect` at line 52

**Current:** Only `city`, `state`, `country` are copied from the parent property group.
`street_address` is left blank and labelled `(optional)`.

**Fix:**
1. In the useEffect that runs on `[isOpen, initialPropertyId, propertyGroups, initialData]`:
   also copy `pg.street_address` into `form.street_address` when creating a new building.
2. Change the `street_address` label from `"Street Address (optional)"` to `"Street Address *"`
   and add client-side required validation (same pattern as city/state).
3. `address_line` stays optional and empty by default — no change there.

The backend `createBuilding` payload already passes `street_address` through, so no backend
change is needed.

---

## 5. Unit (flat) address auto-fill from building street_address

**Where:** `frontend/src/components/FlatEditModal.jsx` — the flat details tab

**Current:** When the manager edits a flat's address, all fields start from the flat's own
saved values (or blank). There is no auto-fill from the building.

**Fix (edit mode only — flat creation is not exposed via a standalone modal today):**
When `FlatEditModal` opens on a flat that has no `street_address` yet, pre-fill `street_address`
from the building's address. This requires the flat data passed to the modal to include the
building's `street_address` field, which means:
1. Backend `GET /buildings/{id}/units` already returns full flat records. The building's own
   `street_address` should be included in the unit list response so the frontend can read it.
   Add `building_street_address` to each flat record in the unit list (join from buildings row).
2. Frontend `FlatEditModal`: if `flat.street_address` is empty and `flat.building_street_address`
   is present, pre-fill `flatData.street_address` with it.
3. `address_line` remains empty and optional by default.

---

## 6. Phone number and email format validation

**Where:**
- `frontend/src/components/AddTenantModal.jsx` — phone field (currently any string accepted)
- `frontend/src/components/FlatEditModal.jsx` — tenant phone field
- Any other form that collects phone or email for tenants

**Phone rule:**
- Must be in E.164 format: `+<country_code><number>`, digits only after `+`, total length
  10–15 digits (e.g., `+16135551234`).
- Regex: `/^\+[1-9]\d{9,14}$/`
- Show inline error: "Enter a valid phone number with country code (e.g. +16135551234)"
- Do NOT save if validation fails.

**Email rule (if collected):**
- Standard HTML5 email pattern: `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`
- Show inline error: "Enter a valid email address"

**Implementation:** Add a `validatePhone(val)` helper in each modal (or extract to a shared
util). Run it on submit before calling the API. The backend can also add a Pydantic
`field_validator` on `phone` in the tenant schema as a second layer.

---

## 7. Listing modal: show building and property name for each vacant unit

**Where:**
- Backend: `GET /flats?vacant=true` (`backend/app/routes/flats.py` line 278–290)
- Frontend: `frontend/src/components/AddListingModal.jsx` line 167 — unit dropdown
- Frontend: `frontend/src/components/AddTenantModal.jsx` — same dropdown

**Current:** `fetchVacantFlats()` calls `GET /flats?vacant=true` which returns raw flat rows.
The `address` field is often empty. The dropdown shows:
```
101 — no address
```

**Fix — backend:** Enrich the `GET /flats?vacant=true` response to include building name
and property group name by joining through `buildings` and `properties_list`. Add two fields
to each flat row:
```
building_name   — from buildings.name
property_name   — from properties_list.name
```
Join: `flats.building_id → buildings.id → buildings.property_id → properties_list.id`

**Fix — frontend:** Update the dropdown option label to:
```
{flat_number} — {building_name}, {property_name}
```
If either join field is missing, fall back gracefully:
```
{flat_number} — {building_name || property_name || street_address || 'No address'}
```

---

## 8. Lease agent: units shown with proper full address

**Where:** `backend/app/services/vapi_agent_config.py` — `load_listings` and
`search_listings` tool response schemas and the listing records returned to the agent.

**Current:** Listing tool results include `flat_number` but no building or property address
context. The agent cannot meaningfully answer "which units are on Oak Street?" or
"do you have anything in downtown?"

**Fix — backend:**
1. In `GET /leasing/listings` (and the internal listing loader for the VAPI tools), join
   each listing row with its flat → building → property chain to include:
   - `building_name`
   - `street_address` (from building or flat, whichever is populated)
   - `city`, `state`, `country`
2. The agent system prompt already instructs it to only mention address if the caller has
   address preferences (`vapi_agent_config.py` line ~999). Keep that rule.
3. The tool's response object for each listing should add an `address` field:
   ```
   "{flat_number}, {building_name}, {street_address}, {city}"
   ```
   assembled server-side so the agent receives a human-readable string, not raw fields.

---

## 9. Listing not deactivated / "Active" checkbox not cleared when tenant is added

**Backend status:** Already fixed. `PATCH /flats/{uuid}/assign-tenant` (line 322) already
runs `db.table("lease_listings").update({"is_active": False}).eq("flat_uuid", flat_uuid).execute()`
immediately after assigning the tenant.

**Problem is frontend refresh.** After `AssignTenantModal` or `AddTenantModal` succeeds, the
leasing tab's listings list is not re-fetched, so the old `is_active: true` value stays
cached in state.

**Fix — frontend:**
- After a successful tenant assignment (both `AssignTenantModal` and `AddTenantModal`),
  dispatch a custom event `refresh-listings` (same pattern as `refresh-appointments`).
- `LeasingTab.jsx` should listen for `refresh-listings` and re-fetch its listings.
- Alternatively, if both components are children of the same parent, pass a callback that
  invalidates/re-fetches the listings state directly.

---

## Summary checklist

- [x] **1** — Lead detail UUID fallback → `LeadDetailModal.jsx` *(Frontend bug)*
- [x] **2** — Property group delete cascade + tenant warning → `property_groups.py` *(Backend bug + UX)*
- [x] **3** — Stale unit/building count → DB cleanup + cascade atomicity *(Data integrity)*
- [x] **4** — Building street_address auto-fill → `AddBuildingModal.jsx` *(Frontend feature)*
- [x] **5** — Unit street_address auto-fill from building → `buildings.py`, `FlatEditModal.jsx` *(Full-stack feature)*
- [x] **6** — Phone / email validation → `AddTenantModal.jsx`, `FlatEditModal.jsx` *(Frontend validation)*
- [x] **7** — Listing dropdown shows building + property → `flats.py`, `AddListingModal.jsx`, `AddTenantModal.jsx` *(Full-stack feature)*
- [x] **8** — Agent sees unit full address → `vapi_agent_config.py`, `leasing.py` *(Backend feature)*
- [x] **9** — Listing not refreshed after tenant assign → `LeasingTab.jsx`, assign modals *(Frontend bug)*
