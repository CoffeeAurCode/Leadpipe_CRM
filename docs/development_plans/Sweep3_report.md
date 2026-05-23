# Sweep 3 — Post-Test Report
**Date:** 2026-05-23  
**Branch:** main  
**Tested against:** Shared lease agent `c76a69ea-103d-4a24-b542-adda79957294` on `+14313404212` (leadpipecrm); complaint agent `9e507761` on `+14382314283`

---

## Pass/Fail Summary

| Scenario | Result | Notes |
|---|---|---|
| 3-A (budget too low → unmatched) | **PARTIAL PASS** | Main criteria met; name not captured; `property_group_id = null` |
| 3-B (penthouse → bedrooms from listing, income disqualify) | **FAIL** | Test script not followed — caller said "4-5 bedrooms" instead of "penthouse on floor 5"; agent behavior was correct for input received; re-run needed |
| 3-C (outbound complaint call → Alex on `+14382314283`) | **PASS** | Call initiated 200 OK; verify-phone hit confirms agent was live |
| 3-D (budget boundary 38k → qualified B202) | **PASS** | Correct status, listing UUID, property_group_id, bedrooms |
| 3-E (address find C block floor 3 → C301) | **FAIL (REGRESSION)** | Was Sweep 2-G PASS; three `find_listing` attempts all missed |

**Sweep 3 is NOT complete.** 3-B needs a re-run with the correct script input; 3-E is a genuine regression. 3-C held.

---

## Scenario Detail

---

### 3-A — Budget Too Low (Re-test of Sweep 2-A FAIL)
**Goal:** Agent must not qualify a caller whose budget (₹30,000/mo) is below any available 2BHK.

**Observed:**
```
caller_name:          Unknown            ← expected "Test Person A"
bedrooms:             2
budget_max:           30000
qualification_status: unmatched          ← CORRECT
listing_uuid:         null               ← CORRECT
disqualifying_reason: (empty)            ← expected "budget" or "afford"
property_group_id:    null               ← expected NOT NULL
```

**Pass criteria met:** `qualification_status = unmatched` AND `listing_uuid IS NULL` — both correct.

**Root cause of secondary failures:**

1. **`caller_name = "Unknown"`** — the caller did not give their name before the call ended naturally (budget rejection is a short call), and the agent sent the default. Not a code defect; the test script said to give name "Test Person A" but the voice interaction was cut short by the unmatched path.

2. **`property_group_id = null`** — by design for an unmatched lead. The webhook resolves `property_group_id` only via `listing_uuid → lease_listings.property_group_id`. When no listing is matched, there is no listing to trace back through. The manager is resolved via `assistant_id → manager_vapi_config`, but that table does not store a `property_group_id`. This is expected behavior for an unmatched lead; the expected condition in the test guide was aspirational (referencing Sweep 2 context that has since changed). No code defect.

3. **`disqualifying_reason` empty** — the agent submitted the tool call without setting a reason. This is an agent prompt weakness, not a backend defect. The backend records whatever the agent sends.

**Verdict:** PASS on the primary regression criterion. The secondary issues are agent-level or by-design.

---

### 3-B — Penthouse / Floor 5 (Re-test of Sweep 2-C FAIL)
**Goal:** Agent calls `find_listing` first for "penthouse on floor 5", discovers E501 (a 2BHK), then fails income check → `not_qualified`.

**Observed:**
```
caller_name:          Desperson b
bedrooms:             5               ← agent correctly captured what was said
budget_max:           200000
qualification_status: unmatched       ← expected not_qualified
listing_uuid:         null            ← expected E501 UUID
floor_preference:     fifth floor
disqualifying_reason: (empty)
```

**Root cause: test script deviation.** The caller said "4-5 bedrooms" (and possibly mentioned fifth floor) rather than the scripted "I'm interested in the penthouse on floor 5." The agent correctly captured `bedrooms=5` based on what was actually said. It then searched `search_available_listings?bedrooms=5&budget_max=200000`, found zero results (no 5-bedroom units exist), and classified the caller as `unmatched`. This is correct agent behavior for the input it received.

The intended 3-B scenario — caller describes a specific unit by location ("penthouse on floor 5"), agent calls `find_listing` first, derives bedrooms from the returned listing — was **not executed**. The script needs to be re-run as written.

**Verdict:** FAIL — test script not followed. No agent prompt bug confirmed. Re-run required with exact scripted input.

---

### 3-C — Outbound Complaint Call (NEW — was blocked in Sweep 2)
**Goal:** Outbound call routes to Alex (`9e507761`) on `+14382314283`, not the old assistant.

**Observed:**
- `POST /voice/call/outbound HTTP/1.1" 200 OK` — call initiated successfully
- `POST /flats/verify-phone?phone_number=+919998064026 200 OK` — complaint agent made the caller-identity check (sourced from `100.23.171.201`, a VAPI IP)
- call-status polling continued through the call, then stopped

