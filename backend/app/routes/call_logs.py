"""
Call logs API routes using Supabase client.
Handles retrieval of voice call logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

router = APIRouter(prefix="/call_logs", tags=["Call Logs"])


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
