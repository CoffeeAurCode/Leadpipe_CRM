"""
Property Types API Routes
Returns the seeded property type classifications for buildings.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/property-types", tags=["Property Types"])


class PropertyTypeResponse(BaseModel):
    id: UUID
    name: str
    icon_type: str
    created_at: datetime


@router.get("", response_model=List[PropertyTypeResponse])
async def get_property_types(db: Client = Depends(get_db)):
    """Get all property type classifications (Residential, Commercial, Mixed-use)."""
    try:
        response = db.table("property_types").select("*").order("name").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching property types: {str(e)}"
        )
