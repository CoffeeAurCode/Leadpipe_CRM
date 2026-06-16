# API Test Plan — Full Feature Coverage
**Date:** 2026-06-04  
**Account:** Leadpipe (`leadpipecrm@gmail.com`, `manager_id: 28c43c77-8c9c-496f-8d1e-39ffa9d619e3`)  
**L03 status:** ON HOLD (VAPI balance -0.38 — skip all voice agent calls for now)

---

## Setup

```bash
BASE="https://tenant-management-mvp.onrender.com"
TOKEN="eyJhbGciOiJFUzI1NiIsImtpZCI6IjE3ODIzMTZkLTllY2MtNDgxZC1iNDc2LTk2NzA3M2JlM2Q4OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL25mZ254bmRrdGVjcWVsZWFiYmlwLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyOGM0M2M3Ny04YzljLTQ5NmYtOGQxZS0zOWZmYTlkNjE5ZTMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgwNTcxMjU3LCJpYXQiOjE3ODA1Njc2NTcsImVtYWlsIjoibGVhZHBpcGVjcm1AZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJnb29nbGUiLCJwcm92aWRlcnMiOlsiZ29vZ2xlIl19LCJ1c2VyX21ldGFkYXRhIjp7ImF2YXRhcl91cmwiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKS0I4OVRNMVQyR1hKc1FoU2RfQi13MXozOXl2dFZTOTQyaXFQQTcwTmpXR0tNNlE9czk2LWMiLCJlbWFpbCI6ImxlYWRwaXBlY3JtQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJMZWFkcGlwZSIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJMZWFkcGlwZSIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0pLQjg5VE0xVDJHWEpzUWhTZF9CLXcxejM5eXZ0VlM5NDJpcVBBNzBOaldHS002UT1zOTYtYyIsInByb3ZpZGVyX2lkIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIiwic3ViIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib2F1dGgiLCJ0aW1lc3RhbXAiOjE3ODA0MjI2OTR9XSwic2Vzc2lvbl9pZCI6ImY5MTVmNzAzLTJjZmEtNDFjNS1hODYzLTQ2ZDI5M2Y1N2M4YyIsImlzX2Fub255bW91cyI6ZmFsc2V9.myyUmeXEewMutyBmiIvXvL-cDNaTRxIlS1TeibkfAzS6bE-s7D7ktD6nTSaEFa2iOPpU3KFFVjB68MzqDVwhvA"
AUTH="Authorization: Bearer $TOKEN"
CT="Content-Type: application/json"
```

> **Note on JWT expiry:** This token expires at `1780571257` (Unix). If you get HTTP 401 errors, log in again via the app and copy a fresh token from the browser DevTools → Network → any authenticated request → Authorization header.

---

## Test Execution Order

Run sections in this order — each section may create data that later sections reference.

1. Auth / subscription check
2. Property Groups
3. Buildings
4. Flats
5. Tenants
6. Complaints
7. Appointments
8. Rents
9. Leasing (Listings → Leads)
10. Voice / Call Logs
11. Settings
12. Chatbot
13. Notifications
14. Payments
15. VAPI tool endpoints (no auth required)

---

## Section 1 — Auth & Subscription Gate

### T01 — Subscription status
```bash
curl -s "$BASE/payments/subscription-status" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"status": "trialing"}` or `{"status": "active"}`. If `expired` or `cancelled`, the rest of the authenticated tests will 403.

### T02 — No token → 401
```bash
curl -s "$BASE/complaints" | python -m json.tool
```
**Expected:** HTTP 401 / `"Not authenticated"`.

### T03 — Expired / garbage token → 401
```bash
curl -s "$BASE/complaints" -H "Authorization: Bearer garbage.token.here" | python -m json.tool
```
**Expected:** HTTP 401.

### T04 — Token with no subscription → 403 (edge case)
This is hard to test without a separate account. Document: if subscription is not active/trialing, any `require_active_subscription` route returns HTTP 403 and the frontend redirects to `/pricing`.

---

## Section 2 — Property Groups

### P01 — List property groups (GET /property-groups)
```bash
curl -s "$BASE/property-groups" -H "$AUTH" | python -m json.tool
```
**Expected:** JSON array. Note one of the group IDs — call it `PG_ID`.

### P02 — Create property group (POST /property-groups)
```bash
curl -s -X POST "$BASE/property-groups" -H "$AUTH" -H "$CT" \
  -d '{"name":"API Test Group","description":"Created by test","street_address":"123 Test St","city":"Montreal","state":"QC","country":"Canada"}' \
  | python -m json.tool
```
**Expected:** 201 or 200, group object returned with `id`. Save this as `TEST_PG_ID`.
**Side effect:** If this is the manager's FIRST group, VAPI provisioning fires as a background task. Since Leadpipe already has an active config, provisioning is skipped (guard clause).

### P03 — Create group — missing required city/state → 422
```bash
curl -s -X POST "$BASE/property-groups" -H "$AUTH" -H "$CT" \
  -d '{"name":"Incomplete Group"}' | python -m json.tool
```
**Expected:** HTTP 422 (Pydantic validation error — street_address, city, state required for new creates).

### P04 — VAPI config for manager (GET /property-groups/users/me/vapi-config)
```bash
curl -s "$BASE/property-groups/users/me/vapi-config" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"vapi_provisioning_status":"active","vapi_phone_number":"+14313404212"}` (Leadpipe's assigned number).

### P05 — Buildings under a property group (GET /property-groups/:id/buildings)
```bash
curl -s "$BASE/property-groups/$PG_ID/buildings" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of buildings with unit counts.

### P06 — Delete the test group (DELETE /property-groups/:id)
```bash
curl -s -X DELETE "$BASE/property-groups/$TEST_PG_ID" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"deleted": true}` or 204. Cascade deletes all buildings/flats/tenants/leases within.

### P07 — Bulk delete property groups (DELETE /property-groups/bulk)
```bash
# Create two throwaway groups first, then delete both
curl -s -X POST "$BASE/property-groups" -H "$AUTH" -H "$CT" \
  -d '{"name":"Bulk A","street_address":"1 A St","city":"Montreal","state":"QC","country":"Canada"}' | python -m json.tool

