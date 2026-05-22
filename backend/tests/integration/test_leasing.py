"""
Integration tests for /leasing/leads, /leasing/metrics, /leasing/export.

Covers the three failure modes from docs/plans/lease_lead_pipeline_diagnosis.md:
  1. Primary path: properties_list has manager_id row → leads returned normally
  2. Fallback path: properties_list.manager_id is NULL/unset → derive pg_ids from lease_listings
  3. Schema: NULL source / interested_listing_ids must not cause 422
  4. Export data-leak guard: no pg_ids → empty CSV, not all-leads dump
"""
import pytest
from tests.integration.conftest import TEST_USER

PROPERTY_GROUP_ID = "aeb9d575-42e2-439f-ad81-8e99ae6900ed"
LEAD_UUID = "22222222-2222-2222-2222-222222222222"

_PG_ROW = {"id": PROPERTY_GROUP_ID}
_LISTING_ROW = {"property_group_id": PROPERTY_GROUP_ID}

_LEAD_ROW = {
    "id": 1,
    "uuid": LEAD_UUID,
    "property_group_id": PROPERTY_GROUP_ID,
    "listing_uuid": None,
    "interested_listing_ids": None,
    "caller_name": "Raj",
    "phone": "+919998064026",
    "email": None,
    "bedrooms": 2,
    "budget_max": "25000",
    "move_in_timeline": "1 month",
    "occupants": 2,
    "floor_preference": None,
    "qualification_status": "qualified",
    "disqualifying_reason": None,
    "qualifying_answers": {},
    "notes": None,
    "source": None,
    "call_id": "call-abc-123",
    "call_duration_seconds": 120,
    "manager_notes": None,
    "created_at": "2026-05-22T10:00:00",
    "updated_at": None,
}


class TestGetLeadsPrimaryPath:
    """properties_list has a matching manager_id row — primary path."""

    def test_returns_leads(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["phone"] == "+919998064026"
        assert data[0]["qualification_status"] == "qualified"

    def test_null_source_does_not_cause_422(self, authed_client):
        """source=None must parse cleanly — Fix ab85cba5."""
        tc, _ = authed_client(
            properties_list=[_PG_ROW],
            lease_leads=[{**_LEAD_ROW, "source": None}],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json()[0]["source"] is None

    def test_null_interested_listing_ids_does_not_cause_422(self, authed_client):
        """interested_listing_ids=None must parse cleanly — Fix ab85cba5."""
        tc, _ = authed_client(
            properties_list=[_PG_ROW],
            lease_leads=[{**_LEAD_ROW, "interested_listing_ids": None}],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json()[0]["interested_listing_ids"] is None

    def test_budget_max_as_string_parses_correctly(self, authed_client):
        """Supabase returns Decimal columns as strings; Pydantic must coerce them."""
        tc, _ = authed_client(
            properties_list=[_PG_ROW],
            lease_leads=[{**_LEAD_ROW, "budget_max": "35000.50"}],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert float(resp.json()[0]["budget_max"]) == pytest.approx(35000.50)

    def test_empty_leads_table_returns_empty_list(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetLeadsFallbackPath:
    """properties_list has no matching manager_id — fallback via lease_listings (Fix b428ef51)."""

    def test_fallback_returns_leads_when_properties_list_empty(self, authed_client):
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[_LISTING_ROW],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["phone"] == "+919998064026"

    def test_both_paths_empty_returns_empty_list(self, authed_client):
        """Neither properties_list nor lease_listings yields pg_ids → []."""
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_fallback_deduplicates_property_group_ids(self, authed_client):
        """Multiple listings under the same pg_id → only one entry in IN clause."""
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[_LISTING_ROW, _LISTING_ROW],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_listing_row_without_property_group_id_is_skipped(self, authed_client):
        """lease_listings rows with missing property_group_id must not crash."""
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[{"property_group_id": None}],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json() == []


class TestGetMetrics:
    """GET /leasing/metrics — same pg_id resolution logic as get_leads."""

    def test_metrics_via_primary_path(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 1
        assert body["qualified"] == 1
        assert body["not_qualified"] == 0
        assert body["qualification_rate"] == 100.0
        assert body["avg_duration_seconds"] == 120

    def test_metrics_via_fallback_path(self, authed_client):
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[_LISTING_ROW],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        assert resp.json()["total_calls"] == 1

    def test_metrics_no_leads_returns_zeros(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 0
        assert body["qualification_rate"] == 0
        assert body["avg_duration_seconds"] == 0

    def test_metrics_days_param_accepted(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/metrics?days=7")
        assert resp.status_code == 200


class TestExportLeads:
    """GET /leasing/export — must have fallback and must not leak data when pg_ids is empty."""

    def test_export_primary_path_returns_csv_with_data(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers.get("content-type", "")
        assert "Raj" in resp.text

    def test_export_fallback_path_returns_csv_with_data(self, authed_client):
        """export_leads must use the same fallback as get_leads."""
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[_LISTING_ROW],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "Raj" in resp.text

    def test_export_no_pg_ids_returns_empty_csv_not_all_leads(self, authed_client):
        """
        Data-leak guard: when no pg_ids are resolved (neither path),
        export must return only the CSV header — not dump all leads.
        """
        tc, _ = authed_client(
            properties_list=[],
            lease_listings=[],
            lease_leads=[_LEAD_ROW],
        )
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "Raj" not in resp.text

    def test_export_csv_headers_present(self, authed_client):
        tc, _ = authed_client(properties_list=[_PG_ROW], lease_leads=[])
        resp = tc.get("/leasing/export")
        assert resp.status_code == 200
        assert "Name" in resp.text
        assert "Phone" in resp.text
        assert "Qualification Status" in resp.text
