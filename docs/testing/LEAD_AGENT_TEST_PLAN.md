# Lease Agent — Test Plan

## Test Property Setup

Before running any manual test, seed these listings under the `leadpipecrm@gmail.com`
property group ("Sunrise Heights") via the UI or Supabase SQL. All automated tests should
create/clean up their own data.

| ID  | Unit   | Bedrooms | Floor | Rent/mo | Available    | Custom Rules                          | listing_uuid |
|-----|--------|----------|-------|---------|--------------|---------------------------------------|--------------|
| P1  | A101   | 1 BHK    | 1     | ₹20,000 | 2026-05-22   | None                                  | `06424100-448a-4196-b86e-e8c37b4cfc9a` |
| P2  | B202   | 2 BHK    | 2     | ₹38,000 | 2026-06-01   | None                                  | `7b35994b-63cd-40e3-9c35-6ab864c22838` |
| P3  | C301   | 3 BHK    | 3     | ₹65,000 | 2026-05-22   | None                                  | `f1e73d63-cba3-4970-aa8c-f63b49280d04` |
| P4  | D404   | 2 BHK    | 4     | ₹42,000 | 2026-05-22   | No pets allowed                       | `729cac8f-40b0-4906-92f3-763abf72d3bb` |
| P5  | E501   | 2 BHK    | 5     | ₹55,000 | 2026-05-22   | Minimum income: 3× monthly rent       | `096ad042-0803-4f91-b615-9d6c936cd1fd` |

> **Note:** `available_from` is a DATE column — free text like "Immediately" is not valid.
> Units available now use `CURRENT_DATE` (seeded as 2026-05-22). Re-run migration 013 on a different day and these dates will update automatically.

---

## Part 1 — Automated Tests (pytest)

File: `backend/tests/test_leasing.py`

Run with: `pytest backend/tests/test_leasing.py -v`

Each test uses a test client with the FastAPI app. Webhook tests POST a full VAPI-shaped
payload. DB writes go to the real Supabase test project (not mocked).

---

### 1.1 — `GET /leasing/find-listing`

```
TEST: find_listing_by_unit_number
  POST ?query=A101&property_group_id=<pg_id>
  ASSERT response["found"] == True
  ASSERT response["listing_uuid"] is a valid UUID
  ASSERT response["bedrooms"] == 1
  ASSERT response["monthly_rent"] == 20000.0

TEST: find_listing_scoped_to_group
  Create a second property group with unit A101
  POST ?query=A101&property_group_id=<original_pg_id>
  ASSERT only the listing from the specified group is returned

TEST: find_listing_not_found
  POST ?query=Z999
  ASSERT response["found"] == False

TEST: find_listing_by_title_fallback
  Set title="Spacious Studio" on P1
  POST ?query=Spacious+Studio
  ASSERT response["found"] == True
  ASSERT response["listing_uuid"] == P1.uuid
```

---

### 1.2 — `GET /leasing/search`

```
TEST: search_exact_bedroom_budget_match
  GET ?bedrooms=2&budget_max=40000&property_group_id=<pg_id>
  ASSERT "count" >= 1
  ASSERT all returned listings have bedrooms == 2
  ASSERT all returned listings have monthly_rent <= 40000
  # B202 (38k) should appear; D404 (42k) and E501 (55k) should NOT

TEST: search_no_results
  GET ?bedrooms=4&budget_max=10000
  ASSERT response["count"] == 0

TEST: search_budget_only
  GET ?budget_max=25000&property_group_id=<pg_id>
  ASSERT response["count"] == 1  # only P1 at 20k

TEST: search_bedroom_only
  GET ?bedrooms=2&property_group_id=<pg_id>
  ASSERT response["count"] == 3  # B202, D404, E501

TEST: search_returns_listing_uuid_per_result
  # This test will FAIL until Phase 1 of LEAD_ASSIGNMENT_PLAN.md is implemented.
  # It documents the intended post-fix behaviour.
  GET ?bedrooms=2&budget_max=60000
  ASSERT response["listings"] is a list (not a string)
  ASSERT all items in list have "listing_uuid" key
```

