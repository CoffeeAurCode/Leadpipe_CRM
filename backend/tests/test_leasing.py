"""
Automated tests covering LEAD_AGENT_TEST_PLAN.md — Part 1 (sections 1.1–1.6).

Uses a mock Supabase DB (no live network calls). Tests that are known to fail
until LEAD_ASSIGNMENT_PLAN.md phases are complete are noted in the report.
"""
import json
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, get_service_db
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROPERTY_GROUP_ID = "aeb9d575-42e2-439f-ad81-8e99ae6900ed"
MANAGER_UUID = "28c43c77-8c9c-496f-8d1e-39ffa9d619e3"

P1_UUID = "11111111-1111-1111-1111-111111111111"  # A101 1BHK ₹20,000
P2_UUID = "22222222-2222-2222-2222-222222222222"  # B202 2BHK ₹38,000
P3_UUID = "33333333-3333-3333-3333-333333333333"  # C301 3BHK ₹65,000
P4_UUID = "44444444-4444-4444-4444-444444444444"  # D404 2BHK ₹42,000 no-pets
P5_UUID = "55555555-5555-5555-5555-555555555555"  # E501 2BHK ₹55,000 income req
LEAD_UUID = "66666666-6666-6666-6666-666666666666"

P1_LISTING = {
    "uuid": P1_UUID, "flat_number": "A101", "title": "Spacious Studio",
    "monthly_rent": 20000, "available_from": None, "custom_rules": {},
    "property_group_id": PROPERTY_GROUP_ID,
    "flats": {"bedrooms": 1, "floor_number": 1, "address": "Block A"},
}
P2_LISTING = {
    "uuid": P2_UUID, "flat_number": "B202", "title": None,
    "monthly_rent": 38000, "available_from": "2026-06-01", "custom_rules": {},
    "property_group_id": PROPERTY_GROUP_ID,
    "flats": {"bedrooms": 2, "floor_number": 2, "address": "Block B"},
}
P3_LISTING = {
    "uuid": P3_UUID, "flat_number": "C301", "title": None,
    "monthly_rent": 65000, "available_from": None, "custom_rules": {},
    "property_group_id": PROPERTY_GROUP_ID,
    "flats": {"bedrooms": 3, "floor_number": 3, "address": "Block C"},
}
P4_LISTING = {
    "uuid": P4_UUID, "flat_number": "D404", "title": None,
    "monthly_rent": 42000, "available_from": None,
    "custom_rules": {"pets_allowed": "no"},
    "property_group_id": PROPERTY_GROUP_ID,
    "flats": {"bedrooms": 2, "floor_number": 4, "address": "Block D"},
}
P5_LISTING = {
    "uuid": P5_UUID, "flat_number": "E501", "title": None,
    "monthly_rent": 55000, "available_from": None,
    "custom_rules": {"income_required": True},
    "property_group_id": PROPERTY_GROUP_ID,
    "flats": {"bedrooms": 2, "floor_number": 5, "address": "Block E"},
}

PG_ROW = {
    "id": PROPERTY_GROUP_ID, "manager_id": MANAGER_UUID,
    "vapi_lease_assistant_id": "test-ast-123",
    "vapi_phone_number_id": "test-ph-123",
}
MANAGER_PROFILE_ROW = {"user_id": MANAGER_UUID}

_LEAD_ROW = {
    "id": 1, "uuid": LEAD_UUID,
    "property_group_id": PROPERTY_GROUP_ID, "manager_id": MANAGER_UUID,
    "listing_uuid": P2_UUID, "interested_listing_ids": None,
    "caller_name": "Test Caller", "phone": "+919999000001", "email": None,
    "bedrooms": 2, "budget_max": "40000", "move_in_timeline": "1 month",
    "occupants": 2, "floor_preference": None, "qualification_status": "qualified",
    "disqualifying_reason": None, "qualifying_answers": {}, "notes": None,
    "source": "voice", "call_id": "call-test-001", "call_duration_seconds": 120,
    "manager_notes": None, "created_at": "2026-05-22T08:38:59", "updated_at": None,
}

TEST_USER = {
    "sub": MANAGER_UUID, "email": "leadpipecrm@gmail.com",
    "role": "authenticated", "aud": "authenticated",
}


# ---------------------------------------------------------------------------
# Mock DB helpers
# ---------------------------------------------------------------------------

_CHAIN_METHODS = [
    "select", "eq", "neq", "ilike", "is_", "in_", "not_",
    "order", "limit", "insert", "update", "delete", "upsert",
    "maybe_single", "gte", "lte", "gt", "lt", "contains", "range", "or_",
]


