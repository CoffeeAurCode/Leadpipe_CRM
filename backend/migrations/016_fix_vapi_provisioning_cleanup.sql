-- Migration 016 — Fix VAPI provisioning: cleanup + unique constraint
-- Run in Supabase SQL editor (service role)
-- Date: 2026-05-23

-- Step 1: Reset the 3 pool rows claimed by the same manager back to available
UPDATE twilio_number_pool
SET
    status              = 'available',
    assigned_manager_id = NULL,
    assigned_at         = NULL
WHERE assigned_manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';

-- Step 2: Reset manager_vapi_config — clear VAPI fields, keep row for retry
UPDATE manager_vapi_config
SET
    vapi_provisioning_status = 'pending',
    vapi_lease_assistant_id  = NULL,
    vapi_phone_number_id     = NULL,
    vapi_phone_number        = NULL,
    pool_row_id              = NULL
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';

-- Step 3: Add unique constraint — one pool number per manager, forever
-- Partial index allows multiple NULLs (unassigned rows) but only one row per manager_id.
CREATE UNIQUE INDEX IF NOT EXISTS twilio_number_pool_one_per_manager
ON twilio_number_pool (assigned_manager_id)
WHERE assigned_manager_id IS NOT NULL;

-- Verify pool state after running
SELECT phone_number, status, assigned_manager_id
FROM twilio_number_pool
ORDER BY created_at;

-- Verify manager_vapi_config state after running
SELECT manager_id, vapi_provisioning_status, vapi_phone_number, vapi_lease_assistant_id
FROM manager_vapi_config
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';