---

### 1.3 — `POST /voice/lease-lead-webhook` — Resolution Paths

```
TEST: webhook_resolves_via_listing_uuid  (Path 1)
  POST /voice/lease-lead-webhook with:
    toolCalls[0].function.name = "submit_lease_lead"
    toolCalls[0].function.arguments = {
      "caller_name": "Test Caller",
      "qualification_status": "qualified",
      "listing_uuid": "<P2.uuid>"
    }
    call.assistantId = "unknown-id"
    call.phoneNumberId = "unknown-ph"
    call.customer.number = "+919999000001"
  ASSERT HTTP 200
  ASSERT lead inserted with property_group_id == P2.property_group_id
  ASSERT lead.listing_uuid == P2.uuid
  ASSERT lead.manager_id == leadpipecrm@gmail.com UUID
  CLEANUP: delete lead

TEST: webhook_resolves_via_assistant_id  (Path 2)
  Set properties_list.vapi_lease_assistant_id = "test-ast-123" for the property group
  POST with call.assistantId = "test-ast-123", no listing_uuid
  ASSERT lead.property_group_id resolved correctly

TEST: webhook_resolves_via_phone_number_id  (Path 3)
  Set properties_list.vapi_phone_number_id = "test-ph-123" for the property group
  POST with call.phoneNumberId = "test-ph-123", no listing_uuid
  ASSERT lead.property_group_id resolved correctly

TEST: webhook_no_submit_lead_tool_call
  POST with toolCalls = []
  ASSERT HTTP 200
  ASSERT response["status"] == "ignored"
  ASSERT no lead inserted

TEST: webhook_invalid_listing_uuid_ignored
  POST with listing_uuid = "not-a-real-uuid"
  ASSERT lead inserted with listing_uuid == None  (bad UUID rejected by UUID_RE)
  CLEANUP: delete lead

TEST: webhook_lead_fields_written_correctly
  POST with full args: caller_name, bedrooms=2, budget_max=40000, move_in_timeline="1 month",
        occupants=2, floor_preference="high", qualification_status="qualified",
        notes="Looking for pet-friendly"
  ASSERT all fields written to DB as submitted
  ASSERT source == "voice"
```

---

### 1.4 — `GET /leasing/leads`

```
TEST: get_leads_scoped_to_manager
  Insert one lead with manager_id = leadpipecrm UUID
  Insert one lead with manager_id = a different UUID
  Authenticated GET /leasing/leads as leadpipecrm
  ASSERT only the first lead is returned

TEST: get_leads_filter_by_listing_uuid
  GET /leasing/leads?listing_uuid=<P2.uuid>
  ASSERT all returned leads have listing_uuid == P2.uuid

TEST: get_leads_filter_by_status
  GET /leasing/leads?qualification_status=qualified
  ASSERT all returned leads have qualification_status == "qualified"
```

---

### 1.5 — `PATCH /leasing/leads/{uuid}`

```
TEST: manager_can_set_contacted
  PATCH {qualification_status: "contacted"}
  ASSERT 200, updated status

TEST: manager_can_set_toured
  PATCH {qualification_status: "toured"}
  ASSERT 200

TEST: manager_cannot_set_qualified
  PATCH {qualification_status: "qualified"}
  ASSERT 400

TEST: manager_cannot_set_not_qualified
  PATCH {qualification_status: "not_qualified"}
  ASSERT 400

TEST: manager_can_update_notes
  PATCH {manager_notes: "Called back, scheduled tour"}
  ASSERT 200, notes updated
```

---

### 1.6 — `GET /leasing/metrics`

```
TEST: metrics_counts_correct
  Insert 3 qualified, 2 not_qualified, 1 unmatched leads (within last 30 days)
  GET /leasing/metrics
  ASSERT total_calls == 6
  ASSERT qualified == 3
  ASSERT not_qualified == 2
  ASSERT unmatched == 1
  ASSERT qualification_rate == 50.0
```

