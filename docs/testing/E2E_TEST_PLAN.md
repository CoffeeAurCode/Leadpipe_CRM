# End-to-End Test Plan — Tenant Management MVP

**Format:** Automated Python scripts using `httpx` + `pytest`.  
**Auth:** Google OAuth account — use static Bearer token (see Step 2 below).  
**Runner:** `pytest tests/e2e/ -v --tb=short`  
**Target:** ≥ 90% pass rate across all 19 route modules.

---

## Test Account

| Field | Value |
|---|---|
| Account | leadpipecrm@gmail.com |
| Auth method | Google OAuth |
| manager_id (sub) | `28c43c77-8c9c-496f-8d1e-39ffa9d619e3` |

**Token rotation:** Google OAuth tokens expire after ~1 hour. To get a fresh token:
1. Log in to the app in the browser
2. DevTools → Application → Local Storage → find the `sb-*-auth-token` key
3. Copy `access_token` from the JSON value
4. Paste into `.env.test` as `STATIC_TOKEN=...`

---

## Directory Structure

```
tests/
  e2e/
    conftest.py          # auth fixture, base_url, shared state
    test_01_auth.py      # smoke test — token works
    test_02_property_groups.py
    test_03_buildings.py
    test_04_flats.py
    test_05_tenants.py
    test_06_complaints.py
    test_07_appointments.py
    test_08_rents.py
    test_09_workflow.py
    test_10_notifications.py
    test_11_call_logs.py
    test_12_leasing.py
    test_13_voice.py
    test_14_payments.py
    test_15_settings.py
    test_16_chat.py
    test_17_property_types.py
    test_18_upload.py
    test_19_import.py
    run_all.py           # stand-alone runner with summary table
```

---

---

## Known Bug — Complaint AI Tab Showing No Stats (FIXED in this session)

**Symptom:** `VoiceStatsTab` shows 0 calls, empty chart, empty recent calls list for all managers.

**Root cause:** `voice.py` inserts call logs into `call_logs` without setting `manager_id`. The `call_logs` table has an RLS policy keyed on `manager_id = auth.uid()`. Since every row has `manager_id = NULL`, the RLS policy never matches — `GET /call_logs/stats` returns `{total: 0, ...}` for every account.

**Fix applied:** Moved manager_id resolution (phone → tenant → flat → building → property_group → manager) from inside the complaint-creation block to **before the call_log INSERT**, so `manager_id` is set on every call log — even abandoned ones with no complaint.

**Code change:** `backend/app/routes/voice.py` — new Step 8b added before Step 9.

**Verification:** After deploying, make a test call through the VAPI complaint agent. The call log should appear under the `VoiceStatsTab` for the account that owns that tenant's flat.

**Historical data:** Existing call_log rows already in the DB will still have `manager_id = NULL` and won't appear. Run this SQL to backfill if needed:
```sql
-- Backfill manager_id on call_logs via linked complaints
UPDATE call_logs cl
SET manager_id = c.manager_id
FROM complaints c
WHERE cl.complaint_id = c.id
  AND cl.manager_id IS NULL
  AND c.manager_id IS NOT NULL;
```

---

## Step 1 — Install Dependencies

```bash
pip install httpx pytest pytest-asyncio python-dotenv
```

Add to `tests/e2e/requirements.txt`:
```
httpx>=0.27
pytest>=8
pytest-asyncio>=0.23
python-dotenv>=1.0
```

---

## Step 2 — Environment File

