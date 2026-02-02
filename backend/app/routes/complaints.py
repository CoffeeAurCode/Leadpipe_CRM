"""
Complaints API routes using Supabase client.
Handles CRUD operations for tenant complaints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate, ComplaintResponse

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    complaint_data: ComplaintCreate,
    db: Client = Depends(get_db)
):
    """Create a new complaint."""
    try:
        response = db.table("complaints").insert(complaint_data.model_dump()).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create complaint"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating complaint: {str(e)}"
        )


@router.get("", response_model=list[ComplaintResponse])
async def get_all_complaints(db: Client = Depends(get_db)):
    """Get all complaints ordered by created_at (newest first)."""
    try:
        response = db.table("complaints")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complaints: {str(e)}"
        )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_by_id(
    complaint_id: int,
    db: Client = Depends(get_db)
):
    """Get a specific complaint by ID."""
    try:
        response = db.table("complaints")\
            .select("*")\
            .eq("id", complaint_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with id {complaint_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complaint: {str(e)}"
        )


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    complaint_data: ComplaintUpdate,
    db: Client = Depends(get_db)
):
    """Update a complaint's fields."""
    try:
        # Prepare update data (exclude unset fields)
        update_data = complaint_data.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update the complaint
        response = db.table("complaints")\
            .update(update_data)\
            .eq("id", complaint_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with id {complaint_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating complaint: {str(e)}"
        )