---

## Part 2 — Manual Call Test Scenarios

Use the VAPI test call feature or call the actual inbound number.
After each call, check the Leasing tab → Leads panel.

---

### Scenario A — Perfect Single Match (Happy Path)

**Setup:** All 5 listings active.

**Caller says:**
> "I need a 2BHK, my budget is 40,000 rupees, I want to move in next month, just 2 of us."

**Expected agent behaviour:**
1. Calls `search_available_listings` with `bedrooms=2, budget_max=40000`
2. Finds B202 (₹38,000) — the only 2BHK under 40k
3. Presents B202 to caller, asks custom_rules qualifying questions (if any)
4. Caller passes → calls `submit_lease_lead` with `qualification_status=qualified`, `listing_uuid=B202.uuid`

**Expected lead in DB:**
- `qualification_status` = `qualified`
- `listing_uuid` = B202 UUID
- `bedrooms` = 2, `budget_max` = 40000
- `manager_id` = leadpipecrm UUID
- `property_group_id` set

---

### Scenario B — Multiple Listings, Caller Picks One

**Caller says:**
> "2BHK, budget up to 60,000, want a high floor if possible."

**Expected agent behaviour:**
1. Calls `search_available_listings` with `bedrooms=2, budget_max=60000`
2. Gets B202 (38k fl.2), D404 (42k fl.4), E501 (55k fl.5)
3. Presents all three, recommends E501 for high floor
4. Caller says: "E501 sounds great"
5. Asks E501 custom rule: "Can you show proof of income 3× rent (₹1,65,000/mo)?"
6. Caller confirms → `submit_lease_lead` with `listing_uuid=E501.uuid`, `qualification_status=qualified`

**Expected lead in DB:**
- `listing_uuid` = E501 UUID
- `qualification_status` = `qualified`
- `interested_listing_ids` = [B202, D404, E501] UUIDs ← *only after Phase 2+3 implemented*

---

### Scenario C — Over Budget, No Match

**Caller says:**
> "2BHK, I can only pay 30,000 a month."

**Expected agent behaviour:**
1. Calls `search_available_listings` with `bedrooms=2, budget_max=30000`
2. Gets 0 results
3. Offers to show 1BHK options within budget
4. Caller declines
5. `submit_lease_lead` with `qualification_status=unmatched`, `notes="Budget too low for 2BHK"`

**Expected lead in DB:**
- `listing_uuid` = null
- `qualification_status` = `unmatched`
- `bedrooms` = 2, `budget_max` = 30000

---

### Scenario D — Custom Rule Failure (Not Qualified)

**Caller says:**
> "2BHK, budget 45,000, moving in next week, I have a dog."

**Expected agent behaviour:**
1. Finds D404 (42k) and B202 (38k), both 2BHK under 45k
2. B202 has no pet restriction → qualifies
3. D404 has "No pets" rule → disqualified from that unit
4. Agent should offer B202 (which has no pet restriction)
5. If caller insists on D404 → `qualification_status=not_qualified`, `disqualifying_reason="Has pet; unit D404 does not allow pets"`

**Alternate branch:** If agent correctly routes to B202:
- `listing_uuid` = B202 UUID, `qualification_status=qualified`

**What to check:** Does the agent correctly read `custom_rules` from the listing and ask the right qualifying question?

---

### Scenario E — Income Rule Failure

**Caller says:**
> "I want the penthouse on floor 5, budget is fine."

**Expected agent behaviour:**
1. Calls `find_listing` with query "E501" or `search` with floor preference
2. Gets E501 (₹55,000/mo), custom rule: min income 3× rent = ₹1,65,000/mo
3. Asks: "Our policy requires monthly income of at least ₹1,65,000. Can you confirm?"
4. Caller says: "I make about 80,000 a month"
5. `submit_lease_lead` with `qualification_status=not_qualified`, `disqualifying_reason="Income ₹80,000 below required ₹1,65,000 for E501"`

