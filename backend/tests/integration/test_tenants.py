"""
Integration tests for /tenants — Section 4.2 of TEST_PLAN.md

Covers both VAPI endpoints (always return 200) and standard CRUD routes.
"""
import pytest
from unittest.mock import MagicMock, patch
from tests.integration.conftest import FLAT_UUID, TENANT_UUID, TEST_USER

VALID_FLAT_ROW = {
    "uuid": FLAT_UUID,
    "flat_number": "A-101",
    "tenant_uuid": TENANT_UUID,
    "id": 1,
}

VALID_TENANT_ROW = {
    "id": 1,
    "uuid": TENANT_UUID,
    "name": "Ravi Kumar",
    "phone": "+919998064026",
    "email": "ravi@example.com",
    "flat_uuid": FLAT_UUID,
    "flat_number": "A-101",
    "rent_status": "On-time",
    "lease_start_date": "2025-01-01",
    "lease_end_date": "2026-01-01",
    "payment_schedule": "monthly",
    "manager_notes": None,
    "document_urls": [],
    "created_at": "2025-01-01T00:00:00+05:30",
    "rent_amount": None,
    "due_date": None,
    "tenant_details_enabled": True,
    "tenant_documents_enabled": False,
}


# ===========================================================================
# VAPI Endpoint: GET /tenants/by-flat/{flat_no}
# ===========================================================================

class TestGetTenantByFlat:
    """VAPI endpoint — MUST always return HTTP 200."""

    def test_existing_flat_with_tenant_returns_exists_true(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[{"name": "Ravi Kumar", "phone": "+919998064026"}],
        )
        resp = tc.get("/tenants/by-flat/A-101")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is True
        assert body["tenant_name"] == "Ravi Kumar"
        assert body["tenant_phone"] == "+919998064026"

    def test_existing_flat_no_tenant_returns_exists_true_with_null_fields(self, authed_client):
        flat_no_tenant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, _ = authed_client(
            flats=[flat_no_tenant],
            tenants=[],
        )
        resp = tc.get("/tenants/by-flat/A-101")
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is True
        assert body["tenant_name"] is None

    def test_nonexistent_flat_returns_exists_false(self, authed_client):
        tc, _ = authed_client(flats=[], tenants=[])
        resp = tc.get("/tenants/by-flat/Z-999")
        assert resp.status_code == 200
        assert resp.json()["exists"] is False

    def test_flat_number_case_insensitive(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[{"name": "Ravi Kumar", "phone": "+919998064026"}],
        )
        resp = tc.get("/tenants/by-flat/a-101")
        assert resp.status_code == 200
        assert resp.json()["exists"] is True

    def test_flat_number_with_whitespace_handled(self, authed_client):
        tc, _ = authed_client(flats=[], tenants=[])
        resp = tc.get("/tenants/by-flat/ A-101 ")
        assert resp.status_code == 200

    def test_response_includes_datetime(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[{"name": "Ravi Kumar", "phone": "+919998064026"}],
        )
        resp = tc.get("/tenants/by-flat/A-101")
        assert resp.status_code == 200
        assert "datetime" in resp.json()

    def test_internal_error_still_returns_200_with_exists_false(self, authed_client):
        """VAPI contract: errors must not propagate as 4xx/5xx."""
        from unittest.mock import MagicMock
        from tests.integration.conftest import make_mock_db
        from app.main import app
        from app.dependencies.authenticated_db import get_authenticated_db
        from app.dependencies.subscription import require_active_subscription
        from app.db.session import get_db
        from fastapi.testclient import TestClient

        bad_db = MagicMock()
        bad_db.postgrest = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB exploded")

        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
        app.dependency_overrides[get_authenticated_db] = lambda: bad_db
        app.dependency_overrides[get_db] = lambda: bad_db
        tc = TestClient(app, raise_server_exceptions=False)
        resp = tc.get("/tenants/by-flat/A-101")
        assert resp.status_code == 200
        assert resp.json()["exists"] is False
        app.dependency_overrides.clear()


# ===========================================================================
# POST /tenants
# ===========================================================================

