"""
Flats API routes using Supabase client.
Handles CRUD operations and verification for flats.
"""
import re
import json as _json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Request, Query
from pydantic import BaseModel
from supabase import Client
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
from app.db.session import get_db, get_service_db
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.schemas.flat import (
    FlatCreate,
    FlatUpdate,
    FlatResponse,
    FlatVerifyPhoneRequest,
    FlatVerifyPhoneResponse,
)
from app.schemas.flat_update import FlatEditRequest
from app.core.db_errors import clean_db_error
from typing import Optional, List
from uuid import uuid4
from pydantic import BaseModel as _BaseModel

router = APIRouter(prefix="/flats", tags=["Flats"])


def _digits_only(phone: str) -> str:
    """Strip everything except digits from a phone string."""
    return re.sub(r"\D", "", phone)


def _phones_match(a: str, b: str) -> bool:
    """
    Compare two phone numbers flexibly.

    Normalises both to digits only, then checks whether either is a suffix
    of the other.  This handles country-code variations:
      +919998064026  vs  9998064026  →  True
      +919998064026  vs  +919998064026  →  True
      +919998064026  vs  9998064027  →  False
    """
    da, db_ = _digits_only(a), _digits_only(b)
    if not da or not db_:
        return False
    return da.endswith(db_) or db_.endswith(da)


# ---------------------------------------------------------------------------
# VAPI endpoint — must stay above dynamic path routes to avoid shadowing
# ---------------------------------------------------------------------------

@router.post("/verify-phone", response_model=FlatVerifyPhoneResponse)
async def verify_phone(
    request: FlatVerifyPhoneRequest,
    phone_number: Optional[str] = Query(None, description="Caller phone — injected by VAPI as {{customer.number}}"),
    db: Client = Depends(get_service_db),
):
    """
    VAPI apiRequest tool — Verify that the caller is the registered tenant of a flat.

    VAPI tool config:
      Type:   apiRequest
      Method: POST
      URL:    /flats/verify-phone?phone_number={{customer.number}}
      Body:   {"flat_number": "<LLM fills from conversation>"}

    CRITICAL REQUIREMENTS (VAPI contract):
    - ALWAYS returns HTTP 200 — never 404 / 500
    - STATELESS, READ-ONLY, no side effects
    """
    flat_number = request.flat_number
    print(f"[DEBUG] verify_phone: flat_number={flat_number!r} phone_number={phone_number!r}")

    try:
        if not flat_number:
            print("[WARN] verify_phone: flat_number missing")
            return FlatVerifyPhoneResponse(result="Verification failed: no flat number provided.", status="invalid")

        if not phone_number:
            print(f"[WARN] verify_phone: phone_number missing for flat '{flat_number}'")
            return FlatVerifyPhoneResponse(result="Verification failed: phone number not available.", status="invalid")

        normalized_flat = flat_number.strip().upper()

        # 1. Look up flat (case-insensitive); include building_id for property_group resolution
        flat_resp = (
            db.table("flats")
            .select("uuid, tenant_uuid, building_id")
            .ilike("flat_number", normalized_flat)
            .execute()
        )
        print(f"[DEBUG] flat lookup '{normalized_flat}': found={bool(flat_resp.data)}")
        if not flat_resp.data:
            return FlatVerifyPhoneResponse(result="Verification failed: flat not found.", status="invalid")

        flat = flat_resp.data[0]
        flat_uuid = flat["uuid"]

        # 2. Look up tenant — primary: flat_uuid FK; fallback: flat.tenant_uuid
        tenant_resp = (
            db.table("tenants")
            .select("phone")
            .eq("flat_uuid", flat_uuid)
            .execute()
        )
        if not tenant_resp.data and flat.get("tenant_uuid"):
            tenant_resp = (
                db.table("tenants")
                .select("phone")
                .eq("uuid", flat["tenant_uuid"])
                .execute()
            )

        if not tenant_resp.data:
            return FlatVerifyPhoneResponse(result="Verification result: vacant. Flat has no registered tenant.", status="vacant")

        # 3. Compare phones (digits-only, suffix-aware for country codes)
        tenant_phone = tenant_resp.data[0].get("phone", "")
        match = _phones_match(phone_number, tenant_phone)
        print(f"[DEBUG] phone match: caller={phone_number!r} db={tenant_phone!r} match={match}")
        if match:
            current_time_ist = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")

            # Resolve property_group_id via building → properties_list
            property_group_id = None
            if flat.get("building_id"):
                bldg_resp = (
                    db.table("buildings")
                    .select("property_id")
                    .eq("id", flat["building_id"])
                    .limit(1)
                    .execute()
                )
                if bldg_resp.data:
                    property_group_id = str(bldg_resp.data[0]["property_id"])

            return FlatVerifyPhoneResponse(
                result=f"Verification result: valid. Caller is the registered tenant. Current IST time: {current_time_ist}.",
                status="valid",
                datetime=current_time_ist,
                property_group_id=property_group_id,
            )

        return FlatVerifyPhoneResponse(
            result="Verification failed: phone number does not match the registered tenant for this flat.",
            status="invalid",
        )

    except Exception as e:
        print(f"[ERROR] verify_phone failed: {type(e).__name__}: {e}")
        return FlatVerifyPhoneResponse(result="Verification failed due to an internal error.", status="invalid")