**Expected lead in DB:**
- `listing_uuid` = E501 UUID
- `qualification_status` = `not_qualified`
- `disqualifying_reason` contains the income gap

---

### Scenario F — Wrong Bedroom Count (No Inventory)

**Caller says:**
> "I need a 4BHK, budget is 2 lakh."

**Expected agent behaviour:**
1. `search_available_listings` with `bedrooms=4, budget_max=200000`
2. 0 results
3. Tells caller no 4BHK units available
4. Offers alternatives (3BHK C301 at 65k as closest)
5. Caller not interested
6. `submit_lease_lead` with `qualification_status=unmatched`, `notes="No 4BHK available"`

**Expected lead in DB:**
- `listing_uuid` = null
- `qualification_status` = `unmatched`
- `bedrooms` = 4

---

### Scenario G — Find Listing by Address/Unit Query

**Caller says:**
> "I saw a listing for C block, third floor. Is that still available?"

**Expected agent behaviour:**
1. Calls `find_listing` with query "C301" or "C block"
2. Returns C301 (3BHK, ₹65,000)
3. Confirms availability, walks through custom rules
4. Collects requirements and submits lead

**What to check:** Does `find_listing` correctly return `listing_uuid` and does the agent use it in `submit_lease_lead`?

---

### Scenario H — Caller Hangs Up Before Completion

**Caller says:**
> "I need a 2BHK" then hangs up before agent finishes.

**Expected agent behaviour:**
- Agent never calls `submit_lease_lead`
- Webhook receives end-of-call-report with no `submit_lease_lead` tool call
- `response["status"] == "ignored"` from webhook

**Expected result:** No lead inserted. Verify in Leasing tab — no new entry.

---

### Scenario I — Budget Exactly at Rent Price (Boundary)

**Caller says:**
> "2BHK, budget exactly 38,000, move in June."

**Expected agent behaviour:**
1. `search_available_listings` with `bedrooms=2, budget_max=38000`
2. B202 at exactly ₹38,000 should appear (query uses `lte`, inclusive)
3. Agent presents B202
4. `submit_lease_lead` with `listing_uuid=B202.uuid`, `qualification_status=qualified`

**What to verify:** `lte` filter in `leasing.py:111` is inclusive — boundary value included.

---

### Scenario J — Caller Reopens After Rejection

**Caller says:**
> "Can I look at a different option? I was told about the 1BHK."

**Expected agent behaviour:**
1. Calls `find_listing` or `search` for 1BHK
2. Returns A101 (₹20,000)
3. Collects updated requirements
4. Submits a new lead (or updates the existing if agent logic handles it)

**What to check:** Is a duplicate lead created? The system currently creates a new row per call — confirm deduplication is not needed at this stage.

---

## Part 3 — What to Check After Every Manual Test

**In Supabase SQL Editor:**
```sql
SELECT
  caller_name, phone, bedrooms, budget_max, qualification_status,
  listing_uuid, interested_listing_ids, manager_id, property_group_id,
  created_at
FROM lease_leads
ORDER BY created_at DESC
LIMIT 5;
```

**Checklist per test:**
- [ ] Lead row exists (except Scenario H)
- [ ] `manager_id` = leadpipecrm UUID (`28c43c77-8c9c-496f-8d1e-39ffa9d619e3`)
- [ ] `property_group_id` is not null
- [ ] `qualification_status` matches expected
- [ ] `listing_uuid` is set when agent found a matching unit
- [ ] `bedrooms` and `budget_max` match what caller stated
- [ ] `disqualifying_reason` set for Scenarios D, E
- [ ] Lead appears in Leasing tab UI (no filter hiding it)

---

## Part 5 — Second Sweep: Post-Fix Regression (Manual)

Run after deploying the backend changes and re-provisioning the VAPI shared lease agent.
Each scenario below directly targets one of the fixes made in session 2026-05-22.
Prerequisites: migration 013 has been run, DB contains only the 5 Sunrise Heights listings.

---

