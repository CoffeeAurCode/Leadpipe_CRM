"""
Call logs API routes using Supabase client.
Handles retrieval of voice call logs.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db

router = APIRouter(prefix="/call_logs", tags=["Call Logs"])


@router.get("")
async def get_all_call_logs(db: Client = Depends(get_db)):
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
    db: Client = Depends(get_db)
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