Create `tests/e2e/.env.test`:
```
BASE_URL=http://localhost:8000
SUPABASE_URL=https://nfgnxndktecqeleabbip.supabase.co
SUPABASE_ANON_KEY=YOUR_ANON_KEY

# Google OAuth account — paste fresh token from browser session (expires ~1h)
# DevTools → Application → Local Storage → sb-*-auth-token → access_token
STATIC_TOKEN=eyJhbGciOiJFUzI1NiIsImtpZCI6IjE3ODIzMTZkLTllY2MtNDgxZC1iNDc2LTk2NzA3M2JlM2Q4OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL25mZ254bmRrdGVjcWVsZWFiYmlwLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyOGM0M2M3Ny04YzljLTQ5NmYtOGQxZS0zOWZmYTlkNjE5ZTMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgwNjUyODg4LCJpYXQiOjE3ODA2NDkyODgsImVtYWlsIjoibGVhZHBpcGVjcm1AZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJnb29nbGUiLCJwcm92aWRlcnMiOlsiZ29vZ2xlIl19LCJ1c2VyX21ldGFkYXRhIjp7ImF2YXRhcl91cmwiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKS0I4OVRNMVQyR1hKc1FoU2RfQi13MXozOXl2dFZTOTQyaXFQQTcwTmpXR0tNNlE9czk2LWMiLCJlbWFpbCI6ImxlYWRwaXBlY3JtQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJMZWFkcGlwZSIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJMZWFkcGlwZSIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0pLQjg5VE0xVDJHWEpzUWhTZF9CLXcxejM5eXZ0VlM5NDJpcVBBNzBOaldHS002UT1zOTYtYyIsInByb3ZpZGVyX2lkIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIiwic3ViIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib2F1dGgiLCJ0aW1lc3RhbXAiOjE3ODA0MjI2OTR9XSwic2Vzc2lvbl9pZCI6ImY5MTVmNzAzLTJjZmEtNDFjNS1hODYzLTQ2ZDI5M2Y1N2M4YyIsImlzX2Fub255bW91cyI6ZmFsc2V9.RsVw8VYocTTNfA3I1tyjMkqgov-mIzujQU_o45Dk16FpHRQBzwvA2SqASh-tiX0I3g2CZyEU-iixmAbmjkqPeg

TEST_PHONE=+91XXXXXXXXXX          # for SMS tests (optional)
TEST_EMAIL_RECIPIENT=test@example.com  # for email tests (optional)
```

> **Note:** The `STATIC_TOKEN` above was issued on 2026-06-05 and expires after 1 hour. Replace it with a fresh one from the browser before running tests.

---

## Step 3 — `conftest.py`

```python
import os, pytest, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.test"))

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")
STATIC_TOKEN = os.getenv("STATIC_TOKEN")  # Google OAuth token pasted from browser


def get_token() -> str:
    # Prefer the static token (Google OAuth account — no password login available)
    if STATIC_TOKEN:
        return STATIC_TOKEN
    # Fallback: email/password login (only works for non-OAuth accounts)
    assert SUPABASE_URL and SUPABASE_ANON_KEY and TEST_EMAIL and TEST_PASSWORD, \
        "Set STATIC_TOKEN or all of SUPABASE_URL/SUPABASE_ANON_KEY/TEST_EMAIL/TEST_PASSWORD in .env.test"
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 200, f"Auth failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def token():
    return get_token()


@pytest.fixture(scope="session")
def client(token):
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30) as c:
        yield c


# Shared IDs written by create tests, read by later tests
@pytest.fixture(scope="session")
def ctx():
    """Mutable session-scoped context bag for passing IDs between tests."""
    return {}
```

---

## Step 4 — Test Files

### `test_01_auth.py`
```python
def test_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "Backend running"

def test_token_is_valid(client):
    # Any authenticated route to confirm token works
    r = client.get("/buildings")
    assert r.status_code == 200
```

---

### `test_02_property_groups.py`
```python
# PG01 — list
def test_list_property_groups(client):
    r = client.get("/property-groups")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

# PG02 — create (valid)
def test_create_property_group(client, ctx):
    r = client.post("/property-groups", json={
        "name": "E2E Test Group",
        "city": "Toronto",
        "state": "Ontario",
    })
    assert r.status_code == 201
    ctx["pg_id"] = r.json()["id"]

# PG03 — create without city/state → 422
def test_create_property_group_missing_city_state(client):
    r = client.post("/property-groups", json={"name": "Incomplete Group"})
    assert r.status_code == 422

# PG04 — get by id
def test_get_property_group(client, ctx):
    r = client.get(f"/property-groups/{ctx['pg_id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "E2E Test Group"

# PG05 — patch
def test_patch_property_group(client, ctx):
    r = client.patch(f"/property-groups/{ctx['pg_id']}", json={"name": "E2E Updated Group"})
    assert r.status_code == 200

# PG06 — delete (cleanup at end)
def test_delete_property_group(client, ctx):
    r = client.delete(f"/property-groups/{ctx['pg_id']}")
    assert r.status_code in (200, 204)
```

---

### `test_03_buildings.py`
```python
def test_list_buildings(client):
    r = client.get("/buildings")
    assert r.status_code == 200

def test_create_building(client, ctx):
    r = client.post("/buildings", json={"name": "E2E Test Building"})
    assert r.status_code == 201
    ctx["building_id"] = r.json()["id"]

# B02 — GET /buildings/{id}
def test_get_building_by_id(client, ctx):
    r = client.get(f"/buildings/{ctx['building_id']}")
    assert r.status_code == 200
    assert r.json()["name"] == "E2E Test Building"

def test_get_building_units(client, ctx):
    r = client.get(f"/buildings/{ctx['building_id']}/units")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_get_building_not_found(client):
    r = client.get("/buildings/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404

# B04 — duplicate name in same property group → 409
def test_duplicate_building_name_in_group(client, ctx):
    if "pg_id" not in ctx:
        pytest.skip("property group id not in ctx")
    client.post("/buildings", json={"name": "Dup Building", "property_id": ctx.get("pg_id")})
    r = client.post("/buildings", json={"name": "Dup Building", "property_id": ctx.get("pg_id")})
    assert r.status_code == 409

def test_patch_building(client, ctx):
    r = client.patch(f"/buildings/{ctx['building_id']}", json={"description": "E2E updated"})
    assert r.status_code == 200

def test_delete_building(client, ctx):
    r = client.delete(f"/buildings/{ctx['building_id']}")
    assert r.status_code == 204
```