### Sweep 2-A — Re-run Scenario C: Verify `unmatched` status and no hallucinated UUID
**Fixes tested:** Fix 3 (no hallucinated listing_uuid), Fix 5 (unmatched when count=0)  
**What failed before:** Agent submitted `listing_uuid=TM1_TEST_UNIT` and `status=qualified` despite no budget match.

**Caller says:**
> "2BHK, I can only pay 30,000 a month."

**Expected agent behaviour:**
1. Calls `search_available_listings` with `bedrooms=2, budget_max=30000`
2. Gets count=0 (cheapest 2BHK is B202 at ₹38,000)
3. Offers 1BHK A101 at ₹20,000 as alternative
4. Caller declines
5. Calls `submit_lease_lead` with `qualification_status=unmatched`, `listing_uuid=""` (blank)

**What to check in DB:**
- [ ] `qualification_status` = `unmatched` — NOT `qualified`
- [ ] `listing_uuid` = null — NOT a made-up string like `TM1_TEST_UNIT`
- [ ] `bedrooms` = 2, `budget_max` = 30000
- [ ] `property_group_id` = `aeb9d575-42e2-439f-ad81-8e99ae6900ed` (Sunrise Heights) — NOT `0205c976`
- [ ] `pg resolution path` in backend log = `listing_uuid` or `assistant_id` — NOT `shared_agent_fallback` to wrong group

---

### Sweep 2-B — Re-run Scenario D: Verify pet rule read and correct budget capture
**Fixes tested:** Fix 3 (no hallucination), Fix 5 (correct status routing), DB cleanup (correct property group)  
**What failed before:** Budget captured as ₹4,500 (ASR error), wrong property group, status `unmatched` instead of routing to B202.

**Caller says:**
> "2BHK, budget 45,000 rupees, moving in next week, I have a dog."

> **Tip:** Say "forty-five thousand rupees" clearly and slowly to reduce ASR mis-transcription. If `budget_max=4500` still appears, it's the Deepgram ASR issue — note it and re-run with exaggerated pronunciation.

**Expected agent behaviour — Branch 1 (agent routes to B202):**
1. Calls `search_available_listings` with `bedrooms=2, budget_max=45000`
2. Gets B202 (₹38,000, no pet rule) and D404 (₹42,000, `pets_allowed=no`)
3. Reads `custom_rules` on D404 → asks "Do you have any pets?"
4. Caller says yes → excludes D404, offers B202 instead
5. `submit_lease_lead` with `listing_uuid=B202.uuid`, `qualification_status=qualified`

**Expected agent behaviour — Branch 2 (caller insists on D404):**
5. `submit_lease_lead` with `listing_uuid=D404.uuid`, `qualification_status=not_qualified`, `disqualifying_reason` mentions pets + D404

**What to check in DB:**
- [ ] `budget_max` = 45000 — NOT 4500 (watch for ASR regression)
- [ ] `listing_uuid` = B202 UUID or D404 UUID — NOT blank, NOT invented
- [ ] `qualification_status` = `qualified` (Branch 1) or `not_qualified` (Branch 2) — NOT `unmatched`
- [ ] `disqualifying_reason` populated if Branch 2
- [ ] `property_group_id` = Sunrise Heights UUID

---

### Sweep 2-C — Re-run Scenario E: Verify E501 is found and income rule applied
**Fixes tested:** Fix 3, Fix 5, DB cleanup (E501 now exists in correct property group)  
**What failed before:** Agent said "No 5th floor units available", marked `unmatched`, wrong property group. E501 was not in the DB under the correct group.

**Caller says:**
> "I want the penthouse on floor 5, budget is fine."

**Expected agent behaviour:**
1. Calls `search_available_listings` with `bedrooms=2` (or broad budget) — E501 appears at ₹55,000, floor 5
2. OR calls `find_listing` with query "E501" / "floor 5" — returns E501
3. Reads `custom_rules` on E501: `income_required=true`, asks the custom question: "Can you confirm monthly income of at least ₹1,65,000 (3× the monthly rent of ₹55,000)?"
4. Caller says: "I make about 80,000 a month"
5. `submit_lease_lead` with `listing_uuid=E501.uuid`, `qualification_status=not_qualified`, `disqualifying_reason` includes the income shortfall