curl -s -X POST "$BASE/property-groups" -H "$AUTH" -H "$CT" \
  -d '{"name":"Bulk B","street_address":"2 B St","city":"Montreal","state":"QC","country":"Canada"}' | python -m json.tool

# Then bulk delete using the returned IDs:
curl -s -X DELETE "$BASE/property-groups/bulk" -H "$AUTH" -H "$CT" \
  -d '{"ids":["<BULK_A_ID>","<BULK_B_ID>"]}' | python -m json.tool
```
**Expected:** `{"deleted":2,"errors":[]}`.

---

## Section 3 — Buildings

> Uses `PG_ID` from Section 2.

### B01 — List buildings (GET /buildings)
```bash
curl -s "$BASE/buildings" -H "$AUTH" | python -m json.tool
```
**Expected:** Array with `unit_count` per building.

### B02 — Get single building (GET /buildings/:id)
```bash
# Replace BUILDING_ID with a real ID from B01
curl -s "$BASE/buildings/$BUILDING_ID" -H "$AUTH" | python -m json.tool
```
**Expected:** Building object.

### B03 — Create building (POST /buildings)
```bash
curl -s -X POST "$BASE/buildings" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Test Building Alpha\",\"property_id\":\"$PG_ID\",\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}" \
  | python -m json.tool
```
**Expected:** Building object with `id`. Save as `TEST_BLD_ID`.

### B04 — Create building — duplicate name in same group
```bash
curl -s -X POST "$BASE/buildings" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Test Building Alpha\",\"property_id\":\"$PG_ID\",\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}" \
  | python -m json.tool
```
**Expected:** Supabase unique constraint error → HTTP 400 with plain-English message (via `clean_db_error`).

### B05 — Update building (PATCH /buildings/:id)
```bash
curl -s -X PATCH "$BASE/buildings/$TEST_BLD_ID" -H "$AUTH" -H "$CT" \
  -d '{"name":"Test Building Alpha (Updated)","description":"Updated via API test"}' \
  | python -m json.tool
```
**Expected:** Updated building object.

### B06 — Bulk delete buildings (DELETE /buildings/bulk)
```bash
curl -s -X DELETE "$BASE/buildings/bulk" -H "$AUTH" -H "$CT" \
  -d "{\"ids\":[\"$TEST_BLD_ID\"]}" | python -m json.tool
