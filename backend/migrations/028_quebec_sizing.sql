-- Add room breakdown and Quebec size to flats
ALTER TABLE flats
  ADD COLUMN IF NOT EXISTS living_rooms int NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS kitchen int NOT NULL DEFAULT 1,
  ADD COLUMN IF NOT EXISTS quebec_size text;

-- Backfill existing rows that have bedroom/bathroom counts
UPDATE flats SET
  quebec_size = CONCAT(
    (bedrooms + living_rooms + kitchen + GREATEST(0, bathrooms - 1))::text,
    '½'
  )
WHERE bedrooms IS NOT NULL AND bathrooms IS NOT NULL;

-- Mirror room fields to lease_listings for direct querying by the lease agent
ALTER TABLE lease_listings
  ADD COLUMN IF NOT EXISTS bedrooms int,
  ADD COLUMN IF NOT EXISTS bathrooms int,
  ADD COLUMN IF NOT EXISTS living_rooms int,
  ADD COLUMN IF NOT EXISTS kitchen int,
  ADD COLUMN IF NOT EXISTS quebec_size text;

-- Backfill lease_listings from flats
UPDATE lease_listings ll
SET
  bedrooms = f.bedrooms,
  bathrooms = f.bathrooms,
  living_rooms = f.living_rooms,
  kitchen = f.kitchen,
  quebec_size = f.quebec_size
FROM flats f
WHERE ll.flat_uuid = f.uuid;
