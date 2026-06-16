# Session Handoff — Standalone Units, RLS Ownership & the Creation 500 (2026-06-16)

This doc is both a **session recap** (so the next session can continue cold) and a **live bug diagnosis** for the `POST /flats` 500 that currently blocks standalone-unit creation.

---

## 1. What this session accomplished

| Area | What we did | State |
|---|---|---|
| RLS bug (`42501`) | Diagnosed why unit creation logged `new row violates row-level security policy for table "property_features"`. Root cause: feature init ran on the RLS client (`db`) while the flat was inserted on the service-role client (`svc`), and the `property_features` policy could only authorize units reachable via a building chain. | ✅ Fixed |
| Immediate fix (Option A) | `create_flat` now uses `FeatureService(svc)`; `initialize_unit_features` re-raises so the success log can't lie. | ✅ Shipped (code) |
| Durable fix (Option B) | Migration `029_flats_manager_id_and_rls.sql`: added `flats.manager_id` (FK → `auth.users`, indexed), backfilled building-attached flats, rewrote `flats` / `property_features` / `tenants` / `rents` policies to be **additive** (building chain **OR** direct `manager_id`). | ✅ Migration run by user; 4 policies confirmed `ALL` |
| `manager_id` on creation | Set `manager_id = user["sub"]` in all 3 insert paths: `create_flat`, `import_routes`, chatbot (`run_chat → execute_tool → add_new_unit`). | ✅ Shipped |
| Orphan backfill | 6 pre-migration standalone orphans found. Assigned unit **id 46** (flat "355", had 10 complaints → manager `24b1b33e-861b-4ed0-acdc-e83f5b5cd27f`); deleted 5 empty test units (143, 145, 146, 298, 299). | ✅ Done (per user) |
| Learning material | Created `learning_material/session-07-standalone-unit-rls-ownership.html`. | ✅ |
| Sample data | Created `test_csvs/standalone_units_mixed_occupancy.csv` (4 standalone units, 2 occupied / 2 vacant). | ✅ |
| CSV import — standalone mode | Added to `POST /import/properties`: a row with no `building_name` now creates a building-less unit; `tenant_name`+`tenant_phone` create a tenant + optional rent. | ✅ Shipped (code) — ⚠️ blocked by the 500 below |

Related earlier doc: `docs/diagnoses/property_features_rls_init_failure_diagnosis_2026-06-16.md`.

---

## 2. ✅ RESOLVED — `POST /flats` 500 was a NULL `manager_id`, not `address`

**Resolution (2026-06-16, next session).** The schema query in Step 1 came back with exactly six NOT-NULL columns: `flat_number`, `id` (seq default), `kitchen` (default 1), `living_rooms` (default 1), `manager_id` (**no default**), `uuid` (default). This is decisive:

- **`address` is RULED OUT** — it is *not* in the NOT-NULL list, so it is nullable. The planned `ALTER TABLE flats ALTER COLUMN address DROP NOT NULL` is unnecessary (no-op).
- The only NOT-NULL columns without a usable default are `flat_number` (always set + validated) and **`manager_id`**. So the `23502` could only be a **NULL `manager_id`**.
- `manager_id` comes from `user["sub"]`, which `require_active_subscription` already proved non-null before `create_flat` runs. So the NULL could only happen on a **build whose code did not yet set `manager_id` in the payload**.
- That line (`"manager_id": user["sub"]`) was added in commit `abf90f0c`, which is on the deployed branch (`origin/test`; deployed `flats.py` is byte-identical to local). All five `flats` insert sites set it: `flats.py:642`, `import_routes.py:378` & `:445`, `chatbot.py:397` (via `chat.py` passing `user["sub"]`); `seed_flats.py` is a dev-only script.

**Conclusion:** the 500 occurred because `manager_id` was made `NOT NULL` while a pre-`abf90f0c` build (which didn't set it) was still live. The fix is already deployed. **Re-test standalone creation on the live deploy to confirm** (couldn't reproduce from tooling — project still `INACTIVE` to the management API). If it still 500s, add the debug print from Step 1b to surface the raw column. CODEBASE_CONTEXT.md `flats` schema updated to record `manager_id NOT NULL` and that `address` is nullable.

### 🚨 Symptom (original)
- Creating a standalone unit from the UI → `POST /flats` returns **500**, repeatedly:
  ```
  INFO:  ... "POST /flats HTTP/1.1" 500 Internal Server Error
  ```
- Frontend shows: **"Error creating unit: A required field is missing."** — even with every field (including Additional Address) filled in.

### 🔍 Confirmed so far
- The message **"A required field is missing."** is `clean_db_error`'s mapping for Postgres code **`23502`** (`not_null_violation`). See `backend/app/core/db_errors.py:16`.
- So the `flats` INSERT is being rejected because **some NOT-NULL column is receiving NULL**.
- The flat insert in `create_flat` uses `svc` (service role). Service role bypasses **RLS** but **NOT** column constraints — so a `NOT NULL` violation still fires. This is not an RLS issue.

