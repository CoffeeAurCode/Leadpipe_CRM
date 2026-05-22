# Lease Agent — Manual Test Report
**Date:** 2026-05-22  
**Tester:** Pranav Raj  
**Environment:** Production (leadpipecrm@gmail.com / Sunrise Heights)  
**Agent:** Shared Lease Agent (VAPI assistantId: `2dba3a50-6862-400c-861a-bfc0a45d4a95`)  
**Inbound number:** phoneNumberId `969c6812-b520-468e-8f65-5fb8ca4ee240`  
**Scenarios run:** A, B, C, D, E (5 of 10 from LEAD_AGENT_TEST_PLAN.md)

---

## Summary Table

| Scenario | Description | Result | Issues |
|----------|-------------|--------|--------|
| A | Perfect single match (2BHK ≤ ₹40k) | PASS | None |
| B | Multiple listings, caller picks one (E501) | PARTIAL PASS | Duplicate lead inserted |
| C | Over budget, no match (2BHK ≤ ₹30k) | FAIL | Hallucinated listing_uuid; marked `qualified` instead of `unmatched` |
| D | Custom rule failure — no pets (2BHK ≤ ₹45k, has dog) | FAIL | Wrong budget captured (₹4,500 vs ₹45,000); wrong property group; status `unmatched` instead of routing to B202 |
| E | Income rule failure (E501 floor 5, income insufficient) | FAIL | Agent said "no 5th floor units available"; wrong property group; status `unmatched` with wrong reason |

---

## Scenario A — Perfect Single Match ✅ PASS

**Caller said:** "2BHK, budget 40,000, move in next month, 2 of us."

**Expected:** Agent finds B202 (₹38,000), qualifies caller, submits lead with `listing_uuid=B202.uuid`, `status=qualified`.

**Webhook log:**
```
call.id:          019e5014-3e5c-7000-9a43-dc3cc8b84087
bedrooms:         2
budget_max:       40000
listing_uuid:     85610b9d-7326-4891-b30c-29a168d61549   ← B202
qualification_status: qualified
pg resolution:    path=listing_uuid   ← correct path
manager_id:       28c43c77-8c9c-496f-8d1e-39ffa9d619e3
property_group_id: aeb9d575-42e2-439f-ad81-8e99ae6900ed  ← Sunrise Heights ✓
```

**Result:** All fields correct. Property group resolved via listing_uuid (Path 1). Lead saved correctly.

---

## Scenario B — Multiple Listings, Caller Picks One ⚠️ PARTIAL PASS

**Caller said:** "2BHK, budget up to 60,000, want a high floor."

**Expected:** Agent presents B202, D404, E501. Caller picks E501. Agent asks income question. Lead submitted once with `listing_uuid=E501.uuid`, `status=qualified`.

**Webhook log (first call):**
```
call.id:          019e5017-0273-7000-8867-82dfc1b24464
caller_name:      Best Person
listing_uuid:     6fdefef4-905f-456c-b7ab-e8cc43ad0c09   ← E501 ✓
qualification_status: qualified
qualifying_answers: {"Stable source of income":"Yes","Monthly income at least 3x rent (₹1,65,000)":"Yes"}
floor_preference: High floor ✓
```

**Webhook log (second call — same call.id, 15 seconds later):**
```
call.id:          019e5017-0273-7000-8867-82dfc1b24464   ← SAME call
caller_name:      Test Burrison                           ← different name
listing_uuid:     6fdefef4-905f-456c-b7ab-e8cc43ad0c09
qualification_status: qualified
```

**Result:** Lead data correct (E501, qualified, income answers captured). However `submit_lease_lead` was called **twice** in the same conversation — two lead rows were inserted for the same call. The second invocation had a different `caller_name` ("Test Burrison"), suggesting the agent asked for the name again and re-submitted.

**Issue found:** See Issue 2 below.

---

## Scenario C — Over Budget, No Match ❌ FAIL

**Caller said:** "2BHK, I can only pay 30,000 a month."

**Expected:** `search_available_listings` returns 0 results (cheapest 2BHK is B202 at ₹38,000). Agent offers 1BHK alternative, caller declines. Lead submitted with `listing_uuid=""`, `status=unmatched`.

