-- Migration 014: Twilio Number Pool + Notifications table
-- Run in Supabase SQL Editor

-- ── 1. notifications table (may not exist yet in production) ────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    manager_id  UUID NOT NULL REFERENCES auth.users(id),
    title       TEXT NOT NULL,
    body        TEXT NOT NULL,
    type        TEXT NOT NULL,
    entity_id   UUID,
    is_read     BOOLEAN NOT NULL DEFAULT false,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notifications_manager
    ON notifications(manager_id, created_at DESC);

ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'notifications' AND policyname = 'manager sees own notifications'
    ) THEN
        CREATE POLICY "manager sees own notifications"
            ON notifications FOR ALL
            USING (manager_id = auth.uid());
    END IF;
END $$;

-- ── 2. twilio_number_pool table ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS twilio_number_pool (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number                TEXT NOT NULL UNIQUE,
    vapi_phone_number_id        TEXT NOT NULL UNIQUE,
    status                      TEXT NOT NULL DEFAULT 'available'
                                    CHECK (status IN ('available', 'assigned')),
    assigned_property_group_id  UUID REFERENCES properties_list(id) ON DELETE SET NULL,
    assigned_at                 TIMESTAMPTZ,
    notes                       TEXT,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE twilio_number_pool ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'twilio_number_pool' AND policyname = 'service only'
    ) THEN
        CREATE POLICY "service only"
            ON twilio_number_pool FOR ALL
            TO service_role
            USING (true);
    END IF;
END $$;
