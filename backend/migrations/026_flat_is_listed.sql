-- Add is_listed column to flats
-- Tracks whether a vacant flat has an active listing, preventing duplicate listings.
ALTER TABLE flats ADD COLUMN IF NOT EXISTS is_listed boolean DEFAULT false;

-- Backfill: any flat that already has an active listing is marked listed
UPDATE flats
SET is_listed = true
WHERE uuid IN (
    SELECT DISTINCT flat_uuid
    FROM lease_listings
    WHERE is_active = true AND flat_uuid IS NOT NULL
);
