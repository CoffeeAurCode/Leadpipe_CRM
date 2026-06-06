"""
Property Groups API Routes

CRUD for the 'properties_list' table — the true top-level entity.
Each property_group can contain multiple buildings (linked via buildings.property_id FK).

Hierarchy: Property → Building → Unit (flat)
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from fastapi.responses import JSONResponse, Response
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.core.db_errors import clean_db_error
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/property-groups", tags=["Property Groups"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class PropertyGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Canada"


class PropertyGroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_type_name: Optional[str] = None
    property_type_icon: Optional[str] = None
    building_count: int = 0
    created_at: datetime
    vapi_provisioning_status: Optional[str] = None
    vapi_phone_number: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[PropertyGroupResponse])
async def get_all_property_groups(user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Get all property groups with building counts.
    Uses 2 queries to avoid N+1.
    """
    try:
        # Query 1: all property groups with joined property_types
        groups_resp = (
            db.table("properties_list")
            .select("*, property_types(name, icon_type)")
            .order("name")
            .execute()
        )

        # Query 2: count buildings per property group
        buildings_resp = db.table("buildings").select("property_id").execute()

        # Build count map
        count_map: dict[str, int] = {}
        for b in buildings_resp.data:
            pid = b.get("property_id")
            if pid:
                count_map[str(pid)] = count_map.get(str(pid), 0) + 1

        result = []
        for g in groups_resp.data:
            pt = g.get("property_types") or {}
            result.append({
                "id": g["id"],
                "name": g["name"],
                "description": g.get("description"),
                "address": g.get("address"),
                "street_address": g.get("street_address"),
                "city": g.get("city"),
                "state": g.get("state"),
                "country": g.get("country"),
                "image_url": g.get("image_url"),
                "property_type_id": g.get("property_type_id"),
                "property_type_name": pt.get("name"),
                "property_type_icon": pt.get("icon_type"),
                "building_count": count_map.get(str(g["id"]), 0),
                "created_at": g["created_at"],
                "vapi_provisioning_status": g.get("vapi_provisioning_status"),
                "vapi_phone_number": g.get("vapi_phone_number"),
            })
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching property groups: {str(e)}"
        )


