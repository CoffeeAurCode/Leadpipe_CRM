# Test Plan: Lease Agent v2

Covers all changes from `PLAN_lease_agent_v2.md`: threshold-aware listing load,
`search-listings` filtered endpoint, `search_listings` VAPI tool, async `load_listings`,
updated system prompt. Also verifies no existing feature broke.

---

## Baseline (Before Implementation)

Run the full suite before touching any code to establish the baseline:

```powershell
cd backend
pytest tests/ -q --tb=no 2>&1 | tail -5
```

Expected baseline: **388 passed, 27 failed**
- 21 of the 27 failures are the new RED→GREEN tests in this plan
- 6 are pre-existing failures unrelated to this feature:
  - `tests/test_complaint_flow.py::test_complaint_flow_happy_path`
  - `tests/test_leasing.py::TestFindListing` (3 tests)
  - `tests/test_leasing.py::TestLeaseLoanWebhook::test_webhook_resolves_via_assistant_id`
  - `tests/unit/test_features.py::TestGetDefaultState::test_voice_calls_default_is_false`

**Target after implementation:** 27 → 6 failed (only pre-existing remain).

---

## Quick Reference — How to Run

```powershell
# 1. Unit + integration tests (no network required)
cd backend
pytest tests/unit/test_vapi_lease_config.py -v
pytest tests/integration/test_listings_for_agent_v2.py -v
pytest tests/ -v   # full suite including regression

# 2. Live endpoint smoke tests (requires deployed backend)
.\backend\scripts\smoke_test_leasing.ps1

# 3. Deploy config to VAPI then verify structure
python backend/scripts/update_lease_agents.py --dry-run
python backend/scripts/check_lease_agent_config.py

# 4. Manual voice call tests (see Section 5 below)
```

---

## Status Legend

| Symbol | Meaning |
|---|---|
| AUTO | Fully automated (pytest or smoke script) |
| MANUAL | Requires a live phone call |
| RED→GREEN | Test is written TDD-style — fails until the implementation lands |
| GREEN | Passes against current codebase |

---

## 1. VAPI Config Structure — Unit Tests

**File:** `backend/tests/unit/test_vapi_lease_config.py`  
**Run:** `pytest backend/tests/unit/test_vapi_lease_config.py -v`  
**Type:** AUTO | Status: RED→GREEN (tests written for post-implementation shape)

These tests import `build_lease_config()` and check the config dict in memory — no
HTTP, no DB, no VAPI API call. If these pass, the agent config is structurally correct.

| Test | Checks | Status |
|---|---|---|
| `test_server_messages_is_end_of_call_only` | lease agent never gets `tool-calls` — adding it breaks all tools | RED→GREEN |
| `test_load_listings_present` | `load_listings` tool exists | RED→GREEN |
| `test_load_listings_is_async` | `async: True` so tool fires while agent talks | RED→GREEN |
| `test_load_listings_url_contains_manager_id` | URL is scoped to this manager | RED→GREEN |
| `test_load_listings_variable_extraction_has_has_more` | agent can read `has_more` flag | RED→GREEN |
| `test_search_listings_present` | `search_listings` tool exists | RED→GREEN |
| `test_search_listings_is_async` | fires while agent continues talking | RED→GREEN |
| `test_search_listings_url_contains_search_listings_path` | points to new endpoint | RED→GREEN |
| `test_search_listings_has_bedrooms_param` | bedrooms template variable wired | RED→GREEN |
| `test_search_listings_has_budget_max_param` | budget_max template variable wired | RED→GREEN |
| `test_find_listing_not_in_lease_config` | old tool removed — must not reappear | RED→GREEN |
| `test_search_available_listings_not_in_lease_config` | old tool also gone | RED→GREEN |
| `test_submit_lease_lead_present` | lead capture tool still there | RED→GREEN |
| `test_submit_lease_lead_url_contains_lease_lead_direct` | points to correct endpoint | RED→GREEN |
| `test_complaint_server_messages_includes_tool_calls` | complaint config not touched | GREEN |
| `test_verify_phone_number_present` | complaint agent unchanged | GREEN |
| `test_submit_complaint_present` | complaint agent unchanged | GREEN |
| `test_complaint_config_has_no_load_listings` | no cross-contamination | GREEN |

---

## 2. New Backend Endpoints — Integration Tests

**File:** `backend/tests/integration/test_listings_for_agent_v2.py`  
**Run:** `pytest backend/tests/integration/test_listings_for_agent_v2.py -v`  
**Type:** AUTO | Status: mix of RED→GREEN (new) and GREEN (regression)

### 2a. `GET /leasing/listings-for-agent` — Threshold Logic

