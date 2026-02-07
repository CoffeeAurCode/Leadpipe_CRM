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
        complaint_dict = complaint_data.model_dump(mode='json')
        
        # Handle UUID-based flat reference (preferred over flat_number)
        if complaint_data.flat_uuid:
            # Verify flat exists
            flat_check = db.table("flats").select("uuid").eq("uuid", str(complaint_data.flat_uuid)).execute()
            if not flat_check.data:
                raise HTTPException(status_code=404, detail="Flat not found")
        
        # Backward compatibility: Convert flat_number to flat_uuid if provided
        elif complaint_data.flat_number:
            flat = db.table("flats").select("uuid").eq("flat_number", complaint_data.flat_number).execute()
            if flat.data:
                complaint_dict['flat_uuid'] = str(flat.data[0]['uuid'])
            # Keep flat_number for legacy compatibility
        
        # Auto-assign tenant_uuid based on who lives in the flat
        if complaint_dict.get('flat_uuid') and not complaint_dict.get('tenant_uuid'):
            # Find the tenant living in this flat
            tenant = db.table("tenants").select("uuid").eq("flat_uuid", complaint_dict['flat_uuid']).execute()
            if tenant.data and len(tenant.data) > 0:
                complaint_dict['tenant_uuid'] = str(tenant.data[0]['uuid'])
        
        # Convert tenant_id to tenant_uuid if provided (backward compatibility)
        if complaint_data.tenant_id and not complaint_dict.get('tenant_uuid'):
            tenant = db.table("tenants").select("uuid").eq("id", complaint_data.tenant_id).execute()
            if tenant.data:
                complaint_dict['tenant_uuid'] = str(tenant.data[0]['uuid'])
        
        response = db.table("complaints").insert(complaint_dict).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create complaint"
            )
    except HTTPException:
        raise
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
