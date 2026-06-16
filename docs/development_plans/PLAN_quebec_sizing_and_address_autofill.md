# Plan: Quebec Apartment Sizing + Address Auto-fill

## Goals
1. Store full room breakdown (`living_rooms`, `kitchen`, `bedrooms`, `bathrooms`) on flats
2. Derive and store the Quebec size string (e.g. `"3½"`) from these values
3. Mirror the sizing fields to `lease_listings` so the lease agent can query them directly
4. Auto-fill unit `street_address` from its parent building; auto-fill building `street_address` from its parent property group

---

## Part 1 — Database Migration

### `flats` table — new columns

| Column | Type | Notes |
|--------|------|-------|
| `living_rooms` | `int` | Default `1` — almost every unit has one |
| `kitchen` | `int` | Default `1` |
| `quebec_size` | `text` | Computed and stored; e.g. `"3½"`, `"4½"` |

**Drop / rename:** `bedrooms` and `bathrooms` columns already exist — keep them as-is. `living_rooms` and `kitchen` are additions.

**Quebec size formula:**
```
total_full_rooms = bedrooms + living_rooms + kitchen
quebec_size = total_full_rooms + 0.5 * bathrooms
```
Stored as a text string using the `½` character: `"3½"`, `"4½"`, etc.

> Rule: always one bathroom in the formula (0.5 contribution) regardless of the value stored in `bathrooms`. The convention counts one bathroom only. If `bathrooms > 1` the extra bathrooms are full rooms — add `(bathrooms - 1)` to `total_full_rooms`.

Corrected formula:
```
full_rooms = bedrooms + living_rooms + kitchen + max(0, bathrooms - 1)
quebec_size = full_rooms + 0.5
```

Store `½` as the literal Unicode character. Example: `3.5` → `"3½"`.

**Migration file:** `backend/migrations/028_quebec_sizing.sql`

```sql
ALTER TABLE flats
  ADD COLUMN living_rooms int NOT NULL DEFAULT 1,
  ADD COLUMN kitchen int NOT NULL DEFAULT 1,
  ADD COLUMN quebec_size text;

-- Backfill existing rows
UPDATE flats SET
  quebec_size = CONCAT(
    (bedrooms + living_rooms + kitchen + GREATEST(0, bathrooms - 1))::text,
    '½'
  );
```

---

### `lease_listings` table — new columns

Mirror the same room fields here so the lease agent's `find_units` / `search_listings` endpoints can return size info without joining back to `flats`.

| Column | Type | Notes |
|--------|------|-------|
| `bedrooms` | `int` | Copy from flat at listing creation |
| `bathrooms` | `int` | Copy from flat at listing creation |
| `living_rooms` | `int` | Copy from flat at listing creation |
| `kitchen` | `int` | Copy from flat at listing creation |
| `quebec_size` | `text` | Copy from flat at listing creation |

> Note: `bedrooms` and `bathrooms` may already be on `lease_listings` — check before adding.

**Migration:** Add to the same `028_quebec_sizing.sql` file:
```sql
ALTER TABLE lease_listings
  ADD COLUMN IF NOT EXISTS living_rooms int,
  ADD COLUMN IF NOT EXISTS kitchen int,
  ADD COLUMN IF NOT EXISTS quebec_size text;

-- Backfill from joined flats
UPDATE lease_listings ll
SET
  living_rooms = f.living_rooms,
  kitchen = f.kitchen,
  quebec_size = f.quebec_size
FROM flats f
WHERE ll.flat_uuid = f.uuid;
```

---

## Part 2 — Backend Changes

### `app/schemas/flat.py`

Add to `FlatBase` (used by create and update):
```python
living_rooms: Optional[int] = 1
kitchen: Optional[int] = 1
quebec_size: Optional[str] = None
```

`quebec_size` is **computed server-side** — never trust the client's value. Compute it in the route before insert/update.

### `app/schemas/leasing.py`

Add to `ListingCreate` / `ListingResponse`:
```python
living_rooms: Optional[int] = None
kitchen: Optional[int] = None
quebec_size: Optional[str] = None
```

### `routes/flats.py` — `POST /flats` and `PATCH /flats/{uuid}`

Add a helper (in `routes/flats.py` or `app/core/utils.py`):
```python
def compute_quebec_size(bedrooms: int, living_rooms: int, kitchen: int, bathrooms: int) -> str:
    full_rooms = bedrooms + living_rooms + kitchen + max(0, bathrooms - 1)
    return f"{full_rooms}½"
```

Call this before every flat insert or update that touches any room count field. Store the result in `quebec_size`.

### `routes/leasing.py` — `POST /leasing/listings`

When creating a listing, copy `living_rooms`, `kitchen`, `quebec_size` from the flat row into the listing insert payload.

