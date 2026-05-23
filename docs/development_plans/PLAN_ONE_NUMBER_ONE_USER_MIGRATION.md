# Plan: One-Number-One-User Production Migration

**Date:** 2026-05-23  
**Goal:** Remove the shared lease agent env-var fallback, add `+14313415768` to the DB number pool, assign it to `leadpipecrm@gmail.com`'s property group, and make every property group in production use a dedicated, individually-provisioned VAPI phone number.

---

## Overview

### Current (broken) architecture
```
New property group created
  → if pool has a number: provision dedicated assistant (correct)
  → if pool is empty: fall back to SHARED assistant on +14313415768 (bad)

LeasingTab loads
  → calls POST /property-groups/assign-shared-agent
  → bulk-overwrites ALL unprovisioned groups with shared number/assistant (bad)
  → this is what causes the 500 (env vars missing on Render)
```

### Target (production) architecture
```
New property group created
  → pool has a number: provision dedicated per-group assistant (correct)
  → pool is empty: mark as 'failed', admin must add a number (no silent fallback)

LeasingTab loads
  → no auto-assign call at all
  → groups show 'failed' or 'active'; user can click retry manually
```

---

## What Changes

| Layer | What changes |
|---|---|
| Supabase DB | Add `+14313415768` to `twilio_number_pool`; reset `leadpipecrm@gmail.com` groups to `pending` |
| VAPI | `provision-voice` creates a new per-group assistant and re-links `+14313415768` to it |
| `config.py` | Remove `VAPI_SHARED_LEASE_*` fields |
| `vapi_provisioning.py` | Remove `_assign_shared_agent_fallback`; pool-empty → mark `failed` |
| `property_groups.py` | Remove `POST /assign-shared-agent` route |
| `voice.py` | Remove shared-agent fallback in outbound call endpoint |
| `vapi_agent_config.py` | Remove `build_lease_config_shared()` |
| `apiService.js` | Remove `assignSharedAgentToAllGroups()` |
| `LeasingTab.jsx` | Remove auto-assign-on-load block |
| Render env | Delete 3 env vars |

---

## Phase 1 — Supabase SQL (run in Supabase SQL Editor FIRST)

### Step 1.1 — Identify `leadpipecrm@gmail.com`

```sql
-- Find the manager's auth user ID
SELECT id, email FROM auth.users WHERE email = 'leadpipecrm@gmail.com';
-- Copy the UUID — use it as <MANAGER_UUID> in every query below
```

### Step 1.2 — Inspect their property groups

```sql
SELECT
  id,
  name,
  vapi_provisioning_status,
  vapi_lease_assistant_id,
  vapi_phone_number_id,
  vapi_phone_number
FROM properties_list
WHERE manager_id = '<MANAGER_UUID>';
```

**Expected:** One or more rows.  
- If any row already has `vapi_provisioning_status = 'active'` with a **different** phone number (not `+14313415768`), that group is already correctly provisioned — skip it.  
- Rows with `not_applicable`, `pending`, `failed`, or using `+14313415768` need to be re-provisioned.

### Step 1.3 — Check if the number is already in the pool

```sql
SELECT * FROM twilio_number_pool WHERE phone_number = '+14313415768';
```

- If **no row found**: proceed to Step 1.4.  
- If a row **already exists**: skip Step 1.4 and go to Step 1.5.

### Step 1.4 — Add `+14313415768` to the pool

> The number is already registered in VAPI (phone number ID: `969c6812-b520-468e-8f65-5fb8ca4ee240`).  
> We are NOT re-registering it — only inserting the pool record.

```sql
INSERT INTO twilio_number_pool (
  phone_number,
  vapi_phone_number_id,
  status,
  notes
)
VALUES (
  '+14313415768',
  '969c6812-b520-468e-8f65-5fb8ca4ee240',
  'available',
  'Migrated from VAPI_SHARED_LEASE env vars — existing VAPI registration'
);
```

### Step 1.5 — Reset target property groups to `pending`

