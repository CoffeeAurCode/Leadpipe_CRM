"""
Tenant API routes using Supabase client.
Handles CRUD operations for tenants.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from supabase import Client
from app.db.session import get_db
from app.schemas.tenant import TenantCreate, TenantUpdate, TenantResponse
from typing import List, Optional
from datetime import date, datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

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
        normalized_flat_no = flat_no.strip()
        
        # Step 2: Lookup flat by flat_number
        # This is a READ-ONLY operation, NO state change
        flat_response = db.table("flats").select("uuid, flat_number, tenant_uuid").ilike("flat_number", normalized_flat_no).execute()

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
        # Primary: query via tenant.flat_uuid (forward FK from tenant side)
        # Fallback: query via flat.tenant_uuid (forward FK from flat side)
        # Both directions are checked because data may have been created inconsistently
        tenant_response = db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).execute()
        if (not tenant_response.data) and flat.get("tenant_uuid"):
            tenant_response = db.table("tenants").select("name, phone").eq("uuid", flat["tenant_uuid"]).execute()
        
        current_time_str = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")

        # If no tenant assigned to this flat, we still return exists=True but with null tenant fields
        # This tells the AI "The flat exists, but it is vacant"
        if not tenant_response.data or len(tenant_response.data) == 0:
            return JSONResponse(
                status_code=200,
                content={
                    "exists": True,
                    "flat_no": str(flat['flat_number']),
                    "tenant_name": None,
                    "tenant_phone": None,
                    "datetime": current_time_str
                },
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
                "flat_no": str(flat['flat_number']),
                "tenant_name": str(tenant['name']),
                "tenant_phone": str(tenant['phone']),
                "datetime": current_time_str
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
        normalized_flat_no = flat_no.strip()
        
        flat_response = db.table("flats").select("uuid, flat_number, tenant_uuid").ilike("flat_number", normalized_flat_no).execute()

        if not flat_response.data or len(flat_response.data) == 0:
            return {"exists": False}

        flat = flat_response.data[0]
        flat_uuid = flat['uuid']

        tenant_response = db.table("tenants").select("name, phone").eq("flat_uuid", flat_uuid).execute()
        if (not tenant_response.data) and flat.get("tenant_uuid"):
            tenant_response = db.table("tenants").select("name, phone").eq("uuid", flat["tenant_uuid"]).execute()
        
        current_time_str = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")

        if not tenant_response.data or len(tenant_response.data) == 0:
            return {
                "exists": True,
                "flat_no": flat['flat_number'],
                "tenant_name": None,
                "tenant_phone": None,
                "datetime": current_time_str
            }

        tenant = tenant_response.data[0]

        # Flat structure to match Vapi's schema
        return {
            "exists": True,
            "flat_no": flat['flat_number'],
            "tenant_name": tenant['name'],
            "tenant_phone": tenant['phone'],
            "datetime": current_time_str
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


def _compute_lease_status(tenant: dict) -> str:
    """Compute lease status from raw tenant dict for server-side filtering."""
    start = tenant.get("lease_start_date")
    end = tenant.get("lease_end_date")
    if not start or not end:
        return "No Lease"
    today = date.today()
    end_date = date.fromisoformat(end) if isinstance(end, str) else end
    start_date = date.fromisoformat(start) if isinstance(start, str) else start
    if end_date < today:
        return "Expired"
    if (end_date - today).days <= 30:
        return "Expiring Soon"
    if start_date <= today:
        return "Active"
    return "Upcoming"


@router.get("", response_model=List[TenantResponse])
async def get_all_tenants(
    db: Client = Depends(get_db),
    property_id: Optional[int] = Query(None, description="Filter by property group ID"),
    building_id: Optional[int] = Query(None, description="Filter by building ID"),
    unit_uuid: Optional[str] = Query(None, description="Filter by flat/unit UUID"),
    lease_status: Optional[str] = Query(None, description="Active | Expiring Soon | Expired | No Lease"),
    rent_status: Optional[str] = Query(None, description="On-time | Upcoming | Overdue | At Risk"),
    sort_by: Optional[str] = Query(None, description="lease_end_date"),
    sort_order: str = Query("asc", description="asc | desc"),
):
    """Get all tenants with optional filtering, sorting, and enriched join data."""
    try:
        response = db.table("tenants").select("*").execute()
        tenants = response.data or []

        # Filter by specific unit
        if unit_uuid:
            tenants = [t for t in tenants if t.get("flat_uuid") == unit_uuid]

        # Filter by building (fetch matching flat UUIDs once)
        if building_id is not None:
            flat_resp = db.table("flats").select("uuid").eq("building_id", building_id).execute()
            building_flat_uuids = {f["uuid"] for f in (flat_resp.data or [])}
            tenants = [t for t in tenants if t.get("flat_uuid") in building_flat_uuids]

        # Filter by property group (fetch buildings → flats)
        if property_id is not None and building_id is None:
            bldg_resp = db.table("buildings").select("id").eq("property_group_id", property_id).execute()
            bldg_ids = [b["id"] for b in (bldg_resp.data or [])]
            if bldg_ids:
                flat_resp = db.table("flats").select("uuid").in_("building_id", bldg_ids).execute()
                prop_flat_uuids = {f["uuid"] for f in (flat_resp.data or [])}
            else:
                prop_flat_uuids = set()
            tenants = [t for t in tenants if t.get("flat_uuid") in prop_flat_uuids]

        # Filter by rent_status (stored field)
        if rent_status:
            tenants = [t for t in tenants if t.get("rent_status") == rent_status]

        # Filter by lease_status (computed field)
        if lease_status:
            tenants = [t for t in tenants if _compute_lease_status(t) == lease_status]

        # ── Batch-enrich with joined data ─────────────────────────────────────
        flat_uuids = [t["flat_uuid"] for t in tenants if t.get("flat_uuid")]
        if flat_uuids:
            # flat_number + integer id (needed for feature flag lookup)
            flats_resp = (
                db.table("flats")
                .select("uuid, id, flat_number")
                .in_("uuid", flat_uuids)
                .execute()
            )
            flat_map = {f["uuid"]: f for f in (flats_resp.data or [])}
            flat_id_by_uuid = {f["uuid"]: f["id"] for f in (flats_resp.data or [])}

            # Active rent: monthly_rent + effective_from
            rents_resp = (
                db.table("rents")
                .select("flat_uuid, monthly_rent, effective_from")
                .in_("flat_uuid", flat_uuids)
                .eq("is_active", True)
                .execute()
            )
            rent_map = {r["flat_uuid"]: r for r in (rents_resp.data or [])}

            # Feature flags: tenant_details + tenant_documents per unit (integer id)
            flat_ids = list(flat_id_by_uuid.values())
            feature_resp = (
                db.table("property_features")
                .select("unit_id, feature_key, enabled")
                .in_("feature_key", ["tenant_details", "tenant_documents"])
                .in_("unit_id", flat_ids)
                .execute()
            )
            # Build per-feature maps; defaults: tenant_details=True, tenant_documents=False
            tenant_details_map = {}
            tenant_documents_map = {}
            for row in (feature_resp.data or []):
                if row["feature_key"] == "tenant_details":
                    tenant_details_map[row["unit_id"]] = row["enabled"]
                elif row["feature_key"] == "tenant_documents":
                    tenant_documents_map[row["unit_id"]] = row["enabled"]
        else:
            flat_map = {}
            flat_id_by_uuid = {}
            rent_map = {}
            feature_map = {}

        for t in tenants:
            fid = t.get("flat_uuid")
            flat = flat_map.get(fid) if fid else None
            rent = rent_map.get(fid) if fid else None
            unit_int_id = flat_id_by_uuid.get(fid) if fid else None

            t["flat_number"] = flat["flat_number"] if flat else None
            t["rent_amount"] = rent["monthly_rent"] if rent else None
            t["due_date"] = rent["effective_from"] if rent else None
            # Fall back to defaults when no explicit row
            t["tenant_details_enabled"] = tenant_details_map.get(unit_int_id, True) if unit_int_id is not None else True
            t["tenant_documents_enabled"] = tenant_documents_map.get(unit_int_id, False) if unit_int_id is not None else False

        # Sorting
        if sort_by == "lease_end_date":
            tenants.sort(
                key=lambda t: t.get("lease_end_date") or "9999-12-31",
                reverse=(sort_order == "desc"),
            )
        else:
            tenants.sort(key=lambda t: t.get("created_at") or "", reverse=True)

        return tenants
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
    """Delete a tenant, vacate their flat, and remove their rent record."""
    try:
        tenant_resp = db.table("tenants").select("uuid").eq("uuid", tenant_uuid).execute()
        if not tenant_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tenant with UUID {tenant_uuid} not found"
            )

        # Find the linked flat and clean it up
        flat_resp = db.table("flats").select("uuid").eq("tenant_uuid", tenant_uuid).execute()
        if flat_resp.data:
            flat_uuid = flat_resp.data[0]["uuid"]
            # Remove rent record for this flat
            db.table("rents").delete().eq("flat_uuid", flat_uuid).execute()
            # Vacate the flat
            db.table("flats").update({"tenant_uuid": None, "occupied": False}).eq("uuid", flat_uuid).execute()

        # Delete the tenant
        db.table("tenants").delete().eq("uuid", tenant_uuid).execute()
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