| Test | What It Checks | Status |
|---|---|---|
| `test_small_portfolio_returns_has_more_false` | count≤10 → `has_more=false` | RED→GREEN |
| `test_small_portfolio_returns_full_listings_array` | count≤10 → listings populated | RED→GREEN |
| `test_large_portfolio_returns_has_more_true` | count=15 → `has_more=true`, `listings=[]` | RED→GREEN |
| `test_large_portfolio_count_is_accurate` | count=24 returned accurately | RED→GREEN |
| `test_zero_listings_returns_has_more_false` | no listings → count=0, has_more=false | RED→GREEN |
| `test_response_always_200_on_db_error` | never 500 even on DB crash | GREEN |
| `test_listing_row_has_expected_fields` | listing shape has all VAPI-needed fields | RED→GREEN |
| `test_monthly_rent_is_float` | rent not returned as string | GREEN |

### 2b. `GET /leasing/search-listings` — New Filtered Endpoint

| Test | What It Checks | Status |
|---|---|---|
| `test_returns_200` | endpoint exists and returns 200 | RED→GREEN |
| `test_response_has_count_and_listings` | correct response shape | RED→GREEN |
| `test_empty_result_returns_count_zero` | empty is handled cleanly | RED→GREEN |
| `test_db_error_returns_200` | never 500 on DB crash | RED→GREEN |
| `test_budget_max_param_accepted` | filter param wired | RED→GREEN |
| `test_both_filters_accepted` | combined filters work | RED→GREEN |
| `test_no_filters_returns_results` | works without any filter | RED→GREEN |
| `test_listing_fields_present_in_result` | result shape has VAPI-needed fields | RED→GREEN |

### 2c. `POST /voice/lease-lead-direct` — Bug Fix + Regression

| Test | What It Checks | Status |
|---|---|---|
| `test_basic_lead_saves_and_returns_200` | happy path still works | GREEN |
| `test_empty_listing_uuid_coerced_to_null` | **bug fix**: `""` stored as `None` not empty string | RED→GREEN |
| `test_invalid_uuid_string_coerced_to_null` | non-UUID rejected silently | GREEN |
| `test_duplicate_call_id_returns_duplicate_status` | dedup guard works | GREEN |
| `test_db_error_returns_200` | always HTTP 200 | GREEN |
| `test_source_is_always_voice` | source field hardcoded to "voice" | GREEN |
| `test_qualifying_answers_json_string_parsed` | JSON string decoded to dict | GREEN |
| `test_interested_listing_ids_filters_invalid_uuids` | bad UUIDs stripped from array | GREEN |

### 2d. Existing Endpoint Regression

| Test | What It Checks | Status |
|---|---|---|
| `test_get_leads_still_works` | `/leasing/leads` unbroken | GREEN |
| `test_get_metrics_still_works` | `/leasing/metrics` unbroken | GREEN |
| `test_export_csv_still_works` | `/leasing/export` unbroken | GREEN |
| `test_find_listing_still_returns_200` | `/leasing/find-listing` unbroken | GREEN |
| `test_search_available_listings_still_returns_200` | `/leasing/search` unbroken | GREEN |
| `test_listings_for_agent_still_returns_200` | base endpoint always 200 | GREEN |

---

## 3. Live Endpoint Smoke Tests

**File:** `backend/scripts/smoke_test_leasing.ps1`  
**Run:** `.\backend\scripts\smoke_test_leasing.ps1`  
**Type:** AUTO (needs network) | Status: RED→GREEN for new checks

Hits the deployed Render backend directly. No auth needed (VAPI endpoints are public).
Run after every deploy to catch regressions. The script exits non-zero on any failure.

```powershell
# Default manager (Pranav's test account)
.\backend\scripts\smoke_test_leasing.ps1

# Different manager or local dev backend
.\backend\scripts\smoke_test_leasing.ps1 -Manager "your-uuid" -BaseUrl "http://localhost:8000"
```

**Checks included:**

| Section | Checks |
|---|---|
| `/listings-for-agent` | HTTP 200, has `count` / `listings` / `has_more` fields, `has_more` is boolean, listing items have all required fields, `monthly_rent` is a number |
| `/search-listings` | HTTP 200 for bedrooms / budget / combined / no-filter, response shape, result ≤ 5 items, bedroom filter applied correctly |
| `/leasing/find-listing` | Still returns 200, has `found` field |
| `/voice/lease-lead-direct` | 200 for fresh call_id, 200 + `duplicate` for repeated call_id, 200 for empty `listing_uuid` |
| `/leasing/search` | Still returns 200 |
| `/flats/verify-phone` | Still returns 200 |

---

## 4. VAPI Agent Config Deploy Verification

After running `update_lease_agents.py`, verify the live agent in the VAPI dashboard:

```powershell
# Dry-run first — see what will be pushed
python backend/scripts/update_lease_agents.py --dry-run

# Deploy
python backend/scripts/update_lease_agents.py

# Inspect live config
python backend/scripts/check_lease_agent_config.py
```

**Manual VAPI Dashboard Checks:**

Go to https://dashboard.vapi.ai → Assistants → lease agent for your manager.

