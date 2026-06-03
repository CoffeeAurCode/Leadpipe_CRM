-- Add type column to distinguish maintenance visits from manager callbacks
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS type TEXT NOT NULL DEFAULT 'callback'
    CHECK (type IN ('callback', 'visit'));

-- Add tenant_phone so manager knows who to call back
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS tenant_phone TEXT;

-- Backfill existing rows: anything created before this migration is a 'visit'
UPDATE appointments SET type = 'visit' WHERE type = 'callback' AND created_at < NOW();
