"""
Feature Permission Service

Handles feature flag lookups and management for properties.
Provides centralized logic for checking if features are enabled.
"""

from typing import Dict, Optional
from supabase import Client
from app.core.features import Feature, FEATURE_METADATA, get_default_state


class FeatureService:
    """Service for managing property feature flags"""
    
    def __init__(self, db: Client):
        self.db = db
    
    async def is_feature_enabled(
        self, 
        property_uuid: str, 
        feature: Feature
    ) -> bool:
        """
        Check if a feature is enabled for a specific property.
        
        Args:
            property_uuid: UUID of the property
            feature: Feature enum value to check
            
        Returns:
            True if feature is enabled, False otherwise
        """
        try:
            result = self.db.table("property_features")\
                .select("enabled")\
                .eq("property_uuid", property_uuid)\
                .eq("feature_key", feature.value)\
                .execute()
            
            # If no record exists, use default state
            if not result.data:
                return get_default_state(feature)
            
            return result.data[0].get("enabled", False)
            
        except Exception as e:
            # Log error and fail open for core features, closed for non-core
            print(f"[FeatureService] Error checking feature {feature.value}: {e}")
            return get_default_state(feature)
    
    async def get_property_features(self, property_uuid: str) -> Dict[str, dict]:
        """
        Get all feature states and metadata for a property.
        
        Args:
            property_uuid: UUID of the property
            
        Returns:
            Dictionary mapping feature keys to their state and metadata
        """
        try:
            # Fetch all configured features for this property
            result = self.db.table("property_features")\
                .select("feature_key, enabled")\
                .eq("property_uuid", property_uuid)\
                .execute()
            
            # Build map of configured features
            configured_features = {
                row["feature_key"]: row["enabled"] 
                for row in result.data
            }
            
            # Build complete feature map with defaults and metadata
            feature_map = {}
            for feature in Feature:
                metadata = FEATURE_METADATA.get(feature, {})
                feature_map[feature.value] = {
                    "enabled": configured_features.get(
                        feature.value, 
                        get_default_state(feature)
                    ),
                    "category": metadata.get("category", "Other"),
                    "display_name": metadata.get("display_name", feature.value),
                    "description": metadata.get("description", "")
                }
            
            return feature_map
            
        except Exception as e:
            print(f"[FeatureService] Error fetching features for {property_uuid}: {e}")
            # Return defaults on error
            return {
                feature.value: {
                    "enabled": get_default_state(feature),
                    **FEATURE_METADATA.get(feature, {})
                }
                for feature in Feature
            }
    
    async def set_feature_enabled(
        self, 
        property_uuid: str, 
        feature: Feature, 
        enabled: bool
    ) -> None:
        """
        Enable or disable a feature for a property.
        
        Args:
            property_uuid: UUID of the property
            feature: Feature enum value to update
            enabled: True to enable, False to disable
        """
        try:
            self.db.table("property_features")\
                .upsert({
                    "property_uuid": property_uuid,
                    "feature_key": feature.value,
                    "enabled": enabled
                }, on_conflict="property_uuid,feature_key")\
                .execute()
                
        except Exception as e:
            print(f"[FeatureService] Error setting feature {feature.value}: {e}")
            raise
    
    async def initialize_property_features(self, property_uuid: str) -> None:
        """
        Initialize default features for a new property.
        Called when a property is created.
        
        Args:
            property_uuid: UUID of the new property
        """
        core_features = [
            feature for feature in Feature 
            if get_default_state(feature)
        ]
        
        for feature in core_features:
            try:
                await self.set_feature_enabled(property_uuid, feature, True)
            except Exception as e:
                print(f"[FeatureService] Error initializing {feature.value}: {e}")
