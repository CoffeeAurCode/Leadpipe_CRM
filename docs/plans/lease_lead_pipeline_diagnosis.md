# Lease Lead Pipeline — Diagnosis Report

**Date:** 2026-05-22 (updated after CSV inspection)
**Status:** Root causes fully identified — two data fixes required, no further code changes needed

---

## What Is Actually Working

| Layer | Status | Evidence |
|---|---|---|
| VAPI call triggers webhook | ✅ Working | Render log shows `[LEASE LEAD WEBHOOK] Incoming payload` |
| Webhook parses the tool call | ✅ Working | Log shows all `submit_lease_lead` args |
| Property group resolution (Path 4) | ✅ Working (after f51038ab) | Rows 17-19 saved with correct `property_group_id` |
| Lead insert into `lease_leads` | ✅ Working | CSV confirms 4 real calls saved (IDs 16-19) |
| `GET /leasing/leads` HTTP status | ✅ 200 OK | Confirmed via DevTools |
| `GET /leasing/leads` response | ❌ Returns `[]` | Both pg_id resolution paths returning empty |
| Leads appearing in UI | ❌ Not appearing | Downstream of above |
| Fallback code deployed | ✅ Deployed | Commits b428ef51 + ab85cba5 live on origin/main |

---

## What the CSV Reveals

The `lease_leads` table has 19 rows. Only 4 are real calls from +919998064026:

| id | caller_name | property_group_id | call_id | created_at (UTC) | Issue |
|----|-------------|------------------|---------|-----------------|-------|
| 16 | Pablo Singh | **NULL** | 019e4e71 | 06:49 | Webhook bug pre-f51038ab — pg_id resolved in memory but not saved |
| 17 | Raul Singh | aeb9d575-… | 019e4e99 | 07:34 | ✅ Correct — still not showing up |
| 18 | Unknown Caller | aeb9d575-… | 019e4ed2 | 08:36 | ✅ Correct — still not showing up |
| 19 | Raj | aeb9d575-… | 019e4ed4 | 08:38 | ✅ Correct — still not showing up |

Rows 1–15 are automated test data (dummy phone numbers +15551234567 etc.) with NULL or a different `property_group_id`. They are not the user's real leads.

---

## Root Cause Breakdown

### Root Cause A — Row 16 saved with NULL property_group_id (webhook pre-fix bug)

**What happened:** Commit `f51038ab` enhanced property group resolution. Before that commit, the webhook resolved `property_group_id` in a local variable but the INSERT payload didn't include it. Call 019e4e71 (Pablo Singh, 06:49) hit this bug.

**Evidence:** Log showed `path=shared_agent_fallback property_group_id=aeb9d575-…` but the DB row has `property_group_id = NULL`.

**Status:** Webhook bug is fixed (f51038ab). The saved row still needs a manual data fix.

---

### Root Cause B — `get_leads` can't resolve which property groups belong to the manager

Rows 17, 18, 19 have the correct `property_group_id = aeb9d575-…`. They are in the DB. They don't appear because `get_leads` builds a `pg_ids` filter that comes back empty, so the `WHERE property_group_id IN (...)` clause never runs with the right value.

`get_leads` tries two resolution paths:

**Primary path** (line 239):
```python
pg_resp = db.table("properties_list").select("id").eq("manager_id", user["sub"]).execute()
```
Returns `[]` because `properties_list.manager_id` is NULL for row `aeb9d575-…`. (Original Issue 1.)

**Fallback path** (line 242-244, commit b428ef51):
```python
listings_resp = db.table("lease_listings").select("property_group_id").eq("manager_id", user["sub"]).execute()
pg_ids = list({str(r["property_group_id"]) for r in ...})
```
Returns `[]` because `lease_listings` has **no row that has both `manager_id = user.sub` AND `property_group_id = aeb9d575-…`**.

This is most likely because the listing was either:
- Created with a flat whose building maps to a **different** `property_id`, OR
- Created manually (bypassing the API), so `manager_id` was not set

Either way: both paths return `[]` → `get_leads` returns `[]` → UI shows nothing.

---

## Required Fixes (all data fixes in Supabase — no code changes needed)

