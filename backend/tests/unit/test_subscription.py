"""
Unit tests for app/dependencies/subscription.py — Section 3.5 of TEST_PLAN.md

require_active_subscription allows active/trialing, blocks everything else.
"""
import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException

from app.dependencies.subscription import require_active_subscription

TEST_USER = {"sub": "user-uuid-123", "email": "test@example.com"}


def _mock_db_with_subscription(statuses: list[dict]):
    """Return a mock DB client whose subscriptions query returns the given rows."""
    mock_db = MagicMock()
    (
        mock_db.table.return_value
        .select.return_value
        .eq.return_value
        .in_.return_value
        .limit.return_value
        .execute.return_value
        .data
    ) = statuses
    return mock_db


class TestRequireActiveSubscription:
    @pytest.mark.asyncio
    async def test_active_subscription_allows_request(self):
        db = _mock_db_with_subscription([{"status": "active"}])
        result = await require_active_subscription(user=TEST_USER, db=db)
        assert result == TEST_USER

    @pytest.mark.asyncio
    async def test_trialing_subscription_allows_request(self):
        db = _mock_db_with_subscription([{"status": "trialing"}])
        result = await require_active_subscription(user=TEST_USER, db=db)
        assert result == TEST_USER

    @pytest.mark.asyncio
    async def test_past_due_subscription_raises_403(self):
        # DB returns no rows (status is past_due, not in the in_ filter)
        db = _mock_db_with_subscription([])
        with pytest.raises(HTTPException) as exc_info:
            await require_active_subscription(user=TEST_USER, db=db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cancelled_subscription_raises_403(self):
        db = _mock_db_with_subscription([])
        with pytest.raises(HTTPException) as exc_info:
            await require_active_subscription(user=TEST_USER, db=db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_subscription_record_raises_403(self):
        db = _mock_db_with_subscription([])
        with pytest.raises(HTTPException) as exc_info:
            await require_active_subscription(user=TEST_USER, db=db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_403_detail_mentions_subscription(self):
        db = _mock_db_with_subscription([])
        with pytest.raises(HTTPException) as exc_info:
            await require_active_subscription(user=TEST_USER, db=db)
        assert "subscription" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_uses_manager_id_from_sub_claim(self):
        user = {"sub": "specific-manager-uuid"}
        db = _mock_db_with_subscription([{"status": "active"}])
        result = await require_active_subscription(user=user, db=db)
        # Verify .eq() was called with the correct manager_id
        db.table.return_value.select.return_value.eq.assert_called_once_with(
            "manager_id", "specific-manager-uuid"
        )
        assert result == user
