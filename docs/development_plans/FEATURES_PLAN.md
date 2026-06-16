# Implementation Plan — 4 Features

**Date:** 2026-06-04

---

## Feature 1 — Multi-Select Delete for Properties, Buildings, Units

### Current State
No multi-select exists. Each card has a single delete button with `window.confirm()`. Deletes are one-at-a-time only.

### What Needs to Change

#### Backend — 3 new bulk-delete endpoints

**`backend/app/routes/property_groups.py`**
```
DELETE /property-groups/bulk
Body: { "ids": ["uuid1", "uuid2", ...] }
```
- Loops through each ID, runs same cascade as single delete: lease_listings → rents → tenants → flats → buildings → property group
- Returns `{ deleted: N, errors: ["Row X: reason", ...] }`
- Authenticated + subscription gate (same as single delete)

**`backend/app/routes/buildings.py`**
```
DELETE /buildings/bulk
Body: { "ids": ["id1", "id2", ...] }
```
- Cascade: lease_listings → rents → tenants → flats → building
- Returns `{ deleted: N, errors: [...] }`

**`backend/app/routes/flats.py`**
```
DELETE /flats/bulk
Body: { "uuids": ["uuid1", "uuid2", ...] }
```
- Cascade: lease_listings → rents → tenants → flat
- Returns `{ deleted: N, errors: [...] }`

#### Frontend — `frontend/src/components/PropertiesPage.jsx`

**State additions:**
```js
const [selectMode, setSelectMode] = useState(false)
const [selectedPropertyIds, setSelectedPropertyIds] = useState(new Set())
const [selectedBuildingIds, setSelectedBuildingIds] = useState(new Set())
const [selectedFlatUuids, setSelectedFlatUuids] = useState(new Set())
```

**UI pattern — same at all three levels (property groups, buildings, units):**

1. **"Select" toggle button** in the toolbar next to the existing "Add" button at each level. Clicking it enters/exits select mode.

2. **Checkboxes on cards** — visible only when `selectMode` is true:
   - Overlay a checkbox (top-left corner) on each `PropertyGroupCard`, `BuildingCard`, and unit row in `UnitListPanel`
   - Clicking a checkbox toggles the item in the selected set WITHOUT opening the detail modal
   - Clicking outside the checkbox still opens the detail modal as normal

3. **Select-all row** — when in select mode, show a "Select all" checkbox + "N selected" label in the toolbar.

4. **Floating action bar** — when any items are selected, a sticky bar appears at the bottom of the page:
   ```
   [checkbox] 3 selected    [Cancel]    [Delete selected]
   ```
   - "Cancel" exits select mode and clears selection
   - "Delete selected" shows a confirmation modal:
     > "Delete 3 units? All linked tenants, rents, and listings will also be removed. This cannot be undone."
   - On confirm: calls bulk endpoint, removes deleted items from local state, exits select mode

5. **Error display** — if some items fail to delete, show a summary:
   > "2 deleted. 1 failed: Unit B101 has an active lease listing."

#### `frontend/src/services/apiService.js` — 3 new functions
```js
bulkDeletePropertyGroups(ids)   // DELETE /property-groups/bulk
bulkDeleteBuildings(ids)         // DELETE /buildings/bulk
bulkDeleteFlats(uuids)           // DELETE /flats/bulk
```

---

## Feature 2 — English-Only Errors on Frontend (No Raw JSON)

### Root Cause Analysis

**Image 1 (CSV import errors — `tenants_rent_status_check`):**
The Supabase Python SDK raises exceptions whose `str()` representation is a Python dict string:
```
{'message': 'new row for relation "tenants" violates check constraint "tenants_rent_status_check"', 'code': '23514', 'hint': None, 'details': None}
```
- `import_routes.py` records row errors via `f"Row {N}: {str(e)}"` — this raw dict string becomes the error message shown to the user
- Error code `23514` = PostgreSQL CHECK constraint violation (`rent_status` column only accepts `On-time`, `Upcoming`, `Overdue`, `At Risk`)
- `_clean_db_error` in `flats.py` does NOT handle code `23514`, and is never called from import routes