**Webhook log:**
```
call.id:          019e501c-b8fc-7001-93ad-157586b4da88
bedrooms:         2
budget_max:       30000 ✓
listing_uuid:     TM1_TEST_UNIT                          ← HALLUCINATED, not a UUID
qualification_status: qualified                          ← WRONG (should be unmatched)
pg resolution:    path=shared_agent_fallback             ← wrong path
property_group_id: 0205c976-dda7-4281-b87e-b27fbfbc531c ← WRONG group
```

**Issues found:** See Issues 1, 3, 4 below.

---

## Scenario D — Custom Rule Failure (No Pets) ❌ FAIL

**Caller said:** "2BHK, budget 45,000, moving in next week, I have a dog."

**Expected:** Agent finds B202 (no pet rule) and D404 (no pets). Routes caller to B202 as pet-friendly alternative. If caller insists on D404 → `status=not_qualified`. Otherwise `status=qualified` with B202.

**Webhook log:**
```
call.id:          019e501f-1d63-722f-b927-17f2c490a68d
bedrooms:         2
budget_max:       4500                                   ← WRONG (should be 45000)
occupants:        0                                      ← should be ≥1
listing_uuid:     (empty)
disqualifying_reason: (empty)
qualification_status: unmatched
pg resolution:    path=shared_agent_fallback
property_group_id: 0205c976-dda7-4281-b87e-b27fbfbc531c ← WRONG group
```

**Issues found:** See Issues 3, 4, 5 below.

---

## Scenario E — Income Rule Failure ❌ FAIL

**Caller said:** "I want the penthouse on floor 5, budget is fine."

**Expected:** Agent finds E501 (2BHK, ₹55,000, floor 5, income rule). Asks income question. Caller says ₹80,000/mo → fails 3× requirement. `status=not_qualified`, `disqualifying_reason` includes income gap, `listing_uuid=E501.uuid`.

**Webhook log:**
```
call.id:          019e5022-5cd2-7bb0-a1b5-70fd775d7714
bedrooms:         3                                      ← WRONG (E501 is 2BHK)
budget_max:       200000
floor_preference: 5th floor ✓
listing_uuid:     (empty)                               ← E501 not found
disqualifying_reason: No 5th floor units available      ← WRONG reason
qualification_status: unmatched                         ← should be not_qualified
pg resolution:    path=shared_agent_fallback
property_group_id: 0205c976-dda7-4281-b87e-b27fbfbc531c ← WRONG group
```

**Issues found:** See Issues 3, 4 below.

---

## Issues Found

### Issue 1 — Agent says "RS" and reads rent as bare digits

**Observed in:** All scenarios (voice output, not captured in webhook log).  
**Description:** When the agent presents a listing, it says "R S 55,000 per month" or reads the number as digits ("fifty-five-thousand" was not being said as natural words; instead "RS 20000"). This sounds robotic and confusing over a voice call.  
**Root cause:** The system prompt had no instruction about how to pronounce currency. VAPI's TTS engine reads "₹" as "RS" and reads raw numbers digit-by-digit unless told otherwise.

---

### Issue 2 — Duplicate lead inserted for same call (Scenario B)

**Observed in:** Scenario B — two webhook POST requests with the same `call.id` 15 seconds apart, two rows in `lease_leads`.  
**Description:** The agent called `submit_lease_lead` twice in the same conversation. The backend had no guard against this, so both invocations were inserted.  
**Root cause (agent side):** The system prompt said "call submit_lease_lead before ending the call" but didn't prohibit calling it more than once. The agent apparently asked for the caller's name again mid-conversation and re-triggered the tool.  
**Root cause (backend side):** `POST /voice/lease-lead-webhook` did not check whether a lead with the same `call_id` already existed before inserting.

---

### Issue 3 — Agent hallucinated a listing_uuid (Scenario C)

**Observed in:** Scenario C — `listing_uuid: TM1_TEST_UNIT` submitted.  
**Description:** When no listings were found matching the budget, the agent submitted `TM1_TEST_UNIT` as the listing_uuid instead of leaving it blank. This is not a valid UUID and was correctly rejected by the backend's `UUID_RE` regex (stored as `null`), but it indicates the agent invented data.  
**Root cause:** The system prompt said "use the listing_uuid from search or find_listing" but did not explicitly prohibit inventing IDs when no tool result was available. Without a hard prohibition, the LLM filled the required field with a plausible-looking value from its context window (possibly a stale test unit name it had seen earlier in the call).