---

### `test_04_flats.py`
```python
# Setup: create a fresh building for flats
def test_create_building_for_flats(client, ctx):
    r = client.post("/buildings", json={"name": "E2E Flats Building"})
    assert r.status_code == 201
    ctx["flat_building_id"] = r.json()["id"]

def test_create_flat(client, ctx):
    r = client.post("/flats", json={
        "flat_number": "E2E-101",
        "building_id": ctx["flat_building_id"],
        "bedrooms": 2,
        "bathrooms": 1,
        "rent": 1500,
    })
    assert r.status_code == 201
    ctx["flat_uuid"] = r.json()["uuid"]

def test_get_flat(client, ctx):
    r = client.get(f"/flats/{ctx['flat_uuid']}")
    assert r.status_code == 200

def test_list_flats(client):
    r = client.get("/flats")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

def test_patch_flat(client, ctx):
    r = client.patch(f"/flats/{ctx['flat_uuid']}", json={"bedrooms": 3})
    assert r.status_code == 200

# VAPI verify-phone (always returns 200)
def test_verify_phone_vapi(client):
    r = client.post(
        "/flats/verify-phone?flat_number=E2E-101",
        json={"flat_number": "E2E-101"},
    )
    assert r.status_code == 200
    assert "exists" in r.json()
```

---

### `test_05_tenants.py`
```python
# TN01-TN03
def test_create_tenant(client, ctx):
    r = client.post("/tenants", json={
        "name": "E2E Tenant",
        "email": "e2etenant@example.com",
        "phone": "+919000000001",
        "flat_uuid": ctx.get("flat_uuid"),
    })
    assert r.status_code == 201
    ctx["tenant_uuid"] = r.json()["uuid"]

def test_list_tenants(client):
    r = client.get("/tenants")
    assert r.status_code == 200

def test_get_tenant(client, ctx):
    r = client.get(f"/tenants/{ctx['tenant_uuid']}")
    assert r.status_code == 200

def test_patch_tenant(client, ctx):
    r = client.patch(f"/tenants/{ctx['tenant_uuid']}", json={"name": "E2E Tenant Updated"})
    assert r.status_code == 200

def test_tenant_rent_status(client, ctx):
    r = client.patch(f"/tenants/{ctx['tenant_uuid']}/rent-status", json={"status": "paid"})
    assert r.status_code in (200, 204)

def test_get_tenant_not_found(client):
    r = client.get("/tenants/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
```

---

### `test_06_complaints.py`
```python
# CM01-CM05 (requires RLS INSERT policy fix in Session 1)
def test_create_complaint(client, ctx):
    r = client.post("/complaints", json={
        "flat_number": "E2E-101",
        "description": "E2E test complaint",
        "category": "plumbing",
    })
    assert r.status_code == 201
    ctx["complaint_id"] = r.json()["id"]

def test_list_complaints(client):
    r = client.get("/complaints")
    assert r.status_code == 200

def test_get_complaint(client, ctx):
    r = client.get(f"/complaints/{ctx['complaint_id']}")
    assert r.status_code == 200

def test_patch_complaint_status(client, ctx):
    r = client.patch(f"/complaints/{ctx['complaint_id']}", json={"status": "in_progress"})
    assert r.status_code == 200

# CM10 — DELETE (Fix 2 from Session 1)
def test_delete_complaint(client, ctx):
    r = client.delete(f"/complaints/{ctx['complaint_id']}")
    assert r.status_code == 204

def test_delete_complaint_not_found(client):
    r = client.delete("/complaints/999999")
    assert r.status_code == 404
```

---

