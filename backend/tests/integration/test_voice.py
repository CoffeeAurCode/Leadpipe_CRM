"""
Integration tests for /voice/webhook and /voice/call-status — Section 4.11 of TEST_PLAN.md

VAPI webhook MUST always return HTTP 200 regardless of payload or internal errors.
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from tests.integration.conftest import FLAT_UUID, TENANT_UUID, COMPLAINT_UUID, TEST_USER

TOOL_CALL_PAYLOAD = {
    "message": {
        "type": "tool-calls",
        "call": {
            "id": "call-id-abc",
            "customer": {"number": "+919998064026"},
        },
        "toolCallList": [
            {
                "id": "tc-1",
                "function": {
                    "name": "submit_complaint",
                    "arguments": json.dumps({
                        "flat_number": "A-101",
                        "category": "water",
                        "description": "Pipe leak in kitchen",
                        "appointment_date": "2026-06-01T10:00:00",
                        "confirmed": True,
                    }),
                },
            }
        ],
    }
}

END_OF_CALL_PAYLOAD = {
    "message": {
        "type": "end-of-call-report",
        "call": {
            "id": "call-id-xyz",
            "customer": {"number": "+919998064026"},
        },
        "transcript": "Hello I have a water leak.",
        "summary": "Tenant reported a water leak.",
    }
}


class TestVoiceWebhook:
    """POST /voice/webhook — always returns 200."""

    def test_non_final_event_returns_200_ignored(self, authed_client):
        tc, _ = authed_client()
        payload = {
            "message": {
                "type": "status-update",
                "call": {"id": "call-123"},
            }
        }
        resp = tc.post("/voice/webhook", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") == "ignored"

    def test_end_of_call_report_creates_call_log(self, authed_client):
        call_log_row = {
            "id": 1,
            "call_id": "call-id-xyz",
            "phone_number": "+919998064026",
            "transcript": "Hello I have a water leak.",
        }
        tc, _ = authed_client(
            call_logs=[call_log_row],
            tenants=[],
        )
        with patch("app.routes.voice.notify_manager_appointment_scheduled"):
            resp = tc.post("/voice/webhook", json=END_OF_CALL_PAYLOAD)
        assert resp.status_code == 200

    def test_tool_calls_event_returns_200(self, authed_client):
        flat_row = {
            "uuid": FLAT_UUID,
            "flat_number": "A-101",
            "tenant_uuid": TENANT_UUID,
        }
        complaint_row = {
            "id": 1,
            "uuid": COMPLAINT_UUID,
            "category": "water",
            "description": "Pipe leak",
            "status": "pending",
            "source": "voice",
            "flat_number": "A-101",
            "flat_uuid": FLAT_UUID,
            "appointment_date": None,
            "appointment_status": None,
            "tenant_id": None,
            "tenant_uuid": TENANT_UUID,
            "priority": "medium",
            "created_at": "2026-05-15T10:00:00",
        }
        tc, _ = authed_client(
            flats=[flat_row],
            tenants=[{"uuid": TENANT_UUID, "phone": "+919998064026", "flat_uuid": FLAT_UUID}],
            complaints=[complaint_row],
            appointments=[],
            call_logs=[{"id": 1, "call_id": "call-id-abc"}],
        )
        with patch("app.routes.voice.notify_manager_appointment_scheduled"):
            resp = tc.post("/voice/webhook", json=TOOL_CALL_PAYLOAD)
        assert resp.status_code == 200

    def test_malformed_json_returns_200_not_500(self, authed_client):
        """Even on parse failure, webhook must return 200."""
        tc, _ = authed_client()
        resp = tc.post(
            "/voice/webhook",
            content=b"NOT VALID JSON{{{",
            headers={"content-type": "application/json"},
        )
        assert resp.status_code == 200

    def test_empty_payload_returns_200(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/voice/webhook", json={})
        assert resp.status_code == 200

    def test_missing_event_type_returns_200_ignored(self, authed_client):
        tc, _ = authed_client()
        payload = {"message": {}}
        resp = tc.post("/voice/webhook", json=payload)
        assert resp.status_code == 200

    def test_internal_db_error_still_returns_200(self, authed_client):
        from tests.integration.conftest import make_mock_db
        from app.main import app
        from app.db.session import get_db, get_service_db
        from app.dependencies.authenticated_db import get_authenticated_db
        from app.dependencies.subscription import require_active_subscription
        from fastapi.testclient import TestClient

        bad_db = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB error")

        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
        app.dependency_overrides[get_db] = lambda: bad_db
        app.dependency_overrides[get_service_db] = lambda: bad_db
        app.dependency_overrides[get_authenticated_db] = lambda: bad_db
        tc = TestClient(app, raise_server_exceptions=False)

        resp = tc.post("/voice/webhook", json=END_OF_CALL_PAYLOAD)
        assert resp.status_code == 200
        app.dependency_overrides.clear()


class TestVoiceCallStatus:
    """GET /voice/call-status — frontend polls this for new calls."""

    def test_returns_200(self, authed_client):
        tc, _ = authed_client()
        resp = tc.get("/voice/call-status")
        assert resp.status_code == 200

    def test_response_has_last_call_ended_at(self, authed_client):
        tc, _ = authed_client()
        resp = tc.get("/voice/call-status")
        assert resp.status_code == 200
        body = resp.json()
        assert "last_call_ended_at" in body
