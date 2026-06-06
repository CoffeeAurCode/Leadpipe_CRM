-- Migration 024: Scope flat_number uniqueness to (building_id, flat_number)
-- Previously: flat_number UNIQUE globally — blocked same unit number in different buildings
-- Now: unique only within the same building

-- Step 1: Drop the global unique constraint
ALTER TABLE flats DROP CONSTRAINT IF EXISTS flats_flat_number_key;

-- Step 2: Add composite unique constraint scoped to building
ALTER TABLE flats ADD CONSTRAINT flats_building_id_flat_number_key UNIQUE (building_id, flat_number);
