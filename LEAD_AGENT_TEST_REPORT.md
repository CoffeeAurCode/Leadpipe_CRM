# Lease Agent — Test Report

**Date:** 2026-05-22
**Tester:** Claude Code (automated execution)
**Test plan source:** `LEAD_AGENT_TEST_PLAN.md`
**Test file created:** `backend/tests/test_leasing.py`

---

## Summary

| Category | Total | Passed | Failed | Skipped |
|---|---|---|---|---|
| Part 1 — Automated (new, this plan) | 28 | 28 | 0 | 0 |
| Existing leasing integration tests | 17 | 17 | 0 | 0 |
| Full suite (all backend tests) | 354 | 353 | 1* | 0 |

*The 1 failure (`test_complaint_flow_happy_path`) is a **pre-existing bug** in `decision_engine.py` unrelated to the lease agent — `validate_complaint()` returns 3 values but the caller unpacks into 2. This existed before this test run.

---

## Part 1 — Automated Tests (pytest)

All 28 tests in `backend/tests/test_leasing.py` passed.

### 1.1 — `GET /leasing/find-listing`

| Test | Status | Notes |
|---|---|---|
| `find_listing_by_unit_number` | **PASS** | Returns found=True, correct UUID, bedrooms=1, rent=20000 |
| `find_listing_scoped_to_group` | **PASS** | property_group_id query param accepted and used |
| `find_listing_not_found` | **PASS** | Returns `{"found": false}` for unknown query |
| `find_listing_by_title_fallback` | **PASS** | Two-shot mock confirms flat_number first, title second |

---

### 1.2 — `GET /leasing/search`

| Test | Status | Notes |
|---|---|---|
| `search_exact_bedroom_budget_match` | **PASS** | count≥1, all listings have bedrooms=2, rent≤40000 |
| `search_no_results` | **PASS** | count=0 when no listings match |
| `search_budget_only` | **PASS** | count=1 for single listing within budget |
| `search_bedroom_only` | **PASS** | count=3 for three 2BHK listings |
| `search_returns_listing_uuid_per_result` | **PASS** | ⚠️ See note below |
| `search_returns_200_with_no_params` | **PASS** | Endpoint handles missing params gracefully |

> **Note on `search_returns_listing_uuid_per_result`:** The test plan (Part 4) marked this as expected to fail *until Phase 1 of LEAD_ASSIGNMENT_PLAN.md*. It **already passes** — the current `leasing.py` (line 122) already includes `"listing_uuid": listing["uuid"]` in each search result. Phase 1 of the plan appears to be **already implemented**.

---

### 1.3 — `POST /voice/lease-lead-webhook`

| Test | Status | Notes |
|---|---|---|
| `webhook_resolves_via_listing_uuid` (Path 1) | **PASS** | lead inserted with correct listing_uuid, property_group_id, manager_id |
| `webhook_resolves_via_assistant_id` (Path 2) | **PASS** | property_group_id resolved from vapi_lease_assistant_id |
| `webhook_resolves_via_phone_number_id` (Path 3) | **PASS** | property_group_id resolved from vapi_phone_number_id |
| `webhook_no_submit_lead_tool_call` | **PASS** | Returns `{"status": "ignored"}`, no lead inserted |
| `webhook_invalid_listing_uuid_ignored` | **PASS** | listing_uuid="not-a-real-uuid" rejected by UUID_RE, lead saved with listing_uuid=null |
| `webhook_lead_fields_written_correctly` | **PASS** | All 7 fields (bedrooms, budget_max, move_in_timeline, occupants, floor_preference, qualification_status, notes, source) written correctly |

---

### 1.4 — `GET /leasing/leads`

| Test | Status | Notes |
|---|---|---|
| `get_leads_scoped_to_manager` | **PASS** | Returns only leads matching manager_id |
| `get_leads_filter_by_listing_uuid` | **PASS** | listing_uuid query param accepted (uses `or_` for interested_listing_ids too) |
| `get_leads_filter_by_status` | **PASS** | qualification_status filter applied |
| `get_leads_empty` | **PASS** | Returns [] when no leads exist |

---

### 1.5 — `PATCH /leasing/leads/{uuid}`

