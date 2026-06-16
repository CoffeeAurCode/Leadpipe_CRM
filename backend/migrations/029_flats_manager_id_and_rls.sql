-- Migration 029: Direct manager ownership on flats (fixes standalone-unit RLS)
--
-- PROBLEM
--   flats had no direct owner column. RLS for flats / property_features / tenants /
--   rents authorized a unit ONLY via the chain:
--       flats.building_id -> buildings -> properties_list -> manager_id = auth.uid()
--   Building-less ("standalone") units — bungalows etc. — fall outside that chain, so:
--     * property_features INSERT failed with 42501 when a unit was created
--       (see docs/diagnoses/property_features_rls_init_failure_diagnosis_2026-06-16.md)
--     * the unit is invisible to its owner in GET /flats (RLS hides it)
--     * adding a tenant / rent to a standalone unit would fail the same way
--
-- FIX
--   Give flats a direct manager_id FK, populated on creation with the manager's
--   auth.uid(). Rewrite the affected RLS policies to be ADDITIVE — authorize a row
--   via the existing building chain OR the new direct flats.manager_id. Additive
--   keeps existing building-attached rows visible even before manager_id is
--   backfilled, so this migration cannot hide data a manager can currently see.
--
-- Run in: Supabase SQL Editor (AFTER un-pausing the project).

-- ── 1. Column + FK + index ────────────────────────────────────────────────────
ALTER TABLE flats ADD COLUMN IF NOT EXISTS manager_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_flats_manager' AND table_name = 'flats'
  ) THEN
    ALTER TABLE flats
      ADD CONSTRAINT fk_flats_manager
      FOREIGN KEY (manager_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_flats_manager_id ON flats(manager_id);

-- ── 2. Backfill building-attached flats from the existing chain ────────────────
UPDATE flats f
SET manager_id = p.manager_id
FROM buildings b
JOIN properties_list p ON b.property_id = p.id
WHERE f.building_id = b.id
  AND f.manager_id IS NULL;

-- NOTE: standalone flats (building_id IS NULL) created BEFORE this migration cannot
-- be auto-attributed — they have no link to any manager. Backfill them manually once
-- the owner is known, e.g.:
--     UPDATE flats SET manager_id = '<manager-auth-uid>'
--     WHERE building_id IS NULL AND manager_id IS NULL;
-- Find the orphans first:
--     SELECT id, flat_number FROM flats WHERE building_id IS NULL AND manager_id IS NULL;

-- ── 3. Rewrite RLS policies (ADDITIVE: building chain OR direct manager) ───────
-- All four policies were "FOR ALL USING(<building chain>)" with no explicit
-- WITH CHECK (so USING doubled as the INSERT check). We now add the manager_id
-- branch and an explicit matching WITH CHECK.

-- flats ------------------------------------------------------------------------
DROP POLICY IF EXISTS "manager_owns_flats" ON flats;
CREATE POLICY "manager_owns_flats"
ON flats FOR ALL
USING (
  manager_id = auth.uid()
  OR building_id IN (
    SELECT b.id FROM buildings b
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (
  manager_id = auth.uid()
  OR building_id IN (
    SELECT b.id FROM buildings b
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- property_features ------------------------------------------------------------
DROP POLICY IF EXISTS "manager_owns_property_features" ON property_features;
CREATE POLICY "manager_owns_property_features"
ON property_features FOR ALL
USING (
  unit_id IN (SELECT id FROM flats WHERE manager_id = auth.uid())
  OR unit_id IN (
    SELECT f.id FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (
  unit_id IN (SELECT id FROM flats WHERE manager_id = auth.uid())
  OR unit_id IN (
    SELECT f.id FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- tenants ----------------------------------------------------------------------
DROP POLICY IF EXISTS "manager_owns_tenants" ON tenants;
CREATE POLICY "manager_owns_tenants"
ON tenants FOR ALL
USING (
  flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (
  flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- rents ------------------------------------------------------------------------
DROP POLICY IF EXISTS "manager_owns_rents" ON rents;
CREATE POLICY "manager_owns_rents"
ON rents FOR ALL
USING (
  flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (
  flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- ── 4. Verify ─────────────────────────────────────────────────────────────────
-- SELECT COUNT(*) AS orphan_standalone_units
-- FROM flats WHERE building_id IS NULL AND manager_id IS NULL;   -- expect 0 after manual backfill
--
-- SELECT tablename, policyname, cmd FROM pg_policies
-- WHERE tablename IN ('flats','property_features','tenants','rents')
-- ORDER BY tablename, cmd;
