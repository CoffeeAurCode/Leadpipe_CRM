-- Migration 015: Per-manager VAPI provisioning
-- Run in Supabase SQL editor (service role).
-- Full Phase 1 of PLAN_PER_USER_VAPI_PROVISIONING.md


-- ============================================================
-- Step 1.1 — Create manager_vapi_config table
-- ============================================================

CREATE TABLE IF NOT EXISTS manager_vapi_config (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id               UUID NOT NULL UNIQUE,
    vapi_lease_assistant_id  TEXT,
    vapi_phone_number_id     TEXT,
    vapi_phone_number        TEXT,
    vapi_provisioning_status TEXT NOT NULL DEFAULT 'pending',
    pool_row_id              UUID,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE manager_vapi_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "manager reads own vapi config" ON manager_vapi_config;

CREATE POLICY "manager reads own vapi config"
ON manager_vapi_config FOR SELECT
USING (manager_id = auth.uid());


-- ============================================================
-- Step 1.2 — Modify twilio_number_pool
--   Add assigned_manager_id; rename old assigned_property_group_id
-- ============================================================

ALTER TABLE twilio_number_pool
    ADD COLUMN IF NOT EXISTS assigned_manager_id UUID;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'twilio_number_pool'
          AND column_name = 'assigned_property_group_id'
    ) THEN
        ALTER TABLE twilio_number_pool
            RENAME COLUMN assigned_property_group_id TO _legacy_assigned_property_group_id;
    END IF;
END $$;


-- ============================================================
-- Step 1.3 — Insert pending config row for leadpipecrm@gmail.com
--   No active per-group data exists to migrate.
-- ============================================================

INSERT INTO manager_vapi_config (manager_id, vapi_provisioning_status)
VALUES ('28c43c77-8c9c-496f-8d1e-39ffa9d619e3', 'pending')
ON CONFLICT (manager_id) DO NOTHING;


-- ============================================================
-- Step 1.4 — Null out per-group VAPI columns on properties_list
-- ============================================================

UPDATE properties_list
SET
    vapi_lease_assistant_id  = NULL,
    vapi_phone_number_id     = NULL,
    vapi_phone_number        = NULL,
    vapi_provisioning_status = 'not_applicable'
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';


-- ============================================================
-- Step 1.5 — Confirm pool row for +14313415768 is available
-- ============================================================

UPDATE twilio_number_pool
SET
    assigned_manager_id = NULL,
    status = 'available'
WHERE phone_number = '+14313415768';


-- ============================================================
-- Verify
-- ============================================================

-- Expect: manager_id=28c43c77-..., status=pending, phone=null
SELECT manager_id, vapi_provisioning_status, vapi_phone_number
FROM manager_vapi_config
WHERE manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';

-- Expect: status=available, assigned_manager_id=null
SELECT id, phone_number, vapi_phone_number_id, status, assigned_manager_id, assigned_at
FROM twilio_number_pool
WHERE phone_number = '+14313415768';