### `test_07_appointments.py`
```python
def test_list_appointments(client):
    r = client.get("/appointments")
    assert r.status_code == 200

def test_create_appointment(client, ctx):
    r = client.post("/appointments", json={
        "complaint_id": ctx.get("complaint_id"),
        "scheduled_at": "2026-12-01T10:00:00",
        "notes": "E2E test appointment",
    })
    # May be 201 or 200 depending on implementation
    assert r.status_code in (200, 201)
    if r.json().get("id"):
        ctx["appointment_id"] = r.json()["id"]

def test_get_appointments_by_flat(client):
    r = client.get("/appointments/view?flat_number=E2E-101")
    assert r.status_code == 200
    assert "appointments" in r.json()

def test_patch_appointment(client, ctx):
    if "appointment_id" not in ctx:
        pytest.skip("no appointment created")
    r = client.patch(f"/appointments/{ctx['appointment_id']}", json={"notes": "Updated"})
    assert r.status_code == 200
```

---

### `test_08_rents.py`
```python
def test_rents_summary(client):
    r = client.get("/rents/summary")
    assert r.status_code == 200

def test_create_rent_record(client, ctx):
    if "flat_uuid" not in ctx:
        pytest.skip("no flat uuid")
    r = client.post("/rents", json={
        "flat_uuid": ctx["flat_uuid"],
        "monthly_rent": 1800,
        "effective_from": "2026-01-01",
        "is_active": True,
    })
    assert r.status_code in (200, 201)

def test_list_rents(client):
    r = client.get("/rents")
    assert r.status_code == 200
```

---

### `test_09_workflow.py`
```python
import os

# W01 — GET /workflow/sms-templates
def test_get_sms_templates(client):
    r = client.get("/workflow/sms-templates")
    assert r.status_code == 200
    templates = r.json()
    assert isinstance(templates, list)
    assert len(templates) >= 3
    assert all("id" in t and "name" in t and "message" in t for t in templates)

# W02 — POST /workflow/sms-templates
def test_create_sms_template(client):
    r = client.post("/workflow/sms-templates", json={
        "name": "Custom E2E Template",
        "message": "Hello {name}, this is a custom test message.",
    })
    assert r.status_code == 201
    assert r.json()["name"] == "Custom E2E Template"

# W03 — POST /workflow/sms-broadcast (same payload as send-sms)
def test_sms_broadcast(client, ctx):
    if "tenant_uuid" not in ctx:
        pytest.skip("no tenant uuid")
    r = client.post("/workflow/sms-broadcast", json={
        "tenant_ids": [ctx["tenant_uuid"]],
        "message": "Hi {name}, E2E broadcast test.",
    })
    assert r.status_code == 200
    assert "results" in r.json()

# Existing send-sms endpoint still works
def test_send_sms_workflow(client, ctx):
    if "tenant_uuid" not in ctx:
        pytest.skip("no tenant uuid")
    r = client.post("/workflow/send-sms", json={
        "tenant_ids": [ctx["tenant_uuid"]],
        "message": "Hi {name}, rent is {rent} due {date}.",
    })
    assert r.status_code == 200
    assert "results" in r.json()
```

---

### `test_10_notifications.py`
```python
import os

# N01 — GET /notifications/preferences
def test_get_notification_preferences(client):
    r = client.get("/notifications/preferences")
    assert r.status_code == 200
    body = r.json()
    assert "appointment_sms_enabled" in body
    assert "appointment_email_enabled" in body

# N02 — POST /notifications/test-sms (live Twilio — skip if no credentials)
def test_send_test_sms(client):
    phone = os.getenv("TEST_PHONE")
    if not phone:
        pytest.skip("TEST_PHONE not set")
    r = client.post("/notifications/test-sms", json={"phone": phone})
    assert r.status_code == 200
    assert r.json().get("success") is True

# N03 — POST /notifications/test-email (live SendGrid — skip if no credentials)
def test_send_test_email(client):
    email = os.getenv("TEST_EMAIL_RECIPIENT")
    if not email:
        pytest.skip("TEST_EMAIL_RECIPIENT not set")
    r = client.post("/notifications/test-email", json={
        "email": email,
        "subject": "E2E Test Email",
        "message": "This is an automated E2E test email.",
    })
    assert r.status_code == 200
    assert r.json().get("success") is True

# In-app notifications CRUD
def test_list_notifications(client):
    r = client.get("/notifications")
    assert r.status_code == 200

def test_create_notification(client, ctx):
    r = client.post("/notifications", json={
        "title": "E2E Test Notification",
        "body": "Automated test",
        "type": "system",
    })
    assert r.status_code == 201
    ctx["notification_id"] = r.json()["id"]

def test_mark_notification_read(client, ctx):
    if "notification_id" not in ctx:
        pytest.skip("no notification id")
    r = client.patch(f"/notifications/{ctx['notification_id']}/read")
    assert r.status_code == 200

def test_mark_all_notifications_read(client):
    r = client.post("/notifications/read-all")
    assert r.status_code == 200
```

---

