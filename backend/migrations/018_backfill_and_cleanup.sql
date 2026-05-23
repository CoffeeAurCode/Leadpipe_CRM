-- Migration 018 — Backfill lease_listings.manager_id + pool cleanup
-- Run in Supabase SQL editor (service role)
-- Date: 2026-05-23

-- ============================================================
-- STEP 1: Diagnose — see which listings are missing manager_id
-- ============================================================
SELECT uuid, flat_number, title, manager_id, property_group_id
FROM lease_listings
WHERE manager_id IS NULL;

-- ============================================================
-- STEP 2: Backfill manager_id from property group owner
-- Fixes Sweep 3-E regression: listings created before manager_id
-- was being written are excluded by the direct .eq("manager_id") filter
-- ============================================================
UPDATE lease_listings ll
SET manager_id = pl.manager_id
FROM properties_list pl
WHERE ll.property_group_id = pl.id
  AND ll.manager_id IS NULL;

-- Verify — should return 0 rows after backfill
SELECT uuid, flat_number, title, manager_id, property_group_id
FROM lease_listings
WHERE manager_id IS NULL;

-- ============================================================
-- STEP 3: Unassign +12494028641 from orphaned manager
-- (race condition artifact from Sweep 2 provisioning incident)
-- ============================================================
UPDATE twilio_number_pool
SET
    status              = 'available',
    assigned_manager_id = NULL,
    assigned_at         = NULL
WHERE id = '89c1437e-912d-4e62-8794-f42a583e85c6';

-- Also check if the orphaned manager has a stale manager_vapi_config row
-- If it has one, delete it so the number can be cleanly claimed
SELECT id, manager_id, vapi_provisioning_status, vapi_phone_number
FROM manager_vapi_config
WHERE manager_id = '02672346-db53-4f2f-9a68-f2bf87ebf95c';

-- If the above returns a row with status != 'active' (or any row at all),
-- delete it:
-- DELETE FROM manager_vapi_config
-- WHERE manager_id = '02672346-db53-4f2f-9a68-f2bf87ebf95c';

-- ============================================================
-- STEP 4: Final pool state check
-- ============================================================
SELECT phone_number, status, assigned_manager_id, assigned_at
FROM twilio_number_pool
ORDER BY phone_number;
