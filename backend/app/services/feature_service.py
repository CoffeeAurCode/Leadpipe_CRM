"""
Feature Permission Service

Handles feature flag lookups and management for properties.
Provides centralized logic for checking if features are enabled.
Supports hierarchical settings: Property -> Building -> Unit.
- Property-level is the base default.
- Building overrides the property default for all units in that building.
- Unit overrides both property and building level settings.
"""

from typing import Dict, Optional
from supabase import Client
from app.core.features import Feature, FEATURE_METADATA, get_default_state


class FeatureService:
    """Service for managing property feature flags with hierarchical scoping"""

    def __init__(self, db: Client):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL: Generic fetch for any scope
    # ──────────────────────────────────────────────────────────────────────────

    # Whether the DB table has the building_id / unit_id columns yet.
    # This is determined lazily on first call; set to False if they are missing.
    _scoped_columns_available: bool = True

    def _fetch_feature_rows(self, filters: dict) -> dict:
        """Fetch rows from property_features matching all given filters.

        Falls back gracefully if building_id / unit_id columns don't exist yet
        (i.e. migration 006 hasn't been run). In that case, only property_uuid
        and feature_key are used as filters.
        """
        # If we already know scoped columns are absent, skip them
        if not FeatureService._scoped_columns_available:
            filters = {k: v for k, v in filters.items()
                       if k not in ("building_id", "unit_id")}

        query = self.db.table("property_features").select("feature_key, enabled")
        for col, val in filters.items():
            if val is None:
                query = query.is_(col, "null")
            else:
                query = query.eq(col, val)
        try:
            result = query.execute()
            return {row["feature_key"]: row["enabled"] for row in (result.data or [])}
        except Exception as exc:
            err_msg = str(exc)
            if "building_id" in err_msg or "unit_id" in err_msg:
                # Columns don't exist yet — disable scoped lookups globally and retry
                FeatureService._scoped_columns_available = False
                print("[FeatureService] Scoped columns not found, falling back to "
                      "property-only scope. Run migration 006 to enable hierarchy.")
                # Retry without scoped columns
                safe_filters = {k: v for k, v in filters.items()
                                if k not in ("building_id", "unit_id")}
                q2 = self.db.table("property_features").select("feature_key, enabled")
                for col, val in safe_filters.items():
                    if val is None:
                        q2 = q2.is_(col, "null")
                    else:
                        q2 = q2.eq(col, val)
                result2 = q2.execute()
                return {row["feature_key"]: row["enabled"] for row in (result2.data or [])}
            raise

    def _resolve_features(self, property_uuid: str, building_id: Optional[int] = None, unit_id: Optional[int] = None) -> Dict[str, dict]:
        """
        Resolve the effective settings for a given scope by merging inheritance layers.
        Order: Property defaults → Building override → Unit override.
        If scoped columns (building_id, unit_id) don't exist yet, only property-level
        settings are returned (graceful degradation).
        """
        # Layer 1: Property-level (always the baseline)
        prop_features = self._fetch_feature_rows(
            {"property_uuid": property_uuid, "building_id": None, "unit_id": None}
        )

        # Layer 2: Building-level (only if scoped columns exist)
        bldg_features = {}
        if building_id is not None and FeatureService._scoped_columns_available:
            bldg_features = self._fetch_feature_rows(
                {"property_uuid": property_uuid, "building_id": building_id, "unit_id": None}
            )

        # Layer 3: Unit-level (only if scoped columns exist)
        unit_features = {}
        if unit_id is not None and FeatureService._scoped_columns_available:
            unit_features = self._fetch_feature_rows(
                {"property_uuid": property_uuid, "building_id": building_id, "unit_id": unit_id}
            )

        # Build merged feature map with inheritance indicators
        feature_map = {}
        for feature in Feature:
            metadata = FEATURE_METADATA.get(feature, {})
            key = feature.value
            default = get_default_state(feature)

            prop_val = prop_features.get(key)         # None = not set
            bldg_val = bldg_features.get(key)
            unit_val = unit_features.get(key)

            if unit_id is not None and unit_val is not None:
                effective = unit_val
                source = "overridden"
            elif building_id is not None and bldg_val is not None:
                effective = bldg_val
                source = "building"  # unit is inheriting from building
            elif prop_val is not None:
                effective = prop_val
                source = "inherited"  # from property
            else:
                effective = default
                source = "default"

            feature_map[key] = {
                "enabled": effective,
                "source": source,       # "overridden" | "inherited" | "building" | "default"
                "category": metadata.get("category", "Other"),
                "display_name": metadata.get("display_name", key),
                "description": metadata.get("description", "")
            }

        return feature_map

    # ──────────────────────────────────────────────────────────────────────────
    # Public: Get features (property / building / unit scoped)
    # ──────────────────────────────────────────────────────────────────────────

    async def is_feature_enabled(self, property_uuid: str, feature: Feature) -> bool:
        """Check if a feature is enabled for a specific property (fast path)."""
        try:
            result = self.db.table("property_features") \
                .select("enabled") \
                .eq("property_uuid", property_uuid) \
                .eq("feature_key", feature.value) \
                .is_("building_id", "null") \
                .is_("unit_id", "null") \
                .execute()
            if not result.data:
                return get_default_state(feature)
            return result.data[0].get("enabled", False)
        except Exception as e:
            print(f"[FeatureService] Error checking feature {feature.value}: {e}")
            return get_default_state(feature)

    async def get_property_features(self, property_uuid: str) -> Dict[str, dict]:
        """Get all feature states for a property (no building/unit scoping)."""
        try:
            return self._resolve_features(property_uuid)
        except Exception as e:
            print(f"[FeatureService] Error fetching features for {property_uuid}: {e}")
            return {
                feature.value: {
                    "enabled": get_default_state(feature),
                    "source": "default",
                    **FEATURE_METADATA.get(feature, {})
                }
                for feature in Feature
            }

    async def get_scoped_features(
        self,
        property_uuid: str,
        building_id: Optional[int] = None,
        unit_id: Optional[int] = None
    ) -> Dict[str, dict]:
        """
        Get features resolved for a specific scope with inheritance metadata.
        - Building scope: property_uuid + building_id
        - Unit scope: property_uuid + building_id + unit_id
        """
        try:
            return self._resolve_features(property_uuid, building_id, unit_id)
        except Exception as e:
            print(f"[FeatureService] Error fetching scoped features: {e}")
            return {
                feature.value: {
                    "enabled": get_default_state(feature),
                    "source": "default",
                    **FEATURE_METADATA.get(feature, {})
                }
                for feature in Feature
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Public: Set features (upsert into property_features table)
    # ──────────────────────────────────────────────────────────────────────────

    async def set_feature_enabled(
        self,
        property_uuid: str,
        feature: Feature,
        enabled: bool,
        building_id: Optional[int] = None,
        unit_id: Optional[int] = None
    ) -> None:
        """Enable or disable a feature at the specified scope."""
        try:
            if FeatureService._scoped_columns_available:
                row = {
                    "property_uuid": property_uuid,
                    "feature_key": feature.value,
                    "enabled": enabled,
                    "building_id": building_id,
                    "unit_id": unit_id
                }
                self.db.table("property_features") \
                    .upsert(row, on_conflict="property_uuid,feature_key,building_id,unit_id") \
                    .execute()
            else:
                # Scoped columns not available — save at property level only
                row = {
                    "property_uuid": property_uuid,
                    "feature_key": feature.value,
                    "enabled": enabled,
                }
                self.db.table("property_features") \
                    .upsert(row, on_conflict="property_uuid,feature_key") \
                    .execute()
        except Exception as e:
            err_msg = str(e)
            if ("building_id" in err_msg or "unit_id" in err_msg) and FeatureService._scoped_columns_available:
                # Columns missing — retry at property scope only
                FeatureService._scoped_columns_available = False
                row_simple = {
                    "property_uuid": property_uuid,
                    "feature_key": feature.value,
                    "enabled": enabled,
                }
                self.db.table("property_features") \
                    .upsert(row_simple, on_conflict="property_uuid,feature_key") \
                    .execute()
            else:
                print(f"[FeatureService] Error setting feature {feature.value}: {e}")
                raise


    async def initialize_property_features(self, property_uuid: str) -> None:
        """Initialize default features for a new property."""
        core_features = [f for f in Feature if get_default_state(f)]
        for feature in core_features:
            try:
                await self.set_feature_enabled(property_uuid, feature, True)
            except Exception as e:
                print(f"[FeatureService] Error initializing {feature.value}: {e}")