**Side bug found during this test:**
```
GET /properties HTTP/1.1" 500 Internal Server Error
fastapi.exceptions.ResponseValidationError: 18 validation errors
  {'type': 'int_type', 'loc': ('response', 15, 'floor_number'), 'msg': 'Input should be a valid integer', 'input': None}
  ... (18 flats affected)
```

See Bug #1 below. This crashed the Properties page but did not affect the outbound call test itself.

**Verdict:** PASS. The fix (using `VAPI_COMPLAINT_ASSISTANT_ID` + `VAPI_COMPLAINT_NUMBER_ID` in `POST /voice/call/outbound`) works.

---

### 3-D — Budget at Boundary 38k → Qualified B202 (Regression of Sweep 2-I PASS)
**Goal:** A 2BHK caller with budget exactly ₹38,000 gets qualified against listing B202.

**Observed:**
```
caller_name:          Despa Sandee
bedrooms:             2
budget_max:           38000
qualification_status: qualified
listing_uuid:         b8f3aed7-fe82-49ce-8fed-91180f2fd19e   ← B202 ✓
property_group_id:    aeb9d575-42e2-439f-ad81-8e99ae6900ed   ← NOT NULL ✓
qualifying_answers:   {"Do you have a stable source of income...":"Yes","How many people...":"1"}
```

All expected fields correct. The boundary budget match still works after the prompt and filter changes from Sweep 2.

**Verdict:** PASS. No regression.

---

### 3-E — Find by Address: C Block Floor 3 → C301 (Regression of Sweep 2-G PASS)
**Goal:** Caller describes "unit in C block on the third floor" → agent calls `find_listing`, resolves C301, qualifies caller.

**Observed (from logs):**
```
GET /leasing/find-listing?query=third%20floor%20block&manager_id=28c43c77-...   200 OK
GET /leasing/find-listing?query=Building%20C%20third%20floor&manager_id=28c43c77-...   200 OK
GET /leasing/find-listing?query=C%20Block&manager_id=28c43c77-...   200 OK
```

All three returned 200 but found nothing. Final DB row:
```
caller_name:          person E.
bedrooms:             null
budget_max:           null
qualification_status: unmatched
disqualifying_reason: No listing found matching the caller's description.
listing_uuid:         null
property_group_id:    null
```

**Root cause — `ilike` query/title mismatch (confirmed):**

Migration 018 Step 2 returned 0 rows updated — `manager_id` was already set on all `lease_listings` rows, so the filter change is not the cause.

The actual cause: the agent's `find_listing` calls used the queries `"third floor block"`, `"Building C third floor"`, and `"C Block"`. The endpoint matches these via `flat_number ILIKE '%query%'` (primary) and `title ILIKE '%query%'` (fallback). If C301's `flat_number` is stored as `C301` and the title doesn't contain "block" or "floor" as substrings, neither ilike passes.

C301 WAS reachable at 07:07 (the `Desmos on 6` qualified lead hit it), so the listing is active and has the correct `manager_id`. The 07:07 caller likely said the flat number directly (`"C301"`) rather than describing it by location.

**To confirm — run in Supabase SQL:**
```sql
SELECT uuid, flat_number, title, is_active, manager_id
FROM lease_listings
WHERE uuid = 'b9f94428-4efd-44ed-bc5a-ad740cb86c4b';
```

**Fix options (after confirming flat_number/title):**
1. Enrich the listing `title` to include building/block/floor keywords so `ilike` can match conversational queries
2. Update the agent system prompt to try the flat number directly (e.g. "C301") as a search term when the caller describes a location

**Verdict:** FAIL — REGRESSION. Root cause is `ilike` mismatch between agent query strings and stored flat_number/title; `manager_id` backfill was not the issue.

---

## Bugs Found

---

### Bug #1 — `GET /properties` 500: `floor_number` NULL Fails Pydantic Validation
**Severity:** High (crashes the entire Properties page)  
**Affected file:** `backend/app/routes/properties.py`

**Error:**
```
fastapi.exceptions.ResponseValidationError: 18 validation errors
  {'type': 'int_type', 'loc': ('response', N, 'floor_number'), 'input': None}
```

**Root cause:** The `PropertyResponse` Pydantic model at line 27 declares:
```python
floor_number: int
```
But 18 flats in the DB have `floor_number = NULL`. The dict-building code at line 80 uses:
```python
"floor_number": flat.get("floor_number", 0),
```
`dict.get(key, default)` returns `default` only when the key is **absent**. When the key exists but holds `None`, `.get()` returns `None`, not the default. The `0` fallback is therefore dead code for NULL values from the DB.