```
**Expected:** `{"deleted":1,"errors":[]}`. Cascade: all flats inside are deleted.

### B07 — Delete non-existent building → clean error
```bash
curl -s -X DELETE "$BASE/buildings/00000000-0000-0000-0000-000000000000" -H "$AUTH" | python -m json.tool
```
**Expected:** HTTP 404 or `{"errors":["not found"]}`.

---

## Section 4 — Flats

> Create a fresh building first (`TEST_BLD_ID`). You can re-create it after the bulk delete in B06.

```bash
# Re-create test building
BUILDING_RESP=$(curl -s -X POST "$BASE/buildings" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Flat Test Block\",\"property_id\":\"$PG_ID\",\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}")
TEST_BLD_ID=$(echo $BUILDING_RESP | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
```

### F01 — List all flats (GET /flats)
```bash
curl -s "$BASE/flats" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of flats. Check each has `uuid`, `flat_number`, `occupied`, `bedrooms`, `bathrooms`.

### F02 — List vacant flats only (GET /flats?vacant=true)
```bash
curl -s "$BASE/flats?vacant=true" -H "$AUTH" | python -m json.tool
```
**Expected:** Only flats where `occupied=false` / `tenant_uuid=null`.

### F03 — Create flat (POST /flats)
```bash
FLAT_RESP=$(curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"flat_number\":\"APITEST-01\",\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":2,\"bathrooms\":1,\"floor_number\":3,\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}")
echo $FLAT_RESP | python -m json.tool
TEST_FLAT_UUID=$(echo $FLAT_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```
**Expected:** Flat object with `uuid`. `flat_number` stored as UPPER.

### F04 — Create flat — duplicate flat number → 400
```bash
curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"flat_number\":\"APITEST-01\",\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":1,\"bathrooms\":1,\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400, plain-English message containing "already exists".

### F05 — Create flat — missing required flat_number → 422
```bash
curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":1,\"bathrooms\":1}" \
  | python -m json.tool
```
**Expected:** HTTP 422 validation error.

### F06 — Get flat details (GET /flats/:uuid/details)
```bash
curl -s "$BASE/flats/$TEST_FLAT_UUID/details" -H "$AUTH" | python -m json.tool
```
**Expected:** Flat object with tenant details (null since unoccupied).

### F07 — Get flat by flat_number (GET /flats/:flat_number)
```bash
curl -s "$BASE/flats/APITEST-01" -H "$AUTH" | python -m json.tool
```
**Expected:** Same flat object.

### F08 — Update flat (PATCH /flats/:uuid)
```bash
curl -s -X PATCH "$BASE/flats/$TEST_FLAT_UUID" -H "$AUTH" -H "$CT" \
  -d '{"bedrooms":3,"bathrooms":2,"floor_number":5}' | python -m json.tool
```
**Expected:** Updated flat object.

### F09 — Create a second flat for bulk delete test
```bash
FLAT2_RESP=$(curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"flat_number\":\"APITEST-02\",\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":1,\"bathrooms\":1,\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}")
TEST_FLAT2_UUID=$(echo $FLAT2_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```

### F10 — Bulk delete flats (DELETE /flats/bulk)
```bash
curl -s -X DELETE "$BASE/flats/bulk" -H "$AUTH" -H "$CT" \
  -d "{\"uuids\":[\"$TEST_FLAT2_UUID\"]}" | python -m json.tool
```
**Expected:** `{"deleted":1,"errors":[]}`.

### F11 — Delete single flat (DELETE /flats/:uuid) — flat with no tenant
```bash
# First re-create APITEST-02 to have something to delete
curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"flat_number\":\"APITEST-02\",\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":1,\"bathrooms\":1,\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}" \
  | python -m json.tool
```
```bash
curl -s -X DELETE "$BASE/flats/$TEST_FLAT2_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"deleted":true}`.

---

## Section 5 — Tenants

> Requires `TEST_FLAT_UUID` (APITEST-01, currently vacant) from Section 4.

### TN01 — Create tenant (POST /tenants)
```bash
TENANT_RESP=$(curl -s -X POST "$BASE/tenants" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Test Tenant API\",\"phone\":\"+15145559999\",\"email\":\"test@example.com\",\"flat_uuid\":\"$TEST_FLAT_UUID\",\"lease_start_date\":\"2026-01-01\",\"lease_end_date\":\"2026-12-31\",\"rent_status\":\"On-time\",\"payment_schedule\":\"monthly\"}")
echo $TENANT_RESP | python -m json.tool
TEST_TENANT_UUID=$(echo $TENANT_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```
**Expected:** Tenant object with UUID, computed `tenancy_duration_months`, `lease_status`.

### TN02 — Duplicate phone → 400
```bash
curl -s -X POST "$BASE/tenants" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Dupe Phone\",\"phone\":\"+15145559999\",\"flat_uuid\":\"$TEST_FLAT_UUID\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400 — phone already in use.

### TN03 — Create tenant on occupied flat → 400
```bash
# Create a second vacant flat first
FLAT3_RESP=$(curl -s -X POST "$BASE/flats" -H "$AUTH" -H "$CT" \
  -d "{\"flat_number\":\"APITEST-03\",\"building_id\":\"$TEST_BLD_ID\",\"bedrooms\":1,\"bathrooms\":1,\"city\":\"Montreal\",\"state\":\"QC\",\"country\":\"Canada\"}")
TEST_FLAT3_UUID=$(echo $FLAT3_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")

# Try to assign ANOTHER tenant to APITEST-01 (already occupied)
curl -s -X POST "$BASE/tenants" -H "$AUTH" -H "$CT" \
  -d "{\"name\":\"Another Person\",\"phone\":\"+15145550099\",\"flat_uuid\":\"$TEST_FLAT_UUID\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400 — flat already occupied.

### TN04 — List tenants (GET /tenants)
```bash
curl -s "$BASE/tenants" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of all tenants. Each has computed `lease_status`, `tenancy_duration_months`, `remaining_time_on_lease_days`.

### TN05 — List tenants filtered by flat (GET /tenants?flat_uuid=)
```bash
curl -s "$BASE/tenants?flat_uuid=$TEST_FLAT_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** Only the tenant in APITEST-01.

### TN06 — Get single tenant (GET /tenants/:uuid)
```bash
curl -s "$BASE/tenants/$TEST_TENANT_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** Full tenant object with all computed fields.

### TN07 — Get tenant by flat number (GET /tenants/by-flat/:flat_no)
```bash
curl -s "$BASE/tenants/by-flat/APITEST-01" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"exists":true,"flat_no":"APITEST-01","tenant_name":"Test Tenant API","tenant_phone":"+15145559999"}`.

### TN08 — Get tenant for vacant flat (GET /tenants/by-flat/:flat_no)
```bash
curl -s "$BASE/tenants/by-flat/APITEST-03" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"exists":false}` (vacant flat).

### TN09 — Get tenant for nonexistent flat (GET /tenants/by-flat/:flat_no)
```bash
curl -s "$BASE/tenants/by-flat/DOESNOTEXIST" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"exists":false}`.

### TN10 — Update tenant (PATCH /tenants/:uuid)
```bash
curl -s -X PATCH "$BASE/tenants/$TEST_TENANT_UUID" -H "$AUTH" -H "$CT" \
  -d '{"manager_notes":"Updated via API test","rent_status":"Upcoming"}' | python -m json.tool
```
**Expected:** Updated tenant object. `rent_status = "Upcoming"`.

### TN11 — Update tenant rent status via dedicated endpoint (PATCH /tenants/:uuid/rent-status)
```bash
curl -s -X PATCH "$BASE/tenants/$TEST_TENANT_UUID/rent-status" -H "$AUTH" -H "$CT" \
  -d '{"rent_status":"Overdue"}' | python -m json.tool
```
**Expected:** `{"rent_status":"Overdue"}` or updated tenant.

### TN12 — Unassign tenant from flat (PATCH /flats/:uuid/unassign-tenant)
```bash
curl -s -X PATCH "$BASE/flats/$TEST_FLAT_UUID/unassign-tenant" -H "$AUTH" -H "$CT" \
  -d '{}' | python -m json.tool
```
**Expected:** Success. Flat is now vacant. Tenant still exists in DB but `flat_uuid` is null.

### TN13 — Assign existing tenant to flat (PATCH /flats/:uuid/assign-tenant)
```bash
curl -s -X PATCH "$BASE/flats/$TEST_FLAT_UUID/assign-tenant" -H "$AUTH" -H "$CT" \
  -d "{\"tenant_uuid\":\"$TEST_TENANT_UUID\"}" | python -m json.tool
```
**Expected:** Flat becomes occupied again. `flat.tenant_uuid = TEST_TENANT_UUID`.

### TN14 — Delete tenant (DELETE /tenants/:uuid)
```bash
# Note: deleting a tenant does NOT cascade-delete the flat
curl -s -X DELETE "$BASE/tenants/$TEST_TENANT_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"deleted":true}`. Flat reverts to vacant.

---

## Section 6 — Complaints

> We need a tenant in a flat. Re-use APITEST-01 or a real flat from the seeded data.
> Use a seeded flat like T101 (Oak Residences) to avoid dependencies. Look up its UUID first:

```bash
# Find T101 UUID
curl -s "$BASE/flats/T101" -H "$AUTH" | python -m json.tool
# Save the uuid as REAL_FLAT_UUID
```

### CM01 — Create complaint (POST /complaints)
```bash
CMPL_RESP=$(curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"water\",\"priority\":\"high\",\"description\":\"Kitchen faucet dripping\",\"status\":\"pending\",\"source\":\"web\"}")
echo $CMPL_RESP | python -m json.tool
TEST_CMPL_UUID=$(echo $CMPL_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```
**Expected:** Complaint object with UUID.

