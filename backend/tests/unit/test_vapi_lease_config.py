"""
Unit tests for build_lease_config() / build_lease_config_shared().

These are pure-Python, no HTTP, no DB — they validate the config dict that gets
pushed to VAPI. If these tests break, the agent will behave incorrectly even if
the backend is fine.

Run: pytest backend/tests/unit/test_vapi_lease_config.py -v
"""
import pytest
from app.services.vapi_agent_config import (
    build_lease_config,
    build_lease_config_shared,
    build_complaint_config,
)

BACKEND = "https://tenant-management-mvp.onrender.com"
MANAGER_ID = "28c43c77-8c9c-496f-8d1e-39ffa9d619e3"


@pytest.fixture
def lease_cfg():
    return build_lease_config(BACKEND, MANAGER_ID)


@pytest.fixture
def shared_cfg():
    return build_lease_config_shared(BACKEND)


@pytest.fixture
def complaint_cfg():
    return build_complaint_config(BACKEND)


# ---------------------------------------------------------------------------
# Top-level shape
# ---------------------------------------------------------------------------

class TestLeaseConfigShape:
    def test_has_required_top_level_keys(self, lease_cfg):
        for key in ("name", "first_message", "model", "server_messages", "transcriber", "voice"):
            assert key in lease_cfg, f"missing key: {key}"

    def test_server_messages_is_end_of_call_only(self, lease_cfg):
        """Lease agent must NOT have 'tool-calls' in server_messages — adding it breaks all tools."""
        assert lease_cfg["server_messages"] == ["end-of-call-report"]

    def test_model_has_tools(self, lease_cfg):
        tools = lease_cfg["model"]["tools"]
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_name_contains_manager_id_prefix(self, lease_cfg):
        assert MANAGER_ID[:8] in lease_cfg["name"]

    def test_shared_config_name_does_not_contain_manager_id(self, shared_cfg):
        assert MANAGER_ID not in shared_cfg.get("name", "")


# ---------------------------------------------------------------------------
# Tool inventory — load_listings
# ---------------------------------------------------------------------------

class TestLoadListingsTool:
    def _get_tool(self, cfg, name):
        return next((t for t in cfg["model"]["tools"] if t.get("name") == name), None)

    def test_load_listings_present(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        assert tool is not None, "load_listings tool must be present"

    def test_load_listings_is_async(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        assert tool.get("async") is True, "load_listings must be async=True so it fires while agent is talking"

    def test_load_listings_url_contains_manager_id(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        assert MANAGER_ID in tool["url"]

    def test_load_listings_url_points_to_listings_for_agent(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        assert "/leasing/listings-for-agent" in tool["url"]

    def test_load_listings_is_GET(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        assert tool.get("method", "").upper() == "GET"

    def test_load_listings_variable_extraction_has_has_more(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        props = tool["variableExtractionPlan"]["schema"]["properties"]
        assert "has_more" in props, "has_more must be in variableExtractionPlan so agent can read the threshold flag"

    def test_load_listings_variable_extraction_has_count(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        props = tool["variableExtractionPlan"]["schema"]["properties"]
        assert "count" in props

    def test_load_listings_variable_extraction_has_listings(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "load_listings")
        props = tool["variableExtractionPlan"]["schema"]["properties"]
        assert "listings" in props

    def test_load_listings_shared_config_url_has_no_manager_id(self, shared_cfg):
        tool = self._get_tool(shared_cfg, "load_listings")
        assert MANAGER_ID not in tool["url"]


# ---------------------------------------------------------------------------
# Tool inventory — search_listings
# ---------------------------------------------------------------------------

class TestSearchListingsTool:
    def _get_tool(self, cfg, name):
        return next((t for t in cfg["model"]["tools"] if t.get("name") == name), None)

    def test_search_listings_present(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        assert tool is not None, "search_listings tool must be present"

    def test_search_listings_is_async(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        assert tool.get("async") is True

    def test_search_listings_url_contains_search_listings_path(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        assert "/leasing/search-listings" in tool["url"]

    def test_search_listings_url_contains_manager_id(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        assert MANAGER_ID in tool["url"]

    def test_search_listings_is_GET(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        assert tool.get("method", "").upper() == "GET"

    def test_search_listings_has_bedrooms_param(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        body_props = tool.get("body", {}).get("properties", {})
        assert "bedrooms" in body_props

    def test_search_listings_has_budget_max_param(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "search_listings")
        body_props = tool.get("body", {}).get("properties", {})
        assert "budget_max" in body_props


# ---------------------------------------------------------------------------
# Tool inventory — find_listing must be ABSENT
# ---------------------------------------------------------------------------

class TestFindListingRemoved:
    def _tool_names(self, cfg):
        return [t.get("name") for t in cfg["model"]["tools"]]

    def test_find_listing_not_in_lease_config(self, lease_cfg):
        assert "find_listing" not in self._tool_names(lease_cfg), (
            "find_listing was removed in the load_listings fix — must not reappear"
        )

    def test_find_listing_not_in_shared_config(self, shared_cfg):
        assert "find_listing" not in self._tool_names(shared_cfg)

    def test_search_available_listings_not_in_lease_config(self, lease_cfg):
        assert "search_available_listings" not in self._tool_names(lease_cfg)


# ---------------------------------------------------------------------------
# Tool inventory — submit_lease_lead
# ---------------------------------------------------------------------------

class TestSubmitLeaseLeadTool:
    def _get_tool(self, cfg, name):
        return next((t for t in cfg["model"]["tools"] if t.get("name") == name), None)

    def test_submit_lease_lead_present(self, lease_cfg):
        assert self._get_tool(lease_cfg, "submit_lease_lead") is not None

    def test_submit_lease_lead_url_contains_lease_lead_direct(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "submit_lease_lead")
        assert "/voice/lease-lead-direct" in tool["url"]

    def test_submit_lease_lead_required_fields(self, lease_cfg):
        tool = self._get_tool(lease_cfg, "submit_lease_lead")
        required = tool["body"].get("required", [])
        assert "caller_name" in required
        assert "qualification_status" in required


# ---------------------------------------------------------------------------
# Complaint config regression — must not be affected by lease changes
# ---------------------------------------------------------------------------

class TestComplaintConfigRegression:
    def test_complaint_server_messages_includes_tool_calls(self, complaint_cfg):
        """Complaint agent DOES need tool-calls because it uses function-type tools."""
        assert "tool-calls" in complaint_cfg["server_messages"]
        assert "end-of-call-report" in complaint_cfg["server_messages"]

    def test_verify_phone_number_present(self, complaint_cfg):
        tools = complaint_cfg["model"]["tools"]
        names = [t.get("name") or t.get("function", {}).get("name") for t in tools]
        assert "Verify_phone_number" in names

    def test_submit_complaint_present(self, complaint_cfg):
        tools = complaint_cfg["model"]["tools"]
        names = [t.get("function", {}).get("name") for t in tools]
        assert "submit_complaint" in names

    def test_complaint_config_has_no_load_listings(self, complaint_cfg):
        tools = complaint_cfg["model"]["tools"]
        names = [t.get("name") for t in tools]
        assert "load_listings" not in names
