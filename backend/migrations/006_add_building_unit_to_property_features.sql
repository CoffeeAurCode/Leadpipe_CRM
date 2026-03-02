-- Migration 006: Add building_id and unit_id to property_features
-- Enables hierarchical settings scoping:
--   Property-level:  building_id IS NULL AND unit_id IS NULL
--   Building-level:  building_id IS NOT NULL AND unit_id IS NULL
--   Unit-level:      building_id IS NOT NULL AND unit_id IS NOT NULL
--
-- Run this in the Supabase SQL Editor.

-- 1. Add building_id column (UUID — matches buildings.id which is uuid)
ALTER TABLE property_features
    ADD COLUMN IF NOT EXISTS building_id UUID REFERENCES buildings(id) ON DELETE CASCADE;

-- 2. Add unit_id column (INTEGER — matches flats.id which is serial/int)
ALTER TABLE property_features
    ADD COLUMN IF NOT EXISTS unit_id INTEGER REFERENCES flats(id) ON DELETE CASCADE;

-- 3. Drop any old simple unique constraint that only covers property_uuid + feature_key
--    (adjust the name below if Supabase used a different constraint name)
ALTER TABLE property_features
    DROP CONSTRAINT IF EXISTS property_features_property_uuid_feature_key_key;

-- 4. Add a new composite unique index that correctly handles NULL scope columns.
--    We use COALESCE so that (property, feature, NULL building, NULL unit) is unique.
CREATE UNIQUE INDEX IF NOT EXISTS property_features_scope_uix
    ON property_features (
        property_uuid,
        feature_key,
        COALESCE(building_id::text, ''),
        COALESCE(unit_id::text, '')
    );

-- 5. Verify the result
SELECT
    property_uuid,
    feature_key,
    enabled,
    building_id,
    unit_id
FROM property_features
LIMIT 20;