### CM02 — Create complaint with appointment
```bash
curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"electricity\",\"priority\":\"medium\",\"description\":\"Lights flickering in bedroom\",\"status\":\"pending\",\"source\":\"web\",\"appointment_date\":\"2026-08-01T10:00:00\"}" \
  | python -m json.tool
```
**Expected:** Complaint + appointment both created. Appointment should appear in `/appointments`.

### CM03 — Create complaint — invalid category → 400
```bash
curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"flooding\",\"priority\":\"high\",\"description\":\"Category does not exist\",\"status\":\"pending\",\"source\":\"web\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400 — DB CHECK constraint violation on `category`, cleaned to plain English by `clean_db_error`.

### CM04 — Create complaint — invalid status → 400
```bash
curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"noise\",\"priority\":\"low\",\"description\":\"Test\",\"status\":\"fake-status\",\"source\":\"web\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400 — status CHECK constraint violation.

### CM05 — All valid categories (loop test)
```bash
for CAT in water electricity cleaning noise maintenance security other; do
  echo "--- $CAT ---"
  curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
    -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"$CAT\",\"priority\":\"low\",\"description\":\"Testing category $CAT\",\"status\":\"pending\",\"source\":\"web\"}" \
    | python -c "import sys,json; d=json.load(sys.stdin); print('OK uuid='+d.get('uuid','?'))"
done
```
**Expected:** All 7 succeed, each prints an OK uuid.

### CM06 — List complaints (GET /complaints)
```bash
curl -s "$BASE/complaints" -H "$AUTH" | python -m json.tool
```
**Expected:** Array, newest first, each has joined appointment data.

### CM07 — Get single complaint (GET /complaints/:id)
```bash
curl -s "$BASE/complaints/$TEST_CMPL_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** Full complaint object.

### CM08 — Update complaint status (PATCH /complaints/:id)
```bash
curl -s -X PATCH "$BASE/complaints/$TEST_CMPL_UUID" -H "$AUTH" -H "$CT" \
  -d '{"status":"in-progress","priority":"medium"}' | python -m json.tool
```
**Expected:** Updated complaint. `status = "in-progress"`.

### CM09 — Update to resolved (PATCH /complaints/:id)
```bash
curl -s -X PATCH "$BASE/complaints/$TEST_CMPL_UUID" -H "$AUTH" -H "$CT" \
  -d '{"status":"resolved"}' | python -m json.tool
```
**Expected:** `status = "resolved"`.

### CM10 — Delete complaint (DELETE /complaints/:id)
```bash
curl -s -X DELETE "$BASE/complaints/$TEST_CMPL_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"deleted":true}`.

### CM11 — Delete nonexistent complaint → 404
```bash
curl -s -X DELETE "$BASE/complaints/00000000-0000-0000-0000-000000000000" -H "$AUTH" | python -m json.tool
```
**Expected:** HTTP 404 or clean error.

---

## Section 7 — Appointments

> Create a fresh complaint to attach appointments to.

```bash
CMPL2_RESP=$(curl -s -X POST "$BASE/complaints" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"flat_number\":\"T101\",\"category\":\"maintenance\",\"priority\":\"low\",\"description\":\"Appointment test complaint\",\"status\":\"pending\",\"source\":\"web\"}")
CMPL2_UUID=$(echo $CMPL2_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```

### AP01 — Create appointment (POST /appointments)
```bash
APPT_RESP=$(curl -s -X POST "$BASE/appointments" -H "$AUTH" -H "$CT" \
  -d "{\"complaint_uuid\":\"$CMPL2_UUID\",\"flat_number\":\"T101\",\"flat_uuid\":\"$REAL_FLAT_UUID\",\"appointment_date\":\"2026-09-10T14:00:00\",\"status\":\"scheduled\",\"type\":\"callback\",\"tenant_phone\":\"+15145550011\"}")
echo $APPT_RESP | python -m json.tool
TEST_APPT_ID=$(echo $APPT_RESP | python -c "import sys,json; print(json.load(sys.stdin)['id'])")
TEST_APPT_UUID=$(echo $APPT_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```
**Expected:** Appointment object with `id` and `uuid`.

### AP02 — Create appointment — invalid status → 400
```bash
curl -s -X POST "$BASE/appointments" -H "$AUTH" -H "$CT" \
  -d "{\"complaint_uuid\":\"$CMPL2_UUID\",\"flat_number\":\"T101\",\"flat_uuid\":\"$REAL_FLAT_UUID\",\"appointment_date\":\"2026-09-11T10:00:00\",\"status\":\"invalid-status\"}" \
  | python -m json.tool
```
**Expected:** HTTP 400 (DB status CHECK).

### AP03 — List appointments (GET /appointments)
```bash
curl -s "$BASE/appointments" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of all appointments.

### AP04 — List with date filter (GET /appointments?start_date=&end_date=)
```bash
curl -s "$BASE/appointments?start_date=2026-09-01&end_date=2026-09-30" -H "$AUTH" | python -m json.tool
```
**Expected:** Only September 2026 appointments.

### AP05 — List with flat_number filter (GET /appointments?flat_number=)
```bash
curl -s "$BASE/appointments?flat_number=T101" -H "$AUTH" | python -m json.tool
```
**Expected:** Only T101 appointments.

### AP06 — Get single appointment (GET /appointments/:id)
```bash
curl -s "$BASE/appointments/$TEST_APPT_ID" -H "$AUTH" | python -m json.tool
```
**Expected:** Full appointment object.

### AP07 — Update appointment (PATCH /appointments/:id)
```bash
curl -s -X PATCH "$BASE/appointments/$TEST_APPT_ID" -H "$AUTH" -H "$CT" \
  -d '{"status":"attended","notes":"Manager called, issue resolved"}' | python -m json.tool
