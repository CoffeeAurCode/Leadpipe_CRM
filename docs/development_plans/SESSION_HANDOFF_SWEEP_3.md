# Session Handoff — Sweep 3 Test Results

**Prepared:** 2026-05-23  
**Purpose:** Full context for the next session where Sweep 3 test results will be provided and analysed.

---

## What Was Done in This Session

### 1. Fixed: Complaint outbound call using wrong assistant

**File:** `backend/app/routes/voice.py` — `make_outbound_call`, ~line 692 and ~line 712.

**Before (bug):**
```python
if not settings.VAPI_NUMBER_ID:          # wrong guard
    raise ...
...
else:  # complaint path
    assistant_id    = settings.VAPI_ASSISTANT_ID      # legacy — wrong
    phone_number_id = settings.VAPI_NUMBER_ID          # legacy — wrong
```

**After (fix):**
```python
if req.agent == "complaint" and not settings.VAPI_COMPLAINT_NUMBER_ID:
    raise ...
...
else:  # complaint path
    assistant_id    = settings.VAPI_COMPLAINT_ASSISTANT_ID
    phone_number_id = settings.VAPI_COMPLAINT_NUMBER_ID or settings.VAPI_NUMBER_ID
```

**Correct env vars (already in Render):**
- `VAPI_COMPLAINT_ASSISTANT_ID = 9e507761-7bf7-451a-9413-8ae62ec0176f`
- `VAPI_COMPLAINT_NUMBER_ID    = e8367bd3-12c6-4423-aa93-27ee8b264f48`

---

### 2. Fixed: Lease agent prompt — budget enforcement (Issue 1 from Sweep 2-A)

**File:** `backend/app/services/vapi_agent_config.py` — `_LEASE_SYSTEM_PROMPT_BASE`, `[Critical Rules]` section.

**Added rule:**
> BUDGET ENFORCEMENT: If the caller's stated budget_max is below the monthly_rent of every unit returned by search_available_listings, you MUST submit qualification_status="unmatched". Do NOT substitute a cheaper unit of a different bedroom count. A caller asking for 2BHK at ₹30,000 cannot be qualified for a 1BHK at ₹20,000. Only submit "qualified" when a unit matches BOTH the requested bedroom count AND fits within budget_max.

**Root cause of 2-A failure:** Agent found no 2BHK under ₹30k, then offered A101 (1BHK at ₹20k), caller may have accepted, agent submitted `qualified` against A101 even though original request was 2BHK.

---

### 3. Fixed: Lease agent prompt — bedroom hallucination (Issue 2 from Sweep 2-C)

**File:** `backend/app/services/vapi_agent_config.py` — two places in `_LEASE_SYSTEM_PROMPT_BASE`.

**Step 3 (Find a Listing) — updated:**
> If the caller mentions a specific address, floor, or unit name (e.g. "penthouse", "top floor", "unit on floor 5"): call find_listing with their query FIRST. Use the bedrooms value from the tool response — NEVER infer bedroom count from words like "penthouse", "suite", or a floor number.

**Critical Rules — added:**
> BEDROOM COUNT: Never infer bedroom count from descriptive terms like "penthouse", "suite", "top floor", or floor number alone. Always call find_listing first when the caller names a specific unit, floor, or area — use the bedrooms field from the tool response.

**Root cause of 2-C failure:** Agent inferred `bedrooms=3` from "penthouse", searched for 3BHK on floor 5, got 0 results, submitted `unmatched`. Never found E501 (2BHK, ₹55k, floor 5) and never applied its income rule.

---

### 4. Confirmed resolved: property_group_id=None for unmatched leads (Issue 3 from Sweep 2)

User confirmed Issue 3 was already resolved before this session. The four-path resolution in `voice.py:lease_lead_webhook` now includes path 4: shared agent fallback picks the first active property group. Unmatched leads should now have a non-null `property_group_id`.

---

### 5. Prompt published to VAPI

`python backend/scripts/update_shared_agents.py` was run successfully this session. Output:
```
[Complaint agent (+14382314283)]   OK  id=9e507761-7bf7-451a-9413-8ae62ec0176f
[Shared lease agent (+14313415768)] OK  id=2dba3a50-6862-400c-861a-bfc0a45d4a95
Done. Both assistants updated.
```

---

## Sweep 2 Results Summary (History)

| Scenario | Result | Root Cause |
|----------|--------|------------|
| 2-A (budget too low → unmatched) | **FAIL** | Agent qualified caller for wrong unit type (1BHK vs 2BHK) |
| 2-B (pet rule → B202) | PASS | — |
| 2-C (E501 income rule → not_qualified) | **FAIL** | Agent hallucinated bedrooms=3 from "penthouse"; never found E501 |
| 2-E (dedup suppression) | PASS | — |
| 2-F (no 4BHK → unmatched) | PASS (partial) | Correct status; property_group_id=None (now fixed) |
| 2-G (find by address / C block) | PASS | — |
| 2-H (caller hangs up) | PASS | No lead inserted |
| 2-I (budget at boundary ₹38k) | PASS | B202 matched; dedup held |
| 2-J (1BHK pivot → unmatched) | PASS (partial) | Correct status; property_group_id=None (now fixed) |

---

## Sweep 3 Test Scenarios

Full test guide: `docs/development_plans/MANUAL_TEST_GUIDE_SWEEP_3.md`