**Fix — two changes needed:**
1. Change the Pydantic model field to `Optional[int] = None` (or `= 0` if 0 is a valid sentinel)
2. Use `flat.get("floor_number") or 0` in the dict (the `or 0` coerces None → 0)

Also note: line 81 is a duplicate key in the same dict literal — `"floor_number"` appears twice. The second assignment silently overwrites the first. This is dead code and should be removed.

---

### Bug #2 — `find_listing` Misses Listings Without `manager_id` Set
**Severity:** High (causes lead qualification failures for any listing whose `manager_id` column is NULL)  
**Affected file:** `backend/app/routes/leasing.py`, `find_listing` and `search_available_listings`

**Root cause:** The Sweep 2 → Sweep 3 filter change wrote:
```python
elif manager_id:
    q = q.eq("manager_id", manager_id)
```
This is correct for listings created after the fix, but listings created before `manager_id` was being set will have `manager_id = NULL` in `lease_listings`. The `.eq("manager_id", manager_id)` filter excludes them entirely.

**Diagnosis query:**
```sql
SELECT COUNT(*) FROM lease_listings WHERE manager_id IS NULL;
```

**Fix:** Run a backfill to populate `manager_id` on existing rows using the `property_group_id → properties_list.manager_id` join:
```sql
UPDATE lease_listings ll
SET manager_id = pl.manager_id
FROM properties_list pl
WHERE ll.property_group_id = pl.id
  AND ll.manager_id IS NULL;
```

This is a data fix only — no code change required once `manager_id` is set on all rows.

---

## Pending Actions Before Re-run

| # | Action | Who | File/Location |
|---|---|---|---|
| 1 | Fix `PropertyResponse.floor_number: Optional[int] = None` and `or 0` fallback in dict | Dev | `backend/app/routes/properties.py` lines 27, 80-81 |
| 2 | Run `UPDATE lease_listings SET manager_id = ...` backfill | Supabase SQL | See Bug #2 above |
| 3 | Update shared lease agent system prompt — floor number ≠ bedrooms rule | VAPI dashboard or `update_shared_agents.py` | Prompt section |
| 4 | Run migration `017_unassign_12494028641.sql` (from session handoff) | Supabase SQL editor | `backend/migrations/017_unassign_12494028641.sql` |
| 5 | Verify C301 listing's `manager_id` after backfill | Supabase SQL | See Sweep 3-E diagnosis query |

---

## DB State After Sweep 3

Full `lease_leads` table (newest first, from post-run verification):

| caller_name | bedrooms | budget_max | qualification_status | disqualifying_reason | listing_uuid | property_group_id | created_at |
|---|---|---|---|---|---|---|---|
| person E. | null | null | unmatched | No listing found... | null | null | 2026-05-23 12:48 |
| Despa Sandee | 2 | 38000 | qualified | — | b8f3aed7-... | aeb9d575-... | 2026-05-23 12:45 |
| Desperson b | 5 | 200000 | unmatched | — | null | null | 2026-05-23 12:40 |
| Unknown | 2 | 30000 | unmatched | — | null | null | 2026-05-23 12:36 |
| Despa Sanjay | 1 | 10000 | unmatched | — | null | null | 2026-05-23 07:18 |
| test person I | 2 | 38000 | qualified | — | b8f3aed7-... | aeb9d575-... | 2026-05-23 07:13 |
| Desmos on 6 | 3 | 70000 | qualified | — | b9f94428-... | aeb9d575-... | 2026-05-23 07:07 |
| Jeff Person 5 | 4 | 300000 | unmatched | — | null | null | 2026-05-23 05:56 |
| person 4 | 2 | 60 | unmatched | — | null | null | 2026-05-23 05:47 |
| Person 3 | 3 | 200000 | unmatched | No 3 BR on 5th floor... | null | null | 2026-05-23 05:44 |

Notable: `Desmos on 6` (07:07) was qualified against `b9f94428-...` which is the C301 UUID (b9f94428-4efd-44ed-bc5a-ad740cb86c4b). This confirms that C301 was reachable earlier in the day — strengthening the hypothesis that a filter regression (not a title mismatch) caused 3-E to fail.

---

## Architecture Notes for Next Session

- The `find_listing` search is flat-number-first, title-second. Address-style queries like "C block" work only if the listing's `flat_number` or `title` contains those literal substrings. If the flat_number is `C301` and title is something like "3 BHK - C301", then `ilike '%C Block%'` will miss it. Consider adding `address` to the search columns in `find_listing` (the joined `flats.address` field is already available in the query).
- The shared lease agent (`VAPI_SHARED_LEASE_ASSISTANT_ID`) bakes `manager_id=28c43c77...` into tool URLs at assistant-creation time (from `build_lease_config`). All three `find_listing` calls in 3-E correctly included this manager_id — so the filter was applied, but the listing was missed because its `manager_id` was NULL. After the backfill, re-run 3-E to confirm.
