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
    building_name: str
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
            .order("building_name")\
            .order("flat_number")\
            .execute()
        
        # Map flats to properties format
        properties = []
        image_urls = [
            "/assets/adam-winger-A4U4dEuN-hw-unsplash.jpg",
            "/assets/adam-winger-PCDlE94JjcI-unsplash.jpg",
            "/assets/douglas-sheppard-9rYfG8sWRVo-unsplash.jpg",
            "/assets/leohoho-QL7KdXdcfWA-unsplash.jpg",
            "/assets/outsite-co-R-LK3sqLiBw-unsplash.jpg",
            "/assets/pixasquare-4ojhpgKpS68-unsplash.jpg",
            "/assets/rowan-heuvel-bjej8BY1JYQ-unsplash.jpg",
            "/assets/samuel-ryde-dn37EiGIpq4-unsplash.jpg"
        ]
        
        for index, flat in enumerate(response.data):
            # Compute derived fields
            bedrooms = flat.get('bedrooms') or 2  # Default to 2 if not set
            bathrooms = bedrooms + 1  # bathrooms = bedrooms + 1 as per requirement
            
            # Generate property name from flat number and building
            property_name = f"{flat.get('building_name', 'Building')} - Unit {flat.get('flat_number', 'N/A')}"
            
            # Generate address from building and floor
            floor_text = f"Floor {flat.get('floor_number', 0)}"
            address = f"{flat.get('building_name', 'Building')}, {floor_text}"
            
            # Cycle through images
            image_url = image_urls[index % len(image_urls)]
            
            properties.append({
                "id": flat["id"],
                "uuid": flat["uuid"],
                "name": property_name,
                "address": address,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "image_url": image_url,
                "flat_number": flat.get("flat_number", "N/A"),
                "building_name": flat.get("building_name", "Building"),
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
