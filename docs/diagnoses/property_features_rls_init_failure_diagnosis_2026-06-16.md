# Diagnosis — `property_features` RLS INSERT failure on unit creation (2026-06-16)

## The error (from Render logs)

```
[FLAT CREATED] UUID: 63d37150-..., Number: 201
[FeatureService] Error initializing unit 298: {'message': 'new row violates row-level security policy for table "property_features"', 'code': '42501', ...}
[FEATURES INITIALIZED] unit_id: 298
INFO: "POST /flats HTTP/1.1" 201 Created
```

Same thing for unit 299. The `POST /flats` returns **201 Created** (the flat is saved), but the feature-flag initialization for that unit is silently rejected by Postgres Row-Level Security with error `42501`.

Note the misleading log: `[FEATURES INITIALIZED] unit_id: 298` prints **even though initialization failed** — see [Secondary issue](#secondary-issue-misleading-log-line) below.

---

## TL;DR root cause

`POST /flats` inserts the **flat** with the **service-role** client (`svc`, bypasses RLS) but initializes the unit's **feature rows** with the **authenticated anon** client (`db`, RLS-enforced). The `property_features` RLS policy only authorizes a row when the unit's ownership can be traced **`flats.building_id → buildings → properties_list → manager_id = auth.uid()`**. For any flat whose `building_id` does **not** resolve to one of the manager's buildings (a **standalone unit / NULL `building_id`**), that `INNER JOIN` chain produces no match, so the INSERT is rejected.

This is the *same* RLS rejection the team already hit on the **`flats` INSERT** and worked around by switching that insert to the service-role client (documented in `CODEBASE_CONTEXT.md` lines 459 & 1037). The identical fix was never applied to feature initialization, so the rejection simply moved one step downstream to `property_features`.

---

## Mechanism, step by step

### 1. The flat is created with the service-role client (RLS bypassed)
`backend/app/routes/flats.py` → `create_flat`:

```python
flat_response = svc.table("flats").insert(flat_payload).execute()   # line 641 — svc = get_service_db (RLS BYPASSED)
...
flat_id = flat["id"]
```

Because `svc` bypasses RLS, the flat is created **without any ownership validation** against `auth.uid()`. A flat can therefore be persisted even if its `building_id` is `NULL` or doesn't belong to the current manager.

### 2. Features are initialized with the authenticated client (RLS enforced)
Immediately after, same function (lines 663–671):

```python
feature_service = FeatureService(db)          # db = get_authenticated_db (RLS ENFORCED)
await feature_service.initialize_unit_features(flat_id)
```

`initialize_unit_features` (`backend/app/services/feature_service.py:264`) upserts one row per feature into `property_features` using that **RLS-enforced** `db` client.

### 3. The RLS policy can only authorize units that hang off a building
`scripts/02_rls_policies.sql:115`:

```sql
CREATE POLICY "manager_owns_property_features"
ON property_features FOR ALL
USING (
  unit_id IN (
    SELECT f.id FROM flats f
    JOIN buildings b ON f.building_id = b.id          -- INNER JOIN
    JOIN properties_list p ON b.property_id = p.id    -- INNER JOIN
    WHERE p.manager_id = auth.uid()
  )
);
```

Two things matter here:

- The policy is declared `FOR ALL` with **only a `USING` clause and no separate `WITH CHECK`**. In Postgres, when `WITH CHECK` is omitted the `USING` expression is *also* used as the INSERT check. So every inserted `property_features` row must satisfy the predicate above.
- The predicate reaches the manager **exclusively through `building_id`** via two `INNER JOIN`s. If `flats.building_id IS NULL` (or points to a building the manager doesn't own), the flat's `id` is **never** in the allowed set, and the INSERT is rejected with `42501`.

### 4. Why both consecutive creations failed deterministically
Units 298 *and* 299 both failed. A concurrency/race explanation (shared anon client, see [below](#ruled-out-shared-anon-client-jwt-race)) would be intermittent. Two back-to-back deterministic failures point squarely at a **structural** cause: these units' `building_id` does not resolve to the manager — i.e. they are **standalone units** (attached to a property directly, with no building).

The app explicitly supports this shape. `frontend/src/components/SettingsPage.jsx:370`:

```js
// Also find standalone units for this property (property attached, but no building)
const standalones = allFlats.filter(f => f.property_id === property.id && !f.building_id);
```

So "unit with `building_id = NULL`" is a real, supported state — and it is exactly the state the `property_features` RLS policy cannot express.

---

## Why this is the same bug that was already worked around for `flats`

`CODEBASE_CONTEXT.md`:

> **line 459** — *"`POST /flats` uses `svc` (service-role client) for the actual `flats` INSERT — the Supabase RLS INSERT policy rejects the anon client for some manager accounts."*
>
> **line 1037** — *"The `flats` INSERT uses `svc` … some manager accounts have RLS INSERT policies that reject the anon client. … Do not revert this to `db.table('flats').insert()`."*

The `flats` RLS policy (`manager_owns_flats`, `02_rls_policies.sql:47`) has the **same shape** — it authorizes via `building_id IN (manager's buildings)` with no `WITH CHECK`. The "some manager accounts" that were rejected were almost certainly creating **standalone / NULL-building units**, which that policy can't authorize either. The team patched the symptom by moving the `flats` insert to `svc`, but `initialize_unit_features` was left on the RLS-enforced `db` client — so the very same rejection now surfaces on `property_features`.

---

## Impact

- **Non-blocking for flat creation.** The feature init is wrapped in `try/except` in `create_flat` (lines 669–671) and only logged, so `POST /flats` still returns 201 and the flat is usable.
- **The affected units have zero persisted feature rows.** On read, `FeatureService._build_feature_map` falls back to defaults (`source: "default"`), so a freshly created standalone unit *looks* fine but has no row in `property_features`.
- **Downstream feature saves for these units also fail / are invisible.** The Settings routes use `get_feature_service` → `get_authenticated_db` (RLS), so:
  - `set_unit_features(unit_id, …)` hits the **same** RLS `WITH CHECK` rejection for a standalone unit.
  - `set_property_features` resolves units via `_get_units_for_property` (`feature_service.py:88`), which walks `property → buildings → flats` only. Standalone units (no building) are **never found**, so property-level saves silently skip them.
- Net effect: standalone units can never have their feature flags persisted through the normal UI path; they are permanently stuck on system defaults.

---

## Secondary issue: misleading log line

In `create_flat` the success log is printed **unconditionally**, even when init raised:

```python
await feature_service.initialize_unit_features(flat_id)   # swallows the error internally, logs it, returns None
print(f"[FEATURES INITIALIZED] unit_id: {flat_id}")        # always prints
```

`initialize_unit_features` catches its own exception and logs `[FeatureService] Error initializing unit …` but does **not** re-raise, so control returns normally and `[FEATURES INITIALIZED]` prints regardless. That is why both lines appear together in the logs and why the failure is easy to miss.

---

## Ruled out: shared anon-client JWT race

`backend/app/db/session.py` uses a **module-level singleton** `_anon_client`, and `get_authenticated_db` mutates it per request via `db.postgrest.auth(jwt)`. Under truly concurrent requests from *different* managers, one request could overwrite another's JWT and make `auth.uid()` resolve to the wrong user — which would also produce a `42501`. This is a real latent risk worth fixing, but it is **not** the cause here:

- The logs are a single client IP doing sequential operations (same manager).
- Reads in the same window succeed (`GET /properties`, `/buildings`, `/notifications` → 200), so `auth.uid()` is resolving correctly for this user.
- The failure is deterministic across two creations, not intermittent.

(Worth tracking separately; not the trigger for this incident.)

---

## Recommended fixes (in priority order)

**Option A — make feature init bypass RLS, mirroring the existing `flats` workaround (smallest, consistent change).**
Initialize features with the service-role client, since ownership was already established before the flat was created:

```python
feature_service = FeatureService(svc)   # was: FeatureService(db)
await feature_service.initialize_unit_features(flat_id)
```

This is the exact pattern already blessed for the `flats` insert in this same function. Low risk; restores feature rows for every newly created unit. Downside: does not fix later UI-driven saves for standalone units (Settings still uses `db`).

**Option B — fix the RLS policy so it can authorize standalone units (addresses the real root cause).**
Add the direct `flats.property_id → manager` path so units without a building are still ownable, and add an explicit `WITH CHECK`. Sketch:

```sql
DROP POLICY "manager_owns_property_features" ON property_features;
CREATE POLICY "manager_owns_property_features"
ON property_features FOR ALL
USING (
  unit_id IN (
    SELECT f.id FROM flats f
    LEFT JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p
      ON p.id = COALESCE(b.property_id, f.property_id)
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (... same predicate ...);
```

This also fixes `set_unit_features` for standalone units and should be mirrored on the `flats` policy so the original `svc` workaround can eventually be retired. (Confirm `flats.property_id` exists and is populated for standalone units before shipping — see open questions.)

**Option C — keep both:** apply Option A now to stop the bleeding, schedule Option B to fix the policy and the parallel `set_property_features`/`_get_units_for_property` blind spot for standalone units.

I recommend **Option A immediately** + **Option B as the durable fix**.

---

## Open questions to confirm (DB was paused, couldn't verify live)

The Supabase project `bpvzfboslevifpnsezts` is currently **INACTIVE/paused**, so I could not query the live rows. To confirm the mechanism with 100% certainty, please verify (or un-pause and I'll run it):

1. For the affected units, are they standalone? Expected: `building_id IS NULL`.
   ```sql
   SELECT id, flat_number, building_id, property_id FROM flats WHERE id IN (298, 299);
   ```
2. Does `flats` have a `property_id` column populated for standalone units? (Needed for Option B's `COALESCE` path.) `CODEBASE_CONTEXT.md` lists `building_id` on `flats` but the standalone filter in `SettingsPage.jsx:370` reads `f.property_id`, so confirm the column exists and is set on creation — `create_flat`'s payload currently sets neither `property_id` nor a building for standalone units, which may be a separate gap.
3. Confirm there is no separate, newer `property_features` RLS migration overriding `02_rls_policies.sql` (I found none in `backend/migrations/`).

---

## Resolution — implemented (Option C)

Investigation during implementation revised Option B: `flats` has **no usable `property_id`** column (the `SettingsPage.jsx:370` read is effectively dead), so the `COALESCE(b.property_id, f.property_id)` idea above is not viable. Per product direction, standalone units (bungalows, etc.) are first-class and must be owned by a **direct manager FK** instead.

**A — Immediate (shipped, code only):**
- `create_flat` now initializes features with `FeatureService(svc)` instead of `db` (`backend/app/routes/flats.py`), so feature init no longer hits RLS.
- `initialize_unit_features` now re-raises on failure (`feature_service.py`), so the `[FEATURES INITIALIZED]` log only prints on real success (fixes the misleading log).

**B — Durable (migration `029_flats_manager_id_and_rls.sql`, run when DB un-paused):**
- Adds `flats.manager_id` UUID FK → `auth.users(id)`, indexed.
- Backfills building-attached flats from the chain; standalone orphans (e.g. 298/299) need manual backfill (no link to a manager exists).
- Rewrites `flats`, `property_features`, `tenants`, `rents` RLS to **additive** policies: building chain **OR** direct `manager_id` ownership, with explicit `WITH CHECK`. Additive = no existing visible rows are hidden pre-backfill.
- `manager_id = user["sub"]` is now set on every flat insert: `create_flat`, CSV `import_routes.import_properties`, and chatbot `add_new_unit` (threaded via `run_chat` → `execute_tool`).

**Known follow-ups:**
- Un-pause Supabase and run migration 029; then backfill orphaned standalone units and (optionally) set `flats.manager_id` `NOT NULL`.
- Denormalization caveat: `flats.manager_id` is authoritative and won't auto-track a property being reassigned to another manager (not a supported operation today).
