# Manual Test Guide — Sweep 3 (Lease Agent Regression + Complaint Outbound Fix)

**Date:** 2026-05-23  
**Agent under test:** Shared lease agent `2dba3a50-6862-400c-861a-bfc0a45d4a95` on `+1 (518) 318-9117`  
**Complaint agent under test:** Alex `9e507761-7bf7-451a-9413-8ae62ec0176f` on `+1 (438) 231-4283`

---

## Pre-flight Checklist

Before running any test:

- [ ] Run `python backend/scripts/update_shared_agents.py` — confirms the latest prompt (budget enforcement + bedroom rules) is live on the shared lease agent
- [ ] Verify in VAPI dashboard that the shared lease agent system prompt contains the words **"BUDGET ENFORCEMENT"** and **"BEDROOM COUNT"**
- [ ] Confirm Render has `VAPI_COMPLAINT_ASSISTANT_ID=9e507761-7bf7-451a-9413-8ae62ec0176f` and `VAPI_COMPLAINT_NUMBER_ID=e8367bd3-12c6-4423-aa93-27ee8b264f48` set in Environment

---

## Sweep 3-A — Re-test: Budget too low (was Sweep 2-A FAIL)

**Goal:** Confirm agent does NOT qualify caller over budget.

| Step | Action |
|------|--------|
| 1 | Call `+1 (518) 318-9117` |
| 2 | Say: "I'm looking for a 2-bedroom apartment. My budget is 30,000 a month." |
| 3 | Do NOT accept any alternative the agent offers |
| 4 | If agent offers a 1BHK or anything cheaper, say: "No, I specifically need 2 bedrooms." |
| 5 | Give name: "Test Person A" |
| 6 | Let the call end naturally |

**Expected DB row in `lease_leads`:**
```
caller_name     = "Test Person A"
bedrooms        = 2
budget_max      = 30000
qualification_status = unmatched
listing_uuid    = null
disqualifying_reason contains "budget" or "afford"
property_group_id IS NOT NULL   ← confirmed fixed via SQL Option B
```

**Pass condition:** `qualification_status = unmatched` AND `listing_uuid IS NULL`.  
**Fail condition:** `qualification_status = qualified` or a listing_uuid is populated with any unit.

---

## Sweep 3-B — Re-test: Penthouse / floor 5 (was Sweep 2-C FAIL)

**Goal:** Confirm agent calls `find_listing` first and does not hallucinate `bedrooms=3`.

| Step | Action |
|------|--------|
| 1 | Call `+1 (518) 318-9117` |
| 2 | Say: "I'm interested in the penthouse on floor 5. My budget is fine — I can pay up to 2 lakh a month." |
| 3 | Answer qualifying questions honestly — "Yes, I have a stable income." |
| 4 | Give name: "Test Person B" |
| 5 | Let the call end naturally |

**Expected DB row in `lease_leads`:**
```
caller_name     = "Test Person B"
bedrooms        = 2   ← must NOT be 3
budget_max      = 200000
qualification_status = not_qualified   ← income rule blocks E501
listing_uuid    = <E501 UUID>          ← agent must find E501 via find_listing
disqualifying_reason contains "income"
property_group_id IS NOT NULL
```

**Pass condition:** `bedrooms = 2` AND `qualification_status = not_qualified` AND `listing_uuid` is E501's UUID.  
**Fail condition:** `bedrooms = 3`, or `qualification_status = unmatched` (meaning agent never found the listing), or `listing_uuid = null`.

---

## Sweep 3-C — Outbound Complaint Call (NEW — was blocked by bug)

**Goal:** Confirm the complaint outbound call now routes to Alex (`9e507761`) on `+14382314283`.

| Step | Action |
|------|--------|
| 1 | Open the app → navigate to the Outbound Call button |
| 2 | Select agent: **Complaint** |
| 3 | Enter your phone number |
| 4 | Click Call |
| 5 | Answer the call |

**Expected:**
- Call connects and Alex greets you (not the lease agent)
- VAPI dashboard shows call initiated with assistant `9e507761-7bf7-451a-9413-8ae62ec0176f`
- Caller ID shows `+14382314283`
- Alex asks for your flat number

**Pass condition:** Call connects, caller ID is `+14382314283`, assistant ID in VAPI dashboard is `9e507761`.  
**Fail condition:** Old assistant `2cbc056b` shown, or call fails with 500 error.

---

## Sweep 3-D — Regression: Budget at boundary (was Sweep 2-I PASS)

**Goal:** Confirm boundary budget match still works after prompt changes.

| Step | Action |
|------|--------|
| 1 | Call `+1 (518) 318-9117` |
| 2 | Say: "I'm looking for a 2-bedroom unit. My max budget is 38,000 a month." |
| 3 | Answer qualifying questions: no pets |
| 4 | Give name: "Test Person D" |
| 5 | Let the call end naturally |

**Expected DB row:**
```
caller_name     = "Test Person D"
bedrooms        = 2
budget_max      = 38000
qualification_status = qualified
listing_uuid    = <B202 UUID>
property_group_id IS NOT NULL
```

**Pass condition:** `qualification_status = qualified` with B202 listing_uuid.

---

## Sweep 3-E — Regression: Find by address (was Sweep 2-G PASS)

**Goal:** Confirm `find_listing` address query still resolves correctly.

| Step | Action |
|------|--------|
| 1 | Call `+1 (518) 318-9117` |
| 2 | Say: "I'm interested in the unit in C block on the third floor." |
| 3 | Answer qualifying questions honestly |
| 4 | Give name: "Test Person E" |
| 5 | Let the call end naturally |

**Expected DB row:**
```
caller_name     = "Test Person E"
listing_uuid    = <C301 UUID>   ← b9f94428-...
qualification_status = qualified
property_group_id IS NOT NULL
```

---

## Post-Run DB Verification Query

Run in Supabase SQL editor after each test call:

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

## Pass/Fail Summary Template

| Scenario | Pass/Fail | Notes |
|----------|-----------|-------|
| 3-A (budget too low → unmatched) | | |
| 3-B (penthouse → bedrooms from listing, income disqualify) | | |
| 3-C (outbound complaint call → Alex on +14382314283) | | |
| 3-D (budget boundary 38k → qualified B202) | | |
| 3-E (address find C block floor 3 → C301) | | |

**Sweep 3 is complete when:** 3-A, 3-B, 3-C all PASS (they were the failing/blocked scenarios). 3-D and 3-E must not regress.
