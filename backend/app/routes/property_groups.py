"""
Property Groups API Routes

CRUD for the 'properties_list' table — the true top-level entity.
Each property_group can contain multiple buildings (linked via buildings.property_id FK).

Hierarchy: Property → Building → Unit (flat)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
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


class PropertyGroupResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_type_name: Optional[str] = None
    property_type_icon: Optional[str] = None
    building_count: int = 0
    created_at: datetime


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[PropertyGroupResponse])
async def get_all_property_groups(db: Client = Depends(get_db)):
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
                "image_url": g.get("image_url"),
                "property_type_id": g.get("property_type_id"),
                "property_type_name": pt.get("name"),
                "property_type_icon": pt.get("icon_type"),
                "building_count": count_map.get(str(g["id"]), 0),
                "created_at": g["created_at"],
            })
        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching property groups: {str(e)}"
        )


@router.post("", response_model=PropertyGroupResponse, status_code=status.HTTP_201_CREATED)
async def create_property_group(request: PropertyGroupCreate, db: Client = Depends(get_db)):
    """Create a new property group."""
    try:
        payload = request.model_dump(exclude_none=True)
        if "property_type_id" in payload:
            payload["property_type_id"] = str(payload["property_type_id"])

        response = db.table("properties_list").insert(payload).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create property group")

        g = response.data[0]

        # Fetch property type info for response
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


@router.get("/{property_id}/buildings")
async def get_property_buildings(property_id: str, db: Client = Depends(get_db)):
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


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property_group(property_id: str, db: Client = Depends(get_db)):
    """
    Delete a property group and cascade-delete all buildings, flats, rents, and tenants within it.
    Order: tenants → rents → flats → buildings → property group
    """
    try:
        prop_resp = db.table("properties_list").select("id").eq("id", property_id).execute()
        if not prop_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Property group with ID {property_id} not found"
            )

        buildings_resp = db.table("buildings").select("id").eq("property_id", property_id).execute()
        building_ids = [b["id"] for b in buildings_resp.data]

        if building_ids:
            flats_resp = (
                db.table("flats")
                .select("id, uuid, tenant_uuid")
                .in_("building_id", building_ids)
                .execute()
            )
            flat_uuids = [f["uuid"] for f in flats_resp.data if f.get("uuid")]
            tenant_uuids = [f["tenant_uuid"] for f in flats_resp.data if f.get("tenant_uuid")]

            if tenant_uuids:
                db.table("tenants").delete().in_("uuid", tenant_uuids).execute()
            if flat_uuids:
                db.table("rents").delete().in_("flat_uuid", flat_uuids).execute()
            db.table("flats").delete().in_("building_id", building_ids).execute()
            db.table("buildings").delete().eq("property_id", property_id).execute()

        db.table("properties_list").delete().eq("id", property_id).execute()
        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting property group: {str(e)}"
        )
