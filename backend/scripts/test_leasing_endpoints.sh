#!/usr/bin/env bash
# test_leasing_endpoints.sh — automated tests for lease agent backend endpoints
#
# Usage:
#   BASE_URL=http://localhost:8000 \
#   JWT=<token> \
#   FLAT_UUID=<vacant flat uuid> \
#   QUERY_TERM=A-101 \
#   bash backend/scripts/test_leasing_endpoints.sh
#
# Required env vars:
#   BASE_URL    — backend URL (no trailing slash)
#   JWT         — bearer token (needed for C tests)
#   FLAT_UUID   — UUID of a vacant flat for listing creation (needed for C1)
#   QUERY_TERM  — flat_number or title to search for in existing listings (optional)
#
# VAPI tool endpoints (B tests) require no auth.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
JWT="${JWT:-}"
FLAT_UUID="${FLAT_UUID:-}"
QUERY_TERM="${QUERY_TERM:-A-101}"

PASS=0
FAIL=0
CREATED_LISTING_UUID=""
CREATED_LEAD_UUID=""

# ── helpers ──────────────────────────────────────────────────────────────────

pass() { echo "[PASS] $1"; ((PASS++)) || true; }
fail() { echo "[FAIL] $1"; echo "       Response: $2"; ((FAIL++)) || true; }

check_field() {
  local label="$1" response="$2" field="$3" expected="$4"
  actual=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field','<missing>'))" 2>/dev/null || echo "<parse error>")
  if [ "$actual" = "$expected" ]; then
    pass "$label ($field=$expected)"
  else
    fail "$label (expected $field=$expected, got $field=$actual)" "$response"
  fi
}

check_not_null() {
  local label="$1" response="$2" field="$3"
  actual=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field'))" 2>/dev/null || echo "None")
  if [ "$actual" != "None" ] && [ "$actual" != "null" ] && [ -n "$actual" ]; then
    pass "$label ($field is non-null: $actual)"
  else
    fail "$label (expected $field to be non-null)" "$response"
  fi
}

check_http() {
  local label="$1" code="$2" expected_code="$3" response="$4"
  if [ "$code" = "$expected_code" ]; then
    pass "$label (HTTP $code)"
  else
    fail "$label (expected HTTP $expected_code, got $code)" "$response"
  fi
}

check_int_gt() {
  local label="$1" response="$2" field="$3" min="$4"
  actual=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('$field',0))" 2>/dev/null || echo "0")
  if python3 -c "exit(0 if $actual > $min else 1)" 2>/dev/null; then
    pass "$label ($field=$actual > $min)"
  else
    fail "$label (expected $field > $min, got $field=$actual)" "$response"
  fi
}

echo "========================================================"
echo " Lease Agent — Backend Endpoint Tests"
echo " BASE_URL  : $BASE_URL"
echo " QUERY     : $QUERY_TERM"
echo " FLAT_UUID : ${FLAT_UUID:-<not set — C1 will be skipped>}"
echo "========================================================"

# ── B1: find-listing — match ──────────────────────────────────────────────────
echo ""
echo "── B1: GET /leasing/find-listing — match ────────────────"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/find-listing?query=$QUERY_TERM")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B1" "$CODE" "200" "$BODY"
FOUND=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('found',False))" 2>/dev/null || echo "False")
if [ "$FOUND" = "True" ]; then
  pass "B1 found=true (listing exists for '$QUERY_TERM')"
  EXISTING_LISTING_UUID=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('listing_uuid',''))" 2>/dev/null || echo "")
  echo "  listing_uuid = $EXISTING_LISTING_UUID"
else
  echo "  [NOTE] B1 found=false — no listing for '$QUERY_TERM'. Add one first."
fi
EXISTING_LISTING_UUID="${EXISTING_LISTING_UUID:-}"

# ── B2: find-listing — no match ──────────────────────────────────────────────
echo ""
echo "── B2: GET /leasing/find-listing — no match ────────────"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/find-listing?query=ZZZNOMATCH999")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B2" "$CODE" "200" "$BODY"
check_field "B2" "$BODY" "found" "False"

# ── B3: find-listing — wrong property_group_id ────────────────────────────────
echo ""
echo "── B3: GET /leasing/find-listing — scoped to wrong pg_id ─"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/find-listing?query=$QUERY_TERM&property_group_id=00000000-0000-0000-0000-000000000000")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B3" "$CODE" "200" "$BODY"
check_field "B3" "$BODY" "found" "False"