**What to check in DB:**
- [ ] `listing_uuid` = `096ad042-0803-4f91-b615-9d6c936cd1fd` (E501)
- [ ] `qualification_status` = `not_qualified` — NOT `unmatched`
- [ ] `disqualifying_reason` mentions income (e.g. "₹80,000 below required ₹1,65,000")
- [ ] `floor_preference` = "5th floor" or similar
- [ ] `property_group_id` = Sunrise Heights UUID

---

### Sweep 2-D — Currency pronunciation check
**Fix tested:** Fix 1 (agent says "Rupees twenty thousand", not "RS 20000")  
**What failed before:** Agent read rent amounts as "RS" + bare digits on every call.

**Run any scenario** (Scenario A is simplest). During the call, listen specifically when the agent presents rent amounts.

**What to listen for:**
- [ ] Agent says **"Rupees twenty thousand per month"** for A101 — NOT "RS 20000" or "20,000 rupees"
- [ ] Agent says **"Rupees thirty-eight thousand"** for B202 — NOT "RS 38000"
- [ ] Agent says **"Rupees fifty-five thousand"** for E501 — NOT "RS 55000"
- [ ] Numbers spoken as words throughout — no raw digit strings read aloud

> **Note:** This fix is in the system prompt. If "RS" still appears after re-provisioning the agent in VAPI, confirm the new assistant config was published — the old cached config may still be live.

---

### Sweep 2-E — Duplicate lead suppression
**Fix tested:** Fix 2 (backend call_id deduplication), Fix 4 (prompt says EXACTLY ONCE)  
**What failed before:** Scenario B triggered `submit_lease_lead` twice for the same call, creating two lead rows with the same `call_id`.

**Caller says:**
> "2BHK, budget up to 60,000, want a high floor if possible." (repeat Scenario B)

After the call, run this query in Supabase:

```sql
SELECT call_id, COUNT(*) AS lead_count, array_agg(caller_name) AS names
FROM   lease_leads
WHERE  created_at > now() - interval '10 minutes'
GROUP  BY call_id;
```

**What to check:**
- [ ] `lead_count` = 1 for this call's `call_id` — NOT 2
- [ ] Backend log shows `[DUPLICATE] call_id=... already exists, skipping` if a second webhook did fire
- [ ] Only one row visible in the Leasing tab → Leads panel for this call

---

### Sweep 2-F — Scenario F: Wrong bedroom count (first run)
**What was not tested in sweep 1.**

**Caller says:**
> "I need a 4BHK, budget is 2 lakh."

**Expected agent behaviour:**
1. `search_available_listings` with `bedrooms=4, budget_max=200000` → count=0
2. Agent tells caller no 4BHK units available
3. Offers 3BHK C301 at ₹65,000 as closest alternative
4. Caller not interested
5. `submit_lease_lead` with `qualification_status=unmatched`, `listing_uuid=""`, `bedrooms=4`

**What to check in DB:**
- [ ] `listing_uuid` = null
- [ ] `qualification_status` = `unmatched`
- [ ] `bedrooms` = 4
- [ ] `budget_max` = 200000

---

### Sweep 2-G — Scenario G: Find listing by address query (first run)

**Caller says:**
> "I saw a listing for C block, third floor. Is that still available?"

**Expected agent behaviour:**
1. Calls `find_listing` with query "C301" or "C block" or "third floor"
2. Returns C301 (3BHK, ₹65,000, floor 3)
3. Confirms availability and walks through custom rules (none for C301)
4. Collects requirements and `submit_lease_lead` with `listing_uuid=C301.uuid`

**What to check in DB:**
- [ ] `listing_uuid` = `f1e73d63-cba3-4970-aa8c-f63b49280d04` (C301)
- [ ] `qualification_status` = `qualified` (no custom rules to fail)
- [ ] Lead appears in Leasing tab