```
**Expected:** `status = "attended"`.

### AP08 — Check availability — available slot (GET /appointments/availability)
```bash
curl -s "$BASE/appointments/availability?appointment_date=2026-10-01T10:00:00" | python -m json.tool
```
**Expected:** `{"status":"available"}`. (No auth needed — VAPI tool endpoint.)

### AP09 — Check availability — within ±1hr of existing appointment → unavailable
```bash
# The seeded blocker is 2026-07-15T14:00:00
# 13:30 is within 1hr window → unavailable
curl -s "$BASE/appointments/availability?appointment_date=2026-07-15T13:30:00" | python -m json.tool
```
**Expected:** `{"status":"unavailable"}`.

### AP10 — Check availability — back-to-back exact boundary (should be available)
```bash
# 13:00 is exactly 1hr before 14:00 → boundary is exclusive → available
curl -s "$BASE/appointments/availability?appointment_date=2026-07-15T13:00:00" | python -m json.tool
```
**Expected:** `{"status":"available"}` (slot boundary is non-inclusive: `A - 1hr < T < A + 1hr`).

### AP11 — VAPI view appointments tool (GET /appointments/view?flat_number=)
```bash
curl -s "$BASE/appointments/view?flat_number=T202" | python -m json.tool
```
**Expected:** Array of scheduled appointments for T202 (seeded: 2026-07-10T10:00:00). No auth needed.

### AP12 — VAPI view — flat with no appointments
```bash
curl -s "$BASE/appointments/view?flat_number=T101" | python -m json.tool
```
**Expected:** Empty array `[]`.

### AP13 — VAPI reschedule tool (PATCH /appointments/update)
```bash
# Find T202's appointment ID from AP11
curl -s "$BASE/appointments/update?flat_number=T202&id=<T202_APPT_ID>&new_appointment_date=2026-07-25T11:00:00" \
  -X PATCH | python -m json.tool
```
**Expected:** `{"status":"success","appointment_date":"2026-07-25T11:00:00"}`.

### AP14 — VAPI cancel tool (PATCH /appointments/cancel)
```bash
curl -s -X PATCH "$BASE/appointments/cancel?flat_number=T202&id=<T202_APPT_ID>" | python -m json.tool
```
**Expected:** `{"status":"cancelled"}`.

### AP15 — VAPI cancel — already cancelled (idempotent)
```bash
# Call cancel again on the same appointment
curl -s -X PATCH "$BASE/appointments/cancel?flat_number=T202&id=<T202_APPT_ID>" | python -m json.tool
```
**Expected:** `{"status":"cancelled"}` (idempotent — no error).

### AP16 — Delete appointment (DELETE /appointments/:id)
```bash
curl -s -X DELETE "$BASE/appointments/$TEST_APPT_ID" -H "$AUTH" | python -m json.tool
```
**Expected:** Soft-delete via status change (status = `cancelled`).

---

## Section 8 — Rents

### R01 — Set rent for a flat (POST /rents/set)
```bash
curl -s -X POST "$BASE/rents/set" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"monthly_rent\":1500,\"effective_from\":\"2026-01-01\"}" \
  | python -m json.tool
```
**Expected:** New active rent record. Previous rent (if any) deactivated.

### R02 — Update rent (POST /rents/set again — same flat, new amount)
```bash
curl -s -X POST "$BASE/rents/set" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$REAL_FLAT_UUID\",\"monthly_rent\":1600,\"effective_from\":\"2026-07-01\"}" \
  | python -m json.tool
```
**Expected:** Old record `is_active=false`, new record `is_active=true` with $1,600.

### R03 — Rent summary (GET /rents/summary)
```bash
curl -s "$BASE/rents/summary" -H "$AUTH" | python -m json.tool
```
**Expected:** All tenants with active rent; includes flat info and rent_status counts.

### R04 — Tenant rent-status update (PATCH /tenants/:uuid/rent-status)
```bash
# Re-create tenant on APITEST-01 for this test if needed
curl -s -X PATCH "$BASE/tenants/$TEST_TENANT_UUID/rent-status" -H "$AUTH" -H "$CT" \
  -d '{"rent_status":"At Risk"}' | python -m json.tool
```
**Expected:** `{"rent_status":"At Risk"}`.

### R05 — Invalid rent_status value → 422 / 400
```bash
curl -s -X PATCH "$BASE/tenants/$TEST_TENANT_UUID/rent-status" -H "$AUTH" -H "$CT" \
  -d '{"rent_status":"Banana"}' | python -m json.tool
```
**Expected:** HTTP 422 (Pydantic) or HTTP 400 (DB constraint). Should not update to invalid value.

---

## Section 9 — Leasing (Listings + Leads)

### L_LIST01 — List listings (GET /leasing/listings)
```bash
curl -s "$BASE/leasing/listings" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of listings for this manager, newest first.

### L_LIST02 — Create listing (POST /leasing/listings)
```bash
# Use a vacant flat UUID — APITEST-01 or any seeded Maple Tower unit
LISTING_RESP=$(curl -s -X POST "$BASE/leasing/listings" -H "$AUTH" -H "$CT" \
  -d "{\"flat_uuid\":\"$TEST_FLAT_UUID\",\"title\":\"Cozy 2BR API Test\",\"monthly_rent\":1750,\"description\":\"Test listing created via API\",\"available_from\":\"2026-07-01\",\"is_active\":true,\"custom_rules\":{\"max_occupants\":3,\"pets_allowed\":\"yes\",\"vegetarian_only\":false,\"lease_term_months\":12}}")
echo $LISTING_RESP | python -m json.tool
TEST_LISTING_UUID=$(echo $LISTING_RESP | python -c "import sys,json; print(json.load(sys.stdin)['uuid'])")
```
**Expected:** Listing object with UUID, `property_group_id` auto-resolved from flat.

### L_LIST03 — Create listing — FK violation (flat does not exist) → 400
```bash
curl -s -X POST "$BASE/leasing/listings" -H "$AUTH" -H "$CT" \
  -d '{"flat_uuid":"00000000-0000-0000-0000-000000000000","title":"Ghost Listing","monthly_rent":1000,"available_from":"2026-07-01","is_active":true}' \
  | python -m json.tool
```
**Expected:** HTTP 400 — FK violation (clean_db_error: "flat does not exist").

