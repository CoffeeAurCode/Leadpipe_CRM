# Sweep 2 Test Report — Lease Agent Post-Fix Regression

**Date:** 2026-05-23  
**Tester:** Pranav Raj  
**Sweep:** Second sweep (Sweep 2-A through 2-J)  
**Agent:** Shared lease agent (`2dba3a50-6862-400c-861a-bfc0a45d4a95`) on `+1 (518) 318-9117`

---

## Summary

| Scenario | Pass/Fail | Key finding |
|----------|-----------|-------------|
| 2-A (budget too low → unmatched) | **FAIL** | Agent still submitted `qualified` with a listing_uuid despite caller being over-budget |
| 2-B (pet rule → route to B202) | **PASS** | Budget captured correctly; agent routed to B202 |
| 2-C (E501 income rule → not_qualified) | **FAIL** | Agent hallucinated `bedrooms=3`; submitted `unmatched` instead of `not_qualified`; `property_group_id=None` |
| 2-E (duplicate suppression) | **PASS (dedup worked)** | Backend rejected second webhook; only 1 row saved |
| 2-F (no 4BHK available → unmatched) | **PASS (partial)** | Correct status, but `property_group_id=None` |
| 2-G (find by address/C block) | **PASS** | `find_listing` resolved C301; listing_uuid set correctly |
| 2-H (caller hangs up) | **PASS** | No lead inserted; webhook returned `ignored` |
| 2-I (budget exactly at rent price) | **PASS** | B202 matched at boundary ₹38,000; dedup held on repeat |
| 2-J (1BHK pivot) | **PASS (partial)** | Correct unmatched result; `property_group_id=None` |

**3 full passes, 2 partial passes (correct status but pg resolution failed), 2 failures.**

---

## Issue 1 — Sweep 2-A: Agent still qualifies caller over budget

**Severity:** High  
**Test expectation:** Caller says "I can only pay 30,000 a month" for 2BHK. Expected `qualification_status=unmatched`, `listing_uuid=null`.  
**Actual result from DB:**
```
caller_name=test person 1, bedrooms=2, budget_max=30000,
qualification_status=qualified, listing_uuid=34e98d28-..., property_group_id=31ed35ee-...
```

**Root cause:** Fix 3 (no hallucinated listing_uuid) and Fix 5 (unmatched when count=0) from the prior session did not stop the agent from qualifying the caller. One of:
1. The updated system prompt was not republished to the live VAPI assistant — the old cached config is still running.
2. The prompt wording is not strict enough: the agent searched, found no 2BHK under 30k, then offered the 1BHK A101 (₹20,000), the caller may have accepted, and the agent submitted `qualified` against A101 even though the original request was for 2BHK.

**Fix:**
- Run `python backend/scripts/update_shared_agents.py` to confirm the latest config is live.
- In `vapi_agent_config.py` around the `[Qualification & Submission]` section, add a hard rule: "If the caller's stated budget is below the rent of every matching unit, you MUST submit `qualification_status=unmatched`. Do NOT submit `qualified` for a unit the caller cannot afford."
- After republishing, re-run Sweep 2-A to verify.

---

## Issue 2 — Sweep 2-C: Agent hallucinated bedrooms=3; income rule not applied

**Severity:** High  
**Test expectation:** Caller says "I want the penthouse on floor 5, budget is fine." Agent should find E501 (2BHK, ₹55,000, floor 5), apply income rule, submit `qualification_status=not_qualified`.  
**Actual result from DB:**
```
caller_name=Person 3, bedrooms=3, budget_max=200000,
qualification_status=unmatched, listing_uuid=null, property_group_id=None,
disqualifying_reason="No 3 bedroom units available on 5th floor within budget"
```

**Root cause:**
1. **Bedrooms hallucination:** The agent inferred `bedrooms=3` from "penthouse" and submitted 3 instead of looking up E501's actual bedroom count (2). Likely the agent searched with `bedrooms=3` (or user said something that was transcribed as 3-bedroom), got 0 results, and submitted unmatched.
2. **Income rule never reached:** Because the agent reported no match, it never read E501's `custom_rules` and never asked the income qualifying question.
3. **property_group_id=None:** Since `listing_uuid=null`, resolution path 1 fails. The shared agent's ID/phone_number_id are not in `properties_list.vapi_lease_assistant_id` or `vapi_phone_number_id`, so paths 2 and 3 also fail.

