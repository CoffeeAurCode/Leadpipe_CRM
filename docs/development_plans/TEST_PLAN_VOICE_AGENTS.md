# Voice Agents Test Plan — Complaint + Lease

**Date:** 2026-05-21  
**Status:** Active  
**Agents:** Complaint (Alex) `+1 (973) 490-4520` · Shared Lease `+1 (518) 318-9117`  
**Production URL:** `https://tenant-management-mvp.onrender.com`  
**Local URL:** `http://localhost:8000`

---

## 0. Quick Reference

| What | Value |
|------|-------|
| Complaint assistant ID | `9e507761-7bf7-451a-9413-8ae62ec0176f` |
| Complaint phone | `+19734904520` |
| Shared lease assistant ID | `2dba3a50-6862-400c-861a-bfc0a45d4a95` |
| Shared lease phone | `+15183189117` |
| Webhook URL (complaint) | `{BASE_URL}/voice/webhook` |
| Webhook URL (lease lead) | `{BASE_URL}/voice/lease-lead-webhook` |
| Verify-phone tool | `POST {BASE_URL}/flats/verify-phone?phone_number={caller}` |
| Find listing tool | `GET {BASE_URL}/leasing/find-listing?query={q}` |
| Search tool | `GET {BASE_URL}/leasing/search?bedrooms={n}&budget_max={x}` |

---

## 1. Prerequisites — Data Setup

Before running any test, ensure these exist in the DB. Use the app UI or direct Supabase inserts.

### 1.1 Complaint Agent prerequisites

| Item | Requirement |
|------|-------------|
| Flat | At least one flat with a known `flat_number` (e.g. `A-101`) |
| Tenant | Tenant linked to that flat with phone matching your test caller phone |
| Building | Flat is linked to a building which is linked to a `properties_list` row |

> The verify-phone response now returns `property_group_id`. The chain must be complete (flat → building_id → buildings.property_id) or `property_group_id` will be null.

### 1.2 Lease Agent prerequisites

| Item | Requirement |
|------|-------------|
| Listing | At least one active `lease_listings` row with `is_active = true` |
| Flat FK | That listing's `flat_uuid` must point to a real flat (needed for the join) |
| PropertyGroup | Listing's `property_group_id` must point to an existing `properties_list` row |

### 1.3 Get a JWT for authenticated endpoints

```bash
# Log in via the frontend or hit the auth endpoint directly
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"YOUR_EMAIL","password":"YOUR_PASSWORD"}' | jq .access_token
```

Export it:
```bash
export JWT="<paste token here>"
```

---

## 2. Automated Script Tests

Two scripts cover all backend endpoints without needing a real phone call.

```
backend/scripts/test_complaint_endpoints.sh   ← complaint agent tools + webhook
backend/scripts/test_leasing_endpoints.sh     ← lease VAPI tools + manager CRUD
```

Run locally (backend must be running):
```bash
BASE_URL=http://localhost:8000 JWT=$JWT bash backend/scripts/test_complaint_endpoints.sh
BASE_URL=http://localhost:8000 JWT=$JWT bash backend/scripts/test_leasing_endpoints.sh
```

Run against production:
```bash
BASE_URL=https://tenant-management-mvp.onrender.com JWT=$JWT bash backend/scripts/test_complaint_endpoints.sh
```

Each test prints `[PASS]` or `[FAIL]` with the actual response. Exit code is the number of failures (0 = all pass).

---

## 3. Phase A — Complaint Agent: Endpoint Tests

### A1 · Verify-Phone: Valid tenant

**What it tests:** Phone matches flat → returns `status: valid` + non-null `property_group_id`

```bash
curl -s -X POST "$BASE_URL/flats/verify-phone?phone_number=+91TENANT_PHONE" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "A-101"}'
```

**Expected:**
```json
{
  "status": "valid",
  "result": "Verification result: valid. ...",
  "datetime": "2026-05-21T...",
  "property_group_id": "<uuid>"
}
```