@router.post("/identify-caller")
async def identify_caller(
    request: Request,
    db: Client = Depends(get_service_db),
):
    """
    VAPI Option B — Identify a caller by phone number.
    Uses the service-role client (bypasses RLS) to search across ALL managers' data.

    Returns tenant + property chain so VAPI knows which manager/society to route to.
    Always returns HTTP 200 (VAPI contract).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    phone_number = body.get("phone_number", "")
    print(f"[DEBUG] identify_caller: phone_number={phone_number!r}")

    if not phone_number:
        return {
            "exists": False,
            "message": "We don't recognize your number. Please contact your property manager directly.",
        }

    caller_digits = _digits_only(phone_number)
    if not caller_digits:
        return {
            "exists": False,
            "message": "We don't recognize your number. Please contact your property manager directly.",
        }

    try:
        # Search tenants by phone (get all, match flexibly)
        tenants_resp = db.table("tenants").select("uuid, name, phone, flat_uuid").execute()
        matched_tenant = None
        for t in tenants_resp.data or []:
            if _phones_match(phone_number, t.get("phone", "")):
                matched_tenant = t
                break

        if not matched_tenant:
            return {
                "exists": False,
                "message": "We don't recognize your number. Please contact your property manager directly.",
            }

        # Walk up the chain: tenant -> flat -> building -> property_group -> manager
        flat_resp = (
            db.table("flats")
            .select("uuid, flat_number, building_id")
            .eq("uuid", matched_tenant["flat_uuid"])
            .limit(1)
            .execute()
        )
        if not flat_resp.data:
            return {"exists": False, "message": "We don't recognize your number. Please contact your property manager directly."}

        flat = flat_resp.data[0]

        building_resp = (
            db.table("buildings")
            .select("id, name, property_id")
            .eq("id", flat["building_id"])
            .limit(1)
            .execute()
        )
        if not building_resp.data:
            return {"exists": False, "message": "We don't recognize your number. Please contact your property manager directly."}

        building = building_resp.data[0]

        property_resp = (
            db.table("properties_list")
            .select("id, name, manager_id")
            .eq("id", building["property_id"])
            .limit(1)
            .execute()
        )
        if not property_resp.data:
            return {"exists": False, "message": "We don't recognize your number. Please contact your property manager directly."}

        prop = property_resp.data[0]

        # Get manager profile
        manager_name = "Manager"
        manager_phone = ""
        if prop.get("manager_id"):
            mgr_resp = (
                db.table("manager_profiles")
                .select("name, phone")
                .eq("user_id", prop["manager_id"])
                .limit(1)
                .execute()
            )
            if mgr_resp.data:
                manager_name = mgr_resp.data[0].get("name", "Manager")
                manager_phone = mgr_resp.data[0].get("phone", "")

        return {
            "exists": True,
            "tenant_name": matched_tenant.get("name", ""),
            "flat_number": flat["flat_number"],
            "building_name": building["name"],
            "society_name": prop["name"],
            "property_group_id": str(prop["id"]),
            "manager_name": manager_name,
            "manager_phone": manager_phone,
        }

    except Exception as e:
        print(f"[ERROR] identify_caller failed: {type(e).__name__}: {e}")
        return {
            "exists": False,
            "message": "We don't recognize your number. Please contact your property manager directly.",
        }


@router.get("", response_model=list[FlatResponse])
async def get_all_flats(
    vacant: Optional[bool] = Query(None, description="If true, return only vacant flats (tenant_uuid IS NULL)"),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Get all flats ordered by building and flat number."""
    try:
        query = db.table("flats").select("*").order("address").order("flat_number")
        if vacant:
            query = query.is_("tenant_uuid", "null")
        response = query.execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching flats: {str(e)}"
        )


