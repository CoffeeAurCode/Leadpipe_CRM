-- Migration 001: Add UUID columns to all tables
-- Run this in Supabase SQL Editor

-- Add UUID extension if not exists
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Add UUID column to flats
ALTER TABLE flats ADD COLUMN IF NOT EXISTS uuid UUID UNIQUE DEFAULT gen_random_uuid();

-- Add UUID column to tenants  
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS uuid UUID UNIQUE DEFAULT gen_random_uuid();

-- Add UUID column to complaints
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS uuid UUID UNIQUE DEFAULT gen_random_uuid();

-- Add UUID column to appointments
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS uuid UUID UNIQUE DEFAULT gen_random_uuid();

-- Generate UUIDs for existing rows (fill in NULL values if any)
UPDATE flats SET uuid = gen_random_uuid() WHERE uuid IS NULL;
UPDATE tenants SET uuid = gen_random_uuid() WHERE uuid IS NULL;
UPDATE complaints SET uuid = gen_random_uuid() WHERE uuid IS NULL;
UPDATE appointments SET uuid = gen_random_uuid() WHERE uuid IS NULL;

-- Make UUIDs NOT NULL after populating
ALTER TABLE flats ALTER COLUMN uuid SET NOT NULL;
ALTER TABLE tenants ALTER COLUMN uuid SET NOT NULL;
ALTER TABLE complaints ALTER COLUMN uuid SET NOT NULL;
ALTER TABLE appointments ALTER COLUMN uuid SET NOT NULL;

-- Create indexes for faster UUID lookups
CREATE INDEX IF NOT EXISTS idx_flats_uuid ON flats(uuid);
CREATE INDEX IF NOT EXISTS idx_tenants_uuid ON tenants(uuid);
CREATE INDEX IF NOT EXISTS idx_complaints_uuid ON complaints(uuid);
CREATE INDEX IF NOT EXISTS idx_appointments_uuid ON appointments(uuid);

-- Add created_at to tenants if it doesn't exist
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Verify migration
SELECT 'Flats with UUIDs:' as table_name, COUNT(*) as count FROM flats WHERE uuid IS NOT NULL
UNION ALL
SELECT 'Tenants with UUIDs:', COUNT(*) FROM tenants WHERE uuid IS NOT NULL
UNION ALL
SELECT 'Complaints with UUIDs:', COUNT(*) FROM complaints WHERE uuid IS NOT NULL
UNION ALL
SELECT 'Appointments with UUIDs:', COUNT(*) FROM appointments WHERE uuid IS NOT NULL;
