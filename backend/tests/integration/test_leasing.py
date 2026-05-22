"""
Integration tests for /leasing/leads, /leasing/metrics, /leasing/export.

Architecture: lease_leads now has manager_id directly on the row (same pattern
as every other table). All three endpoints filter by manager_id = user.sub —
no two-hop lookup through properties_list or lease_listings.
"""
import pytest
from tests.integration.conftest import TEST_USER

PROPERTY_GROUP_ID = "aeb9d575-42e2-439f-ad81-8e99ae6900ed"
LEAD_UUID = "22222222-2222-2222-2222-222222222222"
MANAGER_UUID = "aaaaaaaa-bbbb-cccc-dddd-111111111111"

_LEAD_ROW = {
    "id": 1,
    "uuid": LEAD_UUID,
    "property_group_id": PROPERTY_GROUP_ID,
    "manager_id": MANAGER_UUID,
    "listing_uuid": None,
    "interested_listing_ids": None,
    "caller_name": "Raj",
    "phone": "+919998064026",
    "email": None,
    "bedrooms": 3,
    "budget_max": "25000",
    "move_in_timeline": "By end of month",
    "occupants": None,
    "floor_preference": None,
    "qualification_status": "qualified",
    "disqualifying_reason": None,
    "qualifying_answers": {},
    "notes": None,
    "source": "voice",
    "call_id": "019e4ed4-6c28-7000-867c-238be08af154",
    "call_duration_seconds": 120,
    "manager_notes": None,
    "created_at": "2026-05-22T08:38:59",
    "updated_at": None,
}


class TestGetLeads:
    """GET /leasing/leads — direct manager_id filter, no property-group indirection."""

    def test_returns_leads_for_manager(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["phone"] == "+919998064026"
        assert data[0]["qualification_status"] == "qualified"

    def test_null_source_does_not_cause_422(self, authed_client):
        """source=None in DB row must parse cleanly."""
        tc, _ = authed_client(lease_leads=[{**_LEAD_ROW, "source": None}])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json()[0]["source"] is None

    def test_null_interested_listing_ids_does_not_cause_422(self, authed_client):
        """interested_listing_ids=None in DB row must parse cleanly."""
        tc, _ = authed_client(lease_leads=[{**_LEAD_ROW, "interested_listing_ids": None}])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json()[0]["interested_listing_ids"] is None

    def test_null_property_group_id_still_returns_lead(self, authed_client):
        """Lead with NULL property_group_id must appear as long as manager_id is set."""
        tc, _ = authed_client(lease_leads=[{**_LEAD_ROW, "property_group_id": None}])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_budget_max_as_string_parses_correctly(self, authed_client):
        """Supabase returns numeric columns as strings; Pydantic must coerce them."""
        tc, _ = authed_client(lease_leads=[{**_LEAD_ROW, "budget_max": "35000.50"}])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert float(resp.json()[0]["budget_max"]) == pytest.approx(35000.50)

    def test_empty_leads_returns_empty_list(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_qualification_status_accepted(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads?qualification_status=qualified")
        assert resp.status_code == 200

    def test_filter_by_listing_uuid_accepted(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads?listing_uuid=11111111-1111-1111-1111-111111111111")
        assert resp.status_code == 200

    def test_manager_id_returned_in_response(self, authed_client):
        """manager_id is now part of LeadResponse."""
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json()[0]["manager_id"] == MANAGER_UUID


class TestGetMetrics:
    """GET /leasing/metrics — same direct manager_id filter."""

    def test_returns_metrics(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 1
        assert body["qualified"] == 1
        assert body["not_qualified"] == 0
        assert body["qualification_rate"] == 100.0
        assert body["avg_duration_seconds"] == 120

    def test_no_leads_returns_zeros(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 0
        assert body["qualification_rate"] == 0
        assert body["avg_duration_seconds"] == 0

    def test_days_param_accepted(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/metrics?days=7")
        assert resp.status_code == 200

    def test_multiple_leads_counted(self, authed_client):
        qualified = {**_LEAD_ROW, "id": 1, "qualification_status": "qualified"}
        not_qual = {
            **_LEAD_ROW, "id": 2,
            "uuid": "33333333-3333-3333-3333-333333333333",
            "qualification_status": "not_qualified",
            "call_duration_seconds": None,
        }
        tc, _ = authed_client(lease_leads=[qualified, not_qual])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 2
        assert body["qualified"] == 1
        assert body["not_qualified"] == 1


class TestExportLeads:
    """GET /leasing/export — same direct manager_id filter, returns CSV."""

    def test_export_returns_csv_with_data(self, authed_client):
        tc, _ = authed_client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert "Raj" in resp.text

    def test_export_empty_leads_returns_headers_only(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "Name" in resp.text
        assert "Raj" not in resp.text

    def test_export_csv_has_all_expected_headers(self, authed_client):
        tc, _ = authed_client(lease_leads=[])
        resp = tc.get("/leasing/export")
        for header in ["Name", "Phone", "Email", "Qualification Status", "Source", "Call ID"]:
            assert header in resp.text

    def test_lead_with_null_property_group_id_appears_in_export(self, authed_client):
        """Leads with NULL property_group_id must still export — manager_id is the filter."""
        tc, _ = authed_client(lease_leads=[{**_LEAD_ROW, "property_group_id": None}])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "Raj" in resp.text