class AssignTenantRequest(BaseModel):
    tenant_uuid: str


@router.patch("/{flat_uuid}/assign-tenant")
async def assign_tenant(
    flat_uuid: str,
    body: AssignTenantRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Assign an existing tenant to a vacant flat (bidirectional link)."""
    try:
        flat_resp = db.table("flats").select("uuid, tenant_uuid").eq("uuid", flat_uuid).execute()
        if not flat_resp.data:
            raise HTTPException(status_code=404, detail="Flat not found")
        if flat_resp.data[0].get("tenant_uuid"):
            raise HTTPException(status_code=400, detail="Flat is already occupied")

        db.table("flats").update({"tenant_uuid": body.tenant_uuid, "occupied": True}).eq("uuid", flat_uuid).execute()
        db.table("tenants").update({"flat_uuid": flat_uuid}).eq("uuid", body.tenant_uuid).execute()
        db.table("lease_listings").update({"is_active": False}).eq("flat_uuid", flat_uuid).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning tenant: {str(e)}")


@router.patch("/{flat_uuid}/unassign-tenant")
async def unassign_tenant(
    flat_uuid: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Remove the tenant from a flat (bidirectional unlink)."""
    try:
        flat_resp = db.table("flats").select("uuid, tenant_uuid").eq("uuid", flat_uuid).execute()
        if not flat_resp.data:
            raise HTTPException(status_code=404, detail="Flat not found")

        tenant_uuid = flat_resp.data[0].get("tenant_uuid")
        if tenant_uuid:
            db.table("tenants").update({"flat_uuid": None}).eq("uuid", tenant_uuid).execute()
        db.table("flats").update({"tenant_uuid": None, "occupied": False}).eq("uuid", flat_uuid).execute()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error unassigning tenant: {str(e)}")


@router.get("/{flat_uuid}/details", response_model=FlatResponse)
async def get_flat_details(
    flat_uuid: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
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
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
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
    building_id: Optional[str] = Form(None),
    street_address: Optional[str] = Form(None),
    address_line: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    country: Optional[str] = Form("Canada"),
    image: Optional[UploadFile] = File(None),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
    svc: Client = Depends(get_service_db),
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
                upload_response = svc.storage.from_("Property Pics").upload(
                    uploaded_filename,
                    contents,
                    {"content-type": image.content_type}
                )

                # Get public URL
                image_url = svc.storage.from_("Property Pics").get_public_url(uploaded_filename)
                
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

        if not re.match(r'^[A-Z0-9]+$', flat_number_normalized):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="flat_number must contain only letters and numbers — no spaces or special characters (e.g. use S104 not S-104)"
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
        
        # ========== STEP 3: CHECK FOR DUPLICATES BEFORE ANY DB WRITES ==========
        existing_flat = db.table("flats").select("*").eq("flat_number", flat_number_normalized).execute()

        if existing_flat.data:
            if uploaded_filename:
                try:
                    svc.storage.from_("Property Pics").remove([uploaded_filename])
                except:
                    pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Flat {flat_number_normalized} already exists"
            )

        if tenant_phone:
            existing_tenant = db.table("tenants").select("uuid").eq("phone", tenant_phone.strip()).execute()
            if existing_tenant.data:
                if uploaded_filename:
                    try:
                        svc.storage.from_("Property Pics").remove([uploaded_filename])
                    except:
                        pass
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A tenant with this phone number already exists."
                )
        
        # ========== STEP 4: CREATE FLAT ==========
        flat_payload = {
            "flat_number": flat_number_normalized,
            "address": address,
            "floor_number": floor_number,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "image_url": image_url,
            "building_id": building_id if building_id else None,
            "tenant_uuid": None,
            "occupied": False,
        }
        if street_address: flat_payload["street_address"] = street_address
        if address_line: flat_payload["address_line"] = address_line
        if city: flat_payload["city"] = city
        if state: flat_payload["state"] = state
        if country: flat_payload["country"] = country
        
        flat_response = svc.table("flats").insert(flat_payload).execute()
        
        if not flat_response.data:
            # Cleanup uploaded image
            if uploaded_filename:
                try:
                    svc.storage.from_("Property Pics").remove([uploaded_filename])
                    print(f"[CLEANUP] Deleted uploaded image due to flat creation failure")
                except:
                    pass
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create flat"
            )
        
        flat = flat_response.data[0]
        flat_uuid = flat["uuid"]
        flat_id = flat["id"]
        
        print(f"[FLAT CREATED] UUID: {flat_uuid}, Number: {flat_number_normalized}")

        # ========== STEP 4.5: INITIALIZE FEATURES ==========
        try:
            from app.services.feature_service import FeatureService
            feature_service = FeatureService(db)
            await feature_service.initialize_unit_features(flat_id)
            print(f"[FEATURES INITIALIZED] unit_id: {flat_id}")
        except Exception as f_err:
            print(f"[FEATURE INIT ERROR] {str(f_err)}")
            # Non-blocking error, flat is still created

        
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
                    db.table("flats").update({
                        "tenant_uuid": tenant_uuid,
                        "occupied": True
                    }).eq("uuid", flat_uuid).execute()
                    db.table("lease_listings").update({"is_active": False}).eq("flat_uuid", flat_uuid).execute()

                    flat["tenant_uuid"] = tenant_uuid
                    flat["occupied"] = True

                    print(f"[TENANT CREATED] UUID: {tenant_uuid}, Name: {tenant_name}")
                    print(f"[TENANT LINKED] Flat {flat_number_normalized} now occupied")

            except HTTPException:
                raise
            except Exception as tenant_error:
                print(f"[TENANT CREATION ERROR] {str(tenant_error)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Unit created but tenant could not be added: {clean_db_error(tenant_error)}"
                )
        
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
                svc.storage.from_("Property Pics").remove([uploaded_filename])
                print(f"[CLEANUP] Deleted uploaded image due to error: {str(e)}")
            except:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating unit: {clean_db_error(e)}"
        )






