"""
Property Settings API Routes

Endpoints for managing feature flags at Property, Building, and Unit levels.
Hierarchical inheritance: Property -> Building -> Unit.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, validator
from typing import Dict, Optional
from app.dependencies.features import get_feature_service
from app.services.feature_service import FeatureService
from app.core.features import Feature


router = APIRouter(tags=["Settings"])


class FeatureToggleRequest(BaseModel):
    """Request body for toggling features"""
    features: Dict[str, bool]
    # Optional scope — if omitted, applies at property level
    building_id: Optional[int] = None
    unit_id: Optional[int] = None
    # Bulk override: when True, existing child overrides are cleared before setting
    replace_overrides: bool = False

    @validator('features')
    def validate_feature_keys(cls, v):
        """Ensure all keys are valid feature names"""
        valid_features = {f.value for f in Feature}
        invalid_keys = set(v.keys()) - valid_features
        if invalid_keys:
            raise ValueError(
                f"Invalid feature keys: {', '.join(invalid_keys)}. "
                f"Valid features: {', '.join(valid_features)}"
            )
        return v


# ──────────────────────────────────────────────────────────────────────────────
# GET  /properties/{property_uuid}/settings
# Backward-compatible: property-level only (no building/unit filter)
# ──────────────────────────────────────────────────────────────────────────────
@router.get("/properties/{property_uuid}/settings")
async def get_property_settings(
    property_uuid: str,
    building_id: Optional[int] = Query(None, description="Optional: filter to a building scope"),
    unit_id: Optional[int] = Query(None, description="Optional: filter to a unit scope (requires building_id)"),
    service: FeatureService = Depends(get_feature_service)
):
    """
    Get resolved feature settings for the given scope.

    - No building_id / unit_id → property-level defaults
    - building_id provided → building-level (inherits from property)
    - unit_id provided     → unit-level   (inherits from property + building)
    """
    try:
        if building_id or unit_id:
            features = await service.get_scoped_features(property_uuid, building_id, unit_id)
        else:
            features = await service.get_property_features(property_uuid)

        return {
            "property_uuid": property_uuid,
            "building_id": building_id,
            "unit_id": unit_id,
            "features": features
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch settings: {str(e)}"
        )


# ──────────────────────────────────────────────────────────────────────────────
# PATCH  /properties/{property_uuid}/settings
# Accepts optional building_id / unit_id in the request body to scope the write.
# ──────────────────────────────────────────────────────────────────────────────
@router.patch("/properties/{property_uuid}/settings")
async def update_property_settings(
    property_uuid: str,
    request: FeatureToggleRequest,
    service: FeatureService = Depends(get_feature_service)
):
    """
    Toggle feature flags at the given scope.

    - body.building_id = null  → property-level update
    - body.building_id set     → building-level update
    - body.unit_id set         → unit-level update

    replace_overrides=true clears all child-level rows before writing
    (useful for a true bulk reset at property or building level).
    """
    try:
        building_id = request.building_id
        unit_id = request.unit_id

        # Optional: clear child overrides for a "real bulk" operation
        if request.replace_overrides:
            if unit_id is None and building_id is None:
                # Property-level bulk: wipe all building and unit rows for this property
                service.db.table("property_features") \
                    .delete() \
                    .eq("property_uuid", property_uuid) \
                    .not_.is_("building_id", "null") \
                    .execute()
            elif unit_id is None and building_id is not None:
                # Building-level bulk: wipe all unit rows for this building
                service.db.table("property_features") \
                    .delete() \
                    .eq("property_uuid", property_uuid) \
                    .eq("building_id", building_id) \
                    .not_.is_("unit_id", "null") \
                    .execute()

        # Apply all feature updates at the specified scope
        for feature_key, enabled in request.features.items():
            await service.set_feature_enabled(
                property_uuid,
                Feature(feature_key),
                enabled,
                building_id=building_id,
                unit_id=unit_id
            )

        # Return updated state
        if building_id or unit_id:
            updated_features = await service.get_scoped_features(property_uuid, building_id, unit_id)
        else:
            updated_features = await service.get_property_features(property_uuid)

        return {
            "property_uuid": property_uuid,
            "building_id": building_id,
            "unit_id": unit_id,
            "features": updated_features,
            "message": f"Updated {len(request.features)} feature(s)"
        }

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )
