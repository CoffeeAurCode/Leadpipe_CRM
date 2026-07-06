-- Migration 033: Direct manager ownership on tenants
--
-- PROBLEM
--   Commit 62d14c0f (2026-06-05) made POST /tenants insert
--   tenant_dict["manager_id"] = user["sub"], but no migration ever added the
--   column, so every standalone Add-Tenant call 500s with PGRST204
--   "Could not find the 'manager_id' column of 'tenants' in the schema cache".
--   Separately, the tenants RLS policy (migration 029) authorizes rows ONLY via
--   flat_uuid -> flats ownership, so UNASSIGNED tenants (flat_uuid IS NULL) are
--   invisible to their own manager — GET /tenants?unassigned=true can never
--   return rows.
--
-- FIX
--   Give tenants a direct manager_id FK populated on creation with the
--   manager's auth.uid() (the route code already sends it). Backfill existing
--   rows from their flat's owner. Rewrite the tenants RLS policy ADDITIVELY —
--   direct manager_id OR the existing flat chains — so nothing currently
--   visible is hidden and unassigned tenants become visible to their owner.
--
-- Run in: Supabase SQL Editor.

-- ── 1. Column + FK + index ────────────────────────────────────────────────────
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS manager_id UUID;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'fk_tenants_manager' AND table_name = 'tenants'
  ) THEN
    ALTER TABLE tenants
      ADD CONSTRAINT fk_tenants_manager
      FOREIGN KEY (manager_id) REFERENCES auth.users(id) ON DELETE CASCADE;
  END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tenants_manager_id ON tenants(manager_id);

-- ── 2. Backfill flat-assigned tenants from their flat's owner ──────────────────
UPDATE tenants t
SET manager_id = f.manager_id
FROM flats f
WHERE t.flat_uuid = f.uuid
  AND t.manager_id IS NULL
  AND f.manager_id IS NOT NULL;

-- Fallback for flats that themselves only resolve via the building chain:
UPDATE tenants t
SET manager_id = p.manager_id
FROM flats f
JOIN buildings b ON f.building_id = b.id
JOIN properties_list p ON b.property_id = p.id
WHERE t.flat_uuid = f.uuid
  AND t.manager_id IS NULL;

-- NOTE: unassigned tenants (flat_uuid IS NULL) created BEFORE this migration
-- cannot be auto-attributed — they have no link to any manager (13 such rows at
-- time of writing). Backfill manually once the owner is known:
--     UPDATE tenants SET manager_id = '<manager-auth-uid>'
--     WHERE flat_uuid IS NULL AND manager_id IS NULL AND name IN (...);
-- Find them first:
--     SELECT uuid, name, phone, created_at FROM tenants
--     WHERE flat_uuid IS NULL AND manager_id IS NULL ORDER BY created_at;

-- ── 3. Rewrite tenants RLS policy (ADDITIVE: direct owner OR flat chains) ──────
DROP POLICY IF EXISTS "manager_owns_tenants" ON tenants;
CREATE POLICY "manager_owns_tenants"
ON tenants FOR ALL
USING (
  manager_id = auth.uid()
  OR flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
)
WITH CHECK (
  manager_id = auth.uid()
  OR flat_uuid IN (SELECT uuid FROM flats WHERE manager_id = auth.uid())
  OR flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- ── 4. Verify ─────────────────────────────────────────────────────────────────
-- Flat-assigned tenants should all be attributed (expect 0):
-- SELECT COUNT(*) FROM tenants WHERE flat_uuid IS NOT NULL AND manager_id IS NULL;
--
-- Orphaned unassigned tenants awaiting manual attribution:
-- SELECT COUNT(*) FROM tenants WHERE flat_uuid IS NULL AND manager_id IS NULL;
--
-- SELECT tablename, policyname, cmd FROM pg_policies WHERE tablename = 'tenants';