**Assertion:** `status == "valid"` AND `property_group_id != null`

---

### A2 · Verify-Phone: Wrong phone for flat

**What it tests:** Phone doesn't match → `status: invalid`, no pg_id

```bash
curl -s -X POST "$BASE_URL/flats/verify-phone?phone_number=+919999999999" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "A-101"}'
```

**Expected:** `{"status": "invalid", "property_group_id": null}`  
**Assertion:** `status == "invalid"` AND HTTP 200

---

### A3 · Verify-Phone: Vacant flat

```bash
curl -s -X POST "$BASE_URL/flats/verify-phone?phone_number=+91TENANT_PHONE" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "VACANT-101"}'
```

**Expected:** `{"status": "vacant"}`  
**Assertion:** HTTP 200, status is "vacant"

---

### A4 · Verify-Phone: Non-existent flat

```bash
curl -s -X POST "$BASE_URL/flats/verify-phone?phone_number=+91TENANT_PHONE" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "ZZZ-999"}'
```

**Expected:** `{"status": "invalid"}`  
**Assertion:** HTTP 200 (never 404)

---

### A5 · Verify-Phone: Missing phone_number query param

```bash
curl -s -X POST "$BASE_URL/flats/verify-phone" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "A-101"}'
```

**Expected:** `{"status": "invalid"}`, result mentions phone not available  
**Assertion:** HTTP 200

---

### A6 · Complaint Webhook: Tool-call event with submit_complaint

Simulates VAPI calling the webhook after the tenant confirms a complaint.

```bash
curl -s -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "test-call-001",
        "customer": {"number": "+91TENANT_PHONE"},
        "assistantId": "9e507761-7bf7-451a-9413-8ae62ec0176f"
      },
      "toolCalls": [{
        "function": {
          "name": "submit_complaint",
          "arguments": "{\"flat_number\":\"A-101\",\"category\":\"plumbing\",\"description\":\"Pipe leak under sink\",\"appointment_date\":\"2026-05-25T10:00:00\",\"property_group_id\":\"<UUID>\"}"
        }
      }]
    }
  }'
```

**Expected:** `{"status": "processed", "complaint_created": true}`  
**Assertion:** complaint row created in DB; call_logs row has status "created"

---

### A7 · Complaint Webhook: End-of-call abandoned (no tool call)

```bash
curl -s -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "end-of-call-report",
      "call": {"id": "test-call-002", "customer": {"number": "+91TENANT_PHONE"}},
      "artifact": {"transcript": "Hello... ok bye"}
    }
  }'
```

**Expected:** `{"status": "processed", "complaint_created": false}`  
**Assertion:** call_logs row has status "abandoned"; no complaint created

---

### A8 · Complaint Webhook: Ignored event (non-final)

```bash
curl -s -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "status-update", "call": {"id": "test-call-003"}}}'
```

**Expected:** `{"status": "ignored", "reason": "non_final_event"}`  
**Assertion:** HTTP 200, no DB writes

---

### A9 · Complaint Webhook: Idempotency (duplicate call_id)

Send A6 twice with the same `call_id`. Second call must not create a duplicate complaint.

**Assertion:** call_logs has exactly one row for `test-call-001`; complaint created only once

---

## 4. Phase B — Lease Agent: Endpoint Tests

### B1 · Find-Listing: Match by flat_number

```bash
curl -s "$BASE_URL/leasing/find-listing?query=A-101"
```

**Expected:**
```json
{"found": true, "listing_uuid": "...", "monthly_rent": 15000.0, "bedrooms": 2, ...}
```
**Assertion:** `found == true`, `listing_uuid` is a valid UUID

---

### B2 · Find-Listing: No match

```bash
curl -s "$BASE_URL/leasing/find-listing?query=ZZZNOMATCH"
```

