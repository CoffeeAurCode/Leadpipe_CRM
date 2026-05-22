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
