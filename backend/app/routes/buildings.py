"""
Buildings API Routes

CRUD for buildings. Each building can hold multiple flats/units (linked via building_id FK).
Property types (Residential, Commercial, Mixed-use) are linked via property_type_id.

Unit counts are aggregated from the flats table in a single extra query to avoid N+1.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
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
    property_id: Optional[UUID] = None  # Link to properties_list table


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_id: Optional[UUID] = None  # Allow re-assigning to a different property group


class BuildingResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    image_url: Optional[str] = None
    property_type_id: Optional[UUID] = None
    property_type_name: Optional[str] = None
    property_type_icon: Optional[str] = None  # "house" | "shop" | "apartment"
    property_id: Optional[UUID] = None  # Parent property group
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
async def get_all_buildings(db: Client = Depends(get_db)):
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
async def get_building_units(building_id: str, db: Client = Depends(get_db)):
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


@router.post("", response_model=BuildingResponse, status_code=status.HTTP_201_CREATED)
async def create_building(request: BuildingCreate, db: Client = Depends(get_db)):
    """Create a new building."""
    try:
        payload = request.model_dump(exclude_none=True)
        if "property_type_id" in payload:
            payload["property_type_id"] = str(payload["property_type_id"])

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
async def update_building(building_id: str, request: BuildingUpdate, db: Client = Depends(get_db)):
    """Update a building's details."""
    try:
        payload = request.model_dump(exclude_none=True)
        if "property_type_id" in payload:
            payload["property_type_id"] = str(payload["property_type_id"])

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
