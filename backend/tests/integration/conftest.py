"""
Shared fixtures for backend integration tests.

Strategy:
  - Import the real FastAPI app
  - Override dependencies to inject mock DBs and bypass auth/subscription checks
  - make_mock_db() builds a Supabase client mock with per-table response data
  - Fixtures expose different client variants: authed (subscription bypassed),
    no_sub (auth bypassed, subscription real), unauthenticated
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, get_service_db
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

TEST_USER = {
    "sub": "test-manager-uuid",
    "email": "test@example.com",
    "role": "authenticated",
    "aud": "authenticated",
}

FLAT_UUID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
TENANT_UUID = "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
COMPLAINT_UUID = "cccccccc-dddd-eeee-ffff-aaaaaaaaaaaa"
BUILDING_UUID = "dddddddd-eeee-ffff-aaaa-bbbbbbbbbbbb"
PROPERTY_UUID = "eeeeeeee-ffff-aaaa-bbbb-cccccccccccc"


def _make_query_builder(data):
    """Return a fluent MagicMock query builder that returns `data` on .execute()."""
    b = MagicMock()
    for method in [
        "select", "eq", "neq", "ilike", "is_", "in_", "not_",
        "order", "limit", "insert", "update", "delete", "upsert",
        "maybe_single", "gte", "lte", "gt", "lt", "contains", "range",
    ]:
        getattr(b, method).return_value = b

    result = MagicMock()
    result.data = data
    b.execute.return_value = result
    return b


def make_mock_db(**table_data):
    """
    Create a mock Supabase client whose .table() calls return configured data.

    Pass keyword args mapping table name → list of row dicts.
    Any table not listed returns [].

    For more complex scenarios (different results on repeated calls to the same
    table), pass a pre-built MagicMock as the value instead of a list.

    Usage::

        db = make_mock_db(
            flats=[{"uuid": FLAT_UUID, "flat_number": "A-101", "tenant_uuid": None}],
            tenants=[],
        )
    """
    mock_db = MagicMock()
    mock_db.postgrest = MagicMock()
    mock_db.storage = MagicMock()

    _cache: dict = {}

    def _table(name):
        if name not in _cache:
            val = table_data.get(name, [])
            if isinstance(val, MagicMock):
                _cache[name] = val
            else:
                _cache[name] = _make_query_builder(val)
        return _cache[name]

    mock_db.table.side_effect = _table
    return mock_db


def _apply_overrides(mock_db, bypass_subscription=True):
    if bypass_subscription:
        app.dependency_overrides[require_active_subscription] = lambda: TEST_USER
    app.dependency_overrides[get_authenticated_db] = lambda: mock_db
    app.dependency_overrides[get_db] = lambda: mock_db
    app.dependency_overrides[get_service_db] = lambda: mock_db


@pytest.fixture
def authed_client():
    """
    Factory fixture.  Call it with **table_data to get (TestClient, mock_db).

    Example::

        tc, db = authed_client(flats=[...], tenants=[])
        response = tc.get("/flats")
    """
    created = []

    def _factory(**table_data):
        mock_db = make_mock_db(**table_data)
        _apply_overrides(mock_db, bypass_subscription=True)
        client = TestClient(app, raise_server_exceptions=False)
        created.append(client)
        return client, mock_db

    yield _factory

    app.dependency_overrides.clear()


@pytest.fixture
def no_sub_client():
    """
    Client where auth is bypassed but the real subscription check runs.
    The mock DB returns no subscription rows → expect 403.
    """
    from app.dependencies.auth import get_current_user

    mock_db = make_mock_db(subscriptions=[])

    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    app.dependency_overrides[get_service_db] = lambda: mock_db
    app.dependency_overrides[get_authenticated_db] = lambda: mock_db
    app.dependency_overrides[get_db] = lambda: mock_db

    client = TestClient(app, raise_server_exceptions=False)
    yield client
    app.dependency_overrides.clear()