### ✅ Ruled out: `building_id`
The obvious guess is "`building_id` is NOT NULL, so building-less units can't be inserted." **This is false.** Unit **id 46** currently exists with `building_id IS NULL` (we kept it during orphan cleanup). Postgres cannot hold a `NOT NULL` constraint on a column that already contains NULLs, so `flats.building_id` is nullable. The failing column is something else.

### 🧠 Reasoning about the real culprit
`create_flat`'s payload is **identical** for standalone vs building-attached units *except* `building_id` (and the form-driven optional fields). So if a NOT-NULL column other than `building_id` is left unset, **building-attached creation should fail too**. Two possibilities:

1. **All unit creation is currently broken** (the user only happened to test standalone). Most likely culprit: a column `create_flat` never sets, e.g. the legacy **`address`** column — `AddPropertyModal.jsx` never sends `address` (it sends `street_address`/`address_line`/etc.), so `flat_payload["address"]` is always `None`. If `flats.address` is `NOT NULL` with no default, every create fails.
2. **A column the building path happens to satisfy** but standalone doesn't — but the payloads don't differ except `building_id` (ruled out), so this is unlikely.

Other candidates to check: `quebec_size` (only set when both `bedrooms` and `bathrooms` are present), `city`/`state`/`country` (only set if the form field is non-empty), or `occupied`/`flat_number` (always set — unlikely).

**`manager_id` is ruled out:** `create_flat` always sets `manager_id = user["sub"]`, and `user["sub"]` is a valid non-null UUID (the `require_active_subscription` check already queried `subscriptions` with it and returned, so the request reached `create_flat` rather than 403'ing).

### ⚠️ Why the logs don't name the column
`create_flat`'s final `except` does `raise HTTPException(... detail=f"Error creating unit: {clean_db_error(e)}")` and **does not print the raw exception**. So the Render logs only show the generic mapped message — the offending column name is swallowed. Surfacing it requires either a schema query or a temporary debug print (see next steps).

---

## 3. NEXT SESSION — how to finish this

### Step 1 — Identify the exact NOT-NULL column (pick either)

**(a) Schema query** (when the DB is reachable in the SQL editor):
```sql
SELECT column_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'flats' AND is_nullable = 'NO'
ORDER BY column_name;
```
Then compare the list against what `create_flat` sets for a **standalone** unit. The NOT-NULL column that isn't in the payload (and has no default) is the culprit. Prime suspect: `address`.

**(b) Temporary debug print** (if the DB stays unreachable from tools):
Add one line before the final `raise` in `create_flat` (`backend/app/routes/flats.py`), redeploy, reproduce once, read the column from the log, then remove it:
```python
print(f"[FLAT CREATE ERROR] {type(e).__name__}: {getattr(e, 'message', e)}")
```
The Supabase error reads like `null value in column "address" violates not-null constraint`.

### Step 2 — Apply the fix (once the column is known)
- If the column **should be optional** for standalone units (very likely for `address`):
  ```sql
  ALTER TABLE flats ALTER COLUMN address DROP NOT NULL;
  ```
- **Or** make `create_flat` (and `_flat_attrs_from_row` in the importer) always provide a value for it.

### Step 3 — Re-test both paths
- UI: create a standalone unit (no building) → expect `201`, unit visible in the list.
- Import: upload `test_csvs/standalone_units_mixed_occupancy.csv` via the CSV import modal → expect 4 flats created, `HOUSE101` + `VILLA9` occupied with tenants + rent, `BUNG22` + `COTTAGE1` vacant.

### Step 4 — Confirm the standalone import end-to-end
The importer code is shipped but **untested** because the same `23502` blocks it (same `flats` table). Once Step 2 lands, the importer should work without further changes.

### Step 5 — Optional hardening
After everything works and `SELECT COUNT(*) FROM flats WHERE manager_id IS NULL` is 0:
```sql
ALTER TABLE flats ALTER COLUMN manager_id SET NOT NULL;
```

---

## 4. Code changed this session (for review)
- `backend/app/routes/flats.py` — `FeatureService(svc)`; `manager_id` in payload.
- `backend/app/services/feature_service.py` — `initialize_unit_features` re-raises.
- `backend/app/routes/import_routes.py` — standalone mode: `PROPERTIES_REQUIRED = {"flat_number"}`; `_flat_attrs_from_row`; `_maybe_create_tenant_and_rent`; loop branches on `building_name`.
- `backend/app/ai/chatbot.py` + `backend/app/routes/chat.py` — thread `manager_id`.
- `backend/migrations/029_flats_manager_id_and_rls.sql` — column + FK + additive RLS.
- `scripts/backfills/backfill_flats_manager_id_orphans.sql` — orphan recovery.
- `test_csvs/standalone_units_mixed_occupancy.csv` — sample data.
- `learning_material/session-07-standalone-unit-rls-ownership.html` — lesson.
- `CODEBASE_CONTEXT.md` — flats schema + RLS notes updated.

## 5. Environment notes
- Supabase project `bpvzfboslevifpnsezts` repeatedly reports `INACTIVE` to the MCP tools and times out on direct SQL, even while the live app serves traffic (the app uses the PostgREST REST path, which is separate). Run schema/verification SQL in the **Supabase SQL editor**, not via tooling.
