#!/usr/bin/env bash
# test_complaint_endpoints.sh — automated tests for complaint agent backend endpoints
#
# Usage:
#   BASE_URL=http://localhost:8000 \
#   FLAT_NUMBER=A-101 \
#   TENANT_PHONE=+919998064026 \
#   JWT=<token> \
#   bash backend/scripts/test_complaint_endpoints.sh
#
# Required env vars:
#   BASE_URL      — backend URL (no trailing slash)
#   FLAT_NUMBER   — a flat that has a tenant linked to TENANT_PHONE
#   TENANT_PHONE  — E.164 format, e.g. +919998064026
#   JWT           — bearer token for authenticated endpoints (not needed for A1–A9)

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
FLAT_NUMBER="${FLAT_NUMBER:-A-101}"
TENANT_PHONE="${TENANT_PHONE:-+919998064026}"
JWT="${JWT:-}"

PASS=0
FAIL=0

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

echo "========================================================"
echo " Complaint Agent — Backend Endpoint Tests"
echo " BASE_URL : $BASE_URL"
echo " FLAT     : $FLAT_NUMBER"
echo " PHONE    : $TENANT_PHONE"
echo "========================================================"

# ── A1: Valid tenant ──────────────────────────────────────────────────────────
echo ""
echo "── A1: Verify-Phone — valid tenant ─────────────────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/flats/verify-phone?phone_number=$TENANT_PHONE" \
  -H "Content-Type: application/json" \
  -d "{\"flat_number\": \"$FLAT_NUMBER\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A1" "$CODE" "200" "$BODY"
check_field "A1" "$BODY" "status" "valid"
check_not_null "A1 property_group_id" "$BODY" "property_group_id"
# Extract pg_id for use in later tests
PG_ID=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('property_group_id',''))" 2>/dev/null || echo "")
echo "  property_group_id = $PG_ID"

# ── A2: Wrong phone ───────────────────────────────────────────────────────────
echo ""
echo "── A2: Verify-Phone — wrong phone ──────────────────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/flats/verify-phone?phone_number=+919999999999" \
  -H "Content-Type: application/json" \
  -d "{\"flat_number\": \"$FLAT_NUMBER\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A2" "$CODE" "200" "$BODY"
check_field "A2" "$BODY" "status" "invalid"

# ── A3: Non-existent flat ─────────────────────────────────────────────────────
echo ""
echo "── A3: Verify-Phone — non-existent flat ────────────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/flats/verify-phone?phone_number=$TENANT_PHONE" \
  -H "Content-Type: application/json" \
  -d '{"flat_number": "ZZZ-999"}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A3" "$CODE" "200" "$BODY"
check_field "A3" "$BODY" "status" "invalid"

# ── A4: Missing phone_number query param ──────────────────────────────────────
echo ""
echo "── A4: Verify-Phone — no phone_number param ────────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/flats/verify-phone" \
  -H "Content-Type: application/json" \
  -d "{\"flat_number\": \"$FLAT_NUMBER\"}")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A4" "$CODE" "200" "$BODY"
check_field "A4" "$BODY" "status" "invalid"

# ── A5: Webhook — ignored (non-final event) ───────────────────────────────────
echo ""
echo "── A5: Webhook — ignored non-final event ───────────────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d '{"message": {"type": "status-update", "call": {"id": "dummy-ignore-001"}}}')
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A5" "$CODE" "200" "$BODY"
check_field "A5" "$BODY" "status" "ignored"

# ── A6: Webhook — abandoned call (end-of-call-report, no tool) ───────────────
echo ""
echo "── A6: Webhook — abandoned call ────────────────────────"
CALL_ID_ABANDONED="test-abandoned-$(date +%s)"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"type\": \"end-of-call-report\",
      \"call\": {\"id\": \"$CALL_ID_ABANDONED\", \"customer\": {\"number\": \"$TENANT_PHONE\"}},
      \"artifact\": {\"transcript\": \"Hello... ok bye\"}
    }
  }")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A6" "$CODE" "200" "$BODY"
CREATED=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('complaint_created',True))" 2>/dev/null || echo "True")
if [ "$CREATED" = "False" ] || [ "$CREATED" = "false" ]; then
  pass "A6 complaint_created=false (correct — abandoned)"
else
  fail "A6 complaint_created should be false" "$BODY"
fi

# ── A7: Webhook — complaint submitted ────────────────────────────────────────
echo ""
echo "── A7: Webhook — submit_complaint tool call ─────────────"
CALL_ID_COMPLAINT="test-complaint-$(date +%s)"
APPT_DATE=$(python3 -c "from datetime import datetime, timedelta; print((datetime.now()+timedelta(days=5)).strftime('%Y-%m-%dT10:00:00'))")
# Build args JSON safely
ARGS=$(python3 -c "
import json
print(json.dumps({
  'flat_number': '$FLAT_NUMBER',
  'category': 'plumbing',
  'description': 'Automated test: pipe leak under kitchen sink',
  'appointment_date': '$APPT_DATE',
  'property_group_id': '$PG_ID'
}))
")
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"type\": \"tool-calls\",
      \"call\": {
        \"id\": \"$CALL_ID_COMPLAINT\",
        \"customer\": {\"number\": \"$TENANT_PHONE\"},
        \"assistantId\": \"9e507761-7bf7-451a-9413-8ae62ec0176f\"
      },
      \"toolCalls\": [{
        \"function\": {
          \"name\": \"submit_complaint\",
          \"arguments\": $(echo "$ARGS" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read().strip()))")
        }
      }]
    }
  }")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A7" "$CODE" "200" "$BODY"
# tool-calls events return VAPI result format: {"results": [{"toolCallId": ..., "result": "Complaint #N created..."}]}
# not {"complaint_created": true} — check the results[0].result string instead
A7_RESULT=$(echo "$BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('results', [])
print(results[0].get('result', '') if results else '')
" 2>/dev/null || echo "")
if echo "$A7_RESULT" | grep -qi "created successfully"; then
  pass "A7 complaint created (result: $A7_RESULT)"
else
  fail "A7 complaint not created" "$BODY"
fi

# ── A8: Webhook — idempotency (re-send same call_id) ─────────────────────────
echo ""
echo "── A8: Webhook — idempotency (duplicate call_id) ───────"
R=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/voice/webhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": {
      \"type\": \"end-of-call-report\",
      \"call\": {\"id\": \"$CALL_ID_ABANDONED\", \"customer\": {\"number\": \"$TENANT_PHONE\"}},
      \"artifact\": {\"transcript\": \"Duplicate send\"}
    }
  }")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A8" "$CODE" "200" "$BODY"
check_field "A8" "$BODY" "status" "processed"
echo "  (verify in DB: call_logs has exactly 1 row for call_id=$CALL_ID_ABANDONED)"

# ── A9: Call-status polling endpoint ─────────────────────────────────────────
echo ""
echo "── A9: GET /voice/call-status ───────────────────────────"
R=$(curl -s -w "\n%{http_code}" "$BASE_URL/voice/call-status")
CODE=$(echo "$R" | tail -1); BODY=$(echo "$R" | head -n -1)
check_http "A9" "$CODE" "200" "$BODY"
HAS_KEY=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print('last_call_ended_at' in d)" 2>/dev/null || echo "False")
if [ "$HAS_KEY" = "True" ]; then
  pass "A9 response contains last_call_ended_at key"
else
  fail "A9 missing last_call_ended_at key" "$BODY"
fi

# ── summary ──────────────────────────────────────────────────────────────────
echo ""
echo "========================================================"
echo " Results: $PASS passed, $FAIL failed"
echo "========================================================"
exit $FAIL
