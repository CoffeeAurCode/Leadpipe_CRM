# Backend Unit Test Result

**145/145 passing in 2.65s.**

---

## New Files Created

| File | Tests | Coverage |
|---|---|---|
| `pytest.ini` | — | Config: `testpaths=tests`, `asyncio_mode=auto` |
| `requirements-test.txt` | — | `pytest`, `pytest-asyncio`, `pytest-mock`, `freezegun` |
| `tests/conftest.py` | — | Path setup for `app.*` imports |
| `tests/unit/test_extractor.py` | 30 | `extract_complaint_from_transcript` (mocked Groq), `extract_fields`, `_extract_flat_number/category/priority` helpers |
| `tests/unit/test_validator.py` | 10 | `validate_complaint` — all field combinations, empty/None values |
| `tests/unit/test_auth.py` | 10 | `get_current_user` — valid HS256/ES256, expired, malformed, tampered, wrong secret |
| `tests/unit/test_subscription.py` | 7 | `require_active_subscription` — active, trialing, past_due, cancelled, no sub, correct `manager_id` used |
| `tests/unit/test_notifications.py` | 13 | `notify_tenant_appointment` — all 5 events, no-tenant guard, no-phone guard, Twilio/DB failures don't raise |
| `tests/unit/test_twilio_client.py` | 8 | `TwilioClient` — send, missing creds, API failure, singleton |
| `tests/unit/test_email_client.py` | 9 | `EmailClient` — send, missing key, no recipient, all 2xx codes, singleton |
| `tests/unit/test_features.py` | 13 | `get_default_state` all features, metadata completeness, type correctness |
| `tests/unit/test_chatbot.py` | 20 | `execute_tool` dispatch + guard cases, `run_chat` truncation/refresh/BadRequestError fallback |

---

## Bug Surfaced

`decision_engine.py` does:

```python
is_valid, invalid_fields = validate_complaint(data)
```

But `validate_complaint` returns a `dict` with 3 keys — this will raise `ValueError` at runtime. Not changed (not asked to fix), but worth noting.

---

## How to Run

Open a terminal, navigate to the `backend/` folder, then run:

```
cd C:\Users\BIT\Coding\Tenant_management_MVP\backend
venv\Scripts\python.exe -m pytest tests/unit/ -v
```

Or from inside Claude Code:

```
! cd backend && venv\Scripts\python.exe -m pytest tests/unit/ -v
```