@router.patch("/{flat_uuid}", response_model=FlatResponse)
async def update_flat_details(
    flat_uuid: str,
    request: FlatEditRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
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
            # Guard: phone must be unique in the tenants table
            existing = db.table("tenants").select("uuid, flat_uuid").eq("phone", request.tenant_data.phone).execute()
            if existing.data:
                existing_tenant = existing.data[0]
                if existing_tenant.get("flat_uuid"):
                    raise HTTPException(
                        status_code=400,
                        detail="A tenant with this phone number is already assigned to another flat. Use 'Assign Existing Tenant' to move them."
                    )
                raise HTTPException(
                    status_code=400,
                    detail="A tenant with this phone number already exists. Use 'Assign Existing Tenant' to link them to this flat."
                )

            # Create new tenant
            tenant_payload = {
                "name": request.tenant_data.name,
                "phone": request.tenant_data.phone,
                "flat_uuid": flat_uuid,
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


class BulkDeleteFlatsRequest(_BaseModel):
    uuids: List[str]


@router.delete("/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete_flats(
    request: BulkDeleteFlatsRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Bulk delete flats by UUID list. Cascade-deletes lease_listings, rents, and tenants."""
    deleted = 0
    errors = []
    for flat_uuid in request.uuids:
        try:
            flat_resp = db.table("flats").select("uuid, tenant_uuid").eq("uuid", flat_uuid).execute()
            if not flat_resp.data:
                errors.append(f"{flat_uuid}: not found")
                continue
            tenant_uuid = flat_resp.data[0].get("tenant_uuid")
            db.table("lease_listings").delete().eq("flat_uuid", flat_uuid).execute()
            db.table("rents").delete().eq("flat_uuid", flat_uuid).execute()
            if tenant_uuid:
                db.table("tenants").delete().eq("uuid", tenant_uuid).execute()
            db.table("flats").delete().eq("uuid", flat_uuid).execute()
            deleted += 1
        except Exception as e:
            errors.append(f"{flat_uuid}: {clean_db_error(e)}")
    return {"deleted": deleted, "errors": errors}


@router.delete("/{flat_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flat(flat_uuid: str, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """Delete a flat. Cascade-deletes lease_listings, rent, and tenant first."""
    try:
        flat_resp = db.table("flats").select("id, uuid, tenant_uuid").eq("uuid", flat_uuid).execute()
        if not flat_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat {flat_uuid} not found"
            )

        flat = flat_resp.data[0]
        tenant_uuid = flat.get("tenant_uuid")

        db.table("lease_listings").delete().eq("flat_uuid", flat_uuid).execute()
        db.table("rents").delete().eq("flat_uuid", flat_uuid).execute()
        if tenant_uuid:
            db.table("tenants").delete().eq("uuid", tenant_uuid).execute()
        db.table("flats").delete().eq("uuid", flat_uuid).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting flat: {clean_db_error(e)}"
        )