**Image 2 (Flat delete — FK from `lease_listings`):**
```
Error deleting flat: {'message': 'update or delete on table "flats" violates foreign key constraint "lease_listings_flat_uuid_fkey"...'}
```
- `flats.py` DELETE route catches `Exception e` and returns `detail=f"Error deleting flat: {str(e)}"` — raw dict string
- The delete cascade only removes rents + tenants, but NOT the linked `lease_listing`. The FK `lease_listings_flat_uuid_fkey` blocks the flat delete
- This is BOTH a bad error message AND a logic bug (incomplete cascade)

**The existing `_clean_db_error` helper** in `flats.py` only covers codes 42501, 23505, 23503 and is never called in DELETE routes or import routes.

### What Needs to Change

#### Step 1 — Create shared error utility `backend/app/core/db_errors.py` (NEW FILE)

```python
def clean_db_error(e: Exception) -> str:
    text = str(e)
    code = str(getattr(e, 'code', ''))

    if '23514' in code or '23514' in text:
        return "One or more field values are not allowed. Check that status fields match the accepted values."

    if '23505' in code or '23505' in text:
        return "This record already exists."

    if '23503' in code or '23503' in text:
        if 'lease_listings' in text:
            return "This unit has an active lease listing. Remove the listing before deleting the unit."
        return "This record is linked to other data and cannot be deleted."

    if '23502' in code or '23502' in text:
        return "A required field is missing."

    if '42501' in code or '42501' in text:
        return "You do not have permission to perform this action."

    msg = getattr(e, 'message', None)
    if msg and isinstance(msg, str) and not msg.startswith('{'):
        return msg

    return "A database error occurred. Please try again."
```

Remove the old `_clean_db_error` from `flats.py` and import from `db_errors.py` everywhere.

#### Step 2 — Fix flat DELETE cascade (logic bug + error message)

**`backend/app/routes/flats.py` — `delete_flat`:**

Correct cascade order (add `lease_listings` deletion FIRST):
```python
db.table("lease_listings").delete().eq("flat_uuid", flat_uuid).execute()
db.table("rents").delete().eq("flat_uuid", flat_uuid).execute()
if tenant_uuid:
    db.table("tenants").delete().eq("uuid", tenant_uuid).execute()
db.table("flats").delete().eq("uuid", flat_uuid).execute()
```

In the except block, replace `str(e)` with `clean_db_error(e)`.

#### Step 3 — Fix building and property group DELETE cascade + error messages

**`backend/app/routes/buildings.py` — `delete_building`:**
- Before `db.table("flats").delete()`, add:
  ```python
  if flat_uuids:
      db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
  ```
- Replace `str(e)` in except block with `clean_db_error(e)`

**`backend/app/routes/property_groups.py` — `delete_property_group`:**
- Before `db.table("flats").delete()`, add:
  ```python
  if flat_uuids:
      db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
  ```
- Replace `str(e)` in except block with `clean_db_error(e)`

#### Step 4 — Fix CSV import error messages

**`backend/app/routes/import_routes.py`:**

Every `except Exception as e:` block that appends to the `errors` list:
```python
# Before:
errors.append(f"Row {row_num}: {str(e)}")

# After:
errors.append(f"Row {row_num}: {clean_db_error(e)}")
```

Apply `from app.core.db_errors import clean_db_error` at the top.

---

## Feature 3 — Edit and Delete in Listings

### Current State
Edit (pencil icon → opens `AddListingModal` pre-filled) and delete (trash icon → `window.confirm()` → `deleteListing()`) **already exist** in `LeasingTab.jsx` on the listing cards.

### What Is Actually Missing

The delete handler has **no error handling**. If `deleteListing()` throws (e.g. network error, server error), the error is silently swallowed — no message shown to the user.

**`frontend/src/components/LeasingTab.jsx` — `handleDeleteListing`:**

```js
// Current — silent failure:
const handleDeleteListing = async (uuid) => {
  if (!window.confirm('Delete this listing?')) return
  await deleteListing(uuid)
  setListings(prev => prev.filter(l => l.uuid !== uuid))
}

// Fixed — shows error:
const handleDeleteListing = async (uuid) => {
  if (!window.confirm('Delete this listing?')) return
  try {
    await deleteListing(uuid)
    setListings(prev => prev.filter(l => l.uuid !== uuid))
  } catch (err) {
    alert(err.message || 'Failed to delete listing. Please try again.')
  }
}
```

That is the only change needed here. Edit already works correctly.

---

## Feature 4 — CSV Import: No Data Exclusion or Silent Skips

### Current Data Loss / Silent Failures

