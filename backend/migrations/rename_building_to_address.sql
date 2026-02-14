-- SQL Migration: Rename building_name to address in flats table
-- Run this in Supabase SQL Editor or via psql

-- Step 1: Rename the column
ALTER TABLE flats 
RENAME COLUMN building_name TO address;

-- Step 2: Verify the change
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'flats' 
ORDER BY ordinal_position;