---

### Sweep 2-H — Scenario H: Caller hangs up — no lead inserted (first run)

**Caller says:**
> "I need a 2BHK" — then hang up immediately before agent responds.

**Expected result:**
- Webhook receives end-of-call-report with no `submit_lease_lead` tool call
- Backend logs `[IGNORED] No submit_lease_lead tool call found`
- `response["status"] == "ignored"`

**What to check in DB:**
```sql
SELECT COUNT(*) FROM lease_leads WHERE created_at > now() - interval '5 minutes';
```
- [ ] Count unchanged — no new row inserted
- [ ] Nothing appears in Leasing tab → Leads panel

---

### Sweep 2-I — Scenario I: Budget exactly at rent price — boundary test (first run)

**Caller says:**
> "2BHK, budget exactly 38,000, move in June."

**Expected agent behaviour:**
1. `search_available_listings` with `bedrooms=2, budget_max=38000`
2. B202 at ₹38,000 appears — `lte` filter is inclusive so boundary value is included
3. Agent presents B202, no custom rules to check
4. `submit_lease_lead` with `listing_uuid=B202.uuid`, `qualification_status=qualified`

**What to check:**
- [ ] `listing_uuid` = `7b35994b-63cd-40e3-9c35-6ab864c22838` (B202)
- [ ] `budget_max` = 38000
- [ ] `qualification_status` = `qualified`

---

### Sweep 2-J — Scenario J: Caller pivots to 1BHK after initial decline (first run)

**Caller says:**
> "Actually, can I look at a cheaper option? Maybe a 1BHK."

(Open conversation — start by asking about 2BHK, go over budget, then pivot.)

**Expected agent behaviour:**
1. Initial search for 2BHK over budget → unmatched
2. Agent proactively offers 1BHK — or caller asks
3. `find_listing` or `search` returns A101 (₹20,000, 1BHK, floor 1)
4. `submit_lease_lead` with `listing_uuid=A101.uuid`, `qualification_status=qualified`

**What to check:**
- [ ] `listing_uuid` = `06424100-448a-4196-b86e-e8c37b4cfc9a` (A101)
- [ ] `qualification_status` = `qualified`
- [ ] Only ONE lead row per call (deduplication check — same `call_id` guard applies)

---

### Sweep 2 — Post-run checklist

After all second-sweep scenarios are complete, run this in Supabase to review the full batch:

```sql
SELECT
  caller_name, bedrooms, budget_max, qualification_status,
  listing_uuid, property_group_id, call_id, created_at
FROM   lease_leads
WHERE  created_at > now() - interval '2 hours'
ORDER  BY created_at DESC;
```

**Sign-off criteria for second sweep:**

| Check | Expected |
|-------|----------|
| All leads → `property_group_id` = Sunrise Heights UUID | `aeb9d575-42e2-439f-ad81-8e99ae6900ed` |
| No `listing_uuid` contains a non-UUID string | All values are valid UUIDs or null |
| No `call_id` appears more than once | Deduplication holding |
| Scenarios C, F with no match → `qualification_status=unmatched` | Not `qualified` |
| Scenarios D, E with rule failure → `qualification_status=not_qualified` | Not `unmatched` |
| Currency spoken as words during calls | "Rupees X thousand", not "RS XXXX" |

---

## Part 4 — Tests That Will Fail Until Plan Is Implemented

These scenarios CANNOT pass until `LEAD_ASSIGNMENT_PLAN.md` phases are complete.
Run them after each phase to track progress.

| Test | Fails Until |
|---|---|
| `search_returns_listing_uuid_per_result` (automated 1.2) | Phase 1 |
| Scenario B: `interested_listing_ids` has all 3 UUIDs | Phase 2 + 3 |
| Scenario A: `listing_uuid` auto-set from agent's search result | Phase 1 + 2 |
| Lead detail modal shows matched unit name | Phase 4 |
| `GET /leasing/leads?listing_uuid=X` also matches `interested_listing_ids` | Phase 5 |