| Test | Status | Notes |
|---|---|---|
| `manager_can_set_contacted` | **PASS** | HTTP 200 |
| `manager_can_set_toured` | **PASS** | HTTP 200 |
| `manager_cannot_set_qualified` | **PASS** | HTTP 400 — "qualified" blocked (voice-agent-only status) |
| `manager_cannot_set_not_qualified` | **PASS** | HTTP 400 — "not_qualified" blocked |
| `manager_can_update_notes` | **PASS** | manager_notes written correctly |
| `patch_lead_not_found_returns_404` | **PASS** | HTTP 404 when no lead row returned |

---

### 1.6 — `GET /leasing/metrics`

| Test | Status | Notes |
|---|---|---|
| `metrics_counts_correct` | **PASS** | 3 qualified + 2 not_qualified + 1 unmatched → total=6, qualified=3, not_qualified=2, unmatched=1, rate=50.0% |
| `metrics_zero_leads` | **PASS** | All zeros when no leads exist |

---

## Part 2 — Manual Call Test Scenarios

These require a live VAPI inbound call or the VAPI test-call feature. **Not executed in this automated run.**

| Scenario | Description | Executable? |
|---|---|---|
| A — Perfect Single Match | 2BHK ≤40k → B202 qualified | Requires live VAPI call |
| B — Multiple Listings | 2BHK ≤60k → 3 results, caller picks E501 | Requires live VAPI call |
| C — Over Budget | 2BHK ≤30k → 0 results → unmatched | Requires live VAPI call |
| D — Custom Rule Failure (pets) | D404 no-pets rule applied | Requires live VAPI call |
| E — Income Rule Failure | E501 income 3× rule applied | Requires live VAPI call |
| F — Wrong Bedroom Count | 4BHK → unmatched | Requires live VAPI call |
| G — Find by Address/Unit | "C block, third floor" → C301 | Requires live VAPI call |
| H — Caller Hangs Up | No lead inserted | Requires live VAPI call |
| I — Boundary Budget | 2BHK exactly ₹38,000 → B202 included (`lte` inclusive) | Requires live VAPI call |
| J — Caller Reopens | 1BHK after rejection → new lead row | Requires live VAPI call |

**Prerequisite not verified:** The 5 test listings (A101, B202, C301, D404, E501) have not been confirmed in the `leadpipecrm@gmail.com` / "Sunrise Heights" property group. Seed them before running any manual test per the setup table in the test plan.

---

## Part 3 — Post-Test SQL Checklist

Not applicable for this automated run. Run this query after each manual scenario:

```sql
SELECT
  caller_name, phone, bedrooms, budget_max, qualification_status,
  listing_uuid, interested_listing_ids, manager_id, property_group_id,
  created_at
FROM lease_leads
ORDER BY created_at DESC
LIMIT 5;
```

---

## Part 4 — Tests Expected to Fail Until Plan Phases Complete

| Test | Expected Until | Actual Status |
|---|---|---|
| `search_returns_listing_uuid_per_result` | Phase 1 | **ALREADY PASSES** — implemented in current code |
| Scenario B: `interested_listing_ids` has all 3 UUIDs | Phase 2+3 | Not tested (manual) |
| Scenario A: `listing_uuid` auto-set from agent search result | Phase 1+2 | Not tested (manual) |
| Lead detail modal shows matched unit name | Phase 4 | Not tested (UI) |
| `GET /leasing/leads?listing_uuid=X` also matches `interested_listing_ids` | Phase 5 | Endpoint has `or_` filter implemented; DB-level test not validated |

---

## Pre-Existing Failures (unrelated to lease agent)

| Test | File | Error |
|---|---|---|
| `test_complaint_flow_happy_path` | `backend/tests/test_complaint_flow.py` | `ValueError: too many values to unpack (expected 2)` in `decision_engine.py:20` — `validate_complaint()` return signature changed but caller not updated |

---

## Files Produced

- **`backend/tests/test_leasing.py`** — 28 automated tests covering all Part 1 sections of the test plan
- **`LEAD_AGENT_TEST_REPORT.md`** — this report

---

## Run Command

```bash
pytest backend/tests/test_leasing.py -v
# 28 passed in 5.29s
```
