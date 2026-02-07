-- Migration 002: Add UUID-based foreign key columns
-- Run this in Supabase SQL Editor AFTER 001_add_uuid_columns.sql

-- Add flat_uuid to tenants (which flat does this tenant live in?)
ALTER TABLE tenants ADD COLUMN IF NOT EXISTS flat_uuid UUID;

-- Add foreign key constraint
ALTER TABLE tenants DROP CONSTRAINT IF EXISTS fk_tenants_flat_uuid;
ALTER TABLE tenants ADD CONSTRAINT fk_tenants_flat_uuid 
    FOREIGN KEY (flat_uuid) REFERENCES flats(uuid) ON DELETE SET NULL;

-- Add tenant_uuid and flat_uuid to complaints
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS tenant_uuid UUID;
ALTER TABLE complaints ADD COLUMN IF NOT EXISTS flat_uuid UUID;

-- Add foreign key constraints for complaints
ALTER TABLE complaints DROP CONSTRAINT IF EXISTS fk_complaints_tenant_uuid;
ALTER TABLE complaints ADD CONSTRAINT fk_complaints_tenant_uuid 
    FOREIGN KEY (tenant_uuid) REFERENCES tenants(uuid) ON DELETE SET NULL;

ALTER TABLE complaints DROP CONSTRAINT IF EXISTS fk_complaints_flat_uuid;
ALTER TABLE complaints ADD CONSTRAINT fk_complaints_flat_uuid 
    FOREIGN KEY (flat_uuid) REFERENCES flats(uuid) ON DELETE CASCADE;

-- Add complaint_uuid and flat_uuid to appointments
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS complaint_uuid UUID;
ALTER TABLE appointments ADD COLUMN IF NOT EXISTS flat_uuid UUID;

-- Add foreign key constraints for appointments
ALTER TABLE appointments DROP CONSTRAINT IF EXISTS fk_appointments_complaint_uuid;
ALTER TABLE appointments ADD CONSTRAINT fk_appointments_complaint_uuid 
    FOREIGN KEY (complaint_uuid) REFERENCES complaints(uuid) ON DELETE SET NULL;

ALTER TABLE appointments DROP CONSTRAINT IF EXISTS fk_appointments_flat_uuid;
ALTER TABLE appointments ADD CONSTRAINT fk_appointments_flat_uuid 
    FOREIGN KEY (flat_uuid) REFERENCES flats(uuid) ON DELETE CASCADE;

-- Create indexes on foreign key columns for better query performance
CREATE INDEX IF NOT EXISTS idx_tenants_flat_uuid ON tenants(flat_uuid);
CREATE INDEX IF NOT EXISTS idx_complaints_tenant_uuid ON complaints(tenant_uuid);
CREATE INDEX IF NOT EXISTS idx_complaints_flat_uuid ON complaints(flat_uuid);
CREATE INDEX IF NOT EXISTS idx_appointments_complaint_uuid ON appointments(complaint_uuid);
CREATE INDEX IF NOT EXISTS idx_appointments_flat_uuid ON appointments(flat_uuid);

-- Verify constraints were created
SELECT 
    tc.table_name, 
    tc.constraint_name, 
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
  AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
  AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type = 'FOREIGN KEY'
  AND tc.table_name IN ('tenants', 'complaints', 'appointments')
  AND kcu.column_name LIKE '%uuid'
ORDER BY tc.table_name, tc.constraint_name;