### 3-A — Budget too low (re-test of 2-A)
- **Call:** Shared lease agent `+1 (518) 318-9117`
- **Script:** "I'm looking for a 2-bedroom apartment. My budget is 30,000 a month." If agent offers 1BHK, decline ("No, I specifically need 2 bedrooms."). Give name.
- **Expected DB:**
  - `bedrooms = 2`
  - `budget_max = 30000`
  - `qualification_status = unmatched`
  - `listing_uuid = null`
  - `property_group_id IS NOT NULL`
- **Pass:** `unmatched` + `listing_uuid` is null
- **Fail:** `qualified` or any listing_uuid populated

### 3-B — Penthouse / floor 5 bedroom resolution (re-test of 2-C)
- **Call:** Shared lease agent `+1 (518) 318-9117`
- **Script:** "I'm interested in the penthouse on floor 5. My budget is fine — I can pay up to 2 lakh a month." Answer income question: "Yes, I have a stable income." (Agent should still disqualify via income rule.) Give name.
- **Expected DB:**
  - `bedrooms = 2` ← MUST NOT be 3
  - `budget_max = 200000`
  - `qualification_status = not_qualified` ← income rule applied
  - `listing_uuid = <E501 UUID>` ← agent must have called find_listing
  - `disqualifying_reason` mentions income
  - `property_group_id IS NOT NULL`
- **Pass:** `bedrooms=2` AND `not_qualified` AND `listing_uuid` is E501
- **Fail:** `bedrooms=3`, or `unmatched` (never found E501), or `listing_uuid=null`

### 3-C — Outbound complaint call (new — was blocked by bug)
- **Action:** App → Outbound Call button → agent = Complaint → enter phone → click Call
- **Expected:**
  - Call connects, Alex greets (not lease agent)
  - VAPI dashboard: `assistantId = 9e507761-7bf7-451a-9413-8ae62ec0176f`
  - Caller ID: `+14382314283`
- **Pass:** Alex answers, correct assistantId in VAPI
- **Fail:** 500 error, wrong agent answers, or call goes to legacy `2cbc056b`

### 3-D — Boundary budget (regression guard, was 2-I PASS)
- **Call:** `+1 (518) 318-9117`
- **Script:** "Looking for 2-bedroom, budget is 38,000 a month." No pets. Give name.
- **Expected:** `qualified`, `listing_uuid = <B202 UUID>`, `budget_max = 38000`

### 3-E — Find by address (regression guard, was 2-G PASS)
- **Call:** `+1 (518) 318-9117`
- **Script:** "Interested in the unit in C block on the third floor."
- **Expected:** `qualified`, `listing_uuid = <C301 UUID b9f94428-...>`

---

## Key DB Query to Run After Each Call

```sql
SELECT
  caller_name,
  bedrooms,
  budget_max,
  qualification_status,
  disqualifying_reason,
  listing_uuid,
  property_group_id,
  created_at
FROM lease_leads
ORDER BY created_at DESC
LIMIT 10;
```

---

## Known Listing UUIDs (Sunrise Heights test data)

| Unit | UUID (partial) | Bedrooms | Rent | Notes |
|------|----------------|----------|------|-------|
| B202 | — | 2 | ₹38,000 | No pets; boundary test unit |
| C301 | b9f94428-... | — | — | Address search test unit |
| E501 | — | 2 | ₹55,000 | Floor 5 "penthouse"; income rule active |
| A101 | — | 1 | ₹20,000 | Cheap 1BHK; agent must NOT qualify 2BHK seekers here |

---

## Files Changed This Session

| File | Change |
|------|--------|
| `backend/app/routes/voice.py` | Complaint outbound path now uses `VAPI_COMPLAINT_ASSISTANT_ID` + `VAPI_COMPLAINT_NUMBER_ID` |
| `backend/app/services/vapi_agent_config.py` | Added BUDGET ENFORCEMENT + BEDROOM COUNT rules to `_LEASE_SYSTEM_PROMPT_BASE` |
| `CODEBASE_CONTEXT.md` | Removed "known bug (unfixed)" notes; updated outbound call description |
| `docs/development_plans/MANUAL_TEST_GUIDE_SWEEP_3.md` | New — step-by-step Sweep 3 test guide |

---

## What to Do With Sweep 3 Results

**If 3-A passes:** Budget enforcement rule is working. No further prompt change needed.  
**If 3-A fails again:** The agent is still substituting units of a different type. Need to add a stricter condition — possibly make the budget check part of the search step, not just the submission step.

**If 3-B passes (bedrooms=2, not_qualified):** Bedroom hallucination is fixed and income rule fires. Done.  
**If 3-B shows bedrooms=3 still:** The `find_listing` instruction isn't being followed. May need to restructure the prompt so step 3 is more explicit (e.g., add "penthouse" as a trigger keyword example).  
**If 3-B shows bedrooms=2 but qualified:** Income rule is not being applied from `custom_rules`. Check `find_listing` response for E501 to confirm `custom_rules` contains `income_required: true`.

**If 3-C passes:** Complaint outbound bug is fully verified as fixed.  
**If 3-C fails with 500:** Check Render env for `VAPI_COMPLAINT_ASSISTANT_ID` and `VAPI_COMPLAINT_NUMBER_ID`. Confirm deploy is live.

**If 3-D or 3-E regress:** The prompt changes broke an existing behaviour. Diff the new `_LEASE_SYSTEM_PROMPT_BASE` against the previous version and narrow down which addition caused the regression.
