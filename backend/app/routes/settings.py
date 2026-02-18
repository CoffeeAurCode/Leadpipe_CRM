"""
Property Settings API Routes

Endpoints for managing property-level feature flags.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
from typing import Dict
from app.dependencies.features import get_feature_service
from app.services.feature_service import FeatureService
from app.core.features import Feature


router = APIRouter(tags=["Settings"])


class FeatureToggleRequest(BaseModel):
    """Request body for toggling features"""
    features: Dict[str, bool]
    
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


@router.get("/properties/{property_uuid}/settings")
async def get_property_settings(
    property_uuid: str,
    service: FeatureService = Depends(get_feature_service)
):
    """
    Get all feature settings for a property.
    
    Returns feature states grouped by category with metadata.
    """
    try:
        features = await service.get_property_features(property_uuid)
        
        return {
            "property_uuid": property_uuid,
            "features": features
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch settings: {str(e)}"
        )


@router.patch("/properties/{property_uuid}/settings")
async def update_property_settings(
    property_uuid: str,
    request: FeatureToggleRequest,
    service: FeatureService = Depends(get_feature_service)
):
    """
    Toggle feature flags for a property.
    
    Accepts a dictionary of feature keys to boolean values.
    Only updates the features specified in the request.
    """
    try:
        # Apply all feature updates
        for feature_key, enabled in request.features.items():
            await service.set_feature_enabled(
                property_uuid,
                Feature(feature_key),
                enabled
            )
        
        # Return updated feature state
        updated_features = await service.get_property_features(property_uuid)
        
        return {
            "property_uuid": property_uuid,
            "features": updated_features,
            "message": f"Updated {len(request.features)} feature(s)"
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}"
        )