Run for **each property group that needs re-provisioning** (i.e., the one(s) for `leadpipecrm@gmail.com` that are not correctly provisioned with a dedicated number).

```sql
-- Reset ONE specific group (replace <GROUP_UUID> with the actual id from Step 1.2)
UPDATE properties_list
SET
  vapi_provisioning_status = 'pending',
  vapi_lease_assistant_id  = NULL,
  vapi_phone_number_id     = NULL,
  vapi_phone_number        = NULL
WHERE id = '<GROUP_UUID>'
  AND manager_id = '<MANAGER_UUID>';
```

If they have **multiple groups** needing re-provisioning and only ONE pool number available (`+14313415768`), reset only the FIRST group. The second group will hit "pool empty" and be marked `failed`. You must add another Twilio number to the pool before provisioning the second group.

### Step 1.6 — Verify pool state

```sql
SELECT phone_number, vapi_phone_number_id, status, assigned_property_group_id
FROM twilio_number_pool
ORDER BY created_at;
```

Confirm `+14313415768` shows `status = 'available'`.

---

## Phase 2 — Trigger VAPI Provisioning (run after SQL)

**Prerequisite:** The backend must be deployed with the code changes from Phase 3 BEFORE you trigger provisioning. If you trigger now (before code changes), the old fallback code still runs.  
**Order:** SQL → Code changes → Deploy → Trigger provisioning.

Once deployed, trigger provisioning for each reset group via the API:

```bash
# Replace <GROUP_UUID> and <BEARER_TOKEN> with real values
curl -X POST https://tenant-management-mvp.onrender.com/property-groups/<GROUP_UUID>/provision-voice \
  -H "Authorization: Bearer <BEARER_TOKEN>"
```

Or use the Leasing tab → click the retry/re-provision button on the property group card (if that UI exists).

**What provisioning does automatically:**
1. Claims `+14313415768` from the pool (marks it `assigned`)
2. Creates a NEW per-group VAPI lease assistant using `build_lease_config()` with the property group ID baked in
3. Calls `client.phone_numbers.update()` to re-link `+14313415768` to the new per-group assistant (overwriting the old shared-assistant link in VAPI)
4. Updates `properties_list` with the new `vapi_lease_assistant_id`, `vapi_phone_number_id = 969c6812-b520-468e-8f65-5fb8ca4ee240`, `vapi_phone_number = +14313415768`, `vapi_provisioning_status = active`
5. Marks the pool row as `assigned` with `assigned_property_group_id`

**After provisioning — verify:**
```sql
SELECT
  id,
  name,
  vapi_provisioning_status,
  vapi_lease_assistant_id,
  vapi_phone_number_id,
  vapi_phone_number
FROM properties_list
WHERE manager_id = '<MANAGER_UUID>';
```

- `vapi_provisioning_status` → `active`
- `vapi_phone_number` → `+14313415768`
- `vapi_lease_assistant_id` → a NEW UUID (not `2dba3a50-...`, which was the shared assistant)

---

## Phase 3 — Code Changes

### 3.1 `backend/app/config.py` — Remove shared lease fields

**Delete these 3 lines:**
```python
# Shared lease agent (existing property groups)          ← delete
VAPI_SHARED_LEASE_ASSISTANT_ID: str = os.getenv("VAPI_SHARED_LEASE_ASSISTANT_ID", "")  ← delete
VAPI_SHARED_LEASE_NUMBER_ID: str = os.getenv("VAPI_SHARED_LEASE_NUMBER_ID", "")        ← delete
VAPI_SHARED_LEASE_PHONE_NUMBER: str = os.getenv("VAPI_SHARED_LEASE_PHONE_NUMBER", "")  ← delete
```

---

### 3.2 `backend/app/services/vapi_provisioning.py` — Remove shared fallback

**Delete the entire `_assign_shared_agent_fallback` function (lines 10–33).**

**Replace the pool-empty branch inside `provision_vapi_for_property_group`:**

Before:
```python
if not pool_resp.data:
    # Pool is empty — fall back to shared lease agent so the group is never left as 'failed'
    _assign_shared_agent_fallback(svc_db, db, property_group_id)
    return
```