| Scenario | Current Behaviour | Problem |
|---|---|---|
| `rent_status` not in allowed values | Row fails — raw dict error (23514) | Should default to `null`, not fail the whole row |
| `rent_amount` cannot be parsed as float | Silent skip — rent record not created, nothing reported | Should report in `skipped` list |
| Flat already exists (property import) | Silently skipped — not in any output | User cannot see which rows were skipped |
| Already-occupied flat (tenant import) | Silently skipped — not in any output | User cannot see which rows were skipped |

### What Needs to Change

#### A — Sanitize `rent_status` before insert (prevents the 23514 constraint error)

**`backend/app/routes/import_routes.py` — tenant import row processing:**

```python
VALID_RENT_STATUSES = {"On-time", "Upcoming", "Overdue", "At Risk"}

raw_status = row.get("rent_status", "").strip()
rent_status = raw_status if raw_status in VALID_RENT_STATUSES else None
```

Only include `rent_status` in the insert payload if it is not `None`. This prevents the check-constraint violation entirely — the row is imported with no rent_status (DB default or null) rather than failing.

#### B — Report `rent_amount` parse failures

**`backend/app/routes/import_routes.py` — rent creation block:**

```python
rent_amount_raw = row.get("rent_amount", "").strip()
rent_amount = None
if rent_amount_raw:
    try:
        rent_amount = float(rent_amount_raw)
    except ValueError:
        skipped.append(
            f"Row {row_num} ({name}): rent_amount '{rent_amount_raw}' is not a valid number — "
            f"tenant imported without a rent record"
        )
```

#### C — Make skipped flats visible in property import

**`backend/app/routes/import_routes.py` — property import "flat already exists" branch:**

```python
# Before: silent skip
# After:
skipped.append(f"Row {row_num}: flat '{flat_number}' already exists — skipped")
```

#### D — Make skipped occupied flats visible in tenant import

**`backend/app/routes/import_routes.py` — tenant import "flat already occupied" branch:**

```python
# Before: silent skip
# After:
skipped.append(f"Row {row_num}: flat '{flat_number}' is already occupied — skipped")
```

#### E — Show skipped row details in the frontend result screen

**`frontend/src/components/CsvImportModal.jsx`:**

After a successful import, the modal shows a result summary. Check whether the `skipped` array items are displayed (not just the count). If only the count is shown, add a collapsible list:

```
✓ 45 imported    ⚠ 3 skipped    ✗ 0 errors

Skipped rows:
  • Row 3: flat 'B101' is already occupied — skipped
  • Row 7: rent_amount 'N/A' is not a valid number — tenant imported without a rent record
  • Row 12: flat 'A205' already exists — skipped
```

---

## Feature 5 — Structured Address Fields (Properties, Buildings, Units)

### Current State
Every level has a single free-text `address` column (e.g. `"123 Main St, Building A"`). Nothing is compulsory. No city, state, or country separation. Buildings and units do not inherit any address info from their parent.

### Address Structure Per Level

| Level | Street | Address Line | City | State / Province | Country | Required? |
|---|---|---|---|---|---|---|
| **Property Group** | ✓ | — | ✓ | ✓ | ✓ | All 4 fields required |
| **Building** | ✓ (optional) | ✓ (optional, extra info) | ✓ auto-filled | ✓ auto-filled | ✓ auto-filled | city/state/country required, auto-filled from property (editable) |
| **Unit (Flat)** | ✓ (optional) | ✓ (optional) | ✓ auto-filled | ✓ auto-filled | ✓ auto-filled | auto-filled from building (editable) |

**Naming convention used throughout:** `street_address`, `address_line`, `city`, `state`, `country`.  
Old `address` column is kept as-is in the DB for existing records — it becomes a deprecated legacy field and is no longer written by new code.

---

### Step 1 — DB Migration (`backend/migrations/022_structured_address.sql`)

```sql
-- properties_list
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';

-- buildings
ALTER TABLE buildings
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS address_line   TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';

-- flats
ALTER TABLE flats
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS address_line   TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';
```

Old `address` column is untouched — existing data stays readable. No backfill needed since old records will display the legacy `address` as a fallback.

---

### Step 2 — Backend Schema Changes

#### `backend/app/routes/property_groups.py` — `PropertyGroupCreate`
```python
class PropertyGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    # Structured address — all required for new creates
    street_address: str
    city: str
    state: str
    country: str = "Canada"
    # Legacy — kept for any old clients; ignored by new logic
    address: Optional[str] = None
```

