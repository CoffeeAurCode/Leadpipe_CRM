"""
Integration tests for the three new edit features (2026-06-05):
  Part A — Auto-delist listing on assign-tenant (flats.py)
  Part B — Property group PATCH (/property-groups/{uuid})
  Part C — Tenant phone/name update with uniqueness guard (tenants.py)

Also covers edge cases from the integration test plan:
  I1 — Assign deactivates listing; unassign does NOT re-activate
  I3 — Phone change validation guards
  I4 — CSV import path also deactivates listing
  I5 — Regression: existing tenant update fields still work
"""
import pytest
from unittest.mock import MagicMock, call
from tests.integration.conftest import FLAT_UUID, TENANT_UUID, BUILDING_UUID, PROPERTY_UUID, TEST_USER

VALID_FLAT_ROW = {
    "uuid": FLAT_UUID,
    "flat_number": "A-101",
    "address": "Block A",
    "floor_number": 1,
    "bedrooms": 2,
    "bathrooms": 1,
    "tenant_uuid": None,
    "occupied": False,
    "building_id": str(BUILDING_UUID),
    "image_url": None,
    "id": 1,
    "created_at": "2026-01-01T00:00:00",
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

VALID_LISTING_ROW = {
    "id": 1,
    "flat_uuid": FLAT_UUID,
    "is_active": True,
    "monthly_rent": 20000,
    "bedrooms": 2,
}

def _make_two_shot_tenant_mock(tenant_row):
    """First execute() returns [] (uniqueness check passes), second returns the row (update result)."""
    b = MagicMock()
    for method in ["select", "eq", "neq", "order", "limit", "update", "insert", "upsert",
                   "delete", "is_", "in_", "not_", "gte", "lte", "gt", "lt", "ilike", "contains"]:
        getattr(b, method).return_value = b
    calls = []

    def _execute():
        result = MagicMock()
        result.data = [] if not calls else [tenant_row]
        calls.append(1)
        return result

    b.execute.side_effect = _execute
    return b


VALID_PROPERTY_GROUP_ROW = {
    "id": str(PROPERTY_UUID),
    "name": "Sunrise Estate",
    "description": "Main complex",
    "street_address": "123 Main St",
    "city": "Toronto",
    "state": "Ontario",
    "country": "Canada",
    "image_url": None,
    "property_type_id": None,
    "created_at": "2026-01-01T00:00:00",
    "vapi_provisioning_status": "not_applicable",
    "vapi_phone_number": None,
}


# ===========================================================================
# Part A — Auto-delist (I1 integration test)
# ===========================================================================

class TestAutoDelistOnAssign:

    def test_assign_tenant_calls_lease_listing_deactivation(self, authed_client):
        """I1 core: assigning a tenant deactivates any active listing for that flat."""
        vacant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, db = authed_client(
            flats=[vacant],
            tenants=[VALID_TENANT_ROW],
            lease_listings=[VALID_LISTING_ROW],
        )
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify lease_listings.update({"is_active": False}).eq("flat_uuid", FLAT_UUID) was called
        listing_mock = db.table("lease_listings")
        listing_mock.update.assert_called_with({"is_active": False})
        listing_mock.eq.assert_any_call("flat_uuid", FLAT_UUID)

    def test_assign_flat_with_no_listing_still_succeeds(self, authed_client):
        """Deactivating a non-existent listing is a no-op (Supabase ignores 0-row updates)."""
        vacant = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, db = authed_client(
            flats=[vacant],
            tenants=[VALID_TENANT_ROW],
            lease_listings=[],
        )
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 200
        # update still called (Supabase ignores 0-row case silently)
        db.table("lease_listings").update.assert_called_with({"is_active": False})

    def test_unassign_does_not_reactivate_listing(self, authed_client):
        """I1 edge: unassigning a tenant must NOT re-activate the listing."""
        occupied = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID, "occupied": True}
        tc, db = authed_client(
            flats=[occupied],
            tenants=[VALID_TENANT_ROW],
            lease_listings=[{**VALID_LISTING_ROW, "is_active": False}],
        )
        resp = tc.patch(f"/flats/{FLAT_UUID}/unassign-tenant")
        assert resp.status_code == 200

        # lease_listings.update should NOT have been called in unassign_tenant
        listing_table = db.table("lease_listings")
        listing_table.update.assert_not_called()

    def test_assign_already_occupied_does_not_touch_listing(self, authed_client):
        """Guard: occupied flat returns 400 before any listing deactivation."""
        occupied = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID, "occupied": True}
        tc, db = authed_client(
            flats=[occupied],
            tenants=[VALID_TENANT_ROW],
            lease_listings=[VALID_LISTING_ROW],
        )
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 400
        db.table("lease_listings").update.assert_not_called()

    def test_assign_nonexistent_flat_does_not_touch_listing(self, authed_client):
        """Guard: nonexistent flat returns 404 before any listing deactivation."""
        tc, db = authed_client(
            flats=[],
            lease_listings=[VALID_LISTING_ROW],
        )
        resp = tc.patch(
            f"/flats/{FLAT_UUID}/assign-tenant",
            json={"tenant_uuid": TENANT_UUID},
        )
        assert resp.status_code == 404
        db.table("lease_listings").update.assert_not_called()


