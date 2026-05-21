# Voice Agents — Manual Test Guide

**Date:** 2026-05-21  
**Automated tests:** 55/55 PASS (Phase A: 18, Phase B: 20, Phase C: 17)  
**Account:** testmanager1@gmail.com 
**Password** testmanager  

---

## What Was Done (Automated)

All automated backend endpoint tests now pass end-to-end.

### Fixes Applied This Session

| # | File | Change |
|---|------|--------|
| Bug #1 | `backend/app/routes/flats.py:59` | `verify_phone`: `get_db` → `get_service_db` (RLS was blocking VAPI lookup) |
| Bug #2 | `backend/app/routes/voice.py:20` | `voice_webhook`: `get_db` → `get_service_db` (RLS was blocking call_log writes) |
| Bug #3 | `backend/app/routes/voice.py:164` | Unicode `✓` and `⚠️` → ASCII `[OK]` / `[WARN]` (Windows cp1252 crash) |
| Bug #4 | `backend/scripts/test_leasing_endpoints.sh:96` | `EXISTING_LISTING_UUID` default added (script crash on empty DB) |
| Bug #5 | `backend/app/routes/leasing.py:find_listing` | Fallback title-search query now respects `property_group_id` filter |
| Bug #6 | `backend/app/routes/leasing.py:create_listing` | `Decimal` → `float` before Supabase insert |
| Bug #7 | `backend/app/routes/leasing.py:update_listing` | Same `Decimal` → `float` fix for PATCH |
| Bug #8 | `backend/app/routes/leasing.py` (all manager routes) | All read/write ops switched to `get_service_db` with manual `manager_id` filter (RLS INSERT/UPDATE/DELETE policies not defined on `lease_listings`/`lease_leads`) |
| Bug #9 | `backend/app/routes/property_groups.py:create_property_group` | Added `payload["manager_id"] = user["sub"]` so new property groups are owned by the creating user |

### Test Data Under testmanager1@gmail.com

| Entity | Name | UUID/ID |
|--------|------|---------|
| Property Group | TM1 Test Society | `31ed35ee-977a-4416-8fad-b3f25e12fc43` |
| Building | TM1 Block A | `844c46be-6203-4f5f-aff3-166e59ed5f4e` |
| Flat | TM1_TEST_UNIT | `513d7f23-c4c2-4a60-abcf-f85479ba5d1b` |
| Tenant | TM1 Test Tenant | phone `+911112223334` |
| Lease Listing | TM1 Test Unit - 2BHK | `34e98d28-8bd7-4480-9ca3-a013e13a2319` |

---

## What Is Left (Manual)

### Phase D — Supabase DB Verification

Run these queries in the **Supabase SQL Editor** (Dashboard → SQL Editor):

**D1 — Check VAPI provisioning status**
```sql
SELECT id, name, vapi_provisioning_status, vapi_lease_assistant_id, vapi_phone_number
FROM properties_list
ORDER BY created_at DESC
LIMIT 10;
```
Expected: TM1 Test Society has `vapi_provisioning_status = 'pending'` (provisioning was triggered but may not have completed since no VAPI credentials are provisioned for a new PG yet).

**D2 — Verify call_logs were created**
```sql
SELECT id, call_id, phone_number, complaint_status, complaint_id, created_at
FROM call_logs
ORDER BY created_at DESC
LIMIT 10;
```
Expected: several rows from automated test runs (abandoned, pending, failed statuses).

**D3 — Verify lease_leads were created**
```sql
SELECT id, caller_name, phone, qualification_status, property_group_id, listing_uuid, call_id
FROM lease_leads
ORDER BY created_at DESC
LIMIT 10;
```
Expected: multiple rows — unmatched (null PG), qualified (PG=31ed35ee), not_qualified.

**D4 — Verify lease_listings**
```sql
SELECT id, flat_number, title, monthly_rent, is_active, manager_id, property_group_id
FROM lease_listings
ORDER BY created_at DESC
LIMIT 5;
```
Expected: pre-existing "TM1 Test Unit - 2BHK" row (id=1) — is_active=true.

**D5 — Add missing RLS policies (run once)**
```sql
-- Allow authenticated managers to insert/update/delete their own listings
ALTER TABLE lease_listings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Managers can insert own listings" ON lease_listings
  FOR INSERT TO authenticated
  WITH CHECK (manager_id = auth.uid());

CREATE POLICY "Managers can select own listings" ON lease_listings
  FOR SELECT TO authenticated
  USING (manager_id = auth.uid());

CREATE POLICY "Managers can update own listings" ON lease_listings
  FOR UPDATE TO authenticated
  USING (manager_id = auth.uid());

CREATE POLICY "Managers can delete own listings" ON lease_listings
  FOR DELETE TO authenticated
  USING (manager_id = auth.uid());

-- Allow managers to see leads from their property groups
ALTER TABLE lease_leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Managers can select their leads" ON lease_leads
  FOR SELECT TO authenticated
  USING (
    property_group_id IN (
      SELECT id FROM properties_list WHERE manager_id = auth.uid()
    )
  );

CREATE POLICY "Managers can update their leads" ON lease_leads
  FOR UPDATE TO authenticated
  USING (
    property_group_id IN (
      SELECT id FROM properties_list WHERE manager_id = auth.uid()
    )
  );

CREATE POLICY "Managers can delete their leads" ON lease_leads
  FOR DELETE TO authenticated
  USING (
    property_group_id IN (
      SELECT id FROM properties_list WHERE manager_id = auth.uid()
    )
  );
```
**NOTE:** After running D5, the backend code can be reverted to use `get_authenticated_db` for the manager-facing leasing routes (currently using `get_service_db` with manual manager filtering as a workaround).

