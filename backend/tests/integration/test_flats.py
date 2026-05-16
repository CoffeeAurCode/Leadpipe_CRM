"""
Integration tests for /flats — Section 4.3 of TEST_PLAN.md

VAPI endpoints (verify-phone, identify-caller) must always return HTTP 200.
Standard CRUD routes require auth + subscription.
"""
import pytest
from unittest.mock import MagicMock
from tests.integration.conftest import FLAT_UUID, TENANT_UUID, BUILDING_UUID, TEST_USER

VALID_FLAT_ROW = {
    "uuid": FLAT_UUID,
    "flat_number": "A-101",
    "address": "Block A",
    "floor_number": 1,
    "bedrooms": 2,
    "bathrooms": 1,
    "tenant_uuid": TENANT_UUID,
    "occupied": True,
    "building_id": str(BUILDING_UUID),
    "image_url": None,
    "id": 1,
    "created_at": "2026-01-01T00:00:00",
}

VALID_TENANT_ROW = {
    "uuid": TENANT_UUID,
    "name": "Ravi Kumar",
    "phone": "+919998064026",
    "flat_uuid": FLAT_UUID,
}


# ===========================================================================
# VAPI: POST /flats/verify-phone
# ===========================================================================

class TestVerifyPhone:
    """VAPI contract: always return HTTP 200, never 4xx/5xx."""

    def test_matching_phone_returns_valid(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "valid"

    def test_phone_suffix_match_returns_valid(self, authed_client):
        """Country-code aware match: +91 prefix optional."""
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=9998064026",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "valid"

    def test_wrong_phone_returns_invalid(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919000000000",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "invalid"

    def test_vacant_flat_returns_vacant(self, authed_client):
        flat_vacant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, _ = authed_client(
            flats=[flat_vacant],
            tenants=[],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "vacant"

    def test_nonexistent_flat_returns_invalid(self, authed_client):
        tc, _ = authed_client(flats=[], tenants=[])
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "Z-999"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "invalid"

    def test_missing_phone_number_query_returns_200(self, authed_client):
        """If phone_number query param is missing, still return 200."""
        tc, _ = authed_client(flats=[VALID_FLAT_ROW])
        resp = tc.post(
            "/flats/verify-phone",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200

    def test_empty_flat_number_returns_200(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": ""},
        )
        assert resp.status_code == 200

    def test_flat_number_normalized_to_upper(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "a-101"},
        )
        assert resp.status_code == 200

    def test_internal_exception_returns_200_not_500(self, authed_client):
        """VAPI contract: even if DB explodes, return 200."""
        from tests.integration.conftest import make_mock_db
        from app.main import app
        from app.db.session import get_db, get_service_db
        from app.dependencies.authenticated_db import get_authenticated_db
        from app.dependencies.subscription import require_active_subscription
        from fastapi.testclient import TestClient

        bad_db = MagicMock()
        bad_db.postgrest = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB down")

        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
        app.dependency_overrides[get_authenticated_db] = lambda: bad_db
        app.dependency_overrides[get_db] = lambda: bad_db
        app.dependency_overrides[get_service_db] = lambda: bad_db
        tc = TestClient(app, raise_server_exceptions=False)
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_response_includes_datetime_when_valid(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.post(
            "/flats/verify-phone?phone_number=+919998064026",
            json={"flat_number": "A-101"},
        )
        assert resp.status_code == 200
        body = resp.json()
        if body["status"] == "valid":
            assert "datetime" in body


# ===========================================================================
# POST /flats/identify-caller
# ===========================================================================

class TestIdentifyCaller:
    """VAPI option B — always returns 200."""

    def test_known_phone_returns_exists_true(self, authed_client):
        from tests.integration.conftest import PROPERTY_UUID, make_mock_db
        from app.main import app
        from app.db.session import get_db, get_service_db
        from app.dependencies.authenticated_db import get_authenticated_db
        from app.dependencies.subscription import require_active_subscription
        from fastapi.testclient import TestClient

        building_row = {
            "id": str(BUILDING_UUID),
            "name": "Sunrise Towers",
            "property_id": str(PROPERTY_UUID),
        }
        property_row = {
            "id": str(PROPERTY_UUID),
            "name": "Green Valley",
            "manager_id": "test-manager-uuid",
        }
        manager_row = {"name": "Manager A", "phone": "+919000000001"}

        db = make_mock_db(
            tenants=[VALID_TENANT_ROW],
            flats=[VALID_FLAT_ROW],
            buildings=[building_row],
            properties_list=[property_row],
            manager_profiles=[manager_row],
        )
        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
        app.dependency_overrides[get_authenticated_db] = lambda: db
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_db] = lambda: db

        tc = TestClient(app, raise_server_exceptions=False)
        resp = tc.post("/flats/identify-caller", json={"phone_number": "+919998064026"})
        assert resp.status_code == 200
        app.dependency_overrides.clear()

    def test_unknown_phone_returns_exists_false(self, authed_client):
        tc, _ = authed_client(tenants=[])
        resp = tc.post("/flats/identify-caller", json={"phone_number": "+910000000000"})
        assert resp.status_code == 200
        assert resp.json()["exists"] is False

    def test_empty_phone_returns_exists_false(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/flats/identify-caller", json={"phone_number": ""})
        assert resp.status_code == 200
        assert resp.json()["exists"] is False

    def test_missing_phone_key_returns_exists_false(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/flats/identify-caller", json={})
        assert resp.status_code == 200
        assert resp.json()["exists"] is False


# ===========================================================================
# GET /flats
# ===========================================================================

class TestListFlats:
    def test_returns_200_with_list(self, authed_client):
        tc, _ = authed_client(flats=[VALID_FLAT_ROW])
        resp = tc.get("/flats")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_returns_200(self, authed_client):
        tc, _ = authed_client(flats=[])
        resp = tc.get("/flats")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_vacant(self, authed_client):
        vacant = {**VALID_FLAT_ROW, "tenant_uuid": None, "occupied": False}
        tc, _ = authed_client(flats=[vacant])
        resp = tc.get("/flats?vacant=true")
        assert resp.status_code == 200

    def test_no_subscription_returns_403(self, no_sub_client):
        resp = no_sub_client.get("/flats")
        assert resp.status_code == 403


# ===========================================================================
# PATCH /flats/{flat_uuid}/assign-tenant
# ===========================================================================

class TestAssignTenant:
    def test_assign_to_vacant_flat_returns_200(self, authed_client):
        vacant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, _ = authed_client(
            flats=[vacant],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_assign_to_occupied_flat_returns_400(self, authed_client):
        occupied = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID}
        tc, _ = authed_client(flats=[occupied])
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 400
        assert "already occupied" in resp.json()["detail"].lower()

    def test_nonexistent_flat_returns_404(self, authed_client):
        tc, _ = authed_client(flats=[])
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 404


# ===========================================================================
# PATCH /flats/{flat_uuid}/unassign-tenant
# ===========================================================================

class TestUnassignTenant:
    def test_unassign_occupied_flat_returns_200(self, authed_client):
        occupied = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID}
        tc, _ = authed_client(
            flats=[occupied],
            tenants=[VALID_TENANT_ROW],
        )
        resp = tc.patch(f"/flats/{FLAT_UUID}/unassign-tenant")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_unassign_nonexistent_flat_returns_404(self, authed_client):
        tc, _ = authed_client(flats=[])
        resp = tc.patch(f"/flats/{FLAT_UUID}/unassign-tenant")
        assert resp.status_code == 404

    def test_unassign_already_vacant_still_succeeds(self, authed_client):
        """Idempotent: vacating an already-vacant flat should not error."""
        vacant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, _ = authed_client(flats=[vacant])
        resp = tc.patch(f"/flats/{FLAT_UUID}/unassign-tenant")
        assert resp.status_code == 200


# ===========================================================================
# DELETE /flats/{flat_uuid}
# ===========================================================================

class TestDeleteFlat:
    def test_delete_existing_flat_returns_204(self, authed_client):
        tc, _ = authed_client(
            flats=[{**VALID_FLAT_ROW, "tenant_uuid": None}],
            rents=[],
            tenants=[],
        )
        resp = tc.delete(f"/flats/{FLAT_UUID}")
        assert resp.status_code == 204

    def test_delete_nonexistent_flat_returns_404(self, authed_client):
        tc, _ = authed_client(flats=[])
        resp = tc.delete(f"/flats/{FLAT_UUID}")
        assert resp.status_code == 404