**Expected:** `{"found": false}`  
**Assertion:** HTTP 200 (not 404), `found == false`

---

### B3 · Find-Listing: Scoped to property_group_id

```bash
curl -s "$BASE_URL/leasing/find-listing?query=A-101&property_group_id=<UUID>"
```

**Expected:** Same result as B1 if listing belongs to that group; `{"found": false}` if not  
**Test both:** listing's pg_id (→ found) and a different pg_id (→ not found)

---

### B4 · Search: By bedroom count

```bash
curl -s "$BASE_URL/leasing/search?bedrooms=2"
```

**Expected:** `{"count": N, "listings": "Unit A-101: 2 BHK, ₹15000/month, ..."}`  
**Assertion:** count > 0 if 2-BHK listings exist; all returned listings match bedrooms

---

### B5 · Search: By budget

```bash
curl -s "$BASE_URL/leasing/search?budget_max=12000"
```

**Assertion:** All returned listings have monthly_rent ≤ 12000

---

### B6 · Search: Combined filters

```bash
curl -s "$BASE_URL/leasing/search?bedrooms=2&budget_max=20000"
```

**Assertion:** Returns listings matching both; empty count if none match

---

### B7 · Search: No results

```bash
curl -s "$BASE_URL/leasing/search?bedrooms=10&budget_max=100"
```

**Expected:** `{"count": 0, "listings": "No listings found matching your criteria."}`  
**Assertion:** HTTP 200

---

### B8 · Search: Scoped to property_group_id

```bash
curl -s "$BASE_URL/leasing/search?bedrooms=2&property_group_id=<WRONG_UUID>"
```

**Assertion:** Returns 0 results (cross-group isolation)

---

### B9 · Lease Lead Webhook: Qualified lead with listing match

```bash
curl -s -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "lease-test-001",
        "customer": {"number": "+15551234567"},
        "assistantId": "2dba3a50-6862-400c-861a-bfc0a45d4a95"
      },
      "toolCalls": [{
        "function": {
          "name": "submit_lease_lead",
          "arguments": "{\"caller_name\":\"John Doe\",\"bedrooms\":2,\"budget_max\":18000,\"move_in_timeline\":\"June 2026\",\"occupants\":2,\"qualification_status\":\"qualified\",\"listing_uuid\":\"<LISTING_UUID>\",\"qualifying_answers\":{\"income_verified\":true}}"
        }
      }]
    }
  }'
```

**Expected:** `{"status": "processed"}`  
**Assertion:** `lease_leads` row exists; `property_group_id` matches listing's group; `qualification_status == "qualified"`

---

### B10 · Lease Lead Webhook: Not qualified

Same as B9 but `"qualification_status": "not_qualified"` and add `"disqualifying_reason": "Budget too low"`.

**Assertion:** Lead row has status "not_qualified" and disqualifying_reason populated

---

### B11 · Lease Lead Webhook: Unmatched (no listing, shared assistant)

```bash
curl -s -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "type": "tool-calls",
      "call": {
        "id": "lease-test-003",
        "customer": {"number": "+15559876543"},
        "assistantId": "2dba3a50-6862-400c-861a-bfc0a45d4a95"
      },
      "toolCalls": [{
        "function": {
          "name": "submit_lease_lead",
          "arguments": "{\"caller_name\":\"Jane Smith\",\"bedrooms\":3,\"budget_max\":5000,\"qualification_status\":\"unmatched\"}"
        }
      }]
    }
  }'
```

**Assertion:** Lead row has `property_group_id == null`, `qualification_status == "unmatched"`

---

### B12 · Lease Lead Webhook: No submit_lease_lead tool in payload

```bash
curl -s -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "tool-calls", "toolCalls": []}}'
```

**Expected:** `{"status": "ignored"}`  
**Assertion:** HTTP 200, no DB write

---

## 5. Phase C — Manager CRUD Tests (Authenticated)

All requests require `Authorization: Bearer $JWT`.