### L_LIST04 — Update listing (PATCH /leasing/listings/:uuid)
```bash
curl -s -X PATCH "$BASE/leasing/listings/$TEST_LISTING_UUID" -H "$AUTH" -H "$CT" \
  -d '{"monthly_rent":1800,"title":"Updated Cozy 2BR","is_active":false}' \
  | python -m json.tool
```
**Expected:** Updated listing, `is_active=false`.

### L_LIST05 — VAPI search listings tool (GET /leasing/search)
```bash
# Filters: 2-bed, budget $1,800, manager_id scoped
curl -s "$BASE/leasing/search?bedrooms=2&budget_max=1800&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3" | python -m json.tool
```
**Expected:** Array of up to 5 matching active listings, all bedrooms=2, rent≤$1,800. No auth needed.

### L_LIST06 — VAPI search — empty string params (VAPI sends "" when not confirmed)
```bash
curl -s "$BASE/leasing/search?bedrooms=&budget_max=&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3" | python -m json.tool
```
**Expected:** Returns listings (no bedroom/budget filter applied — `""` treated as no filter). Must NOT return HTTP 422.

### L_LIST07 — VAPI search — budget=0 (treated as no filter)
```bash
curl -s "$BASE/leasing/search?bedrooms=0&budget_max=0&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3" | python -m json.tool
```
**Expected:** All active listings (up to 5 cheapest).

### L_LIST08 — VAPI find-listing tool (GET /leasing/find-listing)
```bash
curl -s "$BASE/leasing/find-listing?query=T2B01&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3" | python -m json.tool
```
**Expected:** `{"found":true,"listing_uuid":"...","bedrooms":2,"monthly_rent":1700,...}`.

### L_LIST09 — Find listing — not found
```bash
curl -s "$BASE/leasing/find-listing?query=ZZZNOTEXIST&manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3" | python -m json.tool
```
**Expected:** `{"found":false}`.

### L_LIST10 — Leasing metrics (GET /leasing/metrics)
```bash
curl -s "$BASE/leasing/metrics?days=30" -H "$AUTH" | python -m json.tool
```
**Expected:** `{total, qualified, not_qualified, unmatched, rate, avg_duration}`.

### L_LEADS01 — List leads (GET /leasing/leads)
```bash
curl -s "$BASE/leasing/leads" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of leads scoped to this manager's property groups.

### L_LEADS02 — Filter leads by listing (GET /leasing/leads?listing_uuid=)
```bash
curl -s "$BASE/leasing/leads?listing_uuid=$TEST_LISTING_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** Only leads where `listing_uuid` matches OR `TEST_LISTING_UUID` appears in `interested_listing_ids`.

### L_LEADS03 — Filter leads by qualification status
```bash
curl -s "$BASE/leasing/leads?qualification_status=qualified" -H "$AUTH" | python -m json.tool
```
**Expected:** Only qualified leads.

### L_LEADS04 — Update lead status (PATCH /leasing/leads/:uuid)
```bash
# Get a lead UUID from L_LEADS01
curl -s -X PATCH "$BASE/leasing/leads/$LEAD_UUID" -H "$AUTH" -H "$CT" \
  -d '{"qualification_status":"contacted","manager_notes":"Called on 2026-06-05"}' \
  | python -m json.tool
```
**Expected:** Lead updated with `contacted` status and manager notes.

### L_LEADS05 — Update lead — invalid status → 400/422
```bash
curl -s -X PATCH "$BASE/leasing/leads/$LEAD_UUID" -H "$AUTH" -H "$CT" \
  -d '{"qualification_status":"banana"}' | python -m json.tool
```
**Expected:** HTTP 400 or 422 — only `contacted/toured/converted/lost` allowed for manager updates.

### L_LEADS06 — Export leads CSV (GET /leasing/export)
```bash
curl -s "$BASE/leasing/export" -H "$AUTH" -o leads_export.csv
head -5 leads_export.csv
```
**Expected:** CSV file downloaded. First line is header row.

### L_LIST11 — Delete listing (DELETE /leasing/listings/:uuid)
```bash
curl -s -X DELETE "$BASE/leasing/listings/$TEST_LISTING_UUID" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"deleted":true}`.

---

## Section 10 — Voice / Call Logs

### V01 — Agent info (GET /voice/agent-info)
```bash
curl -s "$BASE/voice/agent-info" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"complaint_phone_number":"+14382314283"}`.

### V02 — Call status (GET /voice/call-status)
```bash
curl -s "$BASE/voice/call-status" -H "$AUTH" | python -m json.tool
```
**Expected:** `{"last_call_ended_at":"..."}` or null.

### V03 — List call logs (GET /call-logs)
```bash
curl -s "$BASE/call-logs" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of call log objects (may be empty if no VAPI calls yet).

### V04 — Filter call logs by phone (GET /call-logs?phone=)
```bash
curl -s "$BASE/call-logs?phone=%2B15145550011" -H "$AUTH" | python -m json.tool
```
**Expected:** Logs for +15145550011 only.

### V05 — Filter call logs by complaint_status (GET /call-logs?complaint_status=)
```bash
curl -s "$BASE/call-logs?complaint_status=created" -H "$AUTH" | python -m json.tool
```
**Expected:** Only logs where `complaint_status = "created"`.

### V06 — Outbound call — missing customer_number → 422
```bash
curl -s -X POST "$BASE/voice/call/outbound" -H "$AUTH" -H "$CT" \
  -d '{"agent":"complaint"}' | python -m json.tool
```
**Expected:** HTTP 422 (Pydantic: `customer_number` is required).

### V07 — Outbound call — invalid agent type
```bash
curl -s -X POST "$BASE/voice/call/outbound" -H "$AUTH" -H "$CT" \
  -d '{"customer_number":"+15145550011","agent":"ghost"}' | python -m json.tool
