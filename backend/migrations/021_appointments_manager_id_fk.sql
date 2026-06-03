-- ── 1. Add manager_id to appointments ────────────────────────────────────────
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

CREATE INDEX IF NOT EXISTS idx_appointments_manager
  ON appointments(manager_id);

-- ── 2. Backfill existing appointments from their linked complaint ─────────────
UPDATE appointments a
SET    manager_id = c.manager_id
FROM   complaints c
WHERE  a.complaint_uuid = c.uuid
  AND  a.manager_id IS NULL
  AND  c.manager_id IS NOT NULL;

-- Fallback: any appointment still NULL — pull from manager_profiles
UPDATE appointments
SET    manager_id = (
    SELECT user_id FROM manager_profiles
    ORDER  BY created_at
    LIMIT  1
)
WHERE  manager_id IS NULL;

-- ── 3. RLS: manager sees only their own appointments ─────────────────────────
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'appointments'
          AND policyname = 'manager sees own appointments'
    ) THEN
        CREATE POLICY "manager sees own appointments"
            ON appointments FOR ALL
            USING (manager_id = auth.uid());
    END IF;
END $$;

-- ── 4. Add FK on twilio_number_pool.assigned_manager_id ──────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE  constraint_name = 'fk_pool_assigned_manager'
          AND  table_name      = 'twilio_number_pool'
    ) THEN
        ALTER TABLE twilio_number_pool
            ADD CONSTRAINT fk_pool_assigned_manager
            FOREIGN KEY (assigned_manager_id)
            REFERENCES auth.users(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- ── 5. Add FK on manager_vapi_config.manager_id ───────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE  constraint_name = 'fk_vapi_config_manager'
          AND  table_name      = 'manager_vapi_config'
    ) THEN
        ALTER TABLE manager_vapi_config
            ADD CONSTRAINT fk_vapi_config_manager
            FOREIGN KEY (manager_id)
            REFERENCES auth.users(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ── 6. Verify ─────────────────────────────────────────────────────────────────
-- SELECT
--   (SELECT COUNT(*) FROM appointments WHERE manager_id IS NULL)      AS appts_still_null,
--   (SELECT COUNT(*) FROM appointments WHERE manager_id IS NOT NULL)  AS appts_backfilled;
