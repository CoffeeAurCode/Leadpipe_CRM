"""
Properties API routes using Supabase client.
Maps flats data to properties format for the Properties page.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from typing import List
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
    bathrooms: int
    image_url: str
    flat_number: str
    address: str
    floor_number: int
    occupied: bool
    created_at: datetime


@router.get("", response_model=List[PropertyResponse])
async def get_all_properties(db: Client = Depends(get_db)):
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
            bedrooms = flat.get('bedrooms') or 2  # Default to 2 if not set
            bathrooms = bedrooms + 1  # bathrooms = bedrooms + 1 as per requirement
            
            # Generate property name from flat number and building
            property_name = f"{flat.get('address', 'Building')} - Unit {flat.get('flat_number', 'N/A')}"
            
            # Generate address from building and floor
            floor_text = f"Floor {flat.get('floor_number', 0)}"
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
                "address": flat.get("address", "Building"),
                "floor_number": flat.get("floor_number", 0),
                "occupied": flat.get("occupied", True),
                "created_at": flat["created_at"]
            })
        
        return properties
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching properties: {str(e)}"
        )