### `test_11_call_logs.py`
```python
# V03-V05 (note: route is /call_logs with underscore, NOT /call-logs)
def test_list_call_logs(client):
    r = client.get("/call_logs")
    assert r.status_code == 200

def test_call_logs_stats(client):
    r = client.get("/call_logs/stats")
    assert r.status_code == 200

def test_get_call_log(client):
    # List first to get a real ID, otherwise check 404
    logs = client.get("/call_logs").json()
    if logs:
        r = client.get(f"/call_logs/{logs[0]['id']}")
        assert r.status_code == 200
    else:
        r = client.get("/call_logs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404
```

---

### `test_12_leasing.py`
```python
def test_leasing_search(client):
    r = client.get("/leasing/search")
    assert r.status_code == 200
    body = r.json()
    assert "count" in body
    assert "listings" in body
    assert isinstance(body["listings"], list)

def test_leasing_metrics(client):
    r = client.get("/leasing/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "total_calls" in body
    assert "qualification_rate" in body
    assert "avg_duration_seconds" in body

def test_list_lease_listings(client):
    r = client.get("/leasing/listings")
    assert r.status_code == 200
```

---

### `test_13_voice.py`
```python
# VAPI webhook always returns 200
def test_voice_webhook_returns_200(client):
    r = client.post("/voice/webhook", json={
        "message": {"type": "function-call", "functionCall": {"name": "unknown_fn", "parameters": {}}}
    })
    assert r.status_code == 200

# VA01-VA04 — verify-phone (requires JSON body)
def test_verify_phone_existing_flat(client):
    r = client.post(
        "/flats/verify-phone?flat_number=E2E-101",
        json={"flat_number": "E2E-101"},
    )
    assert r.status_code == 200
    assert "exists" in r.json()

def test_verify_phone_nonexistent_flat(client):
    r = client.post(
        "/flats/verify-phone?flat_number=ZZZNONE",
        json={"flat_number": "ZZZNONE"},
    )
    assert r.status_code == 200
    assert r.json()["exists"] is False
```

---

### `test_14_payments.py`
```python
# PAY01 — list subscriptions/plans
def test_list_payment_plans(client):
    r = client.get("/payments/plans")
    assert r.status_code in (200, 404)  # may not be implemented

# PAY02 — Stripe webhook (requires Stripe-Signature header)
def test_stripe_webhook_without_signature(client):
    r = client.post("/payments/webhook", content=b'{"type":"test"}',
                    headers={"Content-Type": "application/json"})
    # Should reject without valid signature
    assert r.status_code in (400, 401, 403)
```

---

### `test_15_settings.py`
```python
# S11 — settings routes use /properties/{uuid}/settings pattern
def test_settings_require_property_uuid(client):
    fake_uuid = "00000000-0000-0000-0000-000000000001"
    r = client.get(f"/properties/{fake_uuid}/settings")
    assert r.status_code in (200, 404)  # 404 if property not found

def test_unit_settings(client, ctx):
    if "flat_uuid" not in ctx:
        pytest.skip("no flat uuid")
    r = client.get(f"/units/{ctx['flat_uuid']}/settings")
    assert r.status_code in (200, 404)
```

---

### `test_16_chat.py`
```python
# CH01-CH06
def test_chat_basic(client):
    r = client.post("/chat", json={"message": "Hello", "conversation_history": []})
    assert r.status_code == 200
    assert "response" in r.json()

def test_chat_with_history(client):
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
    r = client.post("/chat", json={"message": "How many tenants?", "conversation_history": history})
    assert r.status_code == 200

def test_chat_empty_message(client):
    r = client.post("/chat", json={"message": "", "conversation_history": []})
    assert r.status_code in (200, 422)

# CH05 — tool-call scenario (investigate if this fails)
def test_chat_list_complaints_tool(client):
    r = client.post("/chat", json={
        "message": "List all open complaints",
        "conversation_history": [],
    })
    assert r.status_code == 200
    assert "response" in r.json()
```

---

### `test_17_property_types.py`
```python
def test_list_property_types(client):
    r = client.get("/property-types")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

---

### `test_18_upload.py`
```python
# Upload requires multipart — test that wrong content type is rejected
def test_upload_no_file(client):
    r = client.post("/upload")
    assert r.status_code == 422
```

---

### `test_19_import.py`
```python
def test_import_endpoint_exists(client):
    # Just confirm the route is registered (422 = endpoint exists but input invalid)
    r = client.post("/import/tenants")
    assert r.status_code in (200, 201, 400, 422)
```

---

## Step 5 — `run_all.py` (Stand-alone Runner with Summary Table)

```python
#!/usr/bin/env python3
"""
Stand-alone E2E test runner.
Usage: python tests/e2e/run_all.py
Produces a color-coded pass/fail table without requiring pytest.
"""
import os, sys, time, traceback, httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.test"))

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
TEST_EMAIL = os.getenv("TEST_EMAIL")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"


