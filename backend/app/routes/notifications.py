"""
In-app Notifications API routes.
Reads from the `notifications` table (manager-scoped).

Required DB migration before use:
  CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id UUID REFERENCES auth.users(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    type TEXT NOT NULL,  -- 'appointment' | 'complaint' | 'rent' | 'system'
    entity_id UUID,
    is_read BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT now()
  );
  CREATE INDEX idx_notifications_manager ON notifications(manager_id, created_at DESC);
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from supabase import Client
from typing import Optional
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreate(BaseModel):
    title: str
    body: str
    type: str
    entity_id: Optional[str] = None


@router.get("")
async def get_notifications(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Return the 50 most recent notifications for the current manager."""
    manager_id = user["sub"]
    try:
        resp = (
            db.table("notifications")
            .select("*")
            .eq("manager_id", manager_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        # Table may not exist yet — return empty list gracefully
        print(f"[notifications] fetch error (table may not exist): {e}")
        return []


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Mark a single notification as read."""
    manager_id = user["sub"]
    try:
        resp = (
            db.table("notifications")
            .update({"is_read": True})
            .eq("id", notification_id)
            .eq("manager_id", manager_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=404, detail="Notification not found")
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking notification read: {str(e)}")


@router.post("/read-all")
async def mark_all_read(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Mark all unread notifications as read for the current manager."""
    manager_id = user["sub"]
    try:
        db.table("notifications").update({"is_read": True}).eq("manager_id", manager_id).eq("is_read", False).execute()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error marking all read: {str(e)}")


@router.post("", status_code=201)
async def create_notification(
    body: NotificationCreate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Create a notification for the current manager (used by frontend actions)."""
    manager_id = user["sub"]
    try:
        payload = {
            "manager_id": manager_id,
            "title": body.title,
            "body": body.body,
            "type": body.type,
            "is_read": False,
        }
        if body.entity_id:
            payload["entity_id"] = body.entity_id

        resp = db.table("notifications").insert(payload).execute()
        if not resp.data:
            raise HTTPException(status_code=500, detail="Failed to create notification")
        return resp.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating notification: {str(e)}")