#### `backend/app/routes/buildings.py` — `BuildingCreate`
```python
class BuildingCreate(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    # Structured address — city/state/country required; street optional
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: str                           # required — auto-filled from property on frontend
    state: str                          # required — auto-filled from property on frontend
    country: str = "Canada"
    address: Optional[str] = None       # legacy
```

#### `backend/app/schemas/flat.py` — `FlatCreate` / `FlatUpdate`
```python
# FlatCreate additions:
street_address: Optional[str] = None
address_line: Optional[str] = None
city: Optional[str] = None             # auto-filled from building on frontend
state: Optional[str] = None
country: Optional[str] = "Canada"

# FlatUpdate additions (same fields, all Optional):
street_address: Optional[str] = None
address_line: Optional[str] = None
city: Optional[str] = None
state: Optional[str] = None
country: Optional[str] = None
```

For flats, the form submits via `multipart/form-data` (Form fields). The `create_flat` route in `flats.py` needs the same new `Form(None)` parameters added:
```python
street_address: Optional[str] = Form(None),
address_line: Optional[str] = Form(None),
city: Optional[str] = Form(None),
state: Optional[str] = Form(None),
country: Optional[str] = Form("Canada"),
```

#### Backend insert payloads — all three routes
When inserting, write the new structured columns. Do NOT write to the old `address` column from new code. Example for property group:
```python
payload = {
    "name": ...,
    "street_address": request.street_address,
    "city": request.city,
    "state": request.state,
    "country": request.country,
    # do not include "address"
}
```

---

### Step 3 — Frontend: `AddPropertyGroupModal.jsx`

Replace the single `address` input with four required fields:

```
Street Address *        [_______________________________]
City *                  [______________]
Province / State *      [______________]
Country *               [______________]  (default: Canada)
```

- All four marked required (`*`)
- Validate before submit: if any is empty, show inline error "Street address is required" etc.
- Remove old `address` from form state; add `street_address`, `city`, `state`, `country`
- On submit, send `street_address`, `city`, `state`, `country` in payload (not `address`)

---

### Step 4 — Frontend: `AddBuildingModal.jsx`

**Auto-fill logic:**
The modal already receives `propertyGroupId` as a prop (or has access to it via context/parent). When the modal opens (or when property group is selected), call `apiService.fetchPropertyGroups()` (already exists) and look up the matching property group to extract `city`, `state`, `country`. Pre-populate the building form fields with those values.

If `fetchPropertyGroups` returns all groups, filter client-side by ID. No new API call needed.

**New form layout:**
```
Building Name *         [_______________________________]
Street Address          [_______________________________]  (optional — building-specific)
Additional Address      [_______________________________]  (optional, e.g. "Suite 4B, Ground Floor")
City *                  [______________]   ← auto-filled from property, editable
Province / State *      [______________]   ← auto-filled from property, editable
Country *               [______________]   ← auto-filled from property, editable
```

- `city`, `state`, `country` show a small "Auto-filled from property" hint label beneath them; user can still type to override
- Validation: city, state, country are required before submit
- Form state: add `street_address`, `address_line`, `city`, `state`, `country`; remove old `address`

---

### Step 5 — Frontend: `AddPropertyModal.jsx` (flat creation) + `FlatEditModal.jsx`

**Auto-fill logic for flat creation:**
The flat creation form already receives `building_id`. When `building_id` is set, look up the building from the already-fetched buildings list (available in `PropertiesPage` state) to extract `city`, `state`, `country`. Pass these as props (`initialCity`, `initialState`, `initialCountry`) to `AddPropertyModal`.

**New form layout (flat creation and edit):**
```
Street Address          [_______________________________]  (optional — unit-specific, e.g. "Unit 4A")
Additional Address      [_______________________________]  (optional)
City                    [______________]   ← auto-filled from building, editable
Province / State        [______________]   ← auto-filled from building, editable
Country                 [______________]   ← auto-filled from building, editable
```

- All auto-filled fields are editable
- None are strictly required for flats (the building already has the address)
- Form state: add `street_address`, `address_line`, `city`, `state`, `country`; remove old `address`

---

### Step 6 — Display: Address in Cards and Detail Views

**Wherever an address is currently displayed** (PropertyGroupCard, BuildingCard, FlatDetailModal, etc.), update the display logic to prefer structured fields:

