"""
Tenant API routes using Supabase client.
Handles CRUD operations for tenants.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from supabase import Client
from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse, TenantWithFlat
from typing import List

router = APIRouter(prefix="/tenants", tags=["Tenants"])

# ========== VAPI INTEGRATION ENDPOINTS ==========
# These endpoints are designed specifically for Vapi voice system integration
# They MUST be stateless, idempotent, and always return 200 for AI compatibility


@router.get("/by-flat/{flat_no}")
async def get_tenant_by_flat(
    flat_no: str,
    db: Client = Depends(get_db)
):
    """
    VAPI API REQUEST TOOL ENDPOINT
    
    Purpose: Validate flat number and retrieve tenant info for voice system.
    
    CRITICAL REQUIREMENTS:
    - STATELESS: No session, no memory, no previous request dependency
    - IDEMPOTENT: Same input always returns same output
    - PURE: Read-only, no database writes, no side effects
    - ALWAYS 200: Never return 404/500 (breaks Vapi conversation flow)
    - BOOLEAN CONTRACT: AI logic depends on "exists" field, not HTTP codes
    
    This endpoint is used ONLY for:
    1. Checking if flat number exists
    2. Fetching tenant info to confirm to caller
    
    This endpoint does NOT:
    - Create appointments
    - Reserve dates
    - Mutate data
    - Trigger side effects
    
    Response format:
    - If flat exists + tenant active: {"exists": true, "flat_no": "A-512", "tenant": {...}}
    - If not found or inactive: {"exists": false}
    """
    try:
        # Step 1: Normalize flat number (CRITICAL for consistency)
        # - Trim whitespace
        # - Convert to uppercase
        # This ensures "a-512", " A-512 ", "A-512" all match the same flat
        normalized_flat_no = flat_no.strip().upper()
        
        # Step 2: Lookup flat by flat_number
        # This is a READ-ONLY operation, NO state change
        flat_response = db.table("flats").select("uuid, flat_number").eq("flat_number", normalized_flat_no).execute()
        
        # If flat doesn't exist, return {"exists": false}
        # We return 200 (not 404) because Vapi AI needs boolean logic
        if not flat_response.data or len(flat_response.data) == 0:
            return JSONResponse(
                status_code=200,
                content={"exists": False},
                headers={"Content-Type": "application/json"}
            )
        
        flat = flat_response.data[0]
        flat_uuid = flat['uuid']
        
        # Step 3: Find tenant living in this flat
        # Query: WHERE tenant.flat_uuid = flat.uuid
        # This establishes the relationship: which tenant lives in this flat?
        tenant_response = db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).execute()
        
        # If no tenant assigned to this flat, return {"exists": false}
        # (Vacant flat scenario)
        if not tenant_response.data or len(tenant_response.data) == 0:
            return JSONResponse(
                status_code=200,
                content={"exists": False},
                headers={"Content-Type": "application/json"}
            )
        
        # Step 4: Return tenant information
        # IMPORTANT: Flat structure for Vapi's variableExtractionPlan
        # Vapi expects: tenant_name, tenant_phone (not nested under 'tenant')
        tenant = tenant_response.data[0]
        
        # CRITICAL: Return explicit JSONResponse with proper content-type
        # This ensures Vapi can parse the response correctly
        return JSONResponse(
            status_code=200,
            content={
                "exists": True,
                "flat_no": str(flat['flat_number']),  # Ensure string type
                "tenant_name": str(tenant['name']),  # Ensure string type
                "tenant_phone": str(tenant['phone'])  # Ensure string type
            },
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        # ERROR HANDLING: NEVER leak stack traces to Vapi
        # Always return {"exists": false} on ANY error
        # This keeps the conversation flowing even if DB fails
        
        # Log error internally for debugging (not exposed to caller)
        print(f"Error in tenant lookup for flat {flat_no}: {str(e)}")
        
        # Return safe default response
        # This is CRITICAL: 200 status + {"exists": false} keeps Vapi conversation alive
        return JSONResponse(
            status_code=200,
            content={"exists": False},
            headers={"Content-Type": "application/json"}
        )


@router.get("/by-flat-query")
async def get_tenant_by_flat_query(
    flat_no: str,
    db: Client = Depends(get_db)
):
    """
    VAPI API REQUEST TOOL ENDPOINT (Query Parameter Version)
    
    This is the same as /by-flat/{flat_no} but uses query parameters instead.
    Some API tools (like Vapi) prefer query parameters over path parameters.
    
    Usage: GET /tenants/by-flat-query?flat_no=101
    
    Same guarantees as the path parameter version:
    - STATELESS, IDEMPOTENT, PURE
    - Always returns 200
    - Boolean 'exists' field for AI logic
    """
    # Simply call the existing function with normalization
    try:
        normalized_flat_no = flat_no.strip().upper()
        
        flat_response = db.table("flats").select("uuid, flat_number").eq("flat_number", normalized_flat_no).execute()
        
        if not flat_response.data or len(flat_response.data) == 0:
            return {"exists": False}
        
        flat = flat_response.data[0]
        flat_uuid = flat['uuid']
        
        tenant_response = db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).execute()
        
        if not tenant_response.data or len(tenant_response.data) == 0:
            return {"exists": False}
        
        tenant = tenant_response.data[0]
        
        # Flat structure to match Vapi's schema
        return {
            "exists": True,
            "flat_no": flat['flat_number'],
            "tenant_name": tenant['name'],
            "tenant_phone": tenant['phone']
        }
        
    except Exception as e:
        print(f"Error in tenant lookup (query) for flat {flat_no}: {str(e)}")
        return {"exists": False}


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
