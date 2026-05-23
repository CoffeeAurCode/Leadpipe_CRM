"""
Properties API routes using Supabase client.
Maps flats data to properties format for the Properties page.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/properties", tags=["Properties"])


class PropertyResponse(BaseModel):
    """Response model for property listing"""
    id: int
    uuid: UUID
    name: str
    address: str
    bedrooms: int
    bathrooms: Optional[int] = None
    image_url: str
    flat_number: str
    floor_number: Optional[int] = None
    occupied: bool
    tenant_uuid: UUID | None = None
    created_at: datetime


@router.get("", response_model=List[PropertyResponse])
async def get_all_properties(user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Get all properties (flats) for the properties listing page.
    Maps flat data to property format with computed fields.
    """
    try:
        # Fetch all flats from database
        response = db.table("flats")\
            .select("*")\
            .order("address")\
            .order("flat_number")\
            .execute()
        
        # Map flats to properties format
        properties = []
        
        for index, flat in enumerate(response.data):
            # Compute derived fields
            bedrooms = flat.get('bedrooms') or 2
            bathrooms = flat.get('bathrooms')  # None if not set — frontend shows 0
            
            # Generate property name from flat number and building
            property_name = f"{flat.get('address', 'Building')} - Unit {flat.get('flat_number', 'N/A')}"
            
            # Generate address from building and floor
            floor_text = f"Floor {flat.get('floor_number', '')}" if flat.get('floor_number') is not None else ""
            address_text = f"{flat.get('address', 'Building')}, {floor_text}"
            
            # Use image_url from database or fallback to placeholder
            # Check if image_url exists and is not empty
            db_image_url = flat.get('image_url')
            if db_image_url and len(str(db_image_url).strip()) > 0:
                image_url = db_image_url
            else:
                # Fallback placeholder if no image in DB
                image_url = "https://images.unsplash.com/photo-1560448204-e02f11c3d0af?q=80&w=2574&auto=format&fit=crop"
            
            properties.append({
                "id": flat["id"],
                "uuid": flat["uuid"],
                "name": property_name,
                "address": address_text,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "image_url": image_url,
                "flat_number": flat.get("flat_number", "N/A"),
                "floor_number": flat.get("floor_number"),
                "occupied": flat.get("tenant_uuid") is not None,  # Fix: Derive strictly from tenant presence
                "tenant_uuid": flat.get("tenant_uuid"),
                "created_at": flat["created_at"]
            })
        
        return properties
        
    except Exception as e:
        msg = getattr(e, 'message', None) or "A database error occurred. Please try again."
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching properties: {msg}"
        )