After:
```python
if not pool_resp.data:
    print(f"[TWILIO PROVISION] Pool empty — marking group {property_group_id} as failed. Add a number via add_twilio_number_to_vapi.py")
    db.table("properties_list").update({
        "vapi_provisioning_status": "failed",
    }).eq("id", property_group_id).execute()
    return
```

Also remove the `settings` import at the top of the file since it was only used by `_assign_shared_agent_fallback`. Check that nothing else in the file uses `settings`.

---

### 3.3 `backend/app/routes/property_groups.py` — Remove `/assign-shared-agent` route

**Delete the entire route (from `@router.post("/assign-shared-agent"` through its closing `except` block — currently lines 145–194).**

The docstring, the env-var checks, the try/except, the DB queries — all of it. The endpoint will no longer exist.

---

### 3.4 `backend/app/routes/voice.py` — Remove shared-agent outbound fallback

**Replace the lease agent block in `make_outbound_call`:**

Before (~lines 707–709):
```python
else:
    assistant_id = settings.VAPI_SHARED_LEASE_ASSISTANT_ID
    phone_number_id = settings.VAPI_SHARED_LEASE_NUMBER_ID or settings.VAPI_NUMBER_ID
```

After:
```python
else:
    raise HTTPException(
        status_code=500,
        detail="No active lease agent found for this account. Check VAPI provisioning status."
    )
```