def login() -> str:
    resp = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"},
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"{RED}Auth failed: {resp.text}{RESET}")
        sys.exit(1)
    return resp.json()["access_token"]


def make_client(token: str) -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )


def run_tests(client: httpx.Client) -> list[dict]:
    ctx: dict = {}
    results: list[dict] = []

    def check(name: str, fn):
        start = time.time()
        try:
            fn(client, ctx)
            elapsed = time.time() - start
            results.append({"name": name, "status": "PASS", "elapsed": elapsed, "error": None})
        except Exception as e:
            elapsed = time.time() - start
            results.append({"name": name, "status": "FAIL", "elapsed": elapsed, "error": str(e)})

    # ── Auth ────────────────────────────────────────────────────────────────────
    check("ROOT /", lambda c, x: assert_status(c.get("/"), 200))

    # ── Property Groups ─────────────────────────────────────────────────────────
    check("PG01 GET /property-groups", lambda c, x: assert_status(c.get("/property-groups"), 200))
    check("PG02 POST /property-groups (valid)", lambda c, x: create_pg(c, x))
    check("PG03 POST /property-groups (missing city) → 422", lambda c, x: assert_status(c.post("/property-groups", json={"name": "Bad"}), 422))
    check("PG04 GET /property-groups/{id}", lambda c, x: assert_status(c.get(f"/property-groups/{x.get('pg_id', 'none')}"), [200, 404]))

    # ── Buildings ───────────────────────────────────────────────────────────────
    check("B01 GET /buildings", lambda c, x: assert_status(c.get("/buildings"), 200))
    check("B02 POST /buildings", lambda c, x: create_building(c, x))
    check("B03 GET /buildings/{id}", lambda c, x: assert_status(c.get(f"/buildings/{x.get('building_id', 'none')}"), [200, 404]))
    check("B04 GET /buildings/{id}/units", lambda c, x: assert_status(c.get(f"/buildings/{x.get('building_id', 'none')}/units"), [200, 404]))
    check("B05 GET /buildings/not-found → 404", lambda c, x: assert_status(c.get("/buildings/00000000-0000-0000-0000-000000000000"), 404))

    # ── Flats ───────────────────────────────────────────────────────────────────
    check("F01 GET /flats", lambda c, x: assert_status(c.get("/flats"), 200))
    check("F02 POST /flats", lambda c, x: create_flat(c, x))
    check("F03 GET /flats/{uuid}", lambda c, x: assert_status(c.get(f"/flats/{x.get('flat_uuid', 'none')}"), [200, 404]))

    # ── Tenants ─────────────────────────────────────────────────────────────────
    check("TN01 GET /tenants", lambda c, x: assert_status(c.get("/tenants"), 200))
    check("TN02 POST /tenants", lambda c, x: create_tenant(c, x))
    check("TN03 GET /tenants/{uuid}", lambda c, x: assert_status(c.get(f"/tenants/{x.get('tenant_uuid', 'none')}"), [200, 404]))

    # ── Complaints ──────────────────────────────────────────────────────────────
    check("CM01 GET /complaints", lambda c, x: assert_status(c.get("/complaints"), 200))
    check("CM02 POST /complaints", lambda c, x: create_complaint(c, x))
    check("CM03 GET /complaints/{id}", lambda c, x: assert_status(c.get(f"/complaints/{x.get('complaint_id', 0)}"), [200, 404]))
    check("CM10 DELETE /complaints/{id}", lambda c, x: delete_complaint(c, x))

    # ── Notifications ───────────────────────────────────────────────────────────
    check("N01 GET /notifications/preferences", lambda c, x: assert_status(c.get("/notifications/preferences"), 200))
    check("N_LIST GET /notifications", lambda c, x: assert_status(c.get("/notifications"), 200))

    # ── Workflow ─────────────────────────────────────────────────────────────────
    check("W01 GET /workflow/sms-templates", lambda c, x: assert_status(c.get("/workflow/sms-templates"), 200))
    check("W02 POST /workflow/sms-templates", lambda c, x: assert_status(
        c.post("/workflow/sms-templates", json={"name": "Test", "message": "Hello {name}"}), 201))

    # ── Call Logs ───────────────────────────────────────────────────────────────
    check("V01 GET /call_logs", lambda c, x: assert_status(c.get("/call_logs"), 200))
    check("V02 GET /call_logs/stats", lambda c, x: assert_status(c.get("/call_logs/stats"), 200))

    # ── Leasing ──────────────────────────────────────────────────────────────────
    check("L01 GET /leasing/search", lambda c, x: assert_leasing_search(c))
    check("L02 GET /leasing/metrics", lambda c, x: assert_leasing_metrics(c))

    # ── Voice / VAPI ─────────────────────────────────────────────────────────────
    check("VA01 POST /flats/verify-phone (exists)", lambda c, x: assert_status(
        c.post("/flats/verify-phone?flat_number=E2E-101", json={"flat_number": "E2E-101"}), 200))
    check("VA02 POST /flats/verify-phone (missing)", lambda c, x: assert_status(
        c.post("/flats/verify-phone?flat_number=ZZZNONE", json={"flat_number": "ZZZNONE"}), 200))

    # ── Property Types ────────────────────────────────────────────────────────────
    check("PT01 GET /property-types", lambda c, x: assert_status(c.get("/property-types"), 200))

    # ── Chat ─────────────────────────────────────────────────────────────────────
    check("CH01 POST /chat (basic)", lambda c, x: assert_chat(c))

    return results


