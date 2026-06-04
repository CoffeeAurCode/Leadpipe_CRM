-- Migration 022: Structured address fields for properties, buildings, and flats
-- Run in Supabase SQL Editor. Old 'address' column is kept untouched for backward compatibility.

-- properties_list
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';

-- buildings
ALTER TABLE buildings
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS address_line   TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';

-- flats
ALTER TABLE flats
  ADD COLUMN IF NOT EXISTS street_address TEXT,
  ADD COLUMN IF NOT EXISTS address_line   TEXT,
  ADD COLUMN IF NOT EXISTS city           TEXT,
  ADD COLUMN IF NOT EXISTS state          TEXT,
  ADD COLUMN IF NOT EXISTS country        TEXT DEFAULT 'Canada';
