"""
Flats API routes using Supabase client.
Handles CRUD operations and verification for flats.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
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
from typing import Optional
from uuid import uuid4

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
    flat_number: str = Form(...),
    address: Optional[str] = Form(None),
    floor_number: Optional[int] = Form(None),
    bedrooms: Optional[int] = Form(None),
    bathrooms: Optional[int] = Form(None),
    tenant_name: Optional[str] = Form(None),
    tenant_phone: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Client = Depends(get_db)
):
    """
    Create a new flat with optional image upload and tenant assignment.
    
    - Uploads image to Supabase Storage "Property Pics" bucket if provided
    - Creates flat record with generated UUID
    - Optionally creates and links tenant if tenant details provided
    - Returns flat with nested tenant details
    - Handles cleanup on failures (deletes uploaded image if DB insert fails)
    """
    image_url = None
    uploaded_filename = None
    
    try:
        # ========== STEP 1: UPLOAD IMAGE IF PROVIDED ==========
        if image:
            # Validate file type
            allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
            if image.content_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
                )
            
            # Read file contents
            contents = await image.read()
            
            # Validate file size (10MB limit)
            if len(contents) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="File too large. Maximum size: 10MB"
                )
            
            # Generate unique filename with UUID
            file_ext = image.filename.split('.')[-1] if '.' in image.filename else 'jpg'
            uploaded_filename = f"{uuid4()}.{file_ext}"
            
            # Upload to Supabase Storage
            try:
                upload_response = db.storage.from_("Property Pics").upload(
                    uploaded_filename,
                    contents,
                    {"content-type": image.content_type}
                )
                
                # Get public URL
                image_url = db.storage.from_("Property Pics").get_public_url(uploaded_filename)
                
                print(f"[IMAGE UPLOAD] Successfully uploaded: {uploaded_filename}")
                print(f"[IMAGE UPLOAD] Public URL: {image_url}")
                
            except Exception as upload_error:
                print(f"[IMAGE UPLOAD ERROR] {str(upload_error)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Image upload failed: {str(upload_error)}"
                )
        
        # ========== STEP 2: VALIDATE AND NORMALIZE FLAT DATA ==========
        flat_number_normalized = flat_number.strip().upper()
        
        # Validate required fields
        if not flat_number_normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="flat_number is required"
            )
        
        # Validate numeric fields
        if floor_number is not None and floor_number < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="floor_number must be >= 0"
            )
        
        if bedrooms is not None and (bedrooms < 1 or bedrooms > 10):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bedrooms must be between 1 and 10"
            )

        if bathrooms is not None and (bathrooms < 0 or bathrooms > 10):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bathrooms must be between 0 and 10"
            )
        
        # ========== STEP 3: CHECK FOR DUPLICATE FLAT_NUMBER ==========
        existing_flat = db.table("flats").select("*").eq("flat_number", flat_number_normalized).execute()
        
        if existing_flat.data:
            # Cleanup uploaded image
            if uploaded_filename:
                try:
                    db.storage.from_("Property Pics").remove([uploaded_filename])
                    print(f"[CLEANUP] Deleted uploaded image due to duplicate flat_number")
                except:
                    pass
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flat {flat_number_normalized} already exists"
            )
        
        # ========== STEP 4: CREATE FLAT ==========
        flat_payload = {
            "flat_number": flat_number_normalized,
            "address": address,
            "floor_number": floor_number,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "image_url": image_url,
            "tenant_uuid": None,  # Will be updated if tenant created
            "occupied": False  # Default to vacant
        }
        
        flat_response = db.table("flats").insert(flat_payload).execute()
        
        if not flat_response.data:
            # Cleanup uploaded image
            if uploaded_filename:
                try:
                    db.storage.from_("Property Pics").remove([uploaded_filename])
                    print(f"[CLEANUP] Deleted uploaded image due to flat creation failure")
                except:
                    pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create flat"
            )
        
        flat = flat_response.data[0]
        flat_uuid = flat["uuid"]
        
        print(f"[FLAT CREATED] UUID: {flat_uuid}, Number: {flat_number_normalized}")
        
        # ========== STEP 5: CREATE TENANT IF PROVIDED ==========
        tenant_info = None
        
        if tenant_name and tenant_phone:
            # Validate tenant data
            if not tenant_name.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tenant_name cannot be empty"
                )
            
            if not tenant_phone.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="tenant_phone cannot be empty"
                )
            
            tenant_payload = {
                "name": tenant_name.strip(),
                "phone": tenant_phone.strip(),
                "flat_uuid": flat_uuid
            }
            
            try:
                tenant_response = db.table("tenants").insert(tenant_payload).execute()
                
                if tenant_response.data:
                    tenant_info = tenant_response.data[0]
                    tenant_uuid = tenant_info["uuid"]
                    
                    # Link tenant to flat
                    update_response = db.table("flats").update({
                        "tenant_uuid": tenant_uuid,
                        "occupied": True
                    }).eq("uuid", flat_uuid).execute()
                    
                    flat["tenant_uuid"] = tenant_uuid
                    flat["occupied"] = True
                    
                    print(f"[TENANT CREATED] UUID: {tenant_uuid}, Name: {tenant_name}")
                    print(f"[TENANT LINKED] Flat {flat_number_normalized} now occupied")
                    
            except Exception as tenant_error:
                print(f"[TENANT CREATION ERROR] {str(tenant_error)}")
                # Note: We don't rollback flat creation here
                # Instead, we log the error and continue
                # The flat exists but without a tenant
        
        # ========== STEP 6: RETURN FLAT WITH TENANT DETAILS ==========
        return {
            **flat,
            "tenant": tenant_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        # Cleanup uploaded image on unexpected error
        if uploaded_filename:
            try:
                db.storage.from_("Property Pics").remove([uploaded_filename])
                print(f"[CLEANUP] Deleted uploaded image due to error: {str(e)}")
            except:
                pass
        
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
             flat_update_payload = request.flat_details.model_dump(exclude_unset=True, exclude={'occupied'})
        
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
        tenant_info = None
        if final_flat.get('tenant_uuid'):
             t_res = db.table("tenants").select("*").eq("uuid", final_flat.get('tenant_uuid')).execute()
             if t_res.data:
                 tenant_info = t_res.data[0]
        
        # Strict validation using response model
        return FlatResponse.model_validate({
            **final_flat,
            "tenant": tenant_info
        })

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing update: {str(e)}"
        )