class TestCreateTenant:
    def test_valid_tenant_returns_201(self, authed_client):
        tc, _ = authed_client(
            flats=[VALID_FLAT_ROW],
            tenants=[VALID_TENANT_ROW],
        )
        payload = {
            "name": "Ravi Kumar",
            "phone": "+919998064026",
            "flat_uuid": FLAT_UUID,
        }
        resp = tc.post("/tenants", json=payload)
        assert resp.status_code == 201
        assert resp.json()["name"] == "Ravi Kumar"

    def test_tenant_without_flat_returns_201(self, authed_client):
        tenant_no_flat = {**VALID_TENANT_ROW, "flat_uuid": None}
        tc, _ = authed_client(tenants=[tenant_no_flat])
        payload = {
            "name": "Meena Shah",
            "phone": "+919876543210",
        }
        resp = tc.post("/tenants", json=payload)
        assert resp.status_code == 201

    def test_nonexistent_flat_uuid_returns_404(self, authed_client):
        tc, _ = authed_client(flats=[])
        payload = {
            "name": "Ravi Kumar",
            "phone": "+919998064026",
            "flat_uuid": FLAT_UUID,
        }
        resp = tc.post("/tenants", json=payload)
        assert resp.status_code == 404

    def test_missing_name_returns_422(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/tenants", json={"phone": "+919998064026"})
        assert resp.status_code == 422

    def test_missing_phone_returns_422(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/tenants", json={"name": "Ravi Kumar"})
        assert resp.status_code == 422

    def test_no_subscription_returns_403(self, no_sub_client):
        payload = {"name": "Ravi Kumar", "phone": "+919998064026"}
        resp = no_sub_client.post("/tenants", json=payload)
        assert resp.status_code == 403


# ===========================================================================
# GET /tenants
# ===========================================================================

class TestListTenants:
    def test_returns_200_with_list(self, authed_client):
        tc, _ = authed_client(
            tenants=[VALID_TENANT_ROW],
            flats=[VALID_FLAT_ROW],
            rents=[],
            property_features=[],
        )
        resp = tc.get("/tenants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_returns_empty_list(self, authed_client):
        tc, _ = authed_client(tenants=[], flats=[], rents=[], property_features=[])
        resp = tc.get("/tenants")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_rent_status(self, authed_client):
        overdue = {**VALID_TENANT_ROW, "rent_status": "Overdue"}
        tc, _ = authed_client(
            tenants=[overdue],
            flats=[VALID_FLAT_ROW],
            rents=[],
            property_features=[],
        )
        resp = tc.get("/tenants?rent_status=Overdue")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t["rent_status"] == "Overdue" for t in data)

    def test_filter_unassigned_tenants(self, authed_client):
        unassigned = {**VALID_TENANT_ROW, "flat_uuid": None}
        tc, _ = authed_client(
            tenants=[unassigned],
            flats=[],
            rents=[],
            property_features=[],
        )
        resp = tc.get("/tenants?unassigned=true")
        assert resp.status_code == 200
        data = resp.json()
        assert all(t.get("flat_uuid") is None for t in data)


# ===========================================================================
# GET /tenants/{tenant_uuid}
# ===========================================================================

class TestGetTenant:
    def test_valid_uuid_returns_200(self, authed_client):
        tc, _ = authed_client(tenants=[VALID_TENANT_ROW])
        resp = tc.get(f"/tenants/{TENANT_UUID}")
        assert resp.status_code == 200
        assert resp.json()["uuid"] == TENANT_UUID

    def test_nonexistent_uuid_returns_404(self, authed_client):
        tc, _ = authed_client(tenants=[])
        resp = tc.get(f"/tenants/{TENANT_UUID}")
        assert resp.status_code == 404

    def test_response_includes_computed_lease_status(self, authed_client):
        tc, _ = authed_client(tenants=[VALID_TENANT_ROW])
        resp = tc.get(f"/tenants/{TENANT_UUID}")
        assert resp.status_code == 200
        body = resp.json()
        assert "lease_status" in body


# ===========================================================================
# PATCH /tenants/{tenant_uuid}
# ===========================================================================

class TestUpdateTenant:
    def test_valid_update_returns_200(self, authed_client):
        updated = {**VALID_TENANT_ROW, "name": "Ravi Kumar Updated"}
        tc, _ = authed_client(tenants=[updated])
        resp = tc.patch(f"/tenants/{TENANT_UUID}", json={"name": "Ravi Kumar Updated"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Ravi Kumar Updated"

    def test_empty_update_returns_400(self, authed_client):
        tc, _ = authed_client(tenants=[VALID_TENANT_ROW])
        resp = tc.patch(f"/tenants/{TENANT_UUID}", json={})
        assert resp.status_code == 400

    def test_nonexistent_tenant_returns_404(self, authed_client):
        tc, _ = authed_client(tenants=[])
        resp = tc.patch(f"/tenants/{TENANT_UUID}", json={"name": "New Name"})
        assert resp.status_code == 404


# ===========================================================================
# PATCH /tenants/{tenant_uuid}/rent-status
# ===========================================================================

class TestUpdateRentStatus:
    def test_valid_rent_status_returns_200(self, authed_client):
        updated = {**VALID_TENANT_ROW, "rent_status": "Overdue"}
        tc, _ = authed_client(tenants=[updated])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}/rent-status",
            json={"rent_status": "Overdue"},
        )
        assert resp.status_code == 200
        assert resp.json()["rent_status"] == "Overdue"

    def test_invalid_rent_status_returns_400(self, authed_client):
        tc, _ = authed_client()
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}/rent-status",
            json={"rent_status": "Late"},  # not allowed
        )
        assert resp.status_code == 400

    def test_all_allowed_statuses_accepted(self, authed_client):
        allowed = ["On-time", "Upcoming", "Overdue", "At Risk"]
        for status in allowed:
            updated = {**VALID_TENANT_ROW, "rent_status": status}
            tc, _ = authed_client(tenants=[updated])
            resp = tc.patch(
                f"/tenants/{TENANT_UUID}/rent-status",
                json={"rent_status": status},
            )
            assert resp.status_code == 200, f"Expected 200 for rent_status={status}"


# ===========================================================================
# DELETE /tenants/{tenant_uuid}
# ===========================================================================

class TestDeleteTenant:
    def test_delete_existing_tenant_returns_204(self, authed_client):
        flat_with_tenant = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID}
        tc, _ = authed_client(
            tenants=[{"uuid": TENANT_UUID}],
            flats=[flat_with_tenant],
            rents=[],
        )
        resp = tc.delete(f"/tenants/{TENANT_UUID}")
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, authed_client):
        tc, _ = authed_client(tenants=[])
        resp = tc.delete(f"/tenants/{TENANT_UUID}")
        assert resp.status_code == 404
