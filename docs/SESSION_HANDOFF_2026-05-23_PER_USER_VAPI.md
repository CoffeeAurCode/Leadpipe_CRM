# Session Handoff — Per-User VAPI Provisioning
**Date:** 2026-05-23  
**Branch:** main  
**Last commit before this session:** `215bb2e5` (refactor: remove shared lease agent functionality)

---

## What Was Done This Session

Implemented the full per-user VAPI provisioning redesign from `docs/development_plans/PLAN_PER_USER_VAPI_PROVISIONING.md`.

**Architecture shift:** From per-property-group (1 number per group) → per-manager (1 number per manager account, covering all their groups).

### Files Changed

| File | Change |
|---|---|
| `backend/app/services/vapi_provisioning.py` | Full rewrite — `provision_vapi_for_manager(manager_id, db)` replaces `provision_vapi_for_property_group` |
| `backend/app/services/vapi_agent_config.py` | `build_lease_config(backend_url, manager_id)` — removed `property_group_id`/`pg_name`; tool URLs use `?manager_id=` |
| `backend/app/routes/property_groups.py` | `create_property_group` → only provisions on first group; removed `POST /{id}/provision-voice`; added `GET /users/me/vapi-config` and `POST /users/me/provision-voice` |
| `backend/app/routes/voice.py` | Lease-lead-webhook Paths 2 & 3 → `manager_vapi_config`; outbound lease → `manager_vapi_config` |
| `backend/app/routes/leasing.py` | `/find-listing` and `/search` accept `manager_id` query param; filter across all manager's groups |
| `frontend/src/services/apiService.js` | Added `getUserVapiConfig()` and `retryUserProvisioning()` |
| `frontend/src/components/LeasingTab.jsx` | Per-group VAPI status grid → single account-level banner |
| `CODEBASE_CONTEXT.md` | Updated to reflect new architecture throughout |

---

## What Is NOT Done Yet — Must Do Before Deploying

### Phase 1: Supabase SQL Migrations (run in Supabase SQL editor)

These have NOT been run. The backend code will break at runtime until these are in place.

**Step 1.1 — Create `manager_vapi_config` table:**
```sql
CREATE TABLE manager_vapi_config (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id              UUID NOT NULL UNIQUE,
    vapi_lease_assistant_id TEXT,
    vapi_phone_number_id    TEXT,
    vapi_phone_number       TEXT,
    vapi_provisioning_status TEXT NOT NULL DEFAULT 'pending',
    pool_row_id             UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE manager_vapi_config ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager reads own vapi config"
ON manager_vapi_config FOR SELECT
USING (manager_id = auth.uid());
```

**Step 1.2 — Modify `twilio_number_pool`:**
```sql
ALTER TABLE twilio_number_pool
    ADD COLUMN assigned_manager_id UUID,
    DROP COLUMN IF EXISTS assigned_property_group_id;
```
> If you want to keep the old data for reference, rename instead of drop:
> `ALTER TABLE twilio_number_pool RENAME COLUMN assigned_property_group_id TO _legacy_assigned_property_group_id;`

**Step 1.3 — Migrate `leadpipecrm@gmail.com` existing data:**

First check if there's any active per-group data to migrate:
```sql
SELECT id, name, vapi_lease_assistant_id, vapi_phone_number_id, vapi_phone_number, vapi_provisioning_status
FROM properties_list
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
  AND vapi_provisioning_status = 'active';
```

If rows come back → migrate the first one:
```sql
INSERT INTO manager_vapi_config (manager_id, vapi_lease_assistant_id, vapi_phone_number_id, vapi_phone_number, vapi_provisioning_status)
SELECT
    manager_id,
    vapi_lease_assistant_id,
    vapi_phone_number_id,
    vapi_phone_number,
    'active'
FROM properties_list
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
  AND vapi_provisioning_status = 'active'
LIMIT 1;
```

