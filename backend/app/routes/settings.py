"""
Property Settings API Routes (Unit-Centric)

All feature flags live at the unit level. Bulk operations cascade in the backend.

Endpoints:
  GET  /properties/{property_uuid}/settings          → aggregate view for a property
  GET  /properties/{property_uuid}/settings/building/{building_id}  → aggregate view for a building
  GET  /units/{unit_id}/settings                     → settings for one unit

  PATCH /properties/{property_uuid}/settings         → bulk-apply to ALL units in the property
  PATCH /properties/{property_uuid}/settings/building/{building_id} → bulk-apply to building units
  PATCH /units/{unit_id}/settings                    → update one unit directly
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
from typing import Dict, Optional
from app.dependencies.features import get_feature_service
from app.services.feature_service import FeatureService
from app.core.features import Feature


router = APIRouter(tags=["Settings"])


# ── Request / Response schemas ────────────────────────────────────────────────

class FeatureToggleRequest(BaseModel):
    """Request body: map of feature_key -> enabled bool."""
    features: Dict[str, bool]

    @validator("features")
    def validate_feature_keys(cls, v):
        valid = {f.value for f in Feature}
        bad = set(v.keys()) - valid
        if bad:
            raise ValueError(
                f"Invalid feature keys: {', '.join(bad)}. "
                f"Valid: {', '.join(valid)}"
            )
        return v


# ── GET: Property aggregate ───────────────────────────────────────────────────

@router.get("/properties/{property_uuid}/settings")
async def get_property_settings(
    property_uuid: str,
    service: FeatureService = Depends(get_feature_service),
):
    """
    Returns the aggregate feature state across all units in the property.
    (Majority-vote per feature so the UI shows a representative value.)
    """
    try:
        features = await service.get_property_features(property_uuid)
        return {
            "scope": "property",
            "property_uuid": property_uuid,
            "features": features,
        }
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to fetch property settings: {e}")


# ── GET: Building aggregate ───────────────────────────────────────────────────

@router.get("/properties/{property_uuid}/settings/building/{building_id}")
async def get_building_settings(
    property_uuid: str,
    building_id: str,
    service: FeatureService = Depends(get_feature_service),
):
    """
    Returns the aggregate feature state across all units in the building.
    """
    try:
        features = await service.get_building_features(building_id)
        return {
            "scope": "building",
            "property_uuid": property_uuid,
            "building_id": building_id,
            "features": features,
        }
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to fetch building settings: {e}")


# ── GET: Unit ─────────────────────────────────────────────────────────────────

@router.get("/units/{unit_id}/settings")
async def get_unit_settings(
    unit_id: int,
    service: FeatureService = Depends(get_feature_service),
):
    """Returns the feature flags for one specific unit."""
    try:
        features = await service.get_unit_features(unit_id)
        return {
            "scope": "unit",
            "unit_id": unit_id,
            "features": features,
        }
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to fetch unit settings: {e}")


# ── PATCH: Property bulk ──────────────────────────────────────────────────────

@router.patch("/properties/{property_uuid}/settings")
async def bulk_update_property_settings(
    property_uuid: str,
    request: FeatureToggleRequest,
    service: FeatureService = Depends(get_feature_service),
):
    """
    Applies feature flags to ALL units across all buildings in this property.
    The backend finds every child unit and upserts each one individually.
    """
    try:
        units_updated = await service.set_property_features(property_uuid, request.features)
        updated = await service.get_property_features(property_uuid)
        return {
            "scope": "property",
            "property_uuid": property_uuid,
            "units_updated": units_updated,
            "features": updated,
            "message": f"Bulk-applied {len(request.features)} feature(s) to {units_updated} unit(s)",
        }
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to update property settings: {e}")


# ── PATCH: Building bulk ──────────────────────────────────────────────────────

@router.patch("/properties/{property_uuid}/settings/building/{building_id}")
async def bulk_update_building_settings(
    property_uuid: str,
    building_id: str,
    request: FeatureToggleRequest,
    service: FeatureService = Depends(get_feature_service),
):
    """
    Applies feature flags to ALL units in this building.
    """
    try:
        units_updated = await service.set_building_features(building_id, request.features)
        updated = await service.get_building_features(building_id)
        return {
            "scope": "building",
            "property_uuid": property_uuid,
            "building_id": building_id,
            "units_updated": units_updated,
            "features": updated,
            "message": f"Bulk-applied {len(request.features)} feature(s) to {units_updated} unit(s)",
        }
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to update building settings: {e}")


# ── PATCH: Unit direct ────────────────────────────────────────────────────────

@router.patch("/units/{unit_id}/settings")
async def update_unit_settings(
    unit_id: int,
    request: FeatureToggleRequest,
    service: FeatureService = Depends(get_feature_service),
):
    """
    Directly updates feature flags for one specific unit.
    """
    try:
        await service.set_unit_features(unit_id, request.features)
        updated = await service.get_unit_features(unit_id)
        return {
            "scope": "unit",
            "unit_id": unit_id,
            "features": updated,
            "message": f"Updated {len(request.features)} feature(s) for unit {unit_id}",
        }
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to update unit settings: {e}")