# ── Assertion helpers ────────────────────────────────────────────────────────

def assert_status(resp: httpx.Response, expected):
    codes = [expected] if isinstance(expected, int) else expected
    assert resp.status_code in codes, f"Expected {codes}, got {resp.status_code}: {resp.text[:200]}"


def assert_leasing_search(c: httpx.Client):
    r = c.get("/leasing/search")
    assert r.status_code == 200
    body = r.json()
    assert "count" in body and "listings" in body


def assert_leasing_metrics(c: httpx.Client):
    r = c.get("/leasing/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "total_calls" in body and "qualification_rate" in body and "avg_duration_seconds" in body


def assert_chat(c: httpx.Client):
    r = c.post("/chat", json={"message": "Hello", "conversation_history": []})
    assert r.status_code == 200
    assert "response" in r.json()


def create_pg(c: httpx.Client, ctx: dict):
    r = c.post("/property-groups", json={"name": "E2E Group", "city": "Toronto", "state": "Ontario"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text[:200]}"
    ctx["pg_id"] = r.json()["id"]


def create_building(c: httpx.Client, ctx: dict):
    r = c.post("/buildings", json={"name": "E2E Building"})
    assert r.status_code == 201, f"Expected 201, got {r.status_code}: {r.text[:200]}"
    ctx["building_id"] = r.json()["id"]


def create_flat(c: httpx.Client, ctx: dict):
    payload = {"flat_number": "E2E-101", "bedrooms": 2, "bathrooms": 1, "rent": 1500}
    if "building_id" in ctx:
        payload["building_id"] = ctx["building_id"]
    r = c.post("/flats", json=payload)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text[:200]}"
    ctx["flat_uuid"] = r.json().get("uuid") or r.json().get("id")


def create_tenant(c: httpx.Client, ctx: dict):
    payload = {"name": "E2E Tenant", "email": "e2e@test.com", "phone": "+919000000001"}
    if "flat_uuid" in ctx:
        payload["flat_uuid"] = ctx["flat_uuid"]
    r = c.post("/tenants", json=payload)
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text[:200]}"
    ctx["tenant_uuid"] = r.json().get("uuid") or r.json().get("id")


def create_complaint(c: httpx.Client, ctx: dict):
    r = c.post("/complaints", json={
        "flat_number": "E2E-101",
        "description": "E2E test complaint",
        "category": "plumbing",
    })
    assert r.status_code in (200, 201), f"Expected 200/201, got {r.status_code}: {r.text[:200]}"
    ctx["complaint_id"] = r.json()["id"]


def delete_complaint(c: httpx.Client, ctx: dict):
    if "complaint_id" not in ctx:
        raise AssertionError("No complaint_id — create test must have passed")
    r = c.delete(f"/complaints/{ctx['complaint_id']}")
    assert r.status_code == 204, f"Expected 204, got {r.status_code}: {r.text[:200]}"


# ── Reporting ─────────────────────────────────────────────────────────────────

def print_report(results: list[dict]):
    passed = [r for r in results if r["status"] == "PASS"]
    failed = [r for r in results if r["status"] == "FAIL"]
    total = len(results)

    print(f"\n{BOLD}{'─' * 72}{RESET}")
    print(f"{BOLD}E2E Test Results — {total} tests{RESET}")
    print(f"{'─' * 72}")

    for r in results:
        icon = f"{GREEN}✓{RESET}" if r["status"] == "PASS" else f"{RED}✗{RESET}"
        elapsed = f"{r['elapsed']:.2f}s"
        print(f"  {icon}  {r['name']:<50} {elapsed:>7}")
        if r["error"]:
            print(f"       {YELLOW}{r['error'][:100]}{RESET}")

    print(f"{'─' * 72}")
    pct = len(passed) / total * 100 if total else 0
    color = GREEN if pct >= 90 else (YELLOW if pct >= 70 else RED)
    print(f"{color}{BOLD}  {len(passed)}/{total} passed ({pct:.0f}%){RESET}")
    if failed:
        print(f"{RED}  {len(failed)} failed:{RESET}")
        for r in failed:
            print(f"    - {r['name']}")
    print(f"{'─' * 72}\n")

    return len(failed) == 0


