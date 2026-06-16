"""
Feature Permission Service (Unit-Centric)

Handles feature flag lookups and management for individual units.
The property_features table stores ONE ROW PER UNIT PER FEATURE.

Bulk operations (property-level / building-level saves) are resolved here:
  - The backend finds all child units and upserts their flags directly.
  - No dynamic inheritance. The DB stores only the final boolean per unit.

Hierarchy used ONLY for navigation/bulk writes, not for reads:
  Property --> fetches all buildings --> fetches all units --> upserts each unit
  Building --> fetches all units --> upserts each unit
  Unit     --> upserts directly
"""

from typing import Dict, Optional, List
from supabase import Client
from app.core.features import Feature, FEATURE_METADATA, get_default_state


class FeatureService:
    """Service for managing unit-level feature flags."""

    def __init__(self, db: Client):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL: Flat unit lookups
    # ──────────────────────────────────────────────────────────────────────────

    def _get_unit_features_raw(self, unit_id: int) -> Dict[str, bool]:
        """Fetch all feature rows for one unit. Returns {feature_key: enabled}."""
        result = (
            self.db.table("property_features")
            .select("feature_key, enabled")
            .eq("unit_id", unit_id)
            .execute()
        )
        return {row["feature_key"]: row["enabled"] for row in (result.data or [])}

    def _build_feature_map(self, raw: Dict[str, bool]) -> Dict[str, dict]:
        """Build the full feature map (with metadata) from a raw {key: bool} dict."""
        feature_map = {}
        for feature in Feature:
            metadata = FEATURE_METADATA.get(feature, {})
            key = feature.value
            enabled = raw.get(key)
            if enabled is None:
                enabled = get_default_state(feature)
                source = "default"
            else:
                source = "set"
            feature_map[key] = {
                "enabled": enabled,
                "source": source,
                "category": metadata.get("category", "Other"),
                "display_name": metadata.get("display_name", key),
                "description": metadata.get("description", ""),
            }
        return feature_map

    def _upsert_unit_features(self, unit_id: int, features: Dict[str, bool]) -> None:
        """Upsert multiple feature flags for a single unit."""
        rows = [
            {"unit_id": unit_id, "feature_key": key, "enabled": val}
            for key, val in features.items()
        ]
        if rows:
            self.db.table("property_features") \
                .upsert(rows, on_conflict="unit_id,feature_key") \
                .execute()

    # ──────────────────────────────────────────────────────────────────────────
    # INTERNAL: Hierarchy helpers — used only for bulk writes
    # ──────────────────────────────────────────────────────────────────────────

    def _get_units_for_building(self, building_id: str) -> List[int]:
        """Return all flat IDs that belong to the given building."""
        result = (
            self.db.table("flats")
            .select("id")
            .eq("building_id", building_id)
            .execute()
        )
        return [row["id"] for row in (result.data or [])]

    def _get_units_for_property(self, property_uuid: str) -> List[int]:
        """
        Return all flat IDs that belong to the property.
        Units are linked to a property through buildings (building_id → buildings.property_id).
        """
        unit_ids = set()

        # Step 1: Get all building IDs for this property
        bldg_result = (
            self.db.table("buildings")
            .select("id")
            .eq("property_id", property_uuid)
            .execute()
        )
        building_ids = [str(b["id"]) for b in (bldg_result.data or [])]

        # Step 2: Get all flats in those buildings
        if building_ids:
            flats_result = (
                self.db.table("flats")
                .select("id")
                .in_("building_id", building_ids)
                .execute()
            )
            for row in (flats_result.data or []):
                unit_ids.add(row["id"])

        return list(unit_ids)




    # ──────────────────────────────────────────────────────────────────────────
    # Public: Get features
    # ──────────────────────────────────────────────────────────────────────────

    async def get_unit_features(self, unit_id: int) -> Dict[str, dict]:
        """
        Get all feature states for a specific unit.
        Returns defaults for any feature not yet explicitly set.
        """
        try:
            raw = self._get_unit_features_raw(unit_id)
            return self._build_feature_map(raw)
        except Exception as e:
            print(f"[FeatureService] Error fetching features for unit {unit_id}: {e}")
            return self._build_feature_map({})

    async def get_building_features(self, building_id: str) -> Dict[str, dict]:
        """
        Get aggregate feature states for a building.
        Returns the MAJORITY value per feature across all units in the building.
        If a building has no units, returns system defaults.
        """
        try:
            unit_ids = self._get_units_for_building(building_id)
            if not unit_ids:
                return self._build_feature_map({})

            # Aggregate: for each feature, majority-vote enabled/disabled
            counts: Dict[str, int] = {}
            for uid in unit_ids:
                raw = self._get_unit_features_raw(uid)
                for key, val in raw.items():
                    counts.setdefault(key, 0)
                    if val:
                        counts[key] += 1

            # Build aggregate result (majority rule)
            n = len(unit_ids)
            agg_raw = {}
            for feature in Feature:
                key = feature.value
                if key in counts:
                    agg_raw[key] = counts[key] >= (n / 2)
                else:
                    agg_raw[key] = get_default_state(feature)

            return self._build_feature_map(agg_raw)
        except Exception as e:
            print(f"[FeatureService] Error fetching building features {building_id}: {e}")
            return self._build_feature_map({})

    async def get_property_features(self, property_uuid: str) -> Dict[str, dict]:
        """
        Get aggregate feature states for a property.
        Returns the MAJORITY value per feature across all units in the property.
        """
        try:
            unit_ids = self._get_units_for_property(property_uuid)
            if not unit_ids:
                return self._build_feature_map({})

            counts: Dict[str, int] = {}
            for uid in unit_ids:
                raw = self._get_unit_features_raw(uid)
                for key, val in raw.items():
                    counts.setdefault(key, 0)
                    if val:
                        counts[key] += 1

            n = len(unit_ids)
            agg_raw = {}
            for feature in Feature:
                key = feature.value
                if key in counts:
                    agg_raw[key] = counts[key] >= (n / 2)
                else:
                    agg_raw[key] = get_default_state(feature)

            return self._build_feature_map(agg_raw)
        except Exception as e:
            print(f"[FeatureService] Error fetching property features {property_uuid}: {e}")
            return self._build_feature_map({})

    # ──────────────────────────────────────────────────────────────────────────
    # Public: Fast single-feature check (for middleware/guards)
    # ──────────────────────────────────────────────────────────────────────────

    async def is_feature_enabled(self, unit_id: int, feature: Feature) -> bool:
        """Fast check: is a feature enabled for a specific unit?"""
        try:
            result = (
                self.db.table("property_features")
                .select("enabled")
                .eq("unit_id", unit_id)
                .eq("feature_key", feature.value)
                .execute()
            )
            if not result.data:
                return get_default_state(feature)
            return result.data[0].get("enabled", False)
        except Exception as e:
            print(f"[FeatureService] Error checking feature {feature.value} for unit {unit_id}: {e}")
            return get_default_state(feature)

    # ──────────────────────────────────────────────────────────────────────────
    # Public: Set features (unit / building / property scope)
    # ──────────────────────────────────────────────────────────────────────────

    async def set_unit_features(self, unit_id: int, features: Dict[str, bool]) -> None:
        """Directly update feature flags for one unit."""
        try:
            self._upsert_unit_features(unit_id, features)
        except Exception as e:
            print(f"[FeatureService] Error setting features for unit {unit_id}: {e}")
            raise

    async def set_building_features(self, building_id: str, features: Dict[str, bool]) -> int:
        """
        Bulk-set feature flags for ALL units in a building.
        Returns the number of units updated.
        """
        try:
            unit_ids = self._get_units_for_building(building_id)
            for uid in unit_ids:
                self._upsert_unit_features(uid, features)
            return len(unit_ids)
        except Exception as e:
            print(f"[FeatureService] Error bulk-setting building {building_id}: {e}")
            raise

    async def set_property_features(self, property_uuid: str, features: Dict[str, bool]) -> int:
        """
        Bulk-set feature flags for ALL units across all buildings in a property.
        Returns the number of units updated.
        """
        try:
            unit_ids = self._get_units_for_property(property_uuid)
            for uid in unit_ids:
                self._upsert_unit_features(uid, features)
            return len(unit_ids)
        except Exception as e:
            print(f"[FeatureService] Error bulk-setting property {property_uuid}: {e}")
            raise

    async def initialize_unit_features(self, unit_id: int) -> None:
        """Initialize default feature flags for a newly created unit."""
        defaults = {f.value: get_default_state(f) for f in Feature}
        try:
            self._upsert_unit_features(unit_id, defaults)
        except Exception as e:
            print(f"[FeatureService] Error initializing unit {unit_id}: {e}")
            raise
