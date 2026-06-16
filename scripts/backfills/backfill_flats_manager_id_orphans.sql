-- Backfill: attribute orphaned standalone flats to their owning manager
--
-- Run this AFTER migration 029_flats_manager_id_and_rls.sql.
--
-- Migration 029 auto-backfills manager_id for building-attached flats (via the
-- building -> property -> manager chain). Standalone flats (building_id IS NULL)
-- created BEFORE the migration have no link to any manager and cannot be
-- auto-attributed — fix them here.
--
-- Run in: Supabase SQL Editor.

-- ── STEP 1: Find the orphans ──────────────────────────────────────────────────
-- Lists standalone units that still have no owner. Note their ids/flat_numbers.
SELECT id, flat_number, created_at
FROM flats
WHERE building_id IS NULL
  AND manager_id IS NULL
ORDER BY created_at;

-- IMPORTANT: flats never recorded a "created_by", so the creator of a pre-029
-- standalone unit cannot be read back directly. Recover the owner one of 3 ways:

-- ── STEP 2a-i: Single-manager shortcut (most common) ──────────────────────────
-- If the project has exactly one manager, every orphan belongs to them. This is
-- a no-op unless manager_profiles has exactly one row, so it is safe to run.
-- UPDATE flats
-- SET manager_id = (SELECT user_id FROM manager_profiles LIMIT 1)
-- WHERE building_id IS NULL AND manager_id IS NULL
--   AND (SELECT COUNT(*) FROM manager_profiles) = 1;

-- ── STEP 2a-ii: Infer the owner from related rows (multi-manager) ──────────────
-- Standalone units have no building chain, but rows that reference them may carry
-- a manager link. Inspect the hints, then assign per unit.
-- SELECT
--   f.id, f.flat_number, f.uuid, f.occupied, f.created_at,
--   c.assigned_manager_id AS hint_from_complaint,
--   ll.manager_id         AS hint_from_lease_lead
-- FROM flats f
-- LEFT JOIN LATERAL (
--   SELECT assigned_manager_id FROM complaints
--   WHERE flat_uuid = f.uuid AND assigned_manager_id IS NOT NULL LIMIT 1
-- ) c ON true
-- LEFT JOIN LATERAL (
--   SELECT le.manager_id FROM lease_listings li
--   JOIN lease_leads le ON le.listing_uuid = li.uuid
--   WHERE li.flat_uuid = f.uuid AND le.manager_id IS NOT NULL LIMIT 1
-- ) ll ON true
-- WHERE f.building_id IS NULL AND f.manager_id IS NULL
-- ORDER BY f.created_at;

-- ── STEP 2a-iii: Assign explicitly ────────────────────────────────────────────
-- Replace <MANAGER_AUTH_UID> with the owner's auth.users id (same UUID stored in
-- properties_list.manager_id / manager_profiles.user_id). Look one up with:
--     SELECT id, email FROM auth.users ORDER BY created_at;
--     SELECT user_id, name, phone FROM manager_profiles ORDER BY name;
--
-- Per unit (from the hints above):
-- UPDATE flats SET manager_id = '<MANAGER_AUTH_UID>' WHERE id = <flat_id>;
--
-- ...or all remaining orphans to one manager:
-- UPDATE flats SET manager_id = '<MANAGER_AUTH_UID>'
-- WHERE building_id IS NULL AND manager_id IS NULL;

-- ── STEP 2b: OR delete throwaway test orphans ─────────────────────────────────
-- Use this instead if the orphans are disposable test data. Children are removed
-- first to respect FKs (tenants/rents/property_features cascade off flats, but be
-- explicit to be safe).
-- DELETE FROM property_features WHERE unit_id IN (
--   SELECT id FROM flats WHERE building_id IS NULL AND manager_id IS NULL
-- );
-- DELETE FROM rents WHERE flat_uuid IN (
--   SELECT uuid FROM flats WHERE building_id IS NULL AND manager_id IS NULL
-- );
-- DELETE FROM tenants WHERE flat_uuid IN (
--   SELECT uuid FROM flats WHERE building_id IS NULL AND manager_id IS NULL
-- );
-- DELETE FROM flats WHERE building_id IS NULL AND manager_id IS NULL;

-- ── STEP 3: Verify zero orphans remain ────────────────────────────────────────
SELECT COUNT(*) AS remaining_orphans
FROM flats
WHERE building_id IS NULL AND manager_id IS NULL;
-- Expect: 0

-- ── STEP 4 (OPTIONAL): Lock it in so future flats can never be orphaned ────────
-- Only run once STEP 3 returns 0. After this, any INSERT into flats without a
-- manager_id will be rejected by the database.
-- ALTER TABLE flats ALTER COLUMN manager_id SET NOT NULL;