### C1 · Create Listing

```bash
# First: get a vacant flat UUID from the DB
FLAT_UUID="<vacant flat uuid>"

curl -s -X POST "$BASE_URL/leasing/listings" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d "{
    \"flat_uuid\": \"$FLAT_UUID\",
    \"monthly_rent\": 15000,
    \"title\": \"Test 2BHK\",
    \"description\": \"Test listing\",
    \"available_from\": \"2026-06-01\",
    \"is_active\": true,
    \"custom_rules\": {
      \"max_occupants\": 2,
      \"income_required\": true,
      \"pets_allowed\": \"no\",
      \"vegetarian_only\": false,
      \"lease_term_months\": 11
    }
  }"
```

**Expected:** 201, full listing object with `uuid` and auto-resolved `property_group_id`  
**Save the UUID:** `export LISTING_UUID=<uuid from response>`

---

### C2 · Get Listings

```bash
curl -s "$BASE_URL/leasing/listings" -H "Authorization: Bearer $JWT"
```

**Assertion:** Array includes the listing created in C1; no listings from other managers' groups

---

### C3 · Update Listing

```bash
curl -s -X PATCH "$BASE_URL/leasing/listings/$LISTING_UUID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"monthly_rent": 16000, "is_active": false}'
```

**Expected:** 200, updated fields reflected  
**Assertion:** `monthly_rent == 16000`, `is_active == false`

---

### C4 · Get Leads (with filter)

```bash
curl -s "$BASE_URL/leasing/leads?qualification_status=qualified" \
  -H "Authorization: Bearer $JWT"
```

**Assertion:** All returned leads have `qualification_status == "qualified"`

---

### C5 · Update Lead Status (manager pipeline)

```bash
LEAD_UUID="<uuid from B9>"
curl -s -X PATCH "$BASE_URL/leasing/leads/$LEAD_UUID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"qualification_status": "contacted", "manager_notes": "Called back, very interested"}'
```

**Expected:** 200, status updated to "contacted"

---

### C6 · Update Lead Status: Blocked (voice-only statuses)

```bash
curl -s -X PATCH "$BASE_URL/leasing/leads/$LEAD_UUID" \
  -H "Authorization: Bearer $JWT" \
  -H "Content-Type: application/json" \
  -d '{"qualification_status": "qualified"}'
```

**Expected:** 400 — "Managers can only set status to: contacted, toured, converted, lost"  
**Assertion:** HTTP 400

---

### C7 · Get Metrics

```bash
curl -s "$BASE_URL/leasing/metrics?days=30" -H "Authorization: Bearer $JWT"
```

**Expected:**
```json
{"total_calls": N, "qualified": N, "not_qualified": N, "unmatched": N,
 "qualification_rate": 69.0, "avg_duration_seconds": 0}
```
**Assertion:** `total_calls` matches count of leads created in Phase B tests

---

### C8 · Export CSV

```bash
curl -s "$BASE_URL/leasing/export" -H "Authorization: Bearer $JWT" -o /tmp/leads_export.csv
head -5 /tmp/leads_export.csv
```

**Assertion:** First line matches expected headers; rows present for Phase B leads

---

### C9 · Delete Lead

```bash
curl -s -X DELETE "$BASE_URL/leasing/leads/$LEAD_UUID" -H "Authorization: Bearer $JWT"
```

**Expected:** 204 No Content  
**Assertion:** Subsequent GET does not include that lead UUID

---

### C10 · Delete Listing

```bash
curl -s -X DELETE "$BASE_URL/leasing/listings/$LISTING_UUID" -H "Authorization: Bearer $JWT"
```

**Expected:** 204  
**Assertion:** Subsequent GET /leasing/listings does not include that UUID

---

### C11 · Unauthenticated Request (security check)

```bash
curl -s "$BASE_URL/leasing/listings"
```

**Expected:** 401 or 403  
**Assertion:** No data returned without JWT

