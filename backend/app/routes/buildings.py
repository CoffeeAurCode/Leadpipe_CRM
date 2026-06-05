"""
Buildings API Routes

CRUD for buildings. Each building can hold multiple flats/units (linked via building_id FK).
Property types (Residential, Commercial, Mixed-use) are linked via property_type_id.

Unit counts are aggregated from the flats table in a single extra query to avoid N+1.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.core.db_errors import clean_db_error
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

router = APIRouter(prefix="/buildings", tags=["Buildings"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────────

class BuildingCreate(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Canada"


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_id: Optional[UUID] = None
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class BuildingResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_type_name: Optional[str] = None
    property_type_icon: Optional[str] = None
    property_id: Optional[UUID] = None
    unit_count: int = 0
    occupied_count: int = 0
    created_at: datetime


# ── Helper ────────────────────────────────────────────────────────────────────

def _enrich_buildings(buildings: list, all_flats: list) -> list:
    """
    Merges unit count data from all_flats into buildings list.
    Called after fetching both in the GET /buildings handler to avoid N+1.
    """
    # Build count maps keyed by building_id (str)
    unit_counts: dict[str, int] = {}
    occupied_counts: dict[str, int] = {}

    for flat in all_flats:
        bid = flat.get("building_id")
        if bid:
            unit_counts[bid] = unit_counts.get(bid, 0) + 1
            if flat.get("tenant_uuid"):
                occupied_counts[bid] = occupied_counts.get(bid, 0) + 1

    result = []
    for b in buildings:
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
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "property_id": b.get("property_id"),
            "unit_count": unit_counts.get(bid, 0),
            "occupied_count": occupied_counts.get(bid, 0),
            "created_at": b["created_at"],
        })
    return result


def _fetch_property_type(db: Client, property_type_id: str) -> dict:
    """Fetch property type name/icon for a single building response."""
    if not property_type_id:
        return {}
    try:
        resp = db.table("property_types").select("name, icon_type").eq("id", str(property_type_id)).execute()
        return resp.data[0] if resp.data else {}
    except Exception:
        return {}


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=List[BuildingResponse])
async def get_all_buildings(user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Get all buildings with property type info and unit counts.
    Uses 2 queries total (buildings + flats summary) — no N+1.
    """
    try:
        # Query 1: buildings with joined property_types
        buildings_resp = (
            db.table("buildings")
            .select("*, property_types(name, icon_type)")
            .order("name")
            .execute()
        )

        # Query 2: flat summaries for all buildings (only building_id + tenant_uuid needed)
        flats_resp = db.table("flats").select("building_id, tenant_uuid").execute()

        return _enrich_buildings(buildings_resp.data, flats_resp.data)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching buildings: {str(e)}"
        )


@router.get("/{building_id}/units")
async def get_building_units(building_id: str, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Get all units (flats) belonging to a specific building.
    Returns raw flat records — frontend maps them to unit cards.
    """
    try:
        response = (
            db.table("flats")
            .select("*")
            .eq("building_id", building_id)
            .order("flat_number")
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching units for building {building_id}: {str(e)}"
        )


@router.get("/{building_id}", response_model=BuildingResponse)
async def get_building_by_id(
    building_id: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    try:
        resp = (
            db.table("buildings")
            .select("*, property_types(name, icon_type)")
            .eq("id", building_id)
            .execute()
        )
        if not resp.data:
            raise HTTPException(status_code=404, detail="Building not found")
        b = resp.data[0]
        pt = b.get("property_types") or {}
        flats_resp = db.table("flats").select("tenant_uuid").eq("building_id", building_id).execute()
        units = flats_resp.data or []
        return {
            **b,
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "unit_count": len(units),
            "occupied_count": sum(1 for u in units if u.get("tenant_uuid")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching building: {str(e)}")


@router.post("", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
async def create_building(request: BuildingCreate, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """Create a new building."""
    try:
        payload = {k: str(v) if isinstance(v, UUID) else v for k, v in request.model_dump(exclude_none=True).items()}

        response = db.table("buildings").insert(payload).execute()
        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create building")

        b = response.data[0]
        pt = _fetch_property_type(db, b.get("property_type_id"))

        return {**b, "property_type_name": pt.get("name"), "property_type_icon": pt.get("icon_type"), "unit_count": 0, "occupied_count": 0}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating building: {str(e)}")


@router.patch("/{building_id}", response_model=BuildingResponse)
async def update_building(building_id: str, request: BuildingUpdate, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """Update a building's details."""
    try:
        payload = {k: str(v) if isinstance(v, UUID) else v for k, v in request.model_dump(exclude_none=True).items()}

        response = db.table("buildings").update(payload).eq("id", building_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Building not found")

        b = response.data[0]
        pt = _fetch_property_type(db, b.get("property_type_id"))

        # Get unit counts for the updated building
        flats_resp = db.table("flats").select("tenant_uuid").eq("building_id", building_id).execute()
        units = flats_resp.data

        return {
            **b,
            "property_type_name": pt.get("name"),
            "property_type_icon": pt.get("icon_type"),
            "unit_count": len(units),
            "occupied_count": sum(1 for u in units if u.get("tenant_uuid")),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating building: {str(e)}")


class BulkDeleteBuildingsRequest(BaseModel):
    ids: List[str]


@router.delete("/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete_buildings(
    request: BulkDeleteBuildingsRequest,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """Bulk delete buildings. Cascade-deletes lease_listings, rents, tenants, and flats."""
    deleted = 0
    errors = []
    for building_id in request.ids:
        try:
            building_resp = db.table("buildings").select("id").eq("id", building_id).execute()
            if not building_resp.data:
                errors.append(f"{building_id}: not found")
                continue
            flats_resp = db.table("flats").select("uuid, tenant_uuid").eq("building_id", building_id).execute()
            flat_uuids = [f["uuid"] for f in flats_resp.data if f.get("uuid")]
            tenant_uuids = [f["tenant_uuid"] for f in flats_resp.data if f.get("tenant_uuid")]
            if flat_uuids:
                db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
                db.table("rents").delete().in_("flat_uuid", flat_uuids).execute()
            if tenant_uuids:
                db.table("tenants").delete().in_("uuid", tenant_uuids).execute()
            if flat_uuids:
                db.table("flats").delete().eq("building_id", building_id).execute()
            db.table("buildings").delete().eq("id", building_id).execute()
            deleted += 1
        except Exception as e:
            errors.append(f"{building_id}: {clean_db_error(e)}")
    return {"deleted": deleted, "errors": errors}


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(building_id: str, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """Delete a building and cascade-delete all its flats, tenants, rent records, and lease listings."""
    try:
        building_resp = db.table("buildings").select("id").eq("id", building_id).execute()
        if not building_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Building {building_id} not found"
            )

        flats_resp = db.table("flats").select("uuid, tenant_uuid").eq("building_id", building_id).execute()
        flat_uuids = [f["uuid"] for f in flats_resp.data if f.get("uuid")]
        tenant_uuids = [f["tenant_uuid"] for f in flats_resp.data if f.get("tenant_uuid")]

        if flat_uuids:
            db.table("lease_listings").delete().in_("flat_uuid", flat_uuids).execute()
            db.table("rents").delete().in_("flat_uuid", flat_uuids).execute()
        if tenant_uuids:
            db.table("tenants").delete().in_("uuid", tenant_uuids).execute()
        if flat_uuids:
            db.table("flats").delete().eq("building_id", building_id).execute()

        db.table("buildings").delete().eq("id", building_id).execute()
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting building: {clean_db_error(e)}"
        )