---

### Issue 4 — Wrong property group resolved (Scenarios C, D, E)

**Observed in:** Scenarios C, D, E — `path=shared_agent_fallback`, `property_group_id=0205c976` instead of the Sunrise Heights group `aeb9d575`.  
**Description:** The webhook resolved the lead to the wrong property group. Scenarios A and B resolved correctly via `path=listing_uuid` because those scenarios had a valid `listing_uuid`. When no real listing_uuid was present (Scenarios C, D, E), Path 1 failed; the shared agent's `assistantId` is not stored in `properties_list.vapi_lease_assistant_id`, so Path 2 also failed; `phoneNumberId` is not in `properties_list.vapi_phone_number_id`, so Path 3 failed — and Path 4 (shared_agent_fallback) picked up the first property group in the table, which happened to be `0205c976`.  
**Root cause:** The shared lease agent was configured without a `property_group_id` in its tool URLs (intentional for multi-tenant flexibility), but the webhook's fallback assigns the lead to whichever property group is first in `properties_list`. The test DB contained stale listings from a different property group, causing that group to be returned first.  
**Fix path:** Run migration `013_seed_lead_agent_test_data.sql` to delete stale listings. After cleanup, the search endpoint will only return the 5 Sunrise Heights listings, so Scenarios C/D/E will resolve via `listing_uuid` (once a match is found) or, when there is genuinely no match, the manager can manually reassign via the Leasing tab.

---

### Issue 5 — Agent misheard budget as ₹4,500 instead of ₹45,000 (Scenario D)

**Observed in:** Scenario D — `budget_max: 4500`.  
**Description:** The caller said "45,000" but VAPI's ASR (Deepgram) transcribed it as "4,500". The agent passed the transcribed value to `search_available_listings`, received 0 results (since cheapest unit is ₹20,000), and fell back to `unmatched` without finding B202 or D404.  
**Root cause:** Indian English number pronunciation combined with phone audio compression can cause ASR to drop a digit magnitude. This is an upstream voice-recognition limitation, not a backend bug.  
**Mitigation:** The agent should confirm the budget back to the caller before searching ("Just to confirm, your budget is forty-five thousand rupees per month?"). A confirmation step was not in the system prompt.

---

## Fixes Applied

### Fix 1 — Currency pronunciation rule in system prompt
**File:** `backend/app/services/vapi_agent_config.py`  
**Change:** Added to `[Style]` section:
```
When quoting rent amounts always say "Rupees" followed by the number as words —
e.g. "Rupees twenty thousand per month". Never say "RS", "R S", or read out bare digits like "20000".
```
**Effect:** Agent will say "Rupees thirty-eight thousand per month" instead of "RS 38000".

---

### Fix 2 — Backend deduplication by call_id
**File:** `backend/app/routes/voice.py`  
**Change:** Before inserting a new lead row, the webhook now queries `lease_leads` for an existing row with the same `call_id`. If found, it returns `{"status": "duplicate"}` and skips the insert.
```python
if call_id:
    dup = db.table("lease_leads").select("id").eq("call_id", call_id).limit(1).execute()
    if dup.data:
        print(f"  [DUPLICATE] call_id={call_id} already exists, skipping")
        return {"status": "duplicate"}
```
**Effect:** Even if the agent misfires `submit_lease_lead` twice, only one lead row is ever created per call.

---

### Fix 3 — Stronger prompt rules against hallucinating listing_uuid
**File:** `backend/app/services/vapi_agent_config.py`  
**Change (Step 7):** Updated instruction from "use the listing_uuid from search or find_listing" to:
```
copy the EXACT listing_uuid string returned by find_listing or search_available_listings;
leave blank if no listing was found — NEVER invent or guess a UUID
```
**Change (Critical Rules):** Added:
```
- listing_uuid in submit_lease_lead must be a value returned by a tool.
  If no match was found, leave it blank. NEVER make up a listing ID.
- If search_available_listings returns count=0 and all alternatives are exhausted,
  set qualification_status="unmatched". Never mark a caller "qualified" without a real listing_uuid.
```
**Effect:** Prevents the agent from submitting fabricated UUIDs or marking an unmatched caller as qualified.

