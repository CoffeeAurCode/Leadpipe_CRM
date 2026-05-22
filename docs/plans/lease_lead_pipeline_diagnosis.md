# Lease Lead Pipeline — Diagnosis Report

**Date:** 2026-05-22  
**Status:** 2 root causes identified, code fixes deployed, data fix still required

---

## What Is Actually Working

| Layer | Status | Evidence |
|---|---|---|
| VAPI call triggers webhook | ✅ Working | Render log shows `[LEASE LEAD WEBHOOK] Incoming payload` |
| Webhook parses the tool call | ✅ Working | Log shows all `submit_lease_lead` args |
| Property group resolution (Path 4) | ✅ Working | Log: `path=shared_agent_fallback property_group_id=aeb9d575-42e2-439f-ad81-8e99ae6900ed` |
| Lead insert into `lease_leads` | ✅ Working | Log: `[SAVED] phone=+919998064026 status=qualified` |
| `GET /leasing/leads` HTTP status | ✅ 200 OK | Confirmed via DevTools |
| `GET /leasing/leads` response | ❌ Returns `[]` | Empty array — filter returning nothing |
| Leads appearing in UI | ❌ Not appearing | Downstream of above |
| Call records in Voice Stats | ❌ By design | Explained in Issue 2 below |

---

## Issue 1 — Leads Not Appearing (Root Cause)

### What happens

`GET /leasing/leads` returns HTTP 200 but an empty array `[]`.

### Why

`get_leads` builds a property-group filter before querying `lease_leads`:

```python
# leasing.py:238
pg_resp = db.table("properties_list").select("id").eq("manager_id", user["sub"]).execute()
pg_ids = [str(r["id"]) for r in (pg_resp.data or [])]
```

If `pg_ids` is empty, the endpoint returns `[]` immediately (early exit at line 250).

`pg_ids` is empty because `properties_list.manager_id` is **NULL** (or a different UUID) for the row `aeb9d575-42e2-439f-ad81-8e99ae6900ed`.

### Why `get_listings` works but `get_leads` doesn't

`get_listings` filters `lease_listings.manager_id` directly — a different column on a different table. Listings were created via the API which sets `manager_id`. But the property group row may have been created manually in Supabase (bypassing the API), so `manager_id` was never set.

---

## Fix 1a — Code fix (already deployed)

Commits `b428ef51` and `ab85cba5` are live on `origin/main`. Render should have deployed them.

The fallback in `get_leads` (now deployed):

```python
if not pg_ids:
    listings_resp = db.table("lease_listings").select("property_group_id").eq("manager_id", user["sub"]).execute()
    pg_ids = list({str(r["property_group_id"]) for r in (listings_resp.data or []) if r.get("property_group_id")})
```

This derives `pg_ids` from `lease_listings.manager_id` when `properties_list.manager_id` is unset. Since `get_listings` works, the same `manager_id` applies and this should resolve.

**If leads are still `[]` after Render deploys:** the Render deployment may still be in progress. Check the Render dashboard — free-tier deploys take 2–5 minutes after a push.

---

## Fix 1b — Data fix (do this in Supabase)

Even with the code fallback, the underlying data should be corrected so the primary path works.

1. Open **Supabase → Table Editor → `properties_list`**
2. Find the row where `id = aeb9d575-42e2-439f-ad81-8e99ae6900ed`
3. Set `manager_id` to your user's UUID
4. To find your user UUID: **Supabase → Authentication → Users** — copy the UUID next to your email

---

## Verification checklist for Issue 1

- [ ] Render dashboard shows latest deploy is `Live` (not `In progress`)
- [ ] `GET /leasing/leads` — DevTools Response tab shows a JSON array with at least 1 object (not `[]`)
- [ ] Leads table in Leasing tab shows the test call from Raj (+919998064026)
- [ ] **Supabase:** `properties_list` row has `manager_id` set (permanent fix)

---

## Issue 2 — "No Call Records" in Voice Stats

### This is not a bug — it is a design gap

The VAPI call was a **lease lead call**. Lease lead calls write to the `lease_leads` table only.