If no active rows (current state after the last refactor nulled them out) → insert pending so provisioning can be triggered:
```sql
INSERT INTO manager_vapi_config (manager_id, vapi_provisioning_status)
VALUES ('28c43c77-8c9c-496f-8d1e-39ffa9d619e3', 'pending')
ON CONFLICT (manager_id) DO NOTHING;
```

**Step 1.4 — Null out per-group VAPI columns (they are now unused):**
```sql
UPDATE properties_list
SET
    vapi_lease_assistant_id  = NULL,
    vapi_phone_number_id     = NULL,
    vapi_phone_number        = NULL,
    vapi_provisioning_status = 'not_applicable'
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';
```

**Step 1.5 — Update pool row for `+14313415768` to `available`:**
```sql
UPDATE twilio_number_pool
SET
    assigned_manager_id = NULL,
    status = 'available'
WHERE phone_number = '+14313415768';
```
(Provisioning will flip it to `assigned` when it claims it.)

---

### Phase 4: Post-Deploy Steps

After running migrations and deploying:

1. **Trigger provisioning for `leadpipecrm@gmail.com`** via the API (need their bearer token):
   ```
   POST /property-groups/users/me/provision-voice
   Authorization: Bearer <leadpipecrm token>
   ```
   Or use the Retry button in the LeasingTab UI.

2. **Verify `manager_vapi_config` row:**
   ```sql
   SELECT * FROM manager_vapi_config WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';
   -- Expect: vapi_provisioning_status = 'active', vapi_phone_number = '+14313415768'
   ```

3. **Verify pool row:**
   ```sql
   SELECT * FROM twilio_number_pool WHERE phone_number = '+14313415768';
   -- Expect: status = 'assigned', assigned_manager_id = '28c43c77-...'
   ```

4. **Make test inbound call to `+14313415768`** — agent should show listings from ALL leadpipecrm property groups.

5. **Make test outbound lease call** from the app.

---

## Verification Checklist (from the plan)

- [ ] `manager_vapi_config` for `leadpipecrm@gmail.com`: `status=active`, `vapi_phone_number=+14313415768`
- [ ] `twilio_number_pool`: `+14313415768` row has `status=assigned`, `assigned_manager_id=28c43c77-...`
- [ ] `properties_list` for all leadpipecrm groups: VAPI columns NULL, `vapi_provisioning_status=not_applicable`
- [ ] Inbound call to `+14313415768` → agent can see listings from ALL 10 property groups
- [ ] Lead captured → `manager_id=28c43c77-...`, `property_group_id` populated from `listing_uuid`
- [ ] New user signs up → creates first group → `manager_vapi_config` pending → provisioning runs → active
- [ ] Same user creates second group → NO new provisioning triggered → same number shown
- [ ] Outbound lease call → uses `manager_vapi_config` assistant

---

## Key Architecture Facts for Next Session

### New table: `manager_vapi_config`
One row per manager. Source of truth for VAPI provisioning state. RLS: managers read their own row only; all writes via service role.

### `twilio_number_pool` change
`assigned_property_group_id` column replaced by `assigned_manager_id`.

### Provisioning trigger
`create_property_group` in `property_groups.py` checks `manager_vapi_config` for an existing row. Only inserts + triggers if no row exists. `properties_list.vapi_provisioning_status` is always set to `not_applicable` for new groups — the column is unused going forward.

### Webhook resolution (lease-lead-webhook)
Path 2 and Path 3 now query `manager_vapi_config`, not `properties_list`. They return `manager_id` directly. `property_group_id` is only resolved via Path 1 (listing_uuid lookup).

### Leasing endpoints
`/leasing/find-listing` and `/leasing/search` both accept `?manager_id=<UUID>`. When present, they resolve all property group IDs for that manager and filter listings across all of them.

### Frontend
`LeasingTab` loads `getUserVapiConfig()` instead of `fetchPropertyGroups()` for the phone number display. Shows one banner, not a per-group grid.

---

## Manager IDs for Reference

| Account | manager_id |
|---|---|
| `leadpipecrm@gmail.com` | `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` |
