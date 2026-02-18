-- Migration: Create rents table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS rents (
    id          BIGSERIAL PRIMARY KEY,
    flat_uuid   UUID NOT NULL REFERENCES flats(uuid) ON DELETE CASCADE,
    monthly_rent NUMERIC(10, 2) NOT NULL,
    effective_from DATE NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast active rent lookups
CREATE INDEX IF NOT EXISTS idx_rents_flat_active
    ON rents(flat_uuid, is_active)
    WHERE is_active = TRUE;

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_rents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER rents_updated_at
    BEFORE UPDATE ON rents
    FOR EACH ROW EXECUTE FUNCTION update_rents_updated_at();
