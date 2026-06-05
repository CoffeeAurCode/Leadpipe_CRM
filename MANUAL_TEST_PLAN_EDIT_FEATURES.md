# Manual Test Plan — Edit Features (2026-06-05)

**Scope:** UI + live-backend tests for the three features implemented in `IMPLEMENTATION_PLAN_EDIT_FEATURES.md`.  
**Prerequisite:** Backend running on `localhost:8000`, frontend on `localhost:5173`, logged in as a manager with an active subscription.

---

## Setup — Test Data

Before starting, ensure you have:

- At least one **property group** (e.g. "Sunrise Estate")
- At least one **building** inside it (e.g. "Block A")
- At least two **units** inside that building (e.g. A-101, A-102)
- At least one **active listing** for A-101 (create in LeasingTab if needed)
- At least two **tenants** (one assigned, one unassigned)

---

## Part A — Auto-Delist on Assign

### A1 — Assign deactivates listing

1. Go to **LeasingTab** → confirm unit A-101 listing shows as **Active**
2. Go to **PropertiesPage** → drill into the building → open A-101 → assign the unassigned tenant
3. Return to **LeasingTab** → A-101 listing must show as **Inactive** (or disappear from active list)

**Pass:** listing is inactive after assign  
**Fail:** listing still shows as active

---

### A2 — Unassign does NOT reactivate listing

1. Continuing from A1 (listing is now inactive)
2. Go to **PropertiesPage** → unassign the tenant from A-101
3. Return to **LeasingTab** → A-101 listing must still be **Inactive**

**Pass:** listing remains inactive  
**Fail:** listing became active again

---

### A3 — Assign with no listing is a no-op (no error)

1. Pick a unit that has **no listing** at all
2. Assign a tenant to it
3. Confirm `{ success: true }` response in network tab, no 500 error

**Pass:** assign succeeds cleanly  
**Fail:** 500 or JS console error

---

### A4 — CSV import deactivates listing (I4)

1. Go to **LeasingTab** → create an active listing for unit A-102
2. Go to **PropertiesPage** → Import CSV (Properties or Tenants tab)
3. Upload a tenant CSV that assigns a tenant to A-102 (columns: `name`, `phone`, `flat_number`)
4. After import: go to LeasingTab → A-102 listing must show **Inactive**

**Pass:** listing deactivated after CSV import  
**Fail:** listing still active

---

## Part B — Edit Property Group & Building

### B1 — Edit property group name

1. **PropertiesPage** → Properties view → click pencil icon on "Sunrise Estate"
2. Change name to "Sunrise Estate (Edited)" → Save Changes
3. Confirm card shows new name immediately (no page refresh)
4. Refresh page → new name persists

**Pass:** name updates in UI and DB  
**Fail:** name reverts or save button shows error

---

### B2 — Edit property group address fields

1. Open edit modal for the property group
2. Change City to "Vancouver", Province to "BC"
3. Save → confirm address line on card updates

**Pass:** address fields saved  
**Fail:** save fails or fields revert

---

### B3 — Edit property group — empty name blocked

1. Open edit modal → clear the Name field → click Save Changes
2. Expect: validation error "Name is required" (inline, no API call made)

**Pass:** inline error, no PATCH sent  
**Fail:** PATCH fires or page crashes

---

### B4 — Edit building name

1. PropertiesPage → drill into property group → click pencil on "Block A"
2. Change name to "Block A (Edited)" → Save Changes
3. Confirm BuildingCard shows new name

**Pass:** building name updates in UI and DB  
**Fail:** save fails or old name shown

---

### B5 — Building edit does not affect other buildings

1. After B4, confirm other buildings in the same group are unchanged

**Pass:** only the edited building name changed  
**Fail:** other building names changed or disappeared

---

### B6 — Property group rename does not affect complaint routing (I2)

1. Rename property group to any new name
2. Call the complaint agent from a tenant's phone in that group
3. In the **Complaints** tab → confirm complaint appears and has the correct `property_group_id` (check network response or DB)

**Pass:** complaint created correctly despite name change  
**Fail:** complaint missing or linked to wrong group

---

### B7 — Verify unit/flat edit still works (I5 regression)

1. PropertiesPage → drill to a unit → open FlatDetailModal → click Edit
2. Change rent amount or floor number → Save
3. Confirm values updated in the modal

**Pass:** flat edit saves correctly  
**Fail:** save errors or values don't update

---

### B8 — Verify listing edit still works (I5 regression)

1. LeasingTab → click pencil on any listing
2. Change monthly rent → Save
3. Confirm new rent shown in listings table

**Pass:** listing edit saves correctly  
**Fail:** edit modal broken or save fails

---

## Part C — Tenant Name + Phone Edit

### C1 — Edit tenant name