# ── B4: search — all listings ─────────────────────────────────────────────────
echo ""
echo "── B4: GET /leasing/search — no filters ────────────────"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/search")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B4" "$CODE" "200" "$BODY"
COUNT=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('count',0))" 2>/dev/null || echo "0")
echo "  count=$COUNT (expected > 0 if listings exist)"

# ── B5: search — by budget ────────────────────────────────────────────────────
echo ""
echo "── B5: GET /leasing/search — budget_max=5 (expect 0) ───"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/search?budget_max=5")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B5" "$CODE" "200" "$BODY"
check_field "B5" "$BODY" "count" "0"

# ── B6: search — wrong pg_id (isolation) ──────────────────────────────────────
echo ""
echo "── B6: GET /leasing/search — wrong pg_id → 0 results ──"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/search?property_group_id=00000000-0000-0000-0000-000000000000")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B6" "$CODE" "200" "$BODY"
check_field "B6" "$BODY" "count" "0"

# ── B7: lease-lead-webhook — no tool in payload ───────────────────────────────
echo ""
echo "── B7: POST /voice/lease-lead-webhook — no tool ────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "tool-calls", "call": {"id": "test-ignore"}, "toolCalls": []}}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B7" "$CODE" "200" "$BODY"
check_field "B7" "$BODY" "status" "ignored"

# ── B8: lease-lead-webhook — unmatched lead (no listing) ─────────────────────
echo ""
echo "── B8: POST /voice/lease-lead-webhook — unmatched lead ─"
CALL_ID_UNMATCHED="lease-unmatched-$(date +%s)"
LEAD_ARGS=$(python3 -c "import json; print(json.dumps({
  'caller_name': 'Test Unmatched',
  'bedrooms': 3,
  'budget_max': 5000,
  'move_in_timeline': 'ASAP',
  'qualification_status': 'unmatched',
  'notes': 'Automated test - unmatched lead'
}))")
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"type\": \"tool-calls\",
      \"call\": {
        \"id\": \"$CALL_ID_UNMATCHED\",
        \"customer\": {\"number\": \"+15551234567\"},
        \"assistantId\": \"2dba3a50-6862-400c-861a-bfc0a45d4a95\"
      },
      \"toolCalls\": [{
        \"function\": {
          \"name\": \"submit_lease_lead\",
          \"arguments\": $(echo "$LEAD_ARGS" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
        }
      }]
    }
  }")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B8" "$CODE" "200" "$BODY"
check_field "B8" "$BODY" "status" "processed"
echo "  (verify in DB: lease_leads has row with call_id=$CALL_ID_UNMATCHED, property_group_id=null)"

# ── B9: lease-lead-webhook — qualified lead with listing ──────────────────────
echo ""
echo "── B9: POST /voice/lease-lead-webhook — qualified with listing ──"
if [ -n "$EXISTING_LISTING_UUID" ]; then
  CALL_ID_QUALIFIED="lease-qualified-$(date +%s)"
  LEAD_ARGS=$(python3 -c "import json; print(json.dumps({
    'caller_name': 'Test Qualified',
    'bedrooms': 2,
    'budget_max': 20000,
    'move_in_timeline': 'June 2026',
    'occupants': 2,
    'qualification_status': 'qualified',
    'listing_uuid': '$EXISTING_LISTING_UUID',
    'qualifying_answers': {'income_verified': True},
    'notes': 'Automated test - qualified lead'
  }))")
  R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/lease-lead-webhook" \
    -H "Content-Type: application/json" \
    -d "{
      \"message\": {
        \"type\": \"tool-calls\",
        \"call\": {
          \"id\": \"$CALL_ID_QUALIFIED\",
          \"customer\": {\"number\": \"+15559999999\"},
          \"assistantId\": \"2dba3a50-6862-400c-861a-bfc0a45d4a95\"
        },
        \"toolCalls\": [{
          \"function\": {
            \"name\": \"submit_lease_lead\",
            \"arguments\": $(echo "$LEAD_ARGS" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
          }
        }]
      }
    }")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  check_http "B9" "$CODE" "200" "$BODY"
  check_field "B9" "$BODY" "status" "processed"
  echo "  (verify in DB: lease_leads has row with call_id=$CALL_ID_QUALIFIED, property_group_id non-null)"
  CREATED_LEAD_CALL_ID="$CALL_ID_QUALIFIED"
else
  echo "  [SKIP] B9 — no existing listing found (B1 returned found=false). Create a listing first."
fi