```
**Expected:** HTTP 500 or 400 — "ghost" is not a valid agent type (no assistant config found).

> **Note:** Skip V08 (actual outbound call) if VAPI wallet is negative.

---

## Section 11 — Settings

### S01 — Get settings (GET /settings)
```bash
curl -s "$BASE/settings" -H "$AUTH" | python -m json.tool
```
**Expected:** `{name, email, phone, appointment_sms_enabled, appointment_email_enabled}`.

### S02 — Update settings (PATCH /settings)
```bash
curl -s -X PATCH "$BASE/settings" -H "$AUTH" -H "$CT" \
  -d '{"name":"Leadpipe Updated","phone":"+15145551234"}' | python -m json.tool
```
**Expected:** Updated settings object.

### S03 — Revert name
```bash
curl -s -X PATCH "$BASE/settings" -H "$AUTH" -H "$CT" \
  -d '{"name":"Leadpipe"}' | python -m json.tool
```

### S04 — Get feature flags (GET /settings/features)
```bash
curl -s "$BASE/settings/features" -H "$AUTH" | python -m json.tool
```
**Expected:** Feature flags per building. Keys: `rent_management`, `voice_calls`, `sms_reminders`, etc.

### S05 — Toggle a feature flag (POST /settings/features)
```bash
# Enable SMS reminders for a building
curl -s -X POST "$BASE/settings/features" -H "$AUTH" -H "$CT" \
  -d "{\"building_id\":\"$TEST_BLD_ID\",\"feature_name\":\"sms_reminders\",\"is_enabled\":true}" \
  | python -m json.tool
```
**Expected:** Updated feature flag record.

### S06 — Disable the same flag
```bash
curl -s -X POST "$BASE/settings/features" -H "$AUTH" -H "$CT" \
  -d "{\"building_id\":\"$TEST_BLD_ID\",\"feature_name\":\"sms_reminders\",\"is_enabled\":false}" \
  | python -m json.tool
```
**Expected:** `is_enabled=false`.

---

## Section 12 — Chatbot

### CH01 — Basic greeting
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d '{"messages":[{"role":"user","content":"Hi, what can you help me with?"}]}' \
  | python -m json.tool
```
**Expected:** `{reply: "...", refresh_needed: false}`.

### CH02 — Ask about complaints
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d '{"messages":[{"role":"user","content":"How many open complaints do I have?"}]}' \
  | python -m json.tool
```
**Expected:** Reply with a count of pending + in-progress complaints. `refresh_needed` may be false.

### CH03 — Ask about a specific flat
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d '{"messages":[{"role":"user","content":"Tell me about flat T101"}]}' \
  | python -m json.tool
```
**Expected:** Info about T101 (tenant, status, etc.).

### CH04 — Ask chatbot to add appointment (write action with confirmation)
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d "{\"messages\":[{\"role\":\"user\",\"content\":\"Schedule a maintenance visit for flat T101 on August 15th at 2pm\"}]}" \
  | python -m json.tool
```
**Expected:** Chatbot asks for confirmation before creating. `refresh_needed: false` until confirmed.

### CH05 — Empty messages array → 422
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d '{"messages":[]}' | python -m json.tool
```
**Expected:** HTTP 422 or error from OpenAI (empty messages list).

### CH06 — Today's date awareness
```bash
curl -s -X POST "$BASE/chat" -H "$AUTH" -H "$CT" \
  -d '{"messages":[{"role":"user","content":"What is today'\''s date?"}]}' \
  | python -m json.tool
```
**Expected:** Reply mentions "June 4, 2026" (injected via `{today}` placeholder in system prompt).

---

## Section 13 — Notifications

### N01 — Get notification preferences (GET /notifications/preferences)
```bash
curl -s "$BASE/notifications/preferences" -H "$AUTH" | python -m json.tool
```
**Expected:** `{appointment_sms_enabled, appointment_email_enabled}` per building.

### N02 — Send test SMS (POST /notifications/test-sms)
```bash
curl -s -X POST "$BASE/notifications/test-sms" -H "$AUTH" -H "$CT" \
  -d '{"phone":"+15145559999","message":"API test SMS — please ignore"}' \
  | python -m json.tool
```
**Expected:** `{"status":"sent"}` or Twilio response. Only runs if Twilio creds are active.

### N03 — Send test email (POST /notifications/test-email)
```bash
curl -s -X POST "$BASE/notifications/test-email" -H "$AUTH" -H "$CT" \
  -d '{"email":"leadpipecrm@gmail.com","subject":"API Test Email","body":"This is a test email from the API test plan."}' \
  | python -m json.tool
```
**Expected:** `{"status":"sent"}`. Check inbox for the email.

---

## Section 14 — Payments

### PAY01 — Subscription status (GET /payments/subscription-status)
```bash
curl -s "$BASE/payments/subscription-status" -H "$AUTH" | python -m json.tool
```
**Expected:** `{status: "trialing"}` or `"active"`. Includes `trial_ends_at`, `current_period_end`.

### PAY02 — Create checkout session (POST /payments/create-checkout-session)
```bash
curl -s -X POST "$BASE/payments/create-checkout-session" -H "$AUTH" -H "$CT" \
  -d '{}' | python -m json.tool
```
**Expected:** `{"url":"https://checkout.stripe.com/..."}`. Don't complete the checkout — just verify the URL is returned.

---

## Section 15 — VAPI Tool Endpoints (No Auth)

### VA01 — Verify phone — valid tenant (POST /flats/verify-phone)
```bash
# +15145550011 is registered to T101 (Alex Martin)
curl -s -X POST "$BASE/flats/verify-phone?phone_number=%2B15145550011" | python -m json.tool
```
**Expected:** `{"status":"valid","flat_number":"T101"}`.

### VA02 — Verify phone — wrong number (mismatch)
```bash
# Any number not registered to any flat
curl -s -X POST "$BASE/flats/verify-phone?phone_number=%2B10000000000" | python -m json.tool
```
**Expected:** `{"status":"invalid"}`.

