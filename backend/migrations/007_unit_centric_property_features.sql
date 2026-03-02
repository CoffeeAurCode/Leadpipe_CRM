-- Migration 007: Refactor property_features to unit-centric flat table
--
-- The new design:
--   - One row PER UNIT PER FEATURE
--   - unit_id is the primary foreign key (references flats.id which is an INTEGER)
--   - No building_id or property_uuid — units are the only level
--   - "Bulk" saves are handled in the backend by iterating over child units
--
-- Run this in the Supabase SQL Editor.
-- 
-- ┌─────────────────────────────────────────────────────────────────────────┐
-- │ IMPORTANT: This migration DROPS the old property_features table and     │
-- │ creates a new one. Any existing data will be lost.                      │
-- │ The backend will re-initialize defaults for all units on first access.  │
-- └─────────────────────────────────────────────────────────────────────────┘

-- Step 1: Drop the old table (cascade drops any dependent indexes/constraints)
DROP TABLE IF EXISTS property_features CASCADE;

-- Step 2: Create the new unit-centric table
CREATE TABLE property_features (
    id          SERIAL PRIMARY KEY,
    unit_id     INTEGER NOT NULL REFERENCES flats(id) ON DELETE CASCADE,
    feature_key TEXT    NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT false,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Each unit can only have one row per feature
    CONSTRAINT property_features_unit_feature_uix UNIQUE (unit_id, feature_key)
);

-- Step 3: Index for fast lookup by unit
CREATE INDEX IF NOT EXISTS property_features_unit_idx ON property_features (unit_id);

-- Step 4: Auto-update the updated_at timestamp on every change
CREATE OR REPLACE FUNCTION update_property_features_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_property_features_updated_at ON property_features;
CREATE TRIGGER trg_property_features_updated_at
    BEFORE UPDATE ON property_features
    FOR EACH ROW
    EXECUTE FUNCTION update_property_features_updated_at();

-- Step 5: Verify
SELECT 'property_features table recreated successfully' AS status;
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'property_features'
ORDER BY ordinal_position;
