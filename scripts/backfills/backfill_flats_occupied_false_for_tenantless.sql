-- Backfill: mark tenant-less units as vacant (occupied = false)
--
-- WHY
--   The CSV importer (POST /import/properties) did not set `occupied` on the flats
--   INSERT, so imported vacant units kept the DB default — which is NOT false. That
--   made them fail POST /leasing/listings with 400 "Only vacant units can be listed.
--   This unit is currently occupied." even though they have no tenant.
--   create_flat (UI) always set occupied=false, which is why manually-made units list
--   fine. The importer is now fixed; this repairs rows created before that fix.
--
-- SAFETY
--   A unit with no tenant cannot be occupied, so forcing occupied=false where
--   tenant_uuid IS NULL is always correct. Units WITH a tenant are left untouched.
--
-- Run in: Supabase SQL Editor.

-- 1. Inspect first — see which rows will change:
-- SELECT id, flat_number, building_id, tenant_uuid, occupied, is_listed
-- FROM flats
-- WHERE tenant_uuid IS NULL AND occupied IS DISTINCT FROM false
-- ORDER BY flat_number;

-- 2. Apply:
UPDATE flats
SET occupied = false
WHERE tenant_uuid IS NULL
  AND occupied IS DISTINCT FROM false;

-- 3. Verify (expect 0):
-- SELECT COUNT(*) FROM flats WHERE tenant_uuid IS NULL AND occupied IS DISTINCT FROM false;
