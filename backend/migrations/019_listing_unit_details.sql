-- 019_listing_unit_details.sql
-- Add unit-detail columns to lease_listings (square footage, utilities, parking, laundry).
-- non_smoking lives inside the existing custom_rules JSONB column — no schema change needed.

ALTER TABLE lease_listings
  ADD COLUMN IF NOT EXISTS square_footage  integer,
  ADD COLUMN IF NOT EXISTS included_utilities text[]  DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS parking         text,
  ADD COLUMN IF NOT EXISTS laundry         text;

-- Add has_pets field to lease_leads qualifying_answers is JSONB, no schema change needed.
-- The column already stores arbitrary key/value pairs from the voice agent.