The **Voice Stats tab** reads from the `call_logs` table via `GET /call_logs/stats`. The `call_logs` table is populated exclusively by the **complaint agent** webhook at `POST /voice/webhook`.

```
Complaint call  →  /voice/webhook         →  call_logs  →  Voice Stats tab
Lease lead call →  /voice/lease-lead-webhook  →  lease_leads  →  Leasing tab (Leads section)
```

These are two separate pipelines. A lease lead call will **never** appear in Voice Stats. This matches the intended design.

**If you want lease calls to appear in Voice Stats as well**, that requires adding a `call_logs` insert to the `lease_lead_webhook` — a separate feature change, not a bug fix.

---

## Issue 3 — Render Deployment Timing

Three commits were pushed today that fix the filter and schema:

| Commit | Change |
|---|---|
| `f51038ab` | Earlier leasing enhancements |
| `ab85cba5` | `LeadResponse.source` and `interested_listing_ids` made Optional |
| `b428ef51` | `get_leads` and `get_metrics` fallback via `lease_listings.manager_id` |

Render auto-deploys on push to `main`. Free-tier instances take ~3–5 min. If you checked the Leasing tab within a minute of the push, the old code was still running.

**To verify the right code is live:** Open `https://tenant-management-mvp.onrender.com/docs` and check the `GET /leasing/leads` endpoint summary — or check the Render dashboard directly.

---

## Issue 4 — Potential Response Validation Error (Latent)

If `pg_ids` resolves correctly and rows ARE returned from `lease_leads`, Pydantic validates each row. A validation failure returns HTTP 422 (not 200), and `getLeaseLeads()` throws — the frontend swallows it and leaves `leads = []`.

Risk fields and their status:

| Field | Type in schema | Risk | Status |
|---|---|---|---|
| `source` | `Optional[str] = "voice"` | NULL in older rows | **Fixed** (commit ab85cba5) |
| `interested_listing_ids` | `Optional[List[UUID]]` | Column exists with NULL | **Fixed** (commit ab85cba5) |
| `budget_max` | `Optional[Decimal]` | Supabase returns as string | Safe — Pydantic parses strings |
| `created_at` | `datetime` | Supabase auto-sets UTC ISO | Safe |
| `updated_at` | `Optional[datetime] = None` | Column may not exist | Safe — Optional with default |
| `qualifying_answers` | `Any` | JSONB, any shape | Safe |

**If after deploy you see HTTP 422 (not 200) on `GET /leasing/leads`:** open Render logs and look for `ResponseValidationError` with a field name — that field needs `Optional[...]` or a default added to `LeadResponse`.

---

## Full Action List

| Priority | Action | Where |
|---|---|---|
| 1 | Wait for Render deploy to complete (or trigger manual redeploy) | Render dashboard |
| 2 | Reload Leasing tab and click Refresh — verify leads appear | Browser |
| 3 | Set `manager_id` on `properties_list` row `aeb9d575-...` | Supabase Table Editor |
| 4 | Make one more test call and verify the lead appears without any DB edits | Live test |
| 5 | (Optional) Decide if lease calls should also appear in Voice Stats — requires separate feature work | Code |

---

## How the Full Data Flow Should Work (Reference)

```
VAPI lease call
  └── POST /voice/lease-lead-webhook
        ├── Parse submit_lease_lead args
        ├── Resolve property_group_id (Path 1/2/3/4)
        ├── INSERT into lease_leads ← row created here
        └── Return {"status": "processed"}

Browser: Leasing tab → Refresh
  └── GET /leasing/leads
        ├── Query properties_list WHERE manager_id = user.sub → pg_ids
        │   └── Fallback: query lease_listings WHERE manager_id = user.sub → pg_ids
        ├── Query lease_leads WHERE property_group_id IN pg_ids
        └── Validate each row as LeadResponse → return array

Browser renders leads table ← visible here
```

The Voice Stats tab is a completely separate branch:
```
VAPI complaint call
  └── POST /voice/webhook → INSERT into call_logs
Browser: Voice Stats tab → GET /call_logs/stats ← only complaint calls here
```