### Fix 1 — Set `manager_id` on `properties_list` (the permanent fix)

This fixes the **primary path** for `get_leads`, `get_metrics`, and `export_leads` in one step. All three endpoints share the same resolution logic.

1. Go to **Supabase → Authentication → Users** — copy your user UUID
2. Go to **Supabase → Table Editor → `properties_list`**
3. Find the row `id = aeb9d575-42e2-439f-ad81-8e99ae6900ed`
4. Set `manager_id` = your user UUID
5. Save

Or via **SQL Editor**:
```sql
-- First, find your user UUID
SELECT id, email FROM auth.users WHERE email = 'your@email.com';

-- Then set manager_id (replace the UUID below with yours)
UPDATE properties_list
SET manager_id = '<your-user-uuid>'
WHERE id = 'aeb9d575-42e2-439f-ad81-8e99ae6900ed';
```

After this fix, `get_leads` will return rows 17, 18, 19 immediately (Raj and the others).

---

### Fix 2 — Set `property_group_id` on Row 16 (Pablo Singh)

Row 16 was saved without `property_group_id` due to the pre-f51038ab webhook bug. Fix 1 alone won't surface it — you must patch the row directly.

```sql
UPDATE lease_leads
SET property_group_id = 'aeb9d575-42e2-439f-ad81-8e99ae6900ed'
WHERE id = 16;
```

After this, all 4 real leads (rows 16-19) will appear.

---

### Fix 3 (optional) — Delete automated test rows

Rows 1–15 are noise from test scripts (+155x phone numbers). They have NULL or unrelated `property_group_id` and will never appear in the UI — but they inflate the DB. Clean up if desired:

```sql
DELETE FROM lease_leads
WHERE phone IN ('+15551234567', '+15558888888', '+15559999999');
```

---

## Verification Checklist (after applying fixes)

- [ ] **Fix 1 applied**: `SELECT manager_id FROM properties_list WHERE id = 'aeb9d575-42e2-439f-ad81-8e99ae6900ed'` returns your user UUID (not NULL)
- [ ] **Fix 2 applied**: `SELECT property_group_id FROM lease_leads WHERE id = 16` returns `aeb9d575-...` (not NULL)
- [ ] **Reload Leasing tab → click Refresh** — leads table shows Raj, Raul Singh, Unknown Caller, Pablo Singh (4 rows)
- [ ] **Metrics panel** shows `total_calls = 4`, `qualified = 3`

---

## Issue 2 — "No Call Records" in Voice Stats (unchanged)

This is not a bug — it is a design gap. Lease lead calls write to `lease_leads` only. Voice Stats reads from `call_logs` which is populated exclusively by the complaint agent webhook. Two separate pipelines by design.

---

## Issue 4 — Response Validation (resolved)

Fixed in commit `ab85cba5`: `source` and `interested_listing_ids` made `Optional`. Confirmed working via 17 passing integration tests in `backend/tests/integration/test_leasing.py`.

---

## Export Data-Leak Bug (found and fixed today)

`export_leads` was missing the fallback AND the early-exit guard that `get_leads` had. When `pg_ids` resolved to empty, it queried all leads without a property_group_id filter — a cross-manager data leak. Fixed with the same fallback + early return logic. All 17 tests pass.

---

## Full Data Flow Reference

```
VAPI lease call
  └── POST /voice/lease-lead-webhook
        ├── Parse submit_lease_lead args
        ├── Resolve property_group_id (Paths 1→2→3→4)
        ├── INSERT into lease_leads  ← rows 17-19 correct, row 16 needs Fix 2
        └── Return {"status": "processed"}

Browser: Leasing tab → Refresh
  └── GET /leasing/leads
        ├── Query properties_list WHERE manager_id = user.sub → pg_ids  ← Fix 1 unblocks this
        │   └── Fallback: lease_listings WHERE manager_id = user.sub → pg_ids  ← currently also empty
        ├── Query lease_leads WHERE property_group_id IN pg_ids
        └── Return rows 17-19 (and 16 after Fix 2)

Browser renders leads table  ← visible after both fixes
```
