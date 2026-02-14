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
    FlatCreate, 
    FlatUpdate, 
    FlatResponse, 
    FlatVerifyRequest, 
    FlatVerifyResponse
)
from app.schemas.flat_update import FlatEditRequest

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
            .order("address")\
            .order("flat_number")\
            .execute()
        
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flats: {str(e)}"
        )


@router.get("/{flat_uuid}/details", response_model=FlatResponse)
async def get_flat_details(
    flat_uuid: str,
    db: Client = Depends(get_db)
):
    """
    Get detailed flat information by UUID including tenant data.
    This endpoint is used by the frontend to display flat details.
    """
    try:
        # Fetch flat by UUID
        response = db.table("flats")\
            .select("*")\
            .eq("uuid", flat_uuid)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat with UUID {flat_uuid} not found"
            )
        
        flat = response.data[0]
        
        # Fetch tenant info if tenant_uuid exists
        tenant_info = None
        if flat.get('tenant_uuid'):
            tenant_response = db.table("tenants")\
                .select("*")\
                .eq("uuid", flat.get('tenant_uuid'))\
                .execute()
            if tenant_response.data:
                tenant_info = tenant_response.data[0]
        
        # Return flat with tenant data
        return {
            **flat,
            "tenant": tenant_info
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flat details: {str(e)}"
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






@router.patch("/{flat_uuid}", response_model=FlatResponse)
async def update_flat_details(
    flat_uuid: str,
    request: FlatEditRequest,
    db: Client = Depends(get_db)
):
    """
    Update flat details and manage tenant occupancy.
    Handles adding, updating, and removing tenants transactionally.
    """
    try:
        # 1. Fetch current flat state
        current_flat_response = db.table("flats").select("*").eq("uuid", flat_uuid).execute()
        if not current_flat_response.data:
            raise HTTPException(status_code=404, detail="Flat not found")
        
        current_flat = current_flat_response.data[0]
        current_tenant_uuid = current_flat.get("tenant_uuid")
        
        # 2. Validate Action against Current State
        if request.action == 'ADD_TENANT':
            if current_tenant_uuid:
                raise HTTPException(status_code=400, detail="Cannot add tenant: Flat is already occupied")
            if not request.tenant_data:
                raise HTTPException(status_code=400, detail="Tenant data required for ADD_TENANT")
                
        elif request.action == 'REMOVE_TENANT':
            if not current_tenant_uuid:
                raise HTTPException(status_code=400, detail="Cannot remove tenant: Flat is already vacant")

        elif request.action == 'UPDATE_TENANT':
            if not current_tenant_uuid:
                raise HTTPException(status_code=400, detail="Cannot update tenant: Flat is vacant")
            if not request.tenant_data:
                raise HTTPException(status_code=400, detail="Tenant data required for UPDATE_TENANT")

        # 3. Perform Updates (Conceptually Transactional)
        # Note: Supabase/PostgREST doesn't support multi-table transactions in one HTTP call easily
        # without store procedures. We will proceed carefully with strict ordering.
        
        # A. Handle Tenant Operations
        new_tenant_uuid = current_tenant_uuid
        
        if request.action == 'ADD_TENANT':
            # Create new tenant
            tenant_payload = {
                "name": request.tenant_data.name,
                "phone": request.tenant_data.phone,
                "flat_uuid": flat_uuid,  # Link back to flat
                # "unit_id": ... (Optional: if we need to link to units table too)
            }
            tenant_res = db.table("tenants").insert(tenant_payload).execute()
            if tenant_res.data:
                new_tenant_uuid = tenant_res.data[0]['uuid']
            else:
                raise HTTPException(status_code=500, detail="Failed to create tenant")
                
        elif request.action == 'REMOVE_TENANT':
            # Delete tenant (CASCAADE or SET NULL handled by DB, but we explicitly clear)
            # First, check if tenant exists
            if current_tenant_uuid:
                db.table("tenants").delete().eq("uuid", current_tenant_uuid).execute()
            new_tenant_uuid = None
            
        elif request.action == 'UPDATE_TENANT':
            # Update existing tenant
             tenant_payload = {
                "name": request.tenant_data.name,
                "phone": request.tenant_data.phone
            }
             db.table("tenants").update(tenant_payload).eq("uuid", current_tenant_uuid).execute()

        # B. Handle Flat Updates
        flat_update_payload = {}
        if request.flat_details:
             flat_update_payload = request.flat_details.model_dump(exclude_unset=True, exclude={'occupied'}) # exclude occupied as it's computed
        
        # Always update tenant_uuid connection
        if new_tenant_uuid != current_tenant_uuid:
            flat_update_payload['tenant_uuid'] = new_tenant_uuid
            
        if flat_update_payload:
            update_res = db.table("flats").update(flat_update_payload).eq("uuid", flat_uuid).execute()
            if not update_res.data:
                 raise HTTPException(status_code=500, detail="Failed to update flat details")
            final_flat = update_res.data[0]
        else:
            final_flat = current_flat
            
        # 4. Fetch details for response (including updated tenant info)
        # We can reuse the get_flat_details logic or helper
        tenant_info = None
        if final_flat.get('tenant_uuid'):
             t_res = db.table("tenants").select("*").eq("uuid", final_flat.get('tenant_uuid')).execute()
             if t_res.data:
                 tenant_info = t_res.data[0]
        
        return {
            **final_flat,
            "tenant": tenant_info
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing update: {str(e)}"
        )
