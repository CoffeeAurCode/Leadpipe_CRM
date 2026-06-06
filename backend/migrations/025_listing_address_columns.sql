-- Migration 025: Add address columns to lease_listings
-- Purpose: store city/street/state/country directly on the listing so agents
-- can filter by location without joining flats, and callers can hear the full
-- address without a separate lookup.

ALTER TABLE lease_listings
  ADD COLUMN IF NOT EXISTS street_address text,
  ADD COLUMN IF NOT EXISTS city           text,
  ADD COLUMN IF NOT EXISTS state          text,
  ADD COLUMN IF NOT EXISTS country        text;

-- Backfill existing listings from their linked flat
UPDATE lease_listings ll
SET
  street_address = f.street_address,
  city           = f.city,
  state          = f.state,
  country        = f.country
FROM flats f
WHERE ll.flat_uuid = f.uuid
  AND ll.street_address IS NULL;
