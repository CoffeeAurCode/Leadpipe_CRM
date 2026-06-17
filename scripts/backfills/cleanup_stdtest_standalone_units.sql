-- Cleanup: remove the STDTEST standalone test units and all their dependent rows.
--
-- Targets ONLY rows from test_csvs/standalone_units_stdtest_occupancy.csv:
--   standalone units (building_id IS NULL) whose flat_number starts with 'STDTEST'.
--   Nothing else is touched.
--
-- Run in: Supabase SQL Editor. Wrapped in a transaction — all-or-nothing.

BEGIN;

-- Preview what will be removed (optional — run as a SELECT before committing):
-- SELECT id, uuid, flat_number, tenant_uuid, occupied, is_listed
-- FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL;

-- 1. Detach any leads that reference these units' listings, then drop the listings.
UPDATE lease_leads SET listing_uuid = NULL
WHERE listing_uuid IN (
    SELECT uuid FROM lease_listings
    WHERE flat_uuid IN (
        SELECT uuid FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL
    )
);

DELETE FROM lease_listings
WHERE flat_uuid IN (
    SELECT uuid FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL
);

-- 2. Rent records.
DELETE FROM rents
WHERE flat_uuid IN (
    SELECT uuid FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL
);

-- 3. Break the flats <-> tenants circular reference before deleting tenants.
UPDATE flats SET tenant_uuid = NULL, occupied = false
WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL;

DELETE FROM tenants
WHERE flat_uuid IN (
    SELECT uuid FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL
);

-- 4. Per-unit feature rows (defensive — the importer does not create these).
DELETE FROM property_features
WHERE unit_id IN (
    SELECT id FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL
);

-- 5. Finally the units themselves.
DELETE FROM flats
WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL;

COMMIT;

-- Verify (expect 0):
-- SELECT COUNT(*) FROM flats WHERE flat_number LIKE 'STDTEST%' AND building_id IS NULL;