---

## 6. Phase D — Property Group Provisioning Tests

### D1 · Existing groups have not_applicable status

Run directly in Supabase SQL editor:
```sql
SELECT id, name, vapi_provisioning_status
FROM properties_list
WHERE vapi_provisioning_status != 'not_applicable';
```

**Expected:** 0 rows (all existing groups should be 'not_applicable')

---

### D2 · New property group triggers provisioning

Create a new property group via the app UI or API. Then query:
```sql
SELECT id, name, vapi_provisioning_status, vapi_phone_number, vapi_lease_assistant_id
FROM properties_list
ORDER BY created_at DESC LIMIT 1;
```

**Expected after ~10s:** `vapi_provisioning_status = 'active'`, `vapi_phone_number` is a real number, `vapi_lease_assistant_id` is set

---

### D3 · Retry provisioning endpoint

```bash
curl -s -X POST "$BASE_URL/property-groups/<PG_ID>/provision-voice" \
  -H "Authorization: Bearer $JWT"
```

**Expected:** `{"status": "provisioning_started"}` HTTP 202  
**Use when:** A group's status is "failed"

---

## 7. Phase E — Manual Voice Tests

These require actually calling the numbers. Do these after all Phase A–D pass.

### Setup for manual tests
1. Backend must be pointed to production URL in tool configs (already done — tools point to `tenant-management-mvp.onrender.com`)
2. Make sure the DB has at least one tenant with YOUR phone number linked to a flat
3. Make sure at least one listing exists before testing the lease agent

---

### E1 · Complaint Agent — Happy path

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call `+19734904520` | Alex greets you |
| 2 | Say your flat number | Alex asks you to wait |
| 3 | Verification passes | Alex confirms your identity silently, asks about issue |
| 4 | Describe a plumbing leak | Alex captures category as "plumbing" |
| 5 | Request appointment for specific date/time | Alex confirms and submits |
| 6 | Call ends | Check DB: complaint + appointment row created; call_logs status = "created" |

**DB check after call:**
```sql
SELECT * FROM complaints ORDER BY created_at DESC LIMIT 1;
SELECT * FROM appointments ORDER BY created_at DESC LIMIT 1;
SELECT * FROM call_logs ORDER BY id DESC LIMIT 1;
```

---

### E2 · Complaint Agent — Wrong phone number

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call from a number NOT registered to any flat | Alex greets |
| 2 | Give any flat number | Verify-phone returns invalid |
| 3 | Alex says one polite sentence | Call ends immediately, no follow-up |

**Assertion:** No complaint or appointment created; call_log status = "abandoned"

---

### E3 · Complaint Agent — Vacant flat

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call with any phone | Alex greets |
| 2 | Give a flat number with no tenant | Verify-phone returns "vacant" |
| 3 | Alex ends call politely | No DB writes for complaint/appointment |

---

### E4 · Complaint Agent — Emergency

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call as valid tenant | Verify passes |
| 2 | Report gas smell | Alex asks for confirmation |
| 3 | Confirm emergency | Alex does NOT troubleshoot; books appointment |
| 4 | Confirm date | Appointment created |

---

### E5 · Complaint Agent — View/update/cancel appointment

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call as tenant who has an existing appointment | Verify passes |
| 2 | Say "I want to reschedule my appointment" | Alex shows existing appointment details |
| 3 | Provide new date/time | Alex updates |
| 4 | Call again, say "cancel my appointment" | Alex confirms and cancels |

---

### E6 · Complaint Agent — property_group_id propagation

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call as valid tenant | Verify passes; agent extracts property_group_id |
| 2 | File complaint | Check DB: `complaints.property_group_id` is set correctly |

**DB check:**
```sql
SELECT flat_number, property_group_id, created_at 
FROM complaints 
ORDER BY created_at DESC LIMIT 1;
```

---

