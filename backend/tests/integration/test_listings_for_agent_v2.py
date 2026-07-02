"""
Integration tests for the v2 lease agent backend endpoints.

New endpoints / behaviour:
  GET /leasing/listings-for-agent — threshold-aware (has_more flag)
  GET /leasing/search-listings    — filtered search for large portfolios

Also covers regression on /voice/lease-lead-direct and the existing /leasing
endpoints so we know nothing broke.

Run: pytest backend/tests/integration/test_listings_for_agent_v2.py -v
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_service_db
from app.dependencies.subscription import require_active_subscription
from tests.integration.conftest import TEST_USER, make_mock_db

MANAGER_ID = "28c43c77-8c9c-496f-8d1e-39ffa9d619e3"
LISTING_UUID = "b9f94428-1111-2222-3333-444455556666"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FLAT_ROW = {
    "bedrooms": 3,
    "floor_number": 3,
    "address": "Block C",
    "buildings": {"name": "Tower 1", "address": "123 Main St"},
}

_LISTING_ROW = {
    "uuid": LISTING_UUID,
    "flat_number": "C301",
    "title": "",
    "monthly_rent": "65000",
    "available_from": "2026-05-22",
    "custom_rules": {"non_smoking": True, "pets_allowed": "no"},
    "square_footage": 900,
    "included_utilities": ["water", "electricity"],
    "parking": "included",
    "laundry": "in-unit",
    "flats": _FLAT_ROW,
    "manager_id": MANAGER_ID,
    "property_group_id": "aeb9d575-0000-0000-0000-000000000000",
}


def _make_count_mock(count: int, rows: list):
    """
    Builds a mock DB where lease_listings first execute() returns .count=count
    (threshold check) and second execute() returns .data=rows (full fetch).

    This matches the two-query pattern in the new listings_for_agent endpoint.
    """
    mock_db = MagicMock()
    mock_db.postgrest = MagicMock()
    mock_db.storage = MagicMock()

    execute_calls = [0]

    b = MagicMock()
    for method in [
        "select", "eq", "neq", "ilike", "is_", "in_", "not_",
        "order", "limit", "insert", "update", "delete", "upsert",
        "maybe_single", "gte", "lte", "gt", "lt", "contains", "range",
    ]:
        getattr(b, method).return_value = b

    def _execute():
        result = MagicMock()
        n = execute_calls[0]
        execute_calls[0] += 1
        if n == 0:
            result.count = count
            result.data = []
        else:
            result.count = None
            result.data = rows
        return result

    b.execute.side_effect = _execute
    mock_db.table.return_value = b
    return mock_db


def _apply_and_get_client(mock_db):
    app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
    app.dependency_overrides[get_service_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /leasing/listings-for-agent — threshold-aware
# ---------------------------------------------------------------------------

class TestListingsForAgentThreshold:
    """After implementation: verify the two-path threshold logic."""

    def teardown_method(self):
        app.dependency_overrides.clear()

    def test_small_portfolio_returns_has_more_false(self):
        mock_db = _make_count_mock(count=5, rows=[_LISTING_ROW])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_more"] is False

    def test_small_portfolio_returns_full_listings_array(self):
        mock_db = _make_count_mock(count=1, rows=[_LISTING_ROW])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] >= 0
        assert isinstance(body["listings"], list)

    def test_large_portfolio_returns_has_more_true(self):
        """count=15 > threshold(10) → should return has_more=true, listings=[]"""
        mock_db = _make_count_mock(count=15, rows=[])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["has_more"] is True
        assert body["listings"] == []
        assert body["count"] == 15

    def test_large_portfolio_count_is_accurate(self):
        mock_db = _make_count_mock(count=24, rows=[])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        body = resp.json()
        assert body["count"] == 24

    def test_zero_listings_returns_has_more_false(self):
        mock_db = _make_count_mock(count=0, rows=[])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get("/leasing/listings-for-agent")
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["has_more"] is False
        assert body["listings"] == []

    def test_response_always_200_on_db_error(self):
        bad_db = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB is down")
        tc = _apply_and_get_client(bad_db)
        resp = tc.get("/leasing/listings-for-agent")
        assert resp.status_code == 200

    def test_listing_row_has_expected_fields(self):
        mock_db = _make_count_mock(count=1, rows=[_LISTING_ROW])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        body = resp.json()
        if body["listings"]:
            listing = body["listings"][0]
            for field in ("listing_uuid", "flat_number", "bedrooms", "monthly_rent",
                          "floor_number", "available_from", "custom_rules",
                          "included_utilities", "parking", "laundry"):
                assert field in listing, f"missing field: {field}"

    def test_monthly_rent_is_float(self):
        mock_db = _make_count_mock(count=1, rows=[_LISTING_ROW])
        tc = _apply_and_get_client(mock_db)
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        body = resp.json()
        if body["listings"]:
            assert isinstance(body["listings"][0]["monthly_rent"], float)


# ---------------------------------------------------------------------------
# GET /leasing/search-listings — new filtered endpoint
# ---------------------------------------------------------------------------

class TestSearchListings:
    """After implementation: verify filtered search behaviour."""

    def teardown_method(self):
        app.dependency_overrides.clear()

    def _rows_for_bedrooms(self, n):
        return [{**_LISTING_ROW, "flats": {**_FLAT_ROW, "bedrooms": n}}]

    def test_returns_200(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get(f"/leasing/search-listings?manager_id={MANAGER_ID}&bedrooms=3")
        assert resp.status_code == 200

    def test_response_has_count_and_listings(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get(f"/leasing/search-listings?bedrooms=3")
        body = resp.json()
        assert "count" in body
        assert "listings" in body

    def test_empty_result_returns_count_zero(self, authed_client):
        tc, _ = authed_client(lease_listings=[])
        resp = tc.get("/leasing/search-listings?bedrooms=5")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0
        assert resp.json()["listings"] == []

    def test_db_error_returns_200(self):
        bad_db = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB is down")
        tc = _apply_and_get_client(bad_db)
        resp = tc.get("/leasing/search-listings?bedrooms=2")
        assert resp.status_code == 200

    def test_budget_max_param_accepted(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get("/leasing/search-listings?budget_max=70000")
        assert resp.status_code == 200

    def test_both_filters_accepted(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get("/leasing/search-listings?bedrooms=3&budget_max=70000")
        assert resp.status_code == 200

    def test_no_filters_returns_results(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get("/leasing/search-listings")
        assert resp.status_code == 200

    def test_listing_fields_present_in_result(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get(f"/leasing/search-listings?manager_id={MANAGER_ID}")
        body = resp.json()
        if body["listings"]:
            listing = body["listings"][0]
            for field in ("listing_uuid", "flat_number", "bedrooms", "monthly_rent"):
                assert field in listing

    def test_quebec_size_variant_spelling_matches(self, authed_client):
        row = {**_LISTING_ROW, "quebec_size": "4½"}
        tc, _ = authed_client(lease_listings=[row])
        resp = tc.get("/leasing/search-listings", params={"quebec_size": "4 1/2"})
        body = resp.json()
        assert body["count"] == 1
        assert body["listings"][0]["quebec_size"] == "4½"

    def test_quebec_size_mismatch_filters_out(self, authed_client):
        row = {**_LISTING_ROW, "quebec_size": "3½"}
        tc, _ = authed_client(lease_listings=[row])
        resp = tc.get("/leasing/search-listings", params={"quebec_size": "4½"})
        assert resp.json()["count"] == 0

    def test_quebec_size_column_is_fetched(self, authed_client):
        """Regression (Transcript3): the filter compares r['quebec_size'], so the
        select MUST fetch that column — otherwise every row silently drops and the
        agent reports 'no listings' for sizes that exist."""
        row = {**_LISTING_ROW, "quebec_size": "4½"}
        tc, db = authed_client(lease_listings=[row])
        tc.get("/leasing/search-listings", params={"quebec_size": "4½"})
        select_arg = db.table("lease_listings").select.call_args.args[0]
        assert "quebec_size" in select_arg


# ---------------------------------------------------------------------------
# POST /voice/lease-lead-direct — regression + bug fix
# ---------------------------------------------------------------------------

class TestLeaseLeadDirect:

    def teardown_method(self):
        app.dependency_overrides.clear()

    def _post_lead(self, mock_db, body, call_id="call-abc-123", phone="+919998064026"):
        tc = _apply_and_get_client(mock_db)
        url = f"/voice/lease-lead-direct?call_id={call_id}&phone={phone}"
        return tc.post(url, json=body)

    def test_basic_lead_saves_and_returns_200(self):
        mock_db = make_mock_db(
            lease_leads=[],
            lease_listings=[_LISTING_ROW],
            notifications=[],
        )
        resp = self._post_lead(mock_db, {
            "caller_name": "Priya Mehta",
            "listing_uuid": LISTING_UUID,
            "qualification_status": "qualified",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "saved"

    def test_empty_listing_uuid_coerced_to_null(self):
        """Bug fix: listing_uuid='' should be stored as None, not empty string."""
        mock_db = make_mock_db(lease_leads=[], lease_listings=[], notifications=[])
        resp = self._post_lead(mock_db, {
            "caller_name": "Test Caller",
            "listing_uuid": "",
            "qualification_status": "unmatched",
        })
        assert resp.status_code == 200
        # Verify the insert was called with listing_uuid=None
        insert_calls = mock_db.table("lease_leads").insert.call_args_list
        assert len(insert_calls) > 0
        inserted = insert_calls[-1].args[0]
        assert inserted["listing_uuid"] is None

    def test_invalid_uuid_string_coerced_to_null(self):
        mock_db = make_mock_db(lease_leads=[], lease_listings=[], notifications=[])
        resp = self._post_lead(mock_db, {
            "caller_name": "Test Caller",
            "listing_uuid": "not-a-uuid",
            "qualification_status": "unmatched",
        })
        assert resp.status_code == 200
        insert_calls = mock_db.table("lease_leads").insert.call_args_list
        inserted = insert_calls[-1].args[0]
        assert inserted["listing_uuid"] is None

    def test_duplicate_call_id_returns_duplicate_status(self):
        mock_db = make_mock_db(
            lease_leads=[{"id": 1}],  # existing row — simulates duplicate
            lease_listings=[],
            notifications=[],
        )
        resp = self._post_lead(mock_db, {
            "caller_name": "Duplicate Caller",
            "qualification_status": "qualified",
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "duplicate"

    def test_db_error_returns_200(self):
        bad_db = MagicMock()
        bad_db.table.side_effect = RuntimeError("DB is down")
        tc = _apply_and_get_client(bad_db)
        resp = tc.post("/voice/lease-lead-direct?call_id=x&phone=+1234", json={
            "caller_name": "Test",
            "qualification_status": "unmatched",
        })
        assert resp.status_code == 200

    def test_source_is_always_voice(self):
        mock_db = make_mock_db(lease_leads=[], lease_listings=[], notifications=[])
        self._post_lead(mock_db, {
            "caller_name": "Raj",
            "qualification_status": "qualified",
        })
        insert_calls = mock_db.table("lease_leads").insert.call_args_list
        inserted = insert_calls[-1].args[0]
        assert inserted["source"] == "voice"

    def test_qualifying_answers_json_string_parsed(self):
        import json
        mock_db = make_mock_db(lease_leads=[], lease_listings=[], notifications=[])
        self._post_lead(mock_db, {
            "caller_name": "Raj",
            "qualification_status": "qualified",
            "qualifying_answers": json.dumps({"landlord_aware": "yes", "has_pets": "false"}),
        })
        insert_calls = mock_db.table("lease_leads").insert.call_args_list
        inserted = insert_calls[-1].args[0]
        assert isinstance(inserted["qualifying_answers"], dict)

    def test_interested_listing_ids_filters_invalid_uuids(self):
        mock_db = make_mock_db(lease_leads=[], lease_listings=[], notifications=[])
        self._post_lead(mock_db, {
            "caller_name": "Raj",
            "qualification_status": "qualified",
            "interested_listing_ids": ["not-a-uuid", LISTING_UUID, ""],
        })
        insert_calls = mock_db.table("lease_leads").insert.call_args_list
        inserted = insert_calls[-1].args[0]
        # Only the real UUID should survive
        assert inserted["interested_listing_ids"] == [LISTING_UUID]


# ---------------------------------------------------------------------------
# Regression: existing /leasing endpoints
# ---------------------------------------------------------------------------

class TestExistingEndpointsRegression:
    """Smoke check that the CRUD endpoints weren't broken by the v2 changes."""

    def test_get_leads_still_works(self, authed_client):
        # Reuse the proven row from test_leasing.py to avoid schema drift
        from tests.integration.test_leasing import _LEAD_ROW
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_metrics_still_works(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert "total_calls" in body
        assert "qualification_rate" in body

    def test_export_csv_still_works(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")

    def test_find_listing_still_returns_200(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get("/leasing/find-listing?query=C301")
        assert resp.status_code == 200
        body = resp.json()
        assert "found" in body

    def test_search_available_listings_still_returns_200(self, authed_client):
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get("/leasing/search?bedrooms=3")
        assert resp.status_code == 200

    def test_listings_for_agent_still_returns_200(self, authed_client):
        """The endpoint must keep returning 200 regardless of path changes."""
        tc, _ = authed_client(lease_listings=[_LISTING_ROW])
        resp = tc.get(f"/leasing/listings-for-agent?manager_id={MANAGER_ID}")
        assert resp.status_code == 200