**Fix:**
- Add to the agent prompt: "Do not guess the bedroom count — if the caller asks about a specific floor or unit name, call `find_listing` first and use the bedrooms value from the listing's response."
- See Issue 3 for the `property_group_id=None` fix.

---

## Issue 3 — Unmatched leads resolve to property_group_id=None (Sweep 2-C, 2-E, 2-F, 2-J)

**Severity:** Medium  
**Affected scenarios:** Any call where `listing_uuid` is blank (all unmatched/no-match results).  
**Backend warning logged for every affected call:**
```
[WARN] Could not resolve property_group_id for assistant=2dba3a50-6862-400c-861a-bfc0a45d4a95 phone_number_id=969c6812-b520-468e-8f65-5fb8ca4ee240
```

**Root cause:** The three resolution paths in `voice.py:lease_lead_webhook` are:
1. Path 1 — via `listing_uuid` → works when agent finds a listing.
2. Path 2 — via `assistantId` matching `properties_list.vapi_lease_assistant_id`.
3. Path 3 — via `phoneNumberId` matching `properties_list.vapi_phone_number_id`.

The shared agent (`2dba3a50`) is **not stored in any row** of `properties_list.vapi_lease_assistant_id` — only per-group provisioned agents are stored there. So for all calls that don't produce a `listing_uuid`, the property group is unresolvable. This affects all unmatched/no-match leads, which is ~40% of real-world calls.

**Fix (two options):**

Option A — Add a 4th fallback path in `voice.py`:
```python
# Path 4: shared agent fallback — if assistant_id matches VAPI_SHARED_LEASE_ASSISTANT_ID,
# use the manager's primary property group as fallback
if not property_group_id and assistant_id == settings.VAPI_SHARED_LEASE_ASSISTANT_ID:
    # Could pick the first active property group for the known manager
    # This requires knowing which manager this shared agent belongs to
```
This approach requires knowing which manager uses the shared agent, which is ambiguous if multiple managers use it.

Option B — Store the shared agent ID in `properties_list` for the primary property group:
Run SQL:
```sql
UPDATE properties_list
SET vapi_lease_assistant_id = '2dba3a50-6862-400c-861a-bfc0a45d4a95',
    vapi_phone_number_id     = '969c6812-b520-468e-8f65-5fb8ca4ee240'
WHERE id = 'aeb9d575-42e2-439f-ad81-8e99ae6900ed';  -- Sunrise Heights
```
This links the shared agent to Sunrise Heights so path 2 and 3 resolve correctly for all calls on this number.

**Recommended:** Option B — it's a one-line SQL change and does not require a code deploy.

---

## Issue 4 — Sweep 2-I: VAPI fired the same webhook twice

**Severity:** Low (dedup handled it)  
**Observation:** The test log shows Sweep 2-I appearing twice with identical `call_id=019e53ad-1c27-7ffa-aae2-b9cf305d8460`. Only one row was saved (backend dedup guard triggered).  
**Root cause:** VAPI occasionally sends duplicate `tool-calls` webhooks for the same call — a known platform behaviour.  
**Fix:** None required. The `call_id` uniqueness check in `lease_lead_webhook` (`voice.py:587-592`) is working correctly.

---

## Passing Scenarios — Details

**Sweep 2-B:** `budget_max=45000` captured correctly (ASR regression from prior sweep is resolved). Agent routed caller to B202 (no pet restriction). `qualification_status=qualified`, correct `property_group_id`.

**Sweep 2-G:** `find_listing` query for "C block, third floor" resolved to `b9f94428-...` (C301). `qualification_status=qualified`, `property_group_id` resolved via listing_uuid.

**Sweep 2-H:** Caller hung up early. No `submit_lease_lead` tool call fired. Webhook returned `{"status": "ignored"}`. Zero new rows in DB.

**Sweep 2-I:** B202 at exactly ₹38,000 matched with `budget_max=38000` (inclusive `lte` filter confirmed working).

---

## Action Items

| Priority | Action | Owner |
|----------|--------|-------|
| P1 | Republish shared lease agent via `update_shared_agents.py` and verify Sweep 2-A prompt was applied | Pranav |
| P1 | Strengthen prompt: add explicit "unmatched when no affordable unit" rule | Pranav |
| P1 | Run SQL Option B to link shared agent to Sunrise Heights property group (fixes property_group_id=None) | Pranav |
| P2 | Strengthen prompt: "use bedroom count from listing, not inferred from caller speech" | Pranav |
| P3 | Investigate why VAPI sends duplicate webhooks for some calls | Later |