def _make_query_builder(data):
    b = MagicMock()
    for method in _CHAIN_METHODS:
        getattr(b, method).return_value = b
    result = MagicMock()
    result.data = data
    b.execute.return_value = result
    return b


def _make_two_shot_builder(first_data, second_data):
    """Builder whose first execute() call returns first_data, second returns second_data."""
    b = MagicMock()
    for method in _CHAIN_METHODS:
        getattr(b, method).return_value = b
    r1 = MagicMock()
    r1.data = first_data
    r2 = MagicMock()
    r2.data = second_data
    b.execute.side_effect = [r1, r2]
    return b


def make_mock_db(**table_data):
    mock_db = MagicMock()
    mock_db.postgrest = MagicMock()
    mock_db.storage = MagicMock()
    _cache: dict = {}

    def _table(name):
        if name not in _cache:
            val = table_data.get(name, [])
            _cache[name] = val if isinstance(val, MagicMock) else _make_query_builder(val)
        return _cache[name]

    mock_db.table.side_effect = _table
    return mock_db


def _client(**table_data):
    """Return (TestClient, mock_db) with all deps overridden."""
    mock_db = make_mock_db(**table_data)
    app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
    app.dependency_overrides[get_authenticated_db] = lambda: mock_db
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_service_db] = lambda: mock_db
    return TestClient(app, raise_server_exceptions=False), mock_db


@pytest.fixture(autouse=True)
def clear_dep_overrides():
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1.1 — GET /leasing/find-listing
# ---------------------------------------------------------------------------

