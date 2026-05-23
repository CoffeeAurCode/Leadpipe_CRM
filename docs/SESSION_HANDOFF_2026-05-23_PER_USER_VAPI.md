# Session Handoff — Per-User VAPI Provisioning
**Date:** 2026-05-23  
**Branch:** main  
**Commit:** `2a29d3c2` — feat: per-manager VAPI provisioning (one number per account)

---

## Status: Code shipped. DB migrated. Provisioning not yet triggered.

---

## What Was Completed This Session

### Code Changes (all committed + pushed)

| File | Change |
|---|---|
| `backend/app/services/vapi_provisioning.py` | Full rewrite — `provision_vapi_for_manager(manager_id, db)` |
| `backend/app/services/vapi_agent_config.py` | `build_lease_config(backend_url, manager_id)` — tool URLs use `?manager_id=` |
| `backend/app/routes/property_groups.py` | Provisions only on first group; removed `/{id}/provision-voice`; added `GET /users/me/vapi-config` and `POST /users/me/provision-voice` |
| `backend/app/routes/voice.py` | Lease-lead-webhook Paths 2 & 3 → `manager_vapi_config`; outbound lease → `manager_vapi_config` |
| `backend/app/routes/leasing.py` | `/find-listing` and `/search` accept `?manager_id=` param |
| `frontend/src/services/apiService.js` | Added `getUserVapiConfig()` and `retryUserProvisioning()` |
| `frontend/src/components/LeasingTab.jsx` | Per-group VAPI grid → single account-level banner |
| `CODEBASE_CONTEXT.md` | Updated throughout |
| `backend/migrations/015_per_manager_vapi.sql` | Full Phase 1 migration (committed for reference) |

### DB Migration (all steps run in Supabase)

| Step | What | Status |
|---|---|---|
| 1.1 | Created `manager_vapi_config` table with RLS | ✅ Done |
| 1.2 | Added `assigned_manager_id` to `twilio_number_pool`; renamed `assigned_property_group_id` → `_legacy_assigned_property_group_id` | ✅ Done |
| 1.3 | Inserted `pending` row for `leadpipecrm@gmail.com` into `manager_vapi_config` | ✅ Done |
| 1.4 | Nulled out VAPI columns on all 10 leadpipecrm `properties_list` rows | ✅ Done |
| 1.5 | Confirmed `+14313415768` pool row: `status=available`, `assigned_manager_id=null` | ✅ Done |

**Final verified pool state:**
```
id: e4eee265-fd19-4760-9d55-eb8b13cb2854
phone_number: +14313415768
vapi_phone_number_id: 969c6812-b520-468e-8f65-5fb8ca4ee240
status: available
assigned_manager_id: null
```

---

## What Still Needs to Be Done

### 1. Trigger provisioning for leadpipecrm (after Render deploy is live)

**Option A — UI:** Log in as `leadpipecrm@gmail.com` → go to Leasing tab → the banner will show "Setting up..." or "Setup failed" → hit **Retry**.

**Option B — API:**
```
POST /property-groups/users/me/provision-voice
Authorization: Bearer <leadpipecrm JWT>
```

This will:
1. Claim `+14313415768` from the pool → `status=assigned`, `assigned_manager_id=28c43c77-...`
2. Create a new VAPI assistant named `Lease Agent [28c43c77]`
3. Link the assistant to `+14313415768` in VAPI
4. Write `status=active` to `manager_vapi_config`

### 2. Verify after provisioning

Run in Supabase SQL editor:
```sql
-- Should show: status=active, phone=+14313415768
SELECT manager_id, vapi_provisioning_status, vapi_phone_number, vapi_lease_assistant_id
FROM manager_vapi_config
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';

-- Should show: status=assigned, assigned_manager_id=28c43c77-...
SELECT phone_number, status, assigned_manager_id, assigned_at
FROM twilio_number_pool
WHERE phone_number = '+14313415768';
```

### 3. Verification Checklist

- [ ] `manager_vapi_config`: `status=active`, `vapi_phone_number=+14313415768`
- [ ] `twilio_number_pool`: `+14313415768` → `status=assigned`, `assigned_manager_id=28c43c77-...`
- [ ] Inbound call to `+14313415768` → agent can see listings from ALL 10 leadpipecrm property groups
- [ ] Lead captured on that call → `manager_id=28c43c77-...`, `property_group_id` populated from `listing_uuid`
- [ ] New user creates first property group → `manager_vapi_config` row inserted → provisioning runs → `active`
- [ ] Same user creates second group → NO new provisioning triggered → same number shown
- [ ] Outbound lease call from app → uses `manager_vapi_config` assistant

---

## Key Architecture Facts

### New table: `manager_vapi_config`
One row per manager. Source of truth for VAPI state. RLS: managers read their own row only; all writes via service role.

### `twilio_number_pool` change
`assigned_property_group_id` renamed to `_legacy_assigned_property_group_id`. New column: `assigned_manager_id`.

### Provisioning trigger (in `property_groups.py`)
`create_property_group` checks `manager_vapi_config` for an existing row. Only provisions on first group. `properties_list.vapi_provisioning_status` always set to `not_applicable` for new groups — that column is unused going forward.

### Webhook resolution (lease-lead-webhook in `voice.py`)
- Path 1: `listing_uuid` → `lease_listings.property_group_id` (unchanged)
- Path 2: `call.assistantId` → `manager_vapi_config.vapi_lease_assistant_id` → returns `manager_id`
- Path 3: `call.phoneNumberId` → `manager_vapi_config.vapi_phone_number_id` → returns `manager_id`

### Leasing endpoints
`/leasing/find-listing` and `/leasing/search` both accept `?manager_id=<UUID>`. Filters listings across all property groups owned by that manager (resolves group IDs internally).

### Frontend
`LeasingTab` calls `getUserVapiConfig()` on load. Shows one banner: phone number (active) / spinner (pending) / retry button (failed) / instructional text (not_set_up).

---

## Manager IDs for Reference

| Account | manager_id |
|---|---|
| `leadpipecrm@gmail.com` | `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` |