### E7 · Lease Agent — Find specific listing

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call `+15183189117` | Lease agent greets (no identity check) |
| 2 | Ask about unit "A-101" | Agent calls find_listing, reads back details |
| 3 | Express interest | Agent collects name, contact, preferences |
| 4 | End call | Check DB: lead created with matching listing_uuid |

---

### E8 · Lease Agent — Browse listings

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call lease number | Agent greets |
| 2 | Say "I'm looking for a 2-bedroom under 20,000" | Agent calls search endpoint |
| 3 | Agent reads back options | Pick one |
| 4 | Go through qualification | Lead submitted |

---

### E9 · Lease Agent — Qualified lead

Go through E8 fully with a caller who passes all custom_rules. Check:
```sql
SELECT * FROM lease_leads ORDER BY created_at DESC LIMIT 1;
```
**Assertion:** `qualification_status = 'qualified'`, `property_group_id` is set from listing

---

### E10 · Lease Agent — Not qualified

Give answers that fail qualification (too many occupants, wrong move-in, etc.).  
**Assertion:** `qualification_status = 'not_qualified'`, `disqualifying_reason` populated

---

### E11 · Lease Agent — Unmatched (no listing found)

Describe a property that doesn't exist.  
**Assertion:** Lead row has `property_group_id = null`, `listing_uuid = null`

---

### E12 · Regression — Complaint number doesn't trigger leasing flow

| Check | Method |
|-------|--------|
| No find_listing calls | VAPI dashboard call logs for complaint assistant |
| No search calls | Same |
| Verify_phone_number IS called | Confirmed in VAPI logs |

---

### E13 · Regression — Lease number doesn't trigger complaint flow

| Check | Method |
|-------|--------|
| Verify_phone_number never called | VAPI dashboard call logs for lease assistant |
| No complaint rows created | DB check after lease calls |

---

## 8. Test Execution Checklist

### Automated (run after every backend change)

- [ ] `test_complaint_endpoints.sh` — all A tests pass
- [ ] `test_leasing_endpoints.sh` — all B + C tests pass

### Before merging / deploying

- [ ] Phase A — all 9 complaint endpoint tests pass
- [ ] Phase B — all 12 lease endpoint tests pass
- [ ] Phase C — all 11 manager CRUD tests pass
- [ ] Phase D1 — existing groups are `not_applicable`

### Before calling it shipped

- [ ] E1 — Happy path complaint
- [ ] E2 — Wrong phone rejects immediately
- [ ] E6 — property_group_id in complaint record
- [ ] E7 — Lease agent captures lead
- [ ] E9 — Qualified lead in DB
- [ ] E12 — No cross-contamination (complaint → no lease tools)
- [ ] E13 — No cross-contamination (lease → no verify-phone)

---

## 9. Common Failure Patterns

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `property_group_id` is null on valid verify-phone | Flat not linked to building, or building not linked to properties_list | Fix flat.building_id → buildings.property_id chain |
| find-listing returns `found: false` for known unit | `is_active` is false, or flat FK missing | Set `is_active = true`; verify `flat_uuid` on listing |
| Lease lead has `property_group_id = null` | Listing UUID not passed, assistant_id lookup failed | Pass `listing_uuid` in tool call; check assistant_id matches DB |
| Complaint webhook: `complaint_created: false` | Verify-phone returned invalid first | Ensure tenant phone in DB matches caller's real phone |
| Manager CRUD returns 403 | Subscription inactive or JWT expired | Renew JWT; check subscription status |
| `vapi_provisioning_status` stays `pending` | `PRIVATE_VAPI_API` missing or VAPI API error | Check env var; check VAPI dashboard for errors |
| VAPI dashboard shows call failed | Backend returned non-200 | Check backend logs; VAPI endpoints must always return 200 |
| Complaint sent to wrong property group | property_group_id not passed from verify to submit | Check VAPI call logs; ensure system prompt is loaded correctly |