### VA03 — Verify phone — vacant flat (no tenant)
```bash
# T103 is vacant — no tenant
# We need a number that maps to T103 — T103 has no tenant, so any call to verify-phone
# will hit the flat lookup by phone, finding no tenant → vacant or invalid
# To test the "vacant" path properly: temporarily use a phone registered to T103-equivalent
# (In practice: vacant = no tenant_uuid on the matched flat)
curl -s -X POST "$BASE/flats/verify-phone?phone_number=%2B15145550033" | python -m json.tool
```
**Expected:** `{"status":"invalid"}` (no flat has this number → not found path).

### VA04 — Verify phone — phone number normalization
```bash
# Test with space and country code variations
curl -s -X POST "$BASE/flats/verify-phone?phone_number=%2B1+514+555+0011" | python -m json.tool
```
**Expected:** Either `valid` (if backend strips spaces) or `invalid`. Document actual behavior.

### VA05 — Check availability — malformed date → no crash (must return HTTP 200)
```bash
curl -s "$BASE/appointments/availability?appointment_date=not-a-date" | python -m json.tool
```
**Expected:** HTTP 200 with `{"status":"unavailable"}` (fails safe — never raises error to keep VAPI alive).

### VA06 — Check availability — missing parameter
```bash
curl -s "$BASE/appointments/availability" | python -m json.tool
```
**Expected:** HTTP 200 with `{"status":"unavailable"}` or HTTP 422. Either is acceptable as long as no 500.

---

## Section 16 — Properties View

### PR01 — Get properties (GET /properties)
```bash
curl -s "$BASE/properties" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of flats mapped as property cards: `{name, address, bedrooms, bathrooms, image_url, occupied}`. `floor_number` may be null (handled by `Optional[int] = None`).

---

## Section 17 — Property Types

### PT01 — List property types (GET /property-types)
```bash
curl -s "$BASE/property-types" -H "$AUTH" | python -m json.tool
```
**Expected:** `[{id, name, icon_type}]` — Residential, Commercial, Mixed-use.

---

## Section 18 — SMS Workflow

### WF01 — List SMS templates (GET /workflow/sms-templates)
```bash
curl -s "$BASE/workflow/sms-templates" -H "$AUTH" | python -m json.tool
```
**Expected:** Array of SMS templates (may be empty).

### WF02 — Create SMS template (POST /workflow/sms-templates)
```bash
curl -s -X POST "$BASE/workflow/sms-templates" -H "$AUTH" -H "$CT" \
  -d '{"name":"Rent Reminder","body":"Hi {{tenant_name}}, your rent is due on {{due_date}}."}' \
  | python -m json.tool
```
**Expected:** Template created with ID.

### WF03 — Broadcast SMS — filter by rent status (POST /workflow/sms-broadcast)
```bash
curl -s -X POST "$BASE/workflow/sms-broadcast" -H "$AUTH" -H "$CT" \
  -d '{"message":"Rent reminder: please ensure payment is up to date.","filter":{"rent_status":"Overdue"}}' \
  | python -m json.tool
```
**Expected:** Sends SMS to all tenants with `rent_status=Overdue`. `{"sent":N,"failed":0}`.

---

## Post-Test Cleanup

Run in Supabase SQL editor to remove test data:

```sql
-- Delete test flats (cascades to tenants, leases, rents, complaints)
DELETE FROM flats WHERE flat_number LIKE 'APITEST-%';

-- Delete test property group
DELETE FROM properties_list WHERE name = 'API Test Group';

-- Delete test building
DELETE FROM buildings WHERE name IN ('Test Building Alpha','Test Building Alpha (Updated)','Flat Test Block');

-- Delete test complaints
DELETE FROM complaints WHERE description LIKE '%API test%' OR description LIKE 'Appointment test%' OR description LIKE 'Testing category%';

-- Verify cleanup
SELECT count(*) FROM flats WHERE flat_number LIKE 'APITEST-%';
```

---

## Quick Checklist

| # | Route | Pass | Fail | Notes |
|---|---|---|---|---|
| T01 | GET /payments/subscription-status | | | |
| T02 | GET /complaints (no token → 401) | | | |
| P01 | GET /property-groups | | | |
| P02 | POST /property-groups | | | |
| P04 | GET /property-groups/users/me/vapi-config | | | |
| B03 | POST /buildings | | | |
| B05 | PATCH /buildings/:id | | | |
| F03 | POST /flats | | | |
| F04 | POST /flats (duplicate → 400) | | | |
| F06 | GET /flats/:uuid/details | | | |
| TN01 | POST /tenants | | | |
| TN02 | POST /tenants (dupe phone → 400) | | | |
| TN04 | GET /tenants | | | |
| TN07 | GET /tenants/by-flat/:flat_no | | | |
| TN12 | PATCH /flats/:uuid/unassign-tenant | | | |
| TN13 | PATCH /flats/:uuid/assign-tenant | | | |
| CM01 | POST /complaints | | | |
| CM03 | POST /complaints (invalid category → 400) | | | |
| CM05 | All 7 categories | | | |
| AP01 | POST /appointments | | | |
| AP08 | GET /appointments/availability (available) | | | |
| AP09 | GET /appointments/availability (unavailable) | | | |
| AP10 | GET /appointments/availability (boundary) | | | |
| AP11 | GET /appointments/view (VAPI) | | | |
| AP15 | PATCH /appointments/cancel (idempotent) | | | |
| R01 | POST /rents/set | | | |
| R02 | POST /rents/set (update) | | | |
| R03 | GET /rents/summary | | | |
| L_LIST05 | GET /leasing/search (VAPI) | | | |
| L_LIST06 | GET /leasing/search (empty params → no 422) | | | |
| L_LIST08 | GET /leasing/find-listing | | | |
| L_LIST10 | GET /leasing/metrics | | | |
| L_LEADS06 | GET /leasing/export | | | |
| V01 | GET /voice/agent-info | | | |
| S04 | GET /settings/features | | | |
| CH02 | POST /chat (complaint count) | | | |
| CH06 | POST /chat (date awareness) | | | |
| VA01 | POST /flats/verify-phone (valid) | | | |
| VA02 | POST /flats/verify-phone (invalid) | | | |
| VA05 | GET /appointments/availability (bad date → 200) | | | |
