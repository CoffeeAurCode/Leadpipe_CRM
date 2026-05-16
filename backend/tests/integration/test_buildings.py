"""
Integration tests for /buildings — Section 4.5 of TEST_PLAN.md

Tests building CRUD with joined property type and unit count enrichment.
"""
import pytest
from tests.integration.conftest import BUILDING_UUID, PROPERTY_UUID, FLAT_UUID, TENANT_UUID

VALID_BUILDING_ROW = {
    "id": str(BUILDING_UUID),
    "name": "Sunrise Towers",
    "description": "A block",
    "address": "123 Main St",
    "image_url": None,
    "property_type_id": None,
    "property_types": {},
    "property_id": str(PROPERTY_UUID),
    "created_at": "2026-01-01T00:00:00",
}

VALID_FLAT_ROW = {
    "uuid": FLAT_UUID,
    "flat_number": "A-101",
    "building_id": str(BUILDING_UUID),
    "tenant_uuid": None,
}


class TestListBuildings:
    def test_returns_200_with_list(self, authed_client):
        tc, _ = authed_client(
            buildings=[VALID_BUILDING_ROW],
            flats=[VALID_FLAT_ROW],
        )
        resp = tc.get("/buildings")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_returns_empty_list(self, authed_client):
        tc, _ = authed_client(buildings=[], flats=[])
        resp = tc.get("/buildings")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_unit_count_enriched(self, authed_client):
        """unit_count should equal the number of flats in that building."""
        flat = {**VALID_FLAT_ROW, "tenant_uuid": None}
        tc, _ = authed_client(
            buildings=[VALID_BUILDING_ROW],
            flats=[flat],
        )
        resp = tc.get("/buildings")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["unit_count"] == 1
        assert data[0]["occupied_count"] == 0

    def test_occupied_count_enriched(self, authed_client):
        occupied_flat = {**VALID_FLAT_ROW, "tenant_uuid": TENANT_UUID}
        tc, _ = authed_client(
            buildings=[VALID_BUILDING_ROW],
            flats=[occupied_flat],
        )
        resp = tc.get("/buildings")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["occupied_count"] == 1

    def test_no_subscription_returns_403(self, no_sub_client):
        resp = no_sub_client.get("/buildings")
        assert resp.status_code == 403


class TestCreateBuilding:
    def test_valid_building_returns_201(self, authed_client):
        created_row = {
            **VALID_BUILDING_ROW,
            "unit_count": 0,
            "occupied_count": 0,
        }
        tc, _ = authed_client(buildings=[created_row], flats=[])
        resp = tc.post("/buildings", json={"name": "Sunrise Towers"})
        assert resp.status_code == 201
        assert resp.json()["name"] == "Sunrise Towers"

    def test_missing_name_returns_422(self, authed_client):
        tc, _ = authed_client()
        resp = tc.post("/buildings", json={})
        assert resp.status_code == 422

    def test_no_subscription_returns_403(self, no_sub_client):
        resp = no_sub_client.post("/buildings", json={"name": "Test"})
        assert resp.status_code == 403


class TestGetBuildingUnits:
    def test_returns_flats_for_building(self, authed_client):
        tc, _ = authed_client(flats=[VALID_FLAT_ROW])
        resp = tc.get(f"/buildings/{BUILDING_UUID}/units")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_building_returns_empty_list(self, authed_client):
        tc, _ = authed_client(flats=[])
        resp = tc.get(f"/buildings/{BUILDING_UUID}/units")
        assert resp.status_code == 200
        assert resp.json() == []


class TestUpdateBuilding:
    def test_valid_patch_returns_200(self, authed_client):
        updated = {**VALID_BUILDING_ROW, "name": "Updated Name"}
        tc, _ = authed_client(buildings=[updated], flats=[])
        resp = tc.patch(f"/buildings/{BUILDING_UUID}", json={"name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Name"

    def test_nonexistent_building_returns_404(self, authed_client):
        tc, _ = authed_client(buildings=[])
        resp = tc.patch(f"/buildings/{BUILDING_UUID}", json={"name": "Test"})
        assert resp.status_code == 404


class TestDeleteBuilding:
    def test_delete_existing_returns_204(self, authed_client):
        tc, _ = authed_client(buildings=[VALID_BUILDING_ROW], flats=[])
        resp = tc.delete(f"/buildings/{BUILDING_UUID}")
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, authed_client):
        tc, _ = authed_client(buildings=[])
        resp = tc.delete(f"/buildings/{BUILDING_UUID}")
        assert resp.status_code == 404
