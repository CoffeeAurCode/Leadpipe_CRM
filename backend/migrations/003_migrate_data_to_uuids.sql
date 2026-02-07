-- Migration 003: Migrate existing data to use UUID foreign keys
-- Run this in Supabase SQL Editor AFTER 002_add_uuid_foreign_keys.sql

-- Step 1: Migrate tenants.flat_id -> tenants.flat_uuid
-- This connects tenants to the flats they live in
UPDATE tenants t
SET flat_uuid = f.uuid
FROM flats f
WHERE t.flat_id = f.id 
  AND t.flat_uuid IS NULL
  AND t.flat_id IS NOT NULL;

-- Verify tenant migration
SELECT 
    'Tenants migrated' as status,
    COUNT(*) as total_tenants,
    COUNT(flat_uuid) as with_flat_uuid,
    COUNT(flat_id) as with_old_flat_id
FROM tenants;

-- Step 2: Migrate complaints.flat_number -> complaints.flat_uuid
-- This properly links complaints to flats
UPDATE complaints c
SET flat_uuid = f.uuid
FROM flats f
WHERE c.flat_number = f.flat_number 
  AND c.flat_uuid IS NULL
  AND c.flat_number IS NOT NULL;

-- Step 3: Migrate complaints.tenant_id -> complaints.tenant_uuid
-- This tracks which tenant created each complaint
UPDATE complaints c
SET tenant_uuid = t.uuid
FROM tenants t
WHERE c.tenant_id = t.id 
  AND c.tenant_uuid IS NULL
  AND c.tenant_id IS NOT NULL;

-- Verify complaints migration
SELECT 
    'Complaints migrated' as status,
    COUNT(*) as total_complaints,
    COUNT(flat_uuid) as with_flat_uuid,
    COUNT(tenant_uuid) as with_tenant_uuid,
    COUNT(flat_number) as with_old_flat_number,
    COUNT(tenant_id) as with_old_tenant_id
FROM complaints;

-- Step 4: Migrate appointments.flat_number -> appointments.flat_uuid  
UPDATE appointments a
SET flat_uuid = f.uuid
FROM flats f
WHERE a.flat_number = f.flat_number 
  AND a.flat_uuid IS NULL
  AND a.flat_number IS NOT NULL;

-- Step 5: Migrate appointments.complaint_id -> appointments.complaint_uuid
UPDATE appointments a
SET complaint_uuid = c.uuid
FROM complaints c
WHERE a.complaint_id = c.id 
  AND a.complaint_uuid IS NULL
  AND a.complaint_id IS NOT NULL;

-- Verify appointments migration
SELECT 
    'Appointments migrated' as status,
    COUNT(*) as total_appointments,
    COUNT(flat_uuid) as with_flat_uuid,
    COUNT(complaint_uuid) as with_complaint_uuid,
    COUNT(flat_number) as with_old_flat_number,
    COUNT(complaint_id) as with_old_complaint_id
FROM appointments;

-- Check for any rows that failed to migrate (potential data issues)
SELECT 'Complaints with invalid flat_number' as issue, COUNT(*) as count
FROM complaints 
WHERE flat_number IS NOT NULL AND flat_uuid IS NULL
UNION ALL
SELECT 'Appointments with invalid flat_number', COUNT(*)
FROM appointments 
WHERE flat_number IS NOT NULL AND flat_uuid IS NULL
UNION ALL
SELECT 'Complaints with invalid tenant_id', COUNT(*)
FROM complaints
WHERE tenant_id IS NOT NULL AND tenant_uuid IS NULL
UNION ALL
SELECT 'Appointments with invalid complaint_id', COUNT(*)
FROM appointments
WHERE complaint_id IS NOT NULL AND complaint_uuid IS NULL;

-- Final verification: Test the relationships work
SELECT 
    c.id as complaint_id,
    c.uuid as complaint_uuid,
    t.uuid as tenant_uuid,
    t.name as tenant_name,
    f.uuid as flat_uuid,
    f.flat_number as flat_number
FROM complaints c
LEFT JOIN tenants t ON c.tenant_uuid = t.uuid
LEFT JOIN flats f ON c.flat_uuid = f.uuid
LIMIT 5;