Also remove the `settings.VAPI_SHARED_LEASE_*` references from the import (they'll no longer exist in config).

---

### 3.5 `backend/app/services/vapi_agent_config.py` — Remove shared lease builder

**Delete `build_lease_config_shared()` (lines 1165–1172).**

The function is no longer called anywhere once the `assign-shared-agent` route and fallback are removed. Leave `build_lease_config()` (per-group builder) and all other functions intact.

---

### 3.6 `frontend/src/services/apiService.js` — Remove shared agent API call

**Delete the `assignSharedAgentToAllGroups` function (~lines 436–444):**
```js
/** Assign the shared lease agent phone number to all unprovisioned property groups for the current manager. */
export async function assignSharedAgentToAllGroups() {
    const response = await authFetch(`${API_BASE_URL}/property-groups/assign-shared-agent`, {
        method: 'POST',
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
}
```

---

### 3.7 `frontend/src/components/LeasingTab.jsx` — Remove auto-assign on load

**Remove the import of `assignSharedAgentToAllGroups` (line 8).**

**Remove the auto-assign block (~lines 74–83):**

Before:
```js
const unprovisioned = pg.filter(g => g.vapi_provisioning_status !== 'active');
if (unprovisioned.length > 0) {
    try {
        await assignSharedAgentToAllGroups();
        const refreshed = await fetchPropertyGroups();
        setPropertyGroups(refreshed);
    } catch (e) {
        console.error('Auto-assign shared agent failed', e);
        setPropertyGroups(pg);
    }
} else {
    setPropertyGroups(pg);
}
```

After (just set directly — no auto-provision):
```js
setPropertyGroups(pg);
```

---

## Phase 4 — Render Environment Changes

Go to Render dashboard → your backend service → **Environment** tab.

### Variables to DELETE (remove entirely):
- `VAPI_SHARED_LEASE_ASSISTANT_ID`
- `VAPI_SHARED_LEASE_NUMBER_ID`
- `VAPI_SHARED_LEASE_PHONE_NUMBER`

### Variables to KEEP (do not touch):
- `VAPI_COMPLAINT_ASSISTANT_ID` = `9e507761-7bf7-451a-9413-8ae62ec0176f`
- `VAPI_COMPLAINT_NUMBER_ID` = `e8367bd3-12c6-4423-aa93-27ee8b264f48`
- `VAPI_COMPLAINT_PHONE_NUMBER` = `+14382314283`
- `PRIVATE_VAPI_API`, `SUPABASE_SERVICE_KEY`, all others

After deleting the 3 vars, click **Save Changes** — Render will redeploy automatically.

---

## Phase 5 — Execution Order

```
1. Run Phase 1 SQL (Supabase SQL Editor)
2. Make Phase 3 code changes locally
3. Commit and push → Render auto-deploys
4. Wait for Render deploy to finish (watch logs for startup OK)
5. Trigger Phase 2 provisioning (API call or UI retry button)
6. Verify DB (Step 1.6 query)
7. Make a test inbound call to +14313415768
   → Should reach the new per-group lease assistant for leadpipecrm@gmail.com
8. Make a test outbound lease call via the app
   → Should use the new per-group assistant
9. Delete Phase 4 Render vars AFTER confirming everything works
```

> **Why delete Render vars last?**  
> If something goes wrong during deploy, the old shared vars being present won't hurt (the code no longer reads them). Deleting them last means rollback is simpler.

---

## Phase 6 — Post-Migration Cleanup (optional, after everything verified)

### Delete the old shared lease VAPI assistant
The shared assistant `2dba3a50-6862-400c-861a-bfc0a45d4a95` is now orphaned — nothing calls it, no number is linked to it (the number was re-linked to the new per-group assistant by provisioning). Delete it from the VAPI dashboard to keep the account clean.

### Remove the old shared number link in VAPI (already done by provisioning)
Provisioning calls `client.phone_numbers.update(vapi_phone_number_id, assistant_id=new_id)` which replaces the link. The VAPI phone number object for `+14313415768` now points to the new per-group assistant.

### Update `backend/scripts/update_shared_agents.py`
This script updates the shared assistant prompt. It's now obsolete. Either delete it or add a note at the top saying it's no longer applicable (the shared agent no longer exists).

---

## Rollback Plan

If something breaks after deploy:

**Fast rollback (Render vars):**
- Re-add `VAPI_SHARED_LEASE_ASSISTANT_ID = 2dba3a50-6862-400c-861a-bfc0a45d4a95`
- Re-add `VAPI_SHARED_LEASE_NUMBER_ID = 969c6812-b520-468e-8f65-5fb8ca4ee240`
- Re-add `VAPI_SHARED_LEASE_PHONE_NUMBER = +14313415768`

But the code changes would already be live. To fully revert, you'd need to redeploy the previous commit.

**DB rollback:**
If provisioning ran and the property group was updated, but you want to undo:
```sql
-- Reset the group (remove the new per-group assignment)
UPDATE properties_list
SET
  vapi_provisioning_status = 'not_applicable',
  vapi_lease_assistant_id  = NULL,
  vapi_phone_number_id     = NULL,
  vapi_phone_number        = NULL
WHERE id = '<GROUP_UUID>';

-- Return the number to available in pool
UPDATE twilio_number_pool
SET
  status                      = 'available',
  assigned_property_group_id  = NULL,
  assigned_at                 = NULL
WHERE phone_number = '+14313415768';
```

Then re-link `+14313415768` back to the old shared assistant in VAPI dashboard manually (assistant ID: `2dba3a50-6862-400c-861a-bfc0a45d4a95`).

---

## Verification Checklist

After full migration:

- [ ] `properties_list` for `leadpipecrm@gmail.com`: `vapi_provisioning_status = active`, `vapi_phone_number = +14313415768`, `vapi_lease_assistant_id` ≠ `2dba3a50-...`
- [ ] `twilio_number_pool`: `+14313415768` row has `status = assigned`, `assigned_property_group_id = <GROUP_UUID>`
- [ ] Inbound call to `+14313415768` → reaches new per-group lease assistant (not shared one)
- [ ] Outbound lease call from app → uses per-group assistant, not shared
- [ ] New property group created by another user → provisioning marks as `failed` (pool is empty) instead of silently using shared
- [ ] Render env: `VAPI_SHARED_LEASE_*` vars are gone
- [ ] No 500 on LeasingTab load (the `/assign-shared-agent` route no longer exists and is no longer called)
- [ ] `webhook` lease-lead resolution: Path 2 (assistant_id lookup) resolves correctly for per-group assistant