# ===========================================================================
# Part B — Property Group PATCH
# ===========================================================================

class TestUpdatePropertyGroup:

    def test_valid_patch_returns_200(self, authed_client):
        """B1: PATCH /property-groups/{uuid} with valid fields returns 200."""
        updated_row = {**VALID_PROPERTY_GROUP_ROW, "name": "Updated Estate"}
        tc, _ = authed_client(
            properties_list=[updated_row],
            property_types=[],
            buildings=[],
        )
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={"name": "Updated Estate"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Estate"

    def test_empty_payload_returns_400(self, authed_client):
        """B1: empty patch body should return 400, not silently succeed."""
        tc, _ = authed_client(properties_list=[VALID_PROPERTY_GROUP_ROW])
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={},
        )
        assert resp.status_code == 400
        assert "no fields" in resp.json()["detail"].lower()

    def test_nonexistent_group_returns_404(self, authed_client):
        """B1: PATCH a group that doesn't exist should return 404."""
        tc, _ = authed_client(
            properties_list=[],
            property_types=[],
            buildings=[],
        )
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={"name": "Ghost Estate"},
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()

    def test_partial_update_returns_200(self, authed_client):
        """B1: Only sending city + state is a valid partial update."""
        updated = {**VALID_PROPERTY_GROUP_ROW, "city": "Vancouver", "state": "BC"}
        tc, _ = authed_client(
            properties_list=[updated],
            property_types=[],
            buildings=[],
        )
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={"city": "Vancouver", "state": "BC"},
        )
        assert resp.status_code == 200

    def test_update_all_fields_accepted(self, authed_client):
        """B1: All editable fields can be sent in one PATCH."""
        updated = {
            **VALID_PROPERTY_GROUP_ROW,
            "name": "New Name",
            "description": "New Desc",
            "street_address": "456 Oak Ave",
            "city": "Calgary",
            "state": "AB",
            "country": "Canada",
        }
        tc, _ = authed_client(
            properties_list=[updated],
            property_types=[],
            buildings=[],
        )
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={
                "name": "New Name",
                "description": "New Desc",
                "street_address": "456 Oak Ave",
                "city": "Calgary",
                "state": "AB",
                "country": "Canada",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"
        assert body["city"] == "Calgary"

    def test_rename_preserves_building_count(self, authed_client):
        """I2: renaming a group should still return accurate building_count."""
        updated = {**VALID_PROPERTY_GROUP_ROW, "name": "Renamed Estate"}
        buildings = [{"id": 1, "property_id": str(PROPERTY_UUID)}]
        tc, _ = authed_client(
            properties_list=[updated],
            property_types=[],
            buildings=buildings,
        )
        resp = tc.patch(
            f"/property-groups/{PROPERTY_UUID}",
            json={"name": "Renamed Estate"},
        )
        assert resp.status_code == 200
        assert resp.json()["building_count"] == 1


# ===========================================================================
# Part C — Tenant name/phone update (I3 integration test)
# ===========================================================================

class TestUpdateTenantNamePhone:

    def test_update_name_returns_200(self, authed_client):
        """C1: updating name to a non-empty string succeeds."""
        updated = {**VALID_TENANT_ROW, "name": "Arjun Sharma"}
        tc, _ = authed_client(tenants=[updated])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"name": "Arjun Sharma"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Arjun Sharma"

    def test_update_phone_returns_200(self, authed_client):
        """C1: updating phone to a new unique number succeeds.
        Two-shot mock: first execute returns [] (no duplicate), second returns updated row."""
        updated = {**VALID_TENANT_ROW, "phone": "+15145551234"}
        tc, _ = authed_client(tenants=_make_two_shot_tenant_mock(updated))
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"phone": "+15145551234"},
        )
        assert resp.status_code == 200

    def test_empty_name_returns_400(self, authed_client):
        """C edge case: blank name must be rejected before hitting DB."""
        tc, _ = authed_client(tenants=[VALID_TENANT_ROW])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"name": ""},
        )
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_whitespace_only_name_returns_400(self, authed_client):
        """C edge case: all-whitespace name is effectively blank."""
        tc, _ = authed_client(tenants=[VALID_TENANT_ROW])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"name": "   "},
        )
        assert resp.status_code == 400

    def test_duplicate_phone_returns_400(self, authed_client):
        """I3 duplicate phone: changing to another tenant's phone returns 400."""
        other_tenant_uuid = "cccccccc-1111-2222-3333-444444444444"
        other_tenant = {**VALID_TENANT_ROW, "uuid": other_tenant_uuid, "phone": "+15145559999"}

        # Mock: phone lookup returns the other tenant
        from tests.integration.conftest import make_mock_db
        from unittest.mock import MagicMock

        def _phone_lookup_builder(data):
            b = MagicMock()
            for method in ["select", "eq", "neq", "order", "limit", "update", "insert", "upsert", "delete"]:
                getattr(b, method).return_value = b
            result = MagicMock()
            result.data = data
            b.execute.return_value = result
            return b

        # Build a DB where:
        #   tenants.select().eq("phone", ...).neq("uuid", ...) → [other_tenant]
        #   tenants.update(...)... → [VALID_TENANT_ROW]  (would be called if not blocked)
        call_count = {"n": 0}

        def smart_tenant_builder():
            b = MagicMock()
            for method in ["select", "eq", "neq", "order", "limit", "update", "insert", "upsert", "delete", "is_", "in_", "not_", "gte", "lte"]:
                getattr(b, method).return_value = b

            def execute():
                call_count["n"] += 1
                result = MagicMock()
                # First execute() is the phone uniqueness check → returns the other tenant
                if call_count["n"] == 1:
                    result.data = [{"uuid": other_tenant_uuid}]
                else:
                    result.data = [VALID_TENANT_ROW]
                return result

            b.execute.side_effect = execute
            return b

        from app.main import app
        from app.db.session import get_db, get_service_db
        from app.dependencies.authenticated_db import get_authenticated_db
        from app.dependencies.subscription import require_active_subscription
        from fastapi.testclient import TestClient

        tenant_mock = smart_tenant_builder()
        db = MagicMock()
        db.postgrest = MagicMock()
        db.storage = MagicMock()
        db.table.return_value = tenant_mock

        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
        app.dependency_overrides[get_authenticated_db] = lambda: db
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_service_db] = lambda: db

        tc = TestClient(app, raise_server_exceptions=False)
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"phone": "+15145559999"},
        )
        app.dependency_overrides.clear()

        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()

    def test_same_tenant_phone_update_skips_duplicate_check(self, authed_client):
        """I3: when the same tenant updates to its OWN phone, neq filter should exclude it.
        In real DB the neq would exclude own row; in mock we simulate [] return from uniqueness query."""
        updated = {**VALID_TENANT_ROW, "phone": "+919998064026"}
        tc, _ = authed_client(tenants=_make_two_shot_tenant_mock(updated))
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"phone": "+919998064026"},
        )
        assert resp.status_code == 200

    def test_update_name_and_phone_together_returns_200(self, authed_client):
        """I5 regression: updating name + phone in one save works."""
        updated = {**VALID_TENANT_ROW, "name": "New Name", "phone": "+15145551234"}
        tc, _ = authed_client(tenants=_make_two_shot_tenant_mock(updated))
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"name": "New Name", "phone": "+15145551234"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "New Name"

    def test_update_existing_fields_still_work(self, authed_client):
        """I5 regression: lease_start_date, manager_notes etc still update correctly."""
        updated = {**VALID_TENANT_ROW, "manager_notes": "Call before 10am"}
        tc, _ = authed_client(tenants=[updated])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"manager_notes": "Call before 10am"},
        )
        assert resp.status_code == 200

    def test_nonexistent_tenant_returns_404(self, authed_client):
        """Guard: updating a tenant that doesn't exist returns 404."""
        tc, _ = authed_client(tenants=[])
        resp = tc.patch(
            f"/tenants/{TENANT_UUID}",
            json={"name": "Ghost"},
        )
        assert resp.status_code == 404
