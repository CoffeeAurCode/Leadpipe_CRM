"""
Subscription gate — ensures manager has an active or trialing subscription.
"""
from fastapi import Depends, HTTPException, status
from supabase import Client
from app.db.session import get_service_db
from app.dependencies.auth import get_current_user


async def require_active_subscription(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db),
) -> dict:
    """
    Raises 403 if the manager has no active/trialing subscription.
    Uses service client to bypass RLS.
    Returns the user payload for downstream use.
    """
    manager_id = user["sub"]

    result = (
        db.table("subscriptions")
        .select("status, trial_ends_at")
        .eq("manager_id", manager_id)
        .in_("status", ["trialing", "active"])
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No active subscription. Please subscribe to continue.",
        )

    return user
