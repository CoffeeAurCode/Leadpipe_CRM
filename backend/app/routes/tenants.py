"""
Tenant API routes using Supabase client.
Handles CRUD operations for tenants.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantWithFlat
from typing import List

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Client = Depends(get_db)
):
    """Create a new tenant"""
    try:
        tenant_dict = tenant_data.model_dump(mode='json')
        
        # Verify flat exists if flat_uuid provided
        if tenant_data.flat_uuid:
            flat = db.table("flats").select("uuid").eq("uuid", str(tenant_data.flat_uuid)).execute()
            if not flat.data:
                raise HTTPException(status_code=404, detail="Flat not found")
        
        response = db.table("tenants").insert(tenant_dict).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating tenant: {str(e)}"
        )


@router.get("", response_model=List[TenantResponse])
async def get_all_tenants(db: Client = Depends(get_db)):
    """Get all tenants"""
    try:
        response = db.table("tenants").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tenants: {str(e)}"
        )


@router.get("/{tenant_uuid}", response_model=TenantResponse)
async def get_tenant(tenant_uuid: str, db: Client = Depends(get_db)):
    """Get tenant by UUID"""
    try:
        response = db.table("tenants").select("*").eq("uuid", tenant_uuid).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with UUID {tenant_uuid} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tenant: {str(e)}"
        )


@router.patch("/{tenant_uuid}", response_model=TenantResponse)
async def update_tenant(
    tenant_uuid: str,
    tenant_data: TenantUpdate,
    db: Client = Depends(get_db)
):
    """Update a tenant's information"""
    try:
        update_data = tenant_data.model_dump(exclude_unset=True, mode='json')
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Verify new flat exists if changing flat assignment
        if 'flat_uuid' in update_data and update_data['flat_uuid']:
            flat = db.table("flats").select("uuid").eq("uuid", update_data['flat_uuid']).execute()
            if not flat.data:
                raise HTTPException(status_code=404, detail="Flat not found")
        
        response = db.table("tenants").update(update_data).eq("uuid", tenant_uuid).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with UUID {tenant_uuid} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating tenant: {str(e)}"
        )


@router.delete("/{tenant_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_uuid: str, db: Client = Depends(get_db)):
    """Delete a tenant"""
    try:
        response = db.table("tenants").delete().eq("uuid", tenant_uuid).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with UUID {tenant_uuid} not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting tenant: {str(e)}"
        )


@router.get("/by-phone/{phone}", response_model=TenantResponse)
async def get_tenant_by_phone(phone: str, db: Client = Depends(get_db)):
    """Get tenant by phone number (useful for voice system)"""
    try:
        response = db.table("tenants").select("*").eq("phone", phone).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with phone {phone} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching tenant: {str(e)}"
        )