| Check | Expected |
|---|---|
| Tools list | `load_listings`, `search_listings`, `submit_lease_lead` — and **nothing else** |
| `load_listings` async flag | `true` |
| `search_listings` async flag | `true` |
| `find_listing` tool | **Must not appear** |
| Server Messages | `["end-of-call-report"]` only — **no** `tool-calls` |
| System prompt Step 2 | Says "Load All Available Units" — does NOT say "find_listing" |
| System prompt mentions `search_listings` | Tool name appears in `[Tools]` section |

---

## 5. Manual Voice Call Tests

These require a real phone call to the lease agent number. Run after deploying config.

### Setup
- Ensure there are active listings for the test manager (use `Test_listing_units.csv` data)
- Use the VAPI dashboard to see the call transcript live

### Test Calls

#### 5a — Path A (Small Portfolio, ≤10 Listings): Unit by bedroom count
```
Say:  "I'm looking for a 3 bedroom unit."
```
| Step | Expected |
|---|---|
| Agent fires `load_listings` | Happens in background — caller doesn't notice |
| Agent response | Names C301, gives bedroom count, floor, rent, availability |
| Agent does NOT say | "I couldn't find that unit" or "unmatched" |
| Agent continues | Asks name, then Q1–Q7 naturally |
| Lead in DB | `qualification_status` = qualified or not_qualified, `listing_uuid` = C301's UUID (not blank/null) |

#### 5b — Path A: Unit by flat number
```
Say:  "I'm asking about unit C301."
```
| Step | Expected |
|---|---|
| Agent response | Confirms C301 details |
| Proceeds to name + Q1–Q7 | ✓ |

#### 5c — Path A: Browse all
```
Say:  "What units do you have available?"
```
| Step | Expected |
|---|---|
| Agent response | Briefly lists all active listings — flat number, bedrooms, rent |
| Asks which one interests you | ✓ |

#### 5d — Path A: Budget preference
```
Say:  "I'm looking for something under forty thousand a month."
```
| Step | Expected |
|---|---|
| Agent response | Suggests A101 (₹20k) and B202 (₹38k), not C301 or D404 (₹42k) |

#### 5e — Path B (Large Portfolio, >10 Listings)
*Temporarily set `LISTING_THRESHOLD = 2` in backend, deploy, then test:*
```
Say:  "Hi, I'm looking for a flat."
```
| Step | Expected |
|---|---|
| Agent gets `has_more=true` | Seamlessly starts asking preferences |
| Agent asks | "What size unit are you looking for?" |
| Caller says "2 bedroom" | Agent asks about budget |
| Caller gives budget | `search_listings` fires async |
| Agent presents matches | Results from search, no awkward pause |

#### 5f — Interruption handling
```
Wait until Max is mid-sentence describing a unit, then say:
"Does it have in-unit laundry?"
```
| Step | Expected |
|---|---|
| Max stops mid-sentence | ✓ |
| Max answers laundry question | ✓ |
| Max resumes from where it paused | ✓ (does not restart from the beginning) |

#### 5g — Disqualification: Pets
```
Ask about a unit with pets_allowed=false. Say you have a dog.
```
| Step | Expected |
|---|---|
| Agent response | "Unfortunately this unit doesn't allow pets." |
| Proceeds to lead capture | qualification_status = "not_qualified", reason = "pets not allowed" |
| Lead in DB | Saved with correct disqualifying_reason |

#### 5h — Full qualified call
```
Complete the entire flow: unit inquiry → name → Q1 through Q7 (all pass)
```
| Step | Expected |
|---|---|
| All 7 questions asked | Not necessarily in order — woven into conversation |
| Lead saved | qualification_status = "qualified" |
| All fields populated | caller_name, move_in_timeline, occupants, qualifying_answers, listing_uuid |
| Closing line | "Our team will reach out to you shortly to arrange a viewing." |

---

## 6. What Is NOT Tested Here

| Item | Why Not Tested |
|---|---|
| VAPI async timing (tool result arrives before agent needs it) | Can't mock real network latency in pytest |
| Language switching (EN/FR) | Requires voice call in French |
| LLM budget match accuracy ("under 40k") | LLM reasoning — depends on model, not our code |
| Notification delivery to frontend | Covered by existing notification tests |
| Supabase RLS on lease_listings INSERT | Covered by existing `test_leasing.py` |

---

## 7. Sequence: What to Test and When

```
1. Implement changes (leasing.py + vapi_agent_config.py)
2. Run:  pytest backend/tests/unit/test_vapi_lease_config.py -v
         → Verify config structure before touching VAPI

3. Run:  pytest backend/tests/integration/test_listings_for_agent_v2.py -v
         → All tests should be green locally

4. Deploy backend to Render (git push)

5. Run:  .\backend\scripts\smoke_test_leasing.ps1
         → Verify live endpoints respond correctly

6. Run:  python backend/scripts/update_lease_agents.py
         → Push config to VAPI

7. Check VAPI dashboard manually (Section 4 checklist)

8. Run manual voice calls (Section 5)
         → Start with 5a (3 bedroom) — this was the original bug
         → Then 5b, 5c, 5f (interruption), 5g (pets disqualify)
         → If all pass, run 5h (full qualified call)
```