1. Go to **TenantManagement** → open any tenant → click Edit (pencil)
2. Confirm **Name** and **Phone** fields are present in the edit form
3. Change name to "New Test Name" → Save
4. Confirm TenantProfile header shows new name
5. Confirm TenantManagement list reflects new name (no page refresh required)

**Pass:** name updated everywhere in UI  
**Fail:** name field missing, or name reverts after save

---

### C2 — Edit tenant phone to valid E.164

1. Open tenant edit form → change Phone to `+15145551234`
2. Save → confirm no error
3. Check network tab: PATCH request body includes `phone`

**Pass:** phone updates successfully  
**Fail:** save error or phone not included in PATCH

---

### C3 — Phone E.164 client validation

1. Open tenant edit form → type `5145551234` (no + prefix) in Phone
2. Click Save → expect **inline** error: "Must be in E.164 format"
3. Confirm no PATCH is sent (check network tab)

**Pass:** inline error shown, no API call  
**Fail:** PATCH sent, or alert() used instead of inline error

---

### C4 — Duplicate phone rejected

1. Note the phone of Tenant B (e.g. `+919998064026`)
2. Open Tenant A's edit form → change phone to Tenant B's number → Save
3. Expect: inline error "A tenant with this phone number already exists"
4. Confirm Tenant A's phone is unchanged in DB

**Pass:** 400 error shown inline  
**Fail:** save succeeds (duplicate allowed) or generic crash

---

### C5 — Empty name blocked

1. Open tenant edit form → clear the Name field → click Save
2. Expect: inline validation error (no PATCH sent)

**Pass:** error shown, no API call  
**Fail:** PATCH fires or field silently resets

---

### C6 — Update email + name + phone in one save (I5)

1. Open tenant edit form
2. Change name, phone (to a unique E.164), and email in the same form submission
3. Save → all three fields should update in the DB

**Pass:** all three fields saved in one PATCH  
**Fail:** only some fields saved, or error on combined update

---

### C7 — Other tenant unaffected (isolation)

1. After editing Tenant A's name/phone, open Tenant B
2. Confirm Tenant B's name and phone are unchanged

**Pass:** tenant data isolated correctly  
**Fail:** Tenant B's data changed or corrupted

---

### C8 — Phone change works with complaint agent (I3)

1. Change a tenant's phone to a new valid number (e.g. `+15145559876`)
2. Call the complaint agent from that new number
3. Agent should verify the caller successfully
4. Complaint should be created with the correct `manager_id`
5. Check **VoiceStatsTab** — call appears

**Pass:** new phone verifies, complaint created  
**Fail:** agent says "unrecognized caller" or no complaint created

---

## Part D — Regression Checks

### D1 — Existing tenant fields still save (I5)

1. Open a tenant edit form → change only `lease_end_date` and `manager_notes`
2. Save → confirm both fields updated

**Pass:** existing fields work alongside new name/phone fields  
**Fail:** existing fields no longer save

---

### D2 — Creating new property group still works

1. PropertiesPage → Add Property Group → fill all required fields → Create
2. Confirm new card appears in properties list

**Pass:** create flow unaffected by edit mode changes  
**Fail:** create modal broken or fails

---

### D3 — Creating new building still works

1. Drill into a property group → Add Building → fill fields → Create
2. Confirm building card appears

**Pass:** create flow unaffected  
**Fail:** building modal broken

---

## Pass/Fail Tracker

| Test | Result | Notes |
|---|---|---|
| A1 — Assign deactivates listing | | |
| A2 — Unassign keeps listing inactive | | |
| A3 — Assign with no listing no-ops | | |
| A4 — CSV import deactivates listing | | |
| B1 — Edit property group name | | |
| B2 — Edit property group address | | |
| B3 — Empty group name blocked | | |
| B4 — Edit building name | | |
| B5 — Other buildings unaffected | | |
| B6 — Complaint routing after rename | | |
| B7 — Unit/flat edit regression | | |
| B8 — Listing edit regression | | |
| C1 — Edit tenant name | | |
| C2 — Edit phone valid E.164 | | |
| C3 — Phone E.164 client validation | | |
| C4 — Duplicate phone rejected | | |
| C5 — Empty name blocked | | |
| C6 — Name + phone + email together | | |
| C7 — Other tenant unaffected | | |
| C8 — Phone change + complaint agent | | |
| D1 — Existing tenant fields regression | | |
| D2 — Create property group regression | | |
| D3 — Create building regression | | |

---

## Cleanup

Once all tests are marked Pass, delete this file:

```
del MANUAL_TEST_PLAN_EDIT_FEATURES.md
```

Also delete `IMPLEMENTATION_PLAN_EDIT_FEATURES.md` and `SESSION_CONTEXT_2026-06-05.md` — both are session artifacts and are superseded by the updated `CODEBASE_CONTEXT.md`.

```
del IMPLEMENTATION_PLAN_EDIT_FEATURES.md
del SESSION_CONTEXT_2026-06-05.md
```
