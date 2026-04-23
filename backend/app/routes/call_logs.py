"""
Call logs API routes using Supabase client.
Handles retrieval of voice call logs.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client
from datetime import datetime, timezone, timedelta
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

IST = timezone(timedelta(hours=5, minutes=30))

router = APIRouter(prefix="/call_logs", tags=["Call Logs"])


@router.get("/stats")
async def get_call_stats(
    days: int = Query(30, description="Number of days to look back"),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Return aggregate stats and recent call logs for the AI Voice Agent Stats tab."""
    try:
        since = (datetime.now(IST) - timedelta(days=days)).isoformat()
        logs_resp = (
            db.table("call_logs")
            .select("*")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .execute()
        )
        logs = logs_resp.data or []
        total = len(logs)
        resolved = sum(1 for l in logs if l.get("complaint_status") in ("resolved", "closed"))
        escalated = sum(1 for l in logs if l.get("complaint_status") == "escalated")

        by_date: dict = {}
        for log in logs:
            d = (log.get("created_at") or "")[:10]
            if d:
                by_date[d] = by_date.get(d, 0) + 1

        return {
            "total": total,
            "resolved": resolved,
            "escalated": escalated,
            "by_date": by_date,
            "recent": logs[:20],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching call stats: {str(e)}")


@router.get("")
async def get_all_call_logs(user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)):
    """Get all call logs ordered by created_at (newest first)."""
    try:
        response = db.table("call_logs")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()

        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call logs: {str(e)}"
        )


@router.get("/{call_log_id}")
async def get_call_log_by_id(
    call_log_id: int,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
):
    """Get a specific call log by ID."""
    try:
        response = db.table("call_logs")\
            .select("*")\
            .eq("id", call_log_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Call log with id {call_log_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call log: {str(e)}"
        )