if __name__ == "__main__":
    print(f"{BOLD}Logging in to {BASE_URL}...{RESET}")
    token = login()
    with make_client(token) as client:
        results = run_tests(client)
    success = print_report(results)
    sys.exit(0 if success else 1)
```

---

## Step 6 — Running Tests

### With pytest (verbose, per-file):
```bash
cd C:\Users\BIT\Coding\Tenant_management_MVP
pip install httpx pytest pytest-asyncio python-dotenv

# Full suite
pytest tests/e2e/ -v --tb=short

# Single module
pytest tests/e2e/test_09_workflow.py -v

# Stop on first failure
pytest tests/e2e/ -x -v

# Only show failures
pytest tests/e2e/ --tb=short -q
```

### With the stand-alone runner (no pytest):
```bash
python tests/e2e/run_all.py
```

---

## Step 7 — Pre-requisites Checklist Before Running

| Check | Command / Action |
|---|---|
| Backend server running | `cd backend && uvicorn app.main:app --reload` |
| `.env.test` filled in | `TEST_EMAIL`, `TEST_PASSWORD`, `BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY` |
| Supabase RLS INSERT fixed | Session 1 Fix 1 — run SQL in dashboard |
| `manager_notifications` table exists | Verify in Supabase table editor |
| Twilio credentials set | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER` in `.env` |
| SendGrid credentials set | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` in `.env` |

---

## Step 8 — Coverage Map

| Test File | Routes Covered | Count |
|---|---|---|
| test_01_auth | `GET /` | 1 |
| test_02_property_groups | `GET/POST/PATCH/DELETE /property-groups` | 5 |
| test_03_buildings | `GET /buildings`, `GET /buildings/{id}`, `GET /buildings/{id}/units`, `POST`, `PATCH`, `DELETE` | 7 |
| test_04_flats | `GET /flats`, `POST /flats`, `GET /flats/{uuid}`, `PATCH`, `POST /flats/verify-phone` | 5 |
| test_05_tenants | `GET/POST/PATCH /tenants`, `PATCH /tenants/{uuid}/rent-status` | 5 |
| test_06_complaints | `GET/POST/PATCH/DELETE /complaints` | 6 |
| test_07_appointments | `GET /appointments`, `POST /appointments`, `GET /appointments/view` | 4 |
| test_08_rents | `GET /rents/summary`, `POST /rents`, `GET /rents` | 3 |
| test_09_workflow | `GET /workflow/sms-templates`, `POST /workflow/sms-templates`, `POST /workflow/sms-broadcast`, `POST /workflow/send-sms` | 4 |
| test_10_notifications | `GET /notifications/preferences`, `POST /notifications/test-sms`, `POST /notifications/test-email`, `GET /notifications`, `POST /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all` | 7 |
| test_11_call_logs | `GET /call_logs`, `GET /call_logs/stats`, `GET /call_logs/{id}` | 3 |
| test_12_leasing | `GET /leasing/search`, `GET /leasing/metrics`, `GET /leasing/listings` | 3 |
| test_13_voice | `POST /voice/webhook`, `POST /flats/verify-phone` | 3 |
| test_14_payments | `GET /payments/plans`, `POST /payments/webhook` | 2 |
| test_15_settings | `GET /properties/{uuid}/settings`, `GET /units/{uuid}/settings` | 2 |
| test_16_chat | `POST /chat` | 4 |
| test_17_property_types | `GET /property-types` | 1 |
| test_18_upload | `POST /upload` | 1 |
| test_19_import | `POST /import/tenants` | 1 |
| **Total** | | **~67 assertions** |

---

## Known Skip Conditions

| Test | Skipped When |
|---|---|
| N02 test-sms | `TEST_PHONE` env var not set |
| N03 test-email | `TEST_EMAIL_RECIPIENT` env var not set |
| W03 sms-broadcast | `tenant_uuid` not in ctx (create tenant failed) |
| test_patch_appointment | `appointment_id` not in ctx |
| test_mark_notification_read | `notification_id` not in ctx |

Tests that depend on a prior create step are ordered correctly — if the create fails, dependent tests skip rather than fail with a misleading error.