---

### Fix 4 — Prompt rule against calling submit_lease_lead twice
**File:** `backend/app/services/vapi_agent_config.py`  
**Change (Step 7 and Critical Rules):** Changed "Always call submit_lease_lead before ending the call" to "Always call submit_lease_lead **EXACTLY ONCE** before ending the call. Never call it twice in the same conversation."  
**Effect:** Reduces the probability of the agent re-submitting after asking for the caller's name again.

---

### Fix 5 — Qualification logic tightened in prompt (Step 5)
**File:** `backend/app/services/vapi_agent_config.py`  
**Change:** Step 5 "Qualification Decision" now reads:
```
All criteria met AND a real listing_uuid exists → qualification_status = "qualified"
Any criterion failed → qualification_status = "not_qualified", note the reason
No listing was found by a tool (count=0 or found=false) → qualification_status = "unmatched"; leave listing_uuid blank
```
**Effect:** The agent can no longer mark a caller `qualified` without having a real listing_uuid from a tool response.

---

### Fix 6 — DB seed migration (run successfully 2026-05-22)
**File:** `backend/migrations/013_seed_lead_agent_test_data.sql`

#### How the query was built

The migration is a single `DO $$ ... END $$` PL/pgSQL block so that intermediate UUIDs (property group, building, each flat) can be captured in variables and reused in subsequent statements within the same transaction — plain SQL has no variables.

**Step-by-step logic:**

**1. Resolve the property group dynamically**
```sql
SELECT id INTO v_pg_id
FROM   properties_list
WHERE  manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
ORDER  BY created_at LIMIT 1;
```
Rather than hardcoding the property group UUID (which would break if the account is recreated), the script looks it up by `manager_id`. If none is found it raises an exception early so nothing partial gets written.

**2. Resolve or create the building**
```sql
SELECT id INTO v_building_id FROM buildings WHERE property_id = v_pg_id LIMIT 1;
IF v_building_id IS NULL THEN
  INSERT INTO buildings (property_id, name, address)
  VALUES (v_pg_id, 'Sunrise Heights', 'Sunrise Heights')
  RETURNING id INTO v_building_id;
END IF;
```
If no building exists yet under the property group, one is created. Otherwise the existing one is reused. Either way `v_building_id` is set for the flat inserts below.

**3. FK-safe delete of lease_listings**

The first version of the script simply ran `DELETE FROM lease_listings WHERE manager_id = ...`. This immediately failed with:
```
ERROR 23503: update or delete on table "lease_listings" violates foreign key constraint
"lease_leads_listing_uuid_fkey" on table "lease_leads"
```
Because `lease_leads.listing_uuid` is a FK → `lease_listings.uuid`, PostgreSQL blocks the delete while any lead still references one of those listing rows. The fix was to nullify the FK in `lease_leads` first, then delete:
```sql
UPDATE lease_leads
SET    listing_uuid = NULL
WHERE  listing_uuid IN (
  SELECT uuid FROM lease_listings WHERE manager_id = v_manager_id
);
DELETE FROM lease_listings WHERE manager_id = v_manager_id;
```
`NULL` is always a valid value for a nullable FK column, so this sidesteps the constraint without dropping it or touching the schema.

**4. Making the flat upserts idempotent — `ON CONFLICT DO UPDATE`**

The `flats.flat_number` column has a `UNIQUE` constraint from the original schema. A plain `INSERT` would fail with a duplicate-key error if A101 already existed from a previous run of the script (or from earlier manual data entry).

The fix is `INSERT ... ON CONFLICT (flat_number) DO UPDATE SET ...`:
```sql
INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
VALUES ('A101', v_building_id, 1, 1, 'Sunrise Heights', false)
ON CONFLICT (flat_number) DO UPDATE
  SET building_id  = EXCLUDED.building_id,
      floor_number = EXCLUDED.floor_number,
      bedrooms     = EXCLUDED.bedrooms,
      address      = EXCLUDED.address,
      occupied     = false
RETURNING uuid INTO v_uuid_A101;
```
`EXCLUDED` refers to the row that would have been inserted. So on a conflict, the existing row is updated with the correct values instead of the statement erroring. The `RETURNING uuid` clause captures the UUID of the row whether it was just inserted or just updated.

