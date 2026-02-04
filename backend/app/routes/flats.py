"""
Flats API routes using Supabase client.
Handles CRUD operations and verification for flats.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from app.schemas.flat import (
    FlatCreate, 
    FlatUpdate, 
    FlatResponse, 
    FlatVerifyRequest, 
    FlatVerifyResponse
)

router = APIRouter(prefix="/flats", tags=["Flats"])


@router.post("/verify", response_model=FlatVerifyResponse)
async def verify_flat(
    request: FlatVerifyRequest,
    db: Client = Depends(get_db)
):
    """
    Verify if a flat exists in the database.
    
    This endpoint is designed for VAPI voice agent integration.
    The agent can call this to check if the flat number provided
    by the caller actually exists before creating a complaint.
    """
    try:
        response = db.table("flats")\
            .select("*")\
            .eq("flat_number", request.flat_number)\
            .execute()
        
        if response.data:
            return FlatVerifyResponse(
                exists=True,
                flat=response.data[0]
            )
        else:
            return FlatVerifyResponse(
                exists=False,
                flat=None
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying flat: {str(e)}"
        )


@router.get("", response_model=list[FlatResponse])
async def get_all_flats(db: Client = Depends(get_db)):
    """Get all flats ordered by building and flat number."""
    try:
        response = db.table("flats")\
            .select("*")\
            .order("building_name")\
            .order("flat_number")\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flats: {str(e)}"
        )


@router.get("/{flat_number}", response_model=FlatResponse)
async def get_flat_by_number(
    flat_number: str,
    db: Client = Depends(get_db)
):
    """Get a specific flat by flat_number."""
    try:
        response = db.table("flats")\
            .select("*")\
            .eq("flat_number", flat_number)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat {flat_number} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flat: {str(e)}"
        )


@router.post("", response_model=FlatResponse, status_code=status.HTTP_201_CREATED)
async def create_flat(
    flat_data: FlatCreate,
    db: Client = Depends(get_db)
):
    """Create a new flat."""
    try:
        response = db.table("flats").insert(flat_data.model_dump()).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create flat"
            )
    except Exception as e:
        if "duplicate key" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flat {flat_data.flat_number} already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating flat: {str(e)}"
        )


@router.patch("/{flat_id}", response_model=FlatResponse)
async def update_flat(
    flat_id: int,
    flat_data: FlatUpdate,
    db: Client = Depends(get_db)
):
    """Update a flat's details."""
    try:
        # Prepare update data (exclude unset fields)
        update_data = flat_data.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update the flat
        response = db.table("flats")\
            .update(update_data)\
            .eq("id", flat_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat with id {flat_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating flat: {str(e)}"
        )