# ── B10: lease-lead-webhook — not_qualified ───────────────────────────────────
echo ""
echo "── B10: POST /voice/lease-lead-webhook — not_qualified ─"
CALL_ID_NQ="lease-nq-$(date +%s)"
LEAD_ARGS=$(python3 -c "import json; print(json.dumps({
  'caller_name': 'Test NQ',
  'bedrooms': 1,
  'budget_max': 3000,
  'qualification_status': 'not_qualified',
  'disqualifying_reason': 'Budget below minimum rent',
  'notes': 'Automated test - not qualified'
}))")
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/lease-lead-webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"type\": \"tool-calls\",
      \"call\": {
        \"id\": \"$CALL_ID_NQ\",
        \"customer\": {\"number\": \"+15558888888\"},
        \"assistantId\": \"2dba3a50-6862-400c-861a-bfc0a45d4a95\"
      },
      \"toolCalls\": [{
        \"function\": {
          \"name\": \"submit_lease_lead\",
          \"arguments\": $(echo "$LEAD_ARGS" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
        }
      }]
    }
  }")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "B10" "$CODE" "200" "$BODY"
check_field "B10" "$BODY" "status" "processed"

# ── C tests — Manager CRUD (requires JWT) ──────────────────────────────────────
echo ""
echo "========================================================"
echo " Manager CRUD Tests (require JWT)"
echo "========================================================"

if [ -z "$JWT" ]; then
  echo "[SKIP] All C tests — JWT not provided. Set JWT env var to run."