However, `RETURNING` only fires on actual inserts — when the `DO UPDATE` branch runs, PostgreSQL still returns the updated row, but in some Supabase SQL Editor contexts it was observed to return `NULL` into the variable. The fallback handles this:
```sql
IF v_uuid_A101 IS NULL THEN
  SELECT uuid INTO v_uuid_A101 FROM flats WHERE flat_number = 'A101';
END IF;
```
This guarantees `v_uuid_A101` is always populated before the `lease_listings` insert that depends on it.

**5. `available_from` — why `NULL` was wrong and `CURRENT_DATE` is correct**

The first version of the script used `NULL` for units described as "available immediately" in the test plan. After running, the verification query showed:

```
A101 | available_from: Immediately   ← displayed as text by COALESCE(..., 'Immediately')
```

The problem: `available_from` is a `DATE` column. The UI's date picker can only write a real date — it has no "Immediately" option. So `NULL` in the column means "no date set", which is ambiguous and renders differently across the UI and the VAPI agent's responses.

The fix was to replace `NULL` with `CURRENT_DATE` for all immediately-available units:
```sql
-- Before
(v_pg_id, v_uuid_A101, 'A101', 20000, NULL, '{}', true, v_manager_id)

-- After
(v_pg_id, v_uuid_A101, 'A101', 20000, CURRENT_DATE, '{}', true, v_manager_id)
```
`CURRENT_DATE` is a PostgreSQL function that returns today's date at execution time. This means if the migration is re-run on a future date, A101/C301/D404/E501 will have that new date as their `available_from` — always reflecting "available as of the day the seed was run". B202 keeps its fixed date `2026-06-01` because the test plan specifically requires a future availability.

**Confirmed DB state after run:**

| flat_number | bedrooms | floor | monthly_rent | available_from | listing_uuid |
|-------------|----------|-------|--------------|----------------|--------------|
| A101 | 1 | 1 | 20000 | 2026-05-22 | `06424100-448a-4196-b86e-e8c37b4cfc9a` |
| B202 | 2 | 2 | 38000 | 2026-06-01 | `7b35994b-63cd-40e3-9c35-6ab864c22838` |
| C301 | 3 | 3 | 65000 | 2026-05-22 | `f1e73d63-cba3-4970-aa8c-f63b49280d04` |
| D404 | 2 | 4 | 42000 | 2026-05-22 | `729cac8f-40b0-4906-92f3-763abf72d3bb` |
| E501 | 2 | 5 | 55000 | 2026-05-22 | `096ad042-0803-4f91-b615-9d6c936cd1fd` |

**Effect:** Eliminates stale listings from other property groups. After this, `shared_agent_fallback` will stop picking the wrong group because the Sunrise Heights listings will be the only active ones when no `listing_uuid` is returned.

---

## Pending — After Deploy

After deploying the backend and re-provisioning the VAPI shared lease agent (so it picks up the updated system prompt), re-run all 5 scenarios and additionally:

- **Scenario D re-run:** Budget re-confirm step will not be present until Issue 5 (ASR) is addressed via a prompt addition. Watch for `budget_max: 4500` recurring — if it does, add a budget-confirmation step to the system prompt.
- **Scenario E re-run:** After DB cleanup, `search_available_listings` for `bedrooms=2, budget_max=200000` should now return E501. The agent should find it, read the income rule from `custom_rules`, ask the income question, and mark `not_qualified`.
- **Verify no duplicate leads:** Run Scenario B again and confirm only one row is inserted in `lease_leads` for the call.

---

## Scenarios Not Yet Run

| Scenario | Description |
|----------|-------------|
| F | Wrong bedroom count (4BHK, no inventory) |
| G | Find listing by address/unit query ("C block, third floor") |
| H | Caller hangs up before completion — no lead should be inserted |
| I | Budget exactly at rent price (2BHK, budget=38,000, B202 boundary) |
| J | Caller reopens after rejection — 1BHK fallback |
