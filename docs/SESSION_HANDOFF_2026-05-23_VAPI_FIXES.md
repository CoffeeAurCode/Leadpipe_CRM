# Session Handoff — VAPI Provisioning Fixes
**Date:** 2026-05-23
**Branch:** main
**Continues from:** `SESSION_HANDOFF_2026-05-23_PER_USER_VAPI.md`

---

## Status: Provisioning working. Listing filter fixed. One pool number pending cleanup.

---

## What Was Fixed This Session

### 1. VAPI `phone_numbers.update` — wrong SDK type
**Problem:** `UpdatePhoneNumberDto` doesn't exist in the installed SDK version. Fallback using `assistant_id=` kwarg also rejected. Final SDK attempt using `UpdatePhoneNumbersRequestBody_Twilio` was rejected by VAPI API with `property provider should not exist`.

**Fix:** Replaced all SDK calls with a direct `httpx.patch` to `https://api.vapi.ai/phone-number/{id}` sending only `{"assistantId": "..."}`. No `provider` field. File: `backend/app/services/vapi_provisioning.py`.

### 2. Race condition — multiple pool numbers assigned to one manager
**Problem:** Rapid button clicks fired multiple concurrent background tasks. Each task ran `SELECT available → UPDATE assigned` non-atomically, claiming a different pool number before any finished.

**Fixes:**
- Added `already_claimed` guard at the top of `provision_vapi_for_manager` — if manager already has a pool row, reuse it instead of claiming a new one.
- Added `CREATE UNIQUE INDEX twilio_number_pool_one_per_manager ON twilio_number_pool (assigned_manager_id) WHERE assigned_manager_id IS NOT NULL` — DB-level enforcement.
- Migration: `backend/migrations/016_fix_vapi_provisioning_cleanup.sql`

### 3. Retry endpoint fired when already active
**Fix:** `POST /users/me/provision-voice` now checks `manager_vapi_config.vapi_provisioning_status`. If `active`, returns early without spawning a background task.

### 4. UI — no button in `pending` state, no debounce
**Fixes:**
- Added "Stuck? Trigger setup" link in the `pending` state banner (alongside spinner).
- `handleRetryProvisioning` now guards against double-fire with `if (retrying) return`.
- After clicking, polls once after 8 seconds to auto-update the UI without requiring a full refresh.
- File: `frontend/src/components/LeasingTab.jsx`

### 5. Background task passed request-scoped DB
**Problem:** `background_tasks.add_task(provision_vapi_for_manager, user["sub"], db)` passed a request-scoped `get_authenticated_db` client that expires after the response is sent.

**Fix:** Routes now pass `svc_db` (service-role client) to the background task. Files: `backend/app/routes/property_groups.py`.

### 6. Lease agent showing all listings (wrong manager)
**Problem:** `/leasing/find-listing` and `/leasing/search` filtered by `manager_id` using a two-step query: lookup `properties_list` by `manager_id` → get group IDs → filter `lease_listings` on `property_group_id`. The fallback title-search path had no `else` clause — if `group_ids` was empty, no filter was applied and ALL listings were returned.

**Fix:** Both routes now filter `lease_listings.manager_id` directly with `.eq("manager_id", manager_id)`. Simpler, correct, avoids the two-step join. `lease_listings.manager_id` is always set at creation (`payload["manager_id"] = user.get("sub")`).
File: `backend/app/routes/leasing.py`

---

## Current Pool State

| phone_number | vapi_phone_number_id | status | assigned_manager_id |
|---|---|---|---|
| `+12494028641` | `d92e90cd-...` | **assigned** (needs cleanup — see below) | `02672346-db53-4f2f-9a68-f2bf87ebf95c` |
| `+14313404212` | `857191a6-...` | assigned | `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` (leadpipecrm) |
| `+14313415768` | `969c6812-...` | available | — |

---

## Pending Action — Unassign `+12494028641`

`+12494028641` was assigned to manager `02672346-db53-4f2f-9a68-f2bf87ebf95c` during the race condition incident. That manager does not appear to have a valid `manager_vapi_config` row (no active provisioning).

**Run in Supabase SQL editor:**
```
backend/migrations/017_unassign_12494028641.sql
```

Which executes:
```sql
UPDATE twilio_number_pool
SET status = 'available', assigned_manager_id = NULL, assigned_at = NULL
WHERE id = '89c1437e-912d-4e62-8794-f42a583e85c6';
```

Also check `manager_vapi_config` for manager `02672346-db53-4f2f-9a68-f2bf87ebf95c` and delete or reset that row if it exists.

---

## Current Provisioning State (leadpipecrm)

| Field | Value |
|---|---|
| manager_id | `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` |
| vapi_provisioning_status | `active` |
| vapi_phone_number | `+14313404212` |
| vapi_phone_number_id | `857191a6-81ec-4fe1-bc45-2e955ec17542` |

---

## Key Architecture Facts

### Provisioning flow (`vapi_provisioning.py`)
1. Check `manager_vapi_config` — exit if already `active`
2. Check `twilio_number_pool` for an existing row `assigned_manager_id = manager_id` — reuse if found (race guard)
3. Else: claim first `available` row from pool
4. `client.assistants.create(**build_lease_config(BACKEND_URL, manager_id))`
5. `httpx.patch(f"https://api.vapi.ai/phone-number/{vapi_phone_number_id}", json={"assistantId": lease.id})`
6. Upsert `manager_vapi_config` → `status=active`

### Tool URL scoping (`vapi_agent_config.py`)
`build_lease_config(backend_url, manager_id)` bakes `&manager_id={manager_id}` into every tool URL at assistant creation time. No dynamic injection needed at call time.

### Listing filter (`leasing.py`)
Both `/leasing/find-listing` and `/leasing/search` now apply `.eq("manager_id", manager_id)` directly on `lease_listings` when `manager_id` param is present. `property_group_id` param still works as a narrower override (used by per-group legacy calls).

### DB constraint added
```sql
CREATE UNIQUE INDEX twilio_number_pool_one_per_manager
ON twilio_number_pool (assigned_manager_id)
WHERE assigned_manager_id IS NOT NULL;
```
Prevents any future race condition from assigning two numbers to the same manager.

---

## Dangling VAPI Assistants
Multiple failed provisioning attempts created orphan assistants in VAPI (each `client.assistants.create` succeeded before the `phone_numbers.update` failed). These are harmless but waste VAPI account slots.

**Clean up:** Go to VAPI dashboard → Assistants → delete any named `Lease Agent [28c43c77]` that is NOT the one currently linked to `+14313404212`.

---

## Files Changed This Session

| File | Change |
|---|---|
| `backend/app/services/vapi_provisioning.py` | `httpx.patch` for phone link; `already_claimed` race guard; service DB throughout |
| `backend/app/routes/property_groups.py` | Retry endpoint checks active status; passes `svc_db` to background task |
| `backend/app/routes/leasing.py` | Direct `manager_id` filter on `lease_listings` in both find and search routes |
| `frontend/src/components/LeasingTab.jsx` | Trigger button in pending state; debounce guard; 8s auto-poll |
| `backend/migrations/016_fix_vapi_provisioning_cleanup.sql` | Reset pool rows; unique index |
| `backend/migrations/017_unassign_12494028641.sql` | Unassign `+12494028641` from orphaned manager |