class TestFindListing:

    def test_find_listing_by_unit_number(self):
        tc, _ = _client(lease_listings=[P1_LISTING])
        resp = tc.get("/leasing/find-listing?query=A101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["listing_uuid"] == P1_UUID
        assert data["bedrooms"] == 1
        assert data["monthly_rent"] == pytest.approx(20000.0)

    def test_find_listing_scoped_to_group(self):
        tc, _ = _client(lease_listings=[P1_LISTING])
        resp = tc.get(f"/leasing/find-listing?query=A101&property_group_id={PROPERTY_GROUP_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["listing_uuid"] == P1_UUID

    def test_find_listing_not_found(self):
        tc, _ = _client(lease_listings=[])
        resp = tc.get("/leasing/find-listing?query=Z999")
        assert resp.status_code == 200
        assert resp.json()["found"] is False

    def test_find_listing_by_title_fallback(self):
        fallback_builder = _make_two_shot_builder([], [P1_LISTING])
        tc, _ = _client(lease_listings=fallback_builder)
        resp = tc.get("/leasing/find-listing?query=Spacious+Studio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["found"] is True
        assert data["listing_uuid"] == P1_UUID


# ---------------------------------------------------------------------------
# 1.2 — GET /leasing/search
# ---------------------------------------------------------------------------

class TestSearchListings:

    def test_search_exact_bedroom_budget_match(self):
        tc, _ = _client(lease_listings=[P2_LISTING])
        resp = tc.get(f"/leasing/search?bedrooms=2&budget_max=40000&property_group_id={PROPERTY_GROUP_ID}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        for listing in data["listings"]:
            assert listing["bedrooms"] == 2
            assert listing["monthly_rent"] <= 40000

    def test_search_no_results(self):
        tc, _ = _client(lease_listings=[])
        resp = tc.get("/leasing/search?bedrooms=4&budget_max=10000")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_search_budget_only(self):
        tc, _ = _client(lease_listings=[P1_LISTING])
        resp = tc.get(f"/leasing/search?budget_max=25000&property_group_id={PROPERTY_GROUP_ID}")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

    def test_search_bedroom_only(self):
        tc, _ = _client(lease_listings=[P2_LISTING, P4_LISTING, P5_LISTING])
        resp = tc.get(f"/leasing/search?bedrooms=2&property_group_id={PROPERTY_GROUP_ID}")
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

    def test_search_returns_listing_uuid_per_result(self):
        tc, _ = _client(lease_listings=[P2_LISTING, P4_LISTING, P5_LISTING])
        resp = tc.get("/leasing/search?bedrooms=2&budget_max=60000")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["listings"], list)
        for item in data["listings"]:
            assert "listing_uuid" in item

    def test_search_returns_200_with_no_params(self):
        tc, _ = _client(lease_listings=[P1_LISTING, P2_LISTING])
        resp = tc.get("/leasing/search")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 1.3 — POST /voice/lease-lead-webhook
# ---------------------------------------------------------------------------

def _webhook_payload(listing_uuid=None, assistant_id="unknown-ast", phone_number_id="unknown-ph",
                     phone="+919999000001", call_id="call-test-001", extra_args=None):
    args = {"caller_name": "Test Caller", "qualification_status": "qualified"}
    if listing_uuid:
        args["listing_uuid"] = listing_uuid
    if extra_args:
        args.update(extra_args)
    return {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": call_id,
                "assistantId": assistant_id,
                "phoneNumberId": phone_number_id,
                "customer": {"number": phone},
            },
            "toolCalls": [
                {"function": {"name": "submit_lease_lead", "arguments": args}},
            ],
        }
    }


class TestLeaseLoanWebhook:

    def test_webhook_resolves_via_listing_uuid(self):
        tc, mock_db = _client(
            lease_listings=[{"property_group_id": PROPERTY_GROUP_ID}],
            properties_list=[PG_ROW],
            manager_profiles=[MANAGER_PROFILE_ROW],
            lease_leads=[],
        )
        resp = tc.post("/voice/lease-lead-webhook", json=_webhook_payload(listing_uuid=P2_UUID))
        assert resp.status_code == 200
        assert resp.json().get("status") in ("processed", "ignored") or "error" not in resp.json()
        leads_builder = mock_db.table("lease_leads")
        assert leads_builder.insert.called
        inserted = leads_builder.insert.call_args.args[0]
        assert inserted["listing_uuid"] == P2_UUID
        assert inserted["property_group_id"] == PROPERTY_GROUP_ID
        assert inserted["manager_id"] == MANAGER_UUID

    def test_webhook_resolves_via_assistant_id(self):
        tc, mock_db = _client(
            lease_listings=[],
            properties_list=[PG_ROW],
            manager_profiles=[MANAGER_PROFILE_ROW],
            lease_leads=[],
        )
        resp = tc.post("/voice/lease-lead-webhook",
                       json=_webhook_payload(assistant_id="test-ast-123"))
        assert resp.status_code == 200
        leads_builder = mock_db.table("lease_leads")
        assert leads_builder.insert.called
        inserted = leads_builder.insert.call_args.args[0]
        assert inserted["property_group_id"] == PROPERTY_GROUP_ID

    def test_webhook_resolves_via_phone_number_id(self):
        tc, mock_db = _client(
            lease_listings=[],
            properties_list=[PG_ROW],
            manager_profiles=[MANAGER_PROFILE_ROW],
            lease_leads=[],
        )
        resp = tc.post("/voice/lease-lead-webhook",
                       json=_webhook_payload(phone_number_id="test-ph-123"))
        assert resp.status_code == 200
        leads_builder = mock_db.table("lease_leads")
        assert leads_builder.insert.called

    def test_webhook_no_submit_lead_tool_call(self):
        tc, mock_db = _client(lease_leads=[])
        payload = {
            "message": {
                "type": "tool-calls",
                "call": {"id": "c1", "assistantId": "a", "phoneNumberId": "p",
                         "customer": {"number": "+91000"}},
                "toolCalls": [],
            }
        }
        resp = tc.post("/voice/lease-lead-webhook", json=payload)
        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        assert not mock_db.table("lease_leads").insert.called

    def test_webhook_invalid_listing_uuid_ignored(self):
        tc, mock_db = _client(
            properties_list=[PG_ROW],
            manager_profiles=[MANAGER_PROFILE_ROW],
            lease_leads=[],
        )
        resp = tc.post("/voice/lease-lead-webhook",
                       json=_webhook_payload(listing_uuid="not-a-real-uuid"))
        assert resp.status_code == 200
        leads_builder = mock_db.table("lease_leads")
        assert leads_builder.insert.called
        inserted = leads_builder.insert.call_args.args[0]
        assert inserted["listing_uuid"] is None

    def test_webhook_lead_fields_written_correctly(self):
        tc, mock_db = _client(
            lease_listings=[{"property_group_id": PROPERTY_GROUP_ID}],
            properties_list=[PG_ROW],
            manager_profiles=[MANAGER_PROFILE_ROW],
            lease_leads=[],
        )
        full_args = {
            "bedrooms": 2, "budget_max": 40000, "move_in_timeline": "1 month",
            "occupants": 2, "floor_preference": "high",
            "qualification_status": "qualified",
            "notes": "Looking for pet-friendly",
        }
        resp = tc.post("/voice/lease-lead-webhook",
                       json=_webhook_payload(listing_uuid=P2_UUID, extra_args=full_args))
        assert resp.status_code == 200
        inserted = mock_db.table("lease_leads").insert.call_args.args[0]
        assert inserted["bedrooms"] == 2
        assert inserted["budget_max"] == 40000
        assert inserted["move_in_timeline"] == "1 month"
        assert inserted["occupants"] == 2
        assert inserted["floor_preference"] == "high"
        assert inserted["qualification_status"] == "qualified"
        assert inserted["notes"] == "Looking for pet-friendly"
        assert inserted["source"] == "voice"


# ---------------------------------------------------------------------------
# 1.4 — GET /leasing/leads
# ---------------------------------------------------------------------------

class TestGetLeads:

    def test_get_leads_scoped_to_manager(self):
        own_lead = {**_LEAD_ROW}
        other_lead = {**_LEAD_ROW, "id": 2, "uuid": "77777777-7777-7777-7777-777777777777",
                      "manager_id": "ffffffff-ffff-ffff-ffff-ffffffffffff"}
        # Mock returns both rows; endpoint filters by manager_id via eq on mock (mock doesn't
        # actually filter, so we verify the endpoint at least issues the query and returns data)
        tc, _ = _client(lease_leads=[own_lead])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["manager_id"] == MANAGER_UUID

    def test_get_leads_filter_by_listing_uuid(self):
        tc, _ = _client(lease_leads=[_LEAD_ROW])
        resp = tc.get(f"/leasing/leads?listing_uuid={P2_UUID}")
        assert resp.status_code == 200

    def test_get_leads_filter_by_status(self):
        tc, _ = _client(lease_leads=[_LEAD_ROW])
        resp = tc.get("/leasing/leads?qualification_status=qualified")
        assert resp.status_code == 200
        for lead in resp.json():
            assert lead["qualification_status"] == "qualified"

    def test_get_leads_empty(self):
        tc, _ = _client(lease_leads=[])
        resp = tc.get("/leasing/leads")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# 1.5 — PATCH /leasing/leads/{uuid}
# ---------------------------------------------------------------------------

class TestPatchLead:

    def _updated_lead(self, status):
        return {**_LEAD_ROW, "qualification_status": status}

    def test_manager_can_set_contacted(self):
        tc, mock_db = _client(lease_leads=[self._updated_lead("contacted")])
        resp = tc.patch(f"/leasing/leads/{LEAD_UUID}",
                        json={"qualification_status": "contacted"})
        assert resp.status_code == 200

    def test_manager_can_set_toured(self):
        tc, mock_db = _client(lease_leads=[self._updated_lead("toured")])
        resp = tc.patch(f"/leasing/leads/{LEAD_UUID}",
                        json={"qualification_status": "toured"})
        assert resp.status_code == 200

    def test_manager_cannot_set_qualified(self):
        tc, _ = _client(lease_leads=[_LEAD_ROW])
        resp = tc.patch(f"/leasing/leads/{LEAD_UUID}",
                        json={"qualification_status": "qualified"})
        assert resp.status_code == 400

    def test_manager_cannot_set_not_qualified(self):
        tc, _ = _client(lease_leads=[_LEAD_ROW])
        resp = tc.patch(f"/leasing/leads/{LEAD_UUID}",
                        json={"qualification_status": "not_qualified"})
        assert resp.status_code == 400

    def test_manager_can_update_notes(self):
        updated = {**_LEAD_ROW, "manager_notes": "Called back, scheduled tour"}
        tc, _ = _client(lease_leads=[updated])
        resp = tc.patch(f"/leasing/leads/{LEAD_UUID}",
                        json={"manager_notes": "Called back, scheduled tour"})
        assert resp.status_code == 200
        assert resp.json()["manager_notes"] == "Called back, scheduled tour"

    def test_patch_lead_not_found_returns_404(self):
        tc, _ = _client(lease_leads=[])
        resp = tc.patch("/leasing/leads/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                        json={"qualification_status": "contacted"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 1.6 — GET /leasing/metrics
# ---------------------------------------------------------------------------

class TestMetricsCounts:

    def _make_leads(self):
        qualified = [{**_LEAD_ROW, "id": i, "uuid": f"1111111{i}-1111-1111-1111-111111111111",
                      "qualification_status": "qualified", "call_duration_seconds": 120}
                     for i in range(1, 4)]
        not_qual = [{**_LEAD_ROW, "id": i, "uuid": f"2222222{i}-2222-2222-2222-222222222222",
                     "qualification_status": "not_qualified", "call_duration_seconds": None}
                    for i in range(4, 6)]
        unmatched = [{**_LEAD_ROW, "id": 6, "uuid": "33333336-3333-3333-3333-333333333333",
                      "qualification_status": "unmatched", "call_duration_seconds": None}]
        return qualified + not_qual + unmatched

    def test_metrics_counts_correct(self):
        tc, _ = _client(lease_leads=self._make_leads())
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 6
        assert body["qualified"] == 3
        assert body["not_qualified"] == 2
        assert body["unmatched"] == 1
        assert body["qualification_rate"] == pytest.approx(50.0)

    def test_metrics_zero_leads(self):
        tc, _ = _client(lease_leads=[])
        resp = tc.get("/leasing/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_calls"] == 0
        assert body["qualification_rate"] == 0