```js
// Helper used in display components:
function formatAddress(entity) {
  const parts = [
    entity.street_address,
    entity.address_line,
    entity.city,
    entity.state,
    entity.country,
  ].filter(Boolean)
  
  if (parts.length > 0) return parts.join(', ')
  return entity.address || '—'  // fallback for legacy records
}
```

Apply this helper in:
- `PropertyGroupCard.jsx`
- `BuildingCard.jsx`
- `BuildingInfoModal.jsx`
- `FlatDetailModal.jsx`
- `UnitListPanel.jsx` (if address is shown)

---

### Step 7 — CSV Import: Accept Structured Address Columns

**`backend/app/routes/import_routes.py` — properties import:**

The CSV column mapping should also recognise the new address columns. After the existing column-detection logic, treat these as optional mappable columns:
- `street_address` → `street_address`
- `city` → `city`
- `state` → `state`  
- `country` → `country`

If only the old `address` column is present in the CSV, leave the new structured columns null (backward compat).

---

## Files Changed Summary

### Backend
| File | Change |
|---|---|
| `backend/app/core/db_errors.py` | **NEW** — `clean_db_error()` covering 23514, 23505, 23503, 23502, 42501 |
| `backend/migrations/022_structured_address.sql` | **NEW** — adds street_address, address_line, city, state, country to 3 tables |
| `backend/app/routes/flats.py` | Fix cascade (add lease_listings), apply `clean_db_error`, add `DELETE /flats/bulk`, add new address Form fields |
| `backend/app/routes/buildings.py` | Fix cascade, apply `clean_db_error`, add `DELETE /buildings/bulk`, add address fields to `BuildingCreate` |
| `backend/app/routes/property_groups.py` | Fix cascade, apply `clean_db_error`, add `DELETE /property-groups/bulk`, add address fields to `PropertyGroupCreate` |
| `backend/app/routes/import_routes.py` | Sanitize `rent_status`, report skips, apply `clean_db_error`, accept new address columns |
| `backend/app/schemas/flat.py` | Add `street_address`, `address_line`, `city`, `state`, `country` to FlatCreate / FlatUpdate |

### Frontend
| File | Change |
|---|---|
| `frontend/src/components/PropertiesPage.jsx` | Add select mode, checkboxes, floating delete bar, bulk delete calls |
| `frontend/src/components/AddPropertyGroupModal.jsx` | Replace single `address` with 4 required structured fields |
| `frontend/src/components/AddBuildingModal.jsx` | Replace single `address` with structured fields + auto-fill city/state/country from parent property |
| `frontend/src/components/AddPropertyModal.jsx` | Replace single `address` with structured fields + auto-fill from parent building |
| `frontend/src/components/FlatEditModal.jsx` | Replace single `address` with structured fields |
| `frontend/src/components/PropertyGroupCard.jsx` | Use `formatAddress()` helper for display |
| `frontend/src/components/BuildingCard.jsx` | Use `formatAddress()` helper for display |
| `frontend/src/components/BuildingInfoModal.jsx` | Use `formatAddress()` helper for display |
| `frontend/src/components/FlatDetailModal.jsx` | Use `formatAddress()` helper for display |
| `frontend/src/components/LeasingTab.jsx` | Add try/catch + error alert to `handleDeleteListing` |
| `frontend/src/components/CsvImportModal.jsx` | Show skipped row detail list in result view |
| `frontend/src/services/apiService.js` | Add `bulkDeletePropertyGroups`, `bulkDeleteBuildings`, `bulkDeleteFlats` |

---

## Implementation Order

1. **`db_errors.py`** — shared utility everything else depends on
2. **DB migration `022_structured_address.sql`** — run in Supabase SQL editor before any backend changes
3. **Delete cascade fixes** (flats, buildings, property groups) — unblocks the FK crash, cleans error messages
4. **`import_routes.py`** — sanitize rent_status, report skips, clean error messages
5. **`LeasingTab.jsx`** — one-line error-handling fix
6. **Structured address — backend** (schemas + route params for all three levels)
7. **Structured address — frontend** (modals in order: PropertyGroup → Building → Flat; then display helpers)
8. **Bulk delete endpoints** (backend) + **multi-select UI** (frontend) — build together, backend first
9. **`CsvImportModal.jsx`** — skipped row display (depends on import_routes being done)