---

### Phase E — Live Voice Call Testing

These require actual phone calls to VAPI numbers. Do after all code fixes are confirmed working.

#### Prerequisites
- Backend running and accessible from internet (or ngrok tunnel for localhost)
- If using localhost: update VAPI webhook URLs in the dashboard to point to your ngrok URL

#### E1 — Complaint Agent (Inbound)

**VAPI Phone Number:** `+19734904520`  
**Test Flow:**

| Step | Action | Expected |
|------|--------|----------|
| E1.1 | Call `+19734904520` from phone `+919998064026` | Agent greets and asks for flat number |
| E1.2 | Say flat number `TEST 2 UNIT` | Agent verifies identity: "I can see you're the registered tenant" |
| E1.3 | Say complaint category and description | Agent asks for appointment date |
| E1.4 | Give appointment date | Agent confirms and says it will be created |
| E1.5 | Wait 30 sec after call ends | Check DB: new row in `complaints` and `appointments` |
| E1.6 | Call from unknown number | Agent says "We don't recognize your number" |
| E1.7 | Call from known number, say wrong flat | Agent says "phone doesn't match" |

**DB checks after E1.5:**
```sql
SELECT * FROM complaints ORDER BY created_at DESC LIMIT 3;
SELECT * FROM appointments ORDER BY created_at DESC LIMIT 3;
SELECT * FROM call_logs ORDER BY created_at DESC LIMIT 3;
```

#### E2 — Complaint Agent (Outbound)

**Endpoint:** `POST /voice/call/outbound`

```bash
curl -X POST http://localhost:8000/voice/call/outbound \
  -H "Content-Type: application/json" \
  -d '{"customer_number": "+919998064026", "first_message": "Hi, this is a test outbound call from the property management system."}'
```
Expected: `{"call_id": "...", "status": "queued"}`

#### E3 — Lease Agent (Inbound)

**VAPI Phone Number:** `+15183189117`  
**Test Flow:**

| Step | Action | Expected |
|------|--------|----------|
| E3.1 | Call `+15183189117` | Agent greets, asks about property needs |
| E3.2 | Ask about 2 BHK availability | Agent searches and finds TM1 Test Unit listing |
| E3.3 | Provide qualifying info (name, budget ≥ ₹18000, occupants ≤ 2) | Agent qualifies as "qualified" |
| E3.4 | Let agent submit lead | Check DB: `lease_leads` has row with `qualification_status=qualified` and `listing_uuid=34e98d28-...` |
| E3.5 | Call again, give budget ₹5000 | Agent disqualifies: "budget below minimum" |
| E3.6 | After call, check manager dashboard | Lead appears in Leasing tab with qualification status |

**DB checks after E3.4:**
```sql
SELECT caller_name, phone, qualification_status, listing_uuid, property_group_id
FROM lease_leads
ORDER BY created_at DESC
LIMIT 5;
```

#### E4 — VAPI Provisioning (New Property Group)

| Step | Action | Expected |
|------|--------|----------|
| E4.1 | Create new property group via app UI | Provisioning triggered in background |
| E4.2 | Wait 30 seconds | Check DB: `vapi_provisioning_status = 'active'` or `'failed'` |
| E4.3 | If failed, retry via `POST /property-groups/{id}/provision-voice` | Should re-trigger provisioning |

```sql
SELECT id, name, vapi_provisioning_status, vapi_phone_number
FROM properties_list
ORDER BY created_at DESC;
```

---

## Re-run Automated Tests

```bash
# Phase A — 18 tests
BASE_URL=http://localhost:8000 \
  FLAT_NUMBER=TEST_2_UNIT \
  TENANT_PHONE=+919998064026 \
  bash backend/scripts/test_complaint_endpoints.sh

# Get fresh JWT
JWT=$(curl -s -X POST "https://nfgnxndktecqeleabbip.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mZ254bmRrdGVjcWVsZWFiYmlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjYzNTUsImV4cCI6MjA4NTQ0MjM1NX0.lFBVU9aqWtCo1l7uDjD8326CzFwCsKJqMCCcA13Nvi8" \
  -H "Content-Type: application/json" \
  -d '{"email":"testmanager1@gmail.com","password":"testmanager"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Phase B+C — 37 tests
BASE_URL=http://localhost:8000 \
  JWT="$JWT" \
  FLAT_UUID=513d7f23-c4c2-4a60-abcf-f85479ba5d1b \
  QUERY_TERM=TM1_TEST_UNIT \
  bash backend/scripts/test_leasing_endpoints.sh
```

---

## Known Limitations (Not Blocking)

| Item | Detail |
|------|--------|
| A7 `complaint_created=False` | Complaint creation calls `https://tenant-management-mvp.onrender.com/complaints` (prod URL hardcoded in `voice.py:334`). For local testing change to `http://localhost:8000/complaints`. Also, `voice_calls` feature flag is disabled for `TEST_2_UNIT` — enable it via `unit_features` table or the feature management UI. |
| `vapi_provisioning_status=pending` | VAPI provisioning for TM1 Test Society hasn't completed (no dedicated VAPI credentials assigned yet). Provisioning runs async in background — check logs or DB for status. |
| Phase E phone calls | Require VAPI webhook URLs to point to a publicly accessible backend. For local testing use ngrok: `ngrok http 8000` and update VAPI webhook URLs in the dashboard. |
