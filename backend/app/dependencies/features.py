"""
Feature Control Dependencies

FastAPI dependency injection utilities for feature gating.
"""

from fastapi import Depends, HTTPException, status
from supabase import Client
from app.db.session import get_db
from app.services.feature_service import FeatureService
from app.core.features import Feature


def get_feature_service(db: Client = Depends(get_db)) -> FeatureService:
    """Dependency: Get feature service instance"""
    return FeatureService(db)


def requires_feature(feature: Feature):
    """
    Dependency factory for feature gating.
    
    Use this to protect routes that require specific features.
    
    Usage:
        @router.post(
            "/rent", 
            dependencies=[Depends(requires_feature(Feature.RENT_MANAGEMENT))]
        )
        async def set_rent(property_uuid: str, ...):
            # This route only executes if RENT_MANAGEMENT is enabled
            ...
    
    Args:
        feature: The Feature enum value that must be enabled
        
    Returns:
        FastAPI dependency function that raises 403 if feature is disabled
    """
    async def check_feature(
        property_uuid: str,
        service: FeatureService = Depends(get_feature_service)
    ):
        is_enabled = await service.is_feature_enabled(property_uuid, feature)
        
        if not is_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_disabled",
                    "message": f"The '{feature.value}' feature is not enabled for this property",
                    "feature": feature.value
                }
            )
    
    return check_feature