### `routes/leasing.py` — `GET /leasing/find-units` and `GET /leasing/search`

Update the returned unit dict to include `quebec_size` alongside `bedrooms` / `bathrooms`:
```python
{
  "listing_uuid": ...,
  "flat_number": ...,
  "quebec_size": ...,   # new
  "bedrooms": ...,
  "bathrooms": ...,
  ...
}
```

Update `search_listings` to accept an optional `quebec_size` query param (e.g. `"3½"`) in addition to the existing `bedrooms` param. When provided, filter by `lease_listings.quebec_size = quebec_size` at DB level.

---

## Part 3 — Frontend Form Changes

### `AddListingModal.jsx` and/or the flat creation form

**Unit entry form — new fields to add:**

| Field | Input type | Default | Label |
|-------|-----------|---------|-------|
| Living rooms | Number input (min 0) | `1` | "Living rooms" |
| Kitchen | Number input (min 0) | `1` | "Kitchen" |
| Bedrooms | Number input (min 0) | already exists | "Bedrooms" |
| Bathrooms | Number input (min 0) | already exists | "Bathrooms" |

**Quebec size preview:** Show a computed read-only field below the room inputs that live-updates as the user types:
```
Quebec size: 3½
```
This is display-only — the server computes and stores the canonical value.

Formula in the frontend (for preview only):
```js
const fullRooms = bedrooms + livingRooms + kitchen + Math.max(0, bathrooms - 1)
const quebecSize = `${fullRooms}½`
```

**Files to edit:**
- `frontend/src/components/FlatEditModal.jsx` — add living_rooms + kitchen fields; add Quebec size preview
- The flat creation form (wherever `POST /flats` is called — likely inside a modal or `AddBuildingModal` flow)

---

## Part 4 — Address Auto-fill

### Context
Auto-fill is already partially implemented:
- `AddBuildingModal.jsx` auto-fills `street_address`, `city`, `state`, `country` from the parent property group when creating a building ✓
- `FlatEditModal.jsx` pre-fills `street_address` from `flat.building_street_address` when the flat's own address is empty ✓

### Gaps to close

**Unit creation form:**
- When creating a new flat, pre-fill `street_address` with the parent building's `street_address`
- The building's street address is available from `GET /buildings/{id}` — it returns `street_address` on each flat row as `building_street_address`
- Make the pre-fill happen on form open, not just on save; user can override

**Building creation form:**
- Already auto-fills from property group — verify this is working and the field is visible/editable

**Rule:** Auto-fill is a default suggestion, not a lock. The user should always be able to type a different address.

---

## Part 5 — VAPI Lease Agent Update

After the DB and backend changes are live, update the lease agent system prompt to:
- Use `quebec_size` when asking about unit size ("Are you looking for a 3½ or 4½?")
- When pitching a unit, say the Quebec size instead of "2-bedroom" (e.g. "a 3½ on Rue X")
- When the caller states a size preference like "3-and-a-half" or "4½", pass it to `search_listings` as `quebec_size`

This is a system prompt change only — no new tools needed.

Run `python backend/scripts/update_lease_agents.py` after.

---

## Implementation Order

1. **Migration** — run `028_quebec_sizing.sql` in Supabase SQL editor
2. **Backend schemas** — add fields to `flat.py` and `leasing.py`
3. **`compute_quebec_size` helper** — add to utils, wire into `POST /flats` and `PATCH /flats/{uuid}`
4. **Listing creation** — copy room fields + `quebec_size` into listing insert
5. **`find_units` / `search_listings`** — return `quebec_size`, accept it as filter
6. **Frontend form** — add living_rooms + kitchen inputs; Quebec size live preview
7. **Address auto-fill** — close the gap in the flat creation form
8. **Agent system prompt** — use Quebec size lingo; run update script

---

## Files Touched Summary

| File | Change |
|------|--------|
| `backend/migrations/028_quebec_sizing.sql` | New migration — add columns to flats + lease_listings |
| `backend/app/schemas/flat.py` | Add `living_rooms`, `kitchen`, `quebec_size` fields |
| `backend/app/schemas/leasing.py` | Add room fields to `ListingCreate` / `ListingResponse` |
| `backend/app/routes/flats.py` | Compute + store `quebec_size` on create/update |
| `backend/app/routes/leasing.py` | Copy room fields to listing; return + filter by `quebec_size` |
| `frontend/src/components/FlatEditModal.jsx` | New room inputs + Quebec size preview |
| `frontend/src/components/<flat creation form>` | New room inputs + address auto-fill |
| `backend/app/services/vapi_agent_config.py` | Use Quebec size lingo in system prompt |
| `backend/scripts/update_lease_agents.py` | Run to deploy agent changes |
| `CODEBASE_CONTEXT.md` | Update flats schema table + lease_listings table |