else

  # ── C1: Unauthenticated access ──────────────────────────────────────────────
  echo ""
  echo "── C1: GET /leasing/listings — no auth (expect 4xx) ───"
  R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/listings")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  if [[ "$CODE" == "401" || "$CODE" == "403" || "$CODE" == "422" ]]; then
    pass "C1 unauthenticated request rejected (HTTP $CODE)"
  else
    fail "C1 expected 4xx without auth, got HTTP $CODE" "$BODY"
  fi

  # ── C2: GET listings ─────────────────────────────────────────────────────────
  echo ""
  echo "── C2: GET /leasing/listings ───────────────────────────"
  R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/listings" \
    -H "Authorization: Bearer $JWT")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  check_http "C2" "$CODE" "200" "$BODY"
  IS_ARRAY=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(isinstance(d,list))" 2>/dev/null || echo "False")
  if [ "$IS_ARRAY" = "True" ]; then
    LEN=$(echo "$BODY" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "0")
    pass "C2 response is array (length=$LEN)"
  else
    fail "C2 expected array response" "$BODY"
  fi

  # ── C3: Create listing (requires FLAT_UUID) ───────────────────────────────────
  echo ""
  echo "── C3: POST /leasing/listings — create ─────────────────"
  if [ -z "$FLAT_UUID" ]; then
    echo "  [SKIP] C3 — FLAT_UUID not set. Set FLAT_UUID env var to a vacant flat UUID."
  else
    R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/leasing/listings" \
      -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      -d "{
        \"flat_uuid\": \"$FLAT_UUID\",
        \"monthly_rent\": 15000,
        \"title\": \"Test Listing $(date +%s)\",
        \"description\": \"Automated test listing\",
        \"available_from\": \"2026-07-01\",
        \"is_active\": true,
        \"custom_rules\": {
          \"max_occupants\": 2,
          \"income_required\": true,
          \"pets_allowed\": \"no\",
          \"vegetarian_only\": false,
          \"lease_term_months\": 11,
          \"custom_question\": \"\"
        }
      }")
    CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
    check_http "C3" "$CODE" "201" "$BODY"
    check_not_null "C3 uuid" "$BODY" "uuid"
    check_not_null "C3 property_group_id" "$BODY" "property_group_id"
    CREATED_LISTING_UUID=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('uuid',''))" 2>/dev/null || echo "")
    echo "  created listing UUID = $CREATED_LISTING_UUID"
  fi

  # ── C4: Update listing ────────────────────────────────────────────────────────
  echo ""
  echo "── C4: PATCH /leasing/listings/{uuid} — update ─────────"
  if [ -z "$CREATED_LISTING_UUID" ]; then
    echo "  [SKIP] C4 — no listing created in C3"
  else
    R=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/leasing/listings/$CREATED_LISTING_UUID" \
      -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      -d '{"monthly_rent": 16000, "is_active": false}')
    CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
    check_http "C4" "$CODE" "200" "$BODY"
    check_field "C4" "$BODY" "is_active" "False"
  fi

  # ── C5: Update lead — valid manager status ────────────────────────────────────
  echo ""
  echo "── C5: PATCH /leasing/leads/{uuid} — valid manager status ─"
  # Find a lead created by our tests (B8 unmatched)
  LEAD_UUID=$(curl -s "$BASE_URL/leasing/leads" -H "Authorization: Bearer $JWT" | \
    python3 -c "
import sys, json
leads = json.load(sys.stdin)
for l in leads:
    if l.get('caller_name') in ('Test Qualified', 'Test Unmatched'):
        print(l.get('uuid', '')); break
" 2>/dev/null || echo "")
  if [ -z "$LEAD_UUID" ]; then
    echo "  [SKIP] C5 — no visible lead found (B9 qualified lead must be in DB and RLS-accessible)."
  else
    R=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/leasing/leads/$LEAD_UUID" \
      -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      -d '{"qualification_status": "contacted", "manager_notes": "Automated test note"}')
    CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
    check_http "C5" "$CODE" "200" "$BODY"
    check_field "C5" "$BODY" "qualification_status" "contacted"
    echo "  lead UUID = $LEAD_UUID"
  fi

  # ── C6: Update lead — blocked (voice-only status) ─────────────────────────────
  echo ""
  echo "── C6: PATCH /leasing/leads/{uuid} — voice-only status blocked ─"
  if [ -z "$LEAD_UUID" ]; then
    echo "  [SKIP] C6 — no lead UUID from C5"
  else
    R=$(curl -s -w "\n%{http_code}" -X PATCH "$BASE_URL/leasing/leads/$LEAD_UUID" \
      -H "Authorization: Bearer $JWT" \
      -H "Content-Type: application/json" \
      -d '{"qualification_status": "qualified"}')
    CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
    check_http "C6" "$CODE" "400" "$BODY"
  fi

  # ── C7: GET metrics ───────────────────────────────────────────────────────────
  echo ""
  echo "── C7: GET /leasing/metrics ─────────────────────────────"
  R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/metrics?days=30" \
    -H "Authorization: Bearer $JWT")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  check_http "C7" "$CODE" "200" "$BODY"
  check_not_null "C7 total_calls" "$BODY" "total_calls"
  check_not_null "C7 qualification_rate" "$BODY" "qualification_rate"

  # ── C8: Export CSV ────────────────────────────────────────────────────────────
  echo ""
  echo "── C8: GET /leasing/export ──────────────────────────────"
  R=$(curl -s -w "\n%{http_code}" "$BASE_URL/leasing/export" \
    -H "Authorization: Bearer $JWT")
  CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
  check_http "C8" "$CODE" "200" "$BODY"
  FIRST_LINE=$(echo "$BODY" | head -1)
  if echo "$FIRST_LINE" | grep -q "Name"; then
    pass "C8 CSV headers present"
  else
    fail "C8 expected CSV with Name header in first line" "$FIRST_LINE"
  fi

  # ── C9: Delete test lead ──────────────────────────────────────────────────────
  echo ""
  echo "── C9: DELETE /leasing/leads/{uuid} ────────────────────"
  if [ -z "$LEAD_UUID" ]; then
    echo "  [SKIP] C9 — no lead UUID"
  else
    R=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/leasing/leads/$LEAD_UUID" \
      -H "Authorization: Bearer $JWT")
    CODE=$(echo "$R" | tail -1)
    check_http "C9" "$CODE" "204" ""
  fi

  # ── C10: Delete test listing ──────────────────────────────────────────────────
  echo ""
  echo "── C10: DELETE /leasing/listings/{uuid} ─────────────────"
  if [ -z "$CREATED_LISTING_UUID" ]; then
    echo "  [SKIP] C10 — no listing UUID from C3"
  else
    R=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/leasing/listings/$CREATED_LISTING_UUID" \
      -H "Authorization: Bearer $JWT")
    CODE=$(echo "$R" | tail -1)
    check_http "C10" "$CODE" "204" ""
  fi

fi  # end JWT block

# ── summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo " Results: $PASS passed, $FAIL failed"
echo "========================================================"
echo ""
echo " DB verification queries to run manually in Supabase:"
echo "   SELECT * FROM lease_leads ORDER BY created_at DESC LIMIT 10;"
echo "   SELECT * FROM lease_listings ORDER BY created_at DESC LIMIT 5;"
echo "   SELECT id,name,vapi_provisioning_status FROM properties_list;"
echo "========================================================"
exit $FAIL