@router.post("", response_model=PropertyGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_property_group(
    request: PropertyGroupCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Create a new property group and trigger VAPI lease assistant provisioning."""
    try:
        payload = request.model_dump(exclude_none=True)
        if "property_type_id" in payload:
            payload["property_type_id"] = str(payload["property_type_id"])

        payload["vapi_provisioning_status"] = "not_applicable"
        payload["manager_id"] = user["sub"]

        response = db.table("properties_list").insert(payload).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create property group")

        g = response.data[0]
        pg_id = str(g["id"])

        # Only provision if this manager has no existing manager_vapi_config row
        from app.db.session import get_service_db
        svc_db = get_service_db()
        existing_config = (
            svc_db.table("manager_vapi_config")
            .select("id, vapi_provisioning_status")
            .eq("manager_id", user["sub"])
            .limit(1)
            .execute()
        )
        if not existing_config.data:
            svc_db.table("manager_vapi_config").insert({
                "manager_id": user["sub"],
                "vapi_provisioning_status": "pending",
            }).execute()
            from app.services.vapi_provisioning import provision_vapi_for_manager
            background_tasks.add_task(provision_vapi_for_manager, user["sub"], svc_db)

        pt = {}
        if g.get("property_type_id"):
            pt_resp = db.table("property_types").select("name, icon_type").eq("id", g["property_type_id"]).execute()
            pt = pt_resp.data[0] if pt_resp.data else {}

        return {
            **g,
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "building_count": 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating property group: {str(e)}")


@router.get("/users/me/vapi-config")
async def get_user_vapi_config(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Return the manager-level VAPI provisioning status and phone number."""
    from app.db.session import get_service_db
    svc_db = get_service_db()
    row = (
        svc_db.table("manager_vapi_config")
        .select("vapi_provisioning_status, vapi_phone_number")
        .eq("manager_id", user["sub"])
        .limit(1)
        .execute()
    )
    if not row.data:
        return {"vapi_provisioning_status": "not_set_up", "vapi_phone_number": None}
    return row.data[0]


@router.post("/users/me/provision-voice", status_code=202)
async def retry_user_voice_provisioning(
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_active_subscription),
):
    """Retry VAPI lease provisioning for this manager account."""
    from app.db.session import get_service_db
    from app.services.vapi_provisioning import provision_vapi_for_manager

    svc_db = get_service_db()

    existing = (
        svc_db.table("manager_vapi_config")
        .select("vapi_provisioning_status")
        .eq("manager_id", user["sub"])
        .limit(1)
        .execute()
    )
    if existing.data and existing.data[0]["vapi_provisioning_status"] == "active":
        return {"status": "already_active"}

    svc_db.table("manager_vapi_config").upsert({
        "manager_id": user["sub"],
        "vapi_provisioning_status": "pending",
    }, on_conflict="manager_id").execute()

    background_tasks.add_task(provision_vapi_for_manager, user["sub"], svc_db)
    return {"status": "provisioning_started"}


@router.get("/{property_id}/buildings")
async def get_property_buildings(property_id: str, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Get all buildings belonging to a specific property group.
    Includes unit counts aggregated from the flats table.
    """
    try:
        # Query buildings for this property
        buildings_resp = (
            db.table("buildings")
            .select("*, property_types(name, icon_type)")
            .eq("property_id", property_id)
            .order("name")
            .execute()
        )

        if not buildings_resp.data:
            return []

        # Get building IDs to fetch unit counts
        building_ids = [b["id"] for b in buildings_resp.data]

        # Fetch flats for these buildings only
        flats_resp = (
            db.table("flats")
            .select("building_id, tenant_uuid")
            .in_("building_id", building_ids)
            .execute()
        )

        # Build count maps
        unit_counts: dict[str, int] = {}
        occupied_counts: dict[str, int] = {}
        for flat in flats_resp.data:
            bid = flat.get("building_id")
            if bid:
                unit_counts[bid] = unit_counts.get(bid, 0) + 1
                if flat.get("tenant_uuid"):
                    occupied_counts[bid] = occupied_counts.get(bid, 0) + 1

        result = []
        for b in buildings_resp.data:
            pt = b.get("property_types") or {}
            bid = str(b["id"])
            result.append({
                "id": b["id"],
                "name": b["name"],
                "description": b.get("description"),
                "address": b.get("address"),
                "street_address": b.get("street_address"),
                "address_line": b.get("address_line"),
                "city": b.get("city"),
                "state": b.get("state"),
                "country": b.get("country"),
                "image_url": b.get("image_url"),
                "property_type_id": b.get("property_type_id"),
                "property_id": b.get("property_id"),
                "property_type_name": pt.get("name"),
                "property_type_icon": pt.get("icon_type"),
                "unit_count": unit_counts.get(bid, 0),
                "occupied_count": occupied_counts.get(bid, 0),
                "created_at": b["created_at"],
            })
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching buildings for property {property_id}: {str(e)}"
        )


class PropertyGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None


@router.patch("/{group_uuid}", response_model=PropertyGroupResponse)
async def update_property_group(
    group_uuid: str,
    request: PropertyGroupUpdate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    try:
        payload = request.model_dump(exclude_unset=True)
        if not payload:
            raise HTTPException(status_code=400, detail="No fields to update")
        if "property_type_id" in payload and payload["property_type_id"] is not None:
            payload["property_type_id"] = str(payload["property_type_id"])

        response = db.table("properties_list").update(payload).eq("id", group_uuid).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Property group not found")

        g = response.data[0]
        pt = {}
        if g.get("property_type_id"):
            pt_resp = db.table("property_types").select("name, icon_type").eq("id", g["property_type_id"]).execute()
            pt = pt_resp.data[0] if pt_resp.data else {}

        buildings_resp = db.table("buildings").select("id").eq("property_id", group_uuid).execute()

        return {
            **g,
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "building_count": len(buildings_resp.data),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating property group: {str(e)}")


class BulkDeletePropertyGroupsRequest(BaseModel):
    ids: List[str]


@router.delete("/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete_property_groups(
    request: BulkDeletePropertyGroupsRequest,
    force: bool = Query(False),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Bulk delete property groups with full cascade."""
    deleted = 0
    errors = []
    for property_id in request.ids:
        try:
            prop_resp = db.table("properties_list").select("id").eq("id", property_id).execute()
            if not prop_resp.data:
                errors.append(f"{property_id}: not found")
                continue
            buildings_resp = db.table("buildings").select("id").eq("property_id", property_id).execute()
            building_ids = [b["id"] for b in buildings_resp.data]
            flat_uuids = []
            tenant_uuids = []
            if building_ids:
                flats_resp = db.table("flats").select("uuid, tenant_uuid").in_("building_id", building_ids).execute()
                flat_uuids = [f["uuid"] for f in flats_resp.data if f.get("uuid")]
                tenant_uuids = [f["tenant_uuid"] for f in flats_resp.data if f.get("tenant_uuid")]
            if not force and tenant_uuids:
                return JSONResponse(
                    status_code=409,
                    content={
                        "detail": "tenant_block",
                        "tenant_count": len(tenant_uuids),
                        "message": f"This property contains {len(tenant_uuids)} active tenant(s). Confirm deletion.",
                    }
                )
            if flat_uuids:
                listings_resp = db.table("lease_listings").select("uuid").in_("flat_uuid", flat_uuids).execute()
                listing_uuids = [l["uuid"] for l in listings_resp.data]
                if listing_uuids:
                    db.table("lease_leads").update({"listing_uuid": None}).in_("listing_uuid", listing_uuids).execute()
                    print(f"  [CASCADE] nullified {len(listing_uuids)} lease_leads for {property_id}")
                db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
                print(f"  [CASCADE] deleted lease_listings for {len(flat_uuids)} flats")
                db.table("rents").delete().in_("flat_uuid", flat_uuids).execute()
                print(f"  [CASCADE] deleted rents for {len(flat_uuids)} flats")
            if tenant_uuids:
                db.table("complaints").delete().in_("tenant_uuid", tenant_uuids).execute()
                print(f"  [CASCADE] deleted complaints for {len(tenant_uuids)} tenants")
                db.table("appointments").delete().in_("tenant_uuid", tenant_uuids).execute()
                print(f"  [CASCADE] deleted appointments for {len(tenant_uuids)} tenants")
                db.table("call_logs").delete().in_("tenant_uuid", tenant_uuids).execute()
                print(f"  [CASCADE] deleted call_logs for {len(tenant_uuids)} tenants")
                db.table("tenants").delete().in_("uuid", tenant_uuids).execute()
                print(f"  [CASCADE] deleted {len(tenant_uuids)} tenants")
            if building_ids:
                db.table("flats").delete().in_("building_id", building_ids).execute()
                print(f"  [CASCADE] deleted flats for {len(building_ids)} buildings")
                db.table("buildings").delete().eq("property_id", property_id).execute()
                print(f"  [CASCADE] deleted {len(building_ids)} buildings")
            db.table("lease_leads").delete().eq("property_group_id", property_id).execute()
            print(f"  [CASCADE] deleted lease_leads for property group {property_id}")
            db.table("properties_list").delete().eq("id", property_id).execute()
            print(f"  [CASCADE] deleted property group {property_id}")
            deleted += 1
        except Exception as e:
            print(f"  [CASCADE ERROR] property_id={property_id}: {e}")
            errors.append(f"{property_id}: {clean_db_error(e)}")
    return {"deleted": deleted, "errors": errors}


@router.delete("/{property_id}", status_code=status.HTTP_200_OK)
async def delete_property_group(
    property_id: str,
    force: bool = Query(False),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    try:
        prop_resp = db.table("properties_list").select("id").eq("id", property_id).execute()
        if not prop_resp.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Property group with ID {property_id} not found")

        buildings_resp = db.table("buildings").select("id").eq("property_id", property_id).execute()
        building_ids = [b["id"] for b in buildings_resp.data]

        flat_uuids = []
        tenant_uuids = []

        if building_ids:
            flats_resp = db.table("flats").select("uuid, tenant_uuid").in_("building_id", building_ids).execute()
            flat_uuids = [f["uuid"] for f in flats_resp.data if f.get("uuid")]
            tenant_uuids = [f["tenant_uuid"] for f in flats_resp.data if f.get("tenant_uuid")]

        if not force and tenant_uuids:
            return JSONResponse(
                status_code=409,
                content={
                    "detail": "tenant_block",
                    "tenant_count": len(tenant_uuids),
                    "message": f"This property contains {len(tenant_uuids)} active tenant(s). Confirm deletion.",
                }
            )

        if flat_uuids:
            listings_resp = db.table("lease_listings").select("uuid").in_("flat_uuid", flat_uuids).execute()
            listing_uuids = [l["uuid"] for l in listings_resp.data]
            if listing_uuids:
                db.table("lease_leads").update({"listing_uuid": None}).in_("listing_uuid", listing_uuids).execute()
                print(f"  [CASCADE] nullified {len(listing_uuids)} lease_leads for {property_id}")
            db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
            print(f"  [CASCADE] deleted lease_listings for {len(flat_uuids)} flats")
            db.table("rents").delete().in_("flat_uuid", flat_uuids).execute()
            print(f"  [CASCADE] deleted rents for {len(flat_uuids)} flats")

        if tenant_uuids:
            db.table("complaints").delete().in_("tenant_uuid", tenant_uuids).execute()
            print(f"  [CASCADE] deleted complaints for {len(tenant_uuids)} tenants")
            db.table("appointments").delete().in_("tenant_uuid", tenant_uuids).execute()
            print(f"  [CASCADE] deleted appointments for {len(tenant_uuids)} tenants")
            db.table("call_logs").delete().in_("tenant_uuid", tenant_uuids).execute()
            print(f"  [CASCADE] deleted call_logs for {len(tenant_uuids)} tenants")
            db.table("tenants").delete().in_("uuid", tenant_uuids).execute()
            print(f"  [CASCADE] deleted {len(tenant_uuids)} tenants")

        if building_ids:
            db.table("flats").delete().in_("building_id", building_ids).execute()
            print(f"  [CASCADE] deleted flats for {len(building_ids)} buildings")
            db.table("buildings").delete().eq("property_id", property_id).execute()
            print(f"  [CASCADE] deleted {len(building_ids)} buildings")

        db.table("lease_leads").delete().eq("property_group_id", property_id).execute()
        print(f"  [CASCADE] deleted lease_leads for property group {property_id}")
        db.table("properties_list").delete().eq("id", property_id).execute()
        print(f"  [CASCADE] deleted property group {property_id}")
        return Response(status_code=204)

    except HTTPException:
        raise
    except Exception as e:
        print(f"  [CASCADE ERROR] property_id={property_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error deleting property group: {clean_db_error(e)}")
