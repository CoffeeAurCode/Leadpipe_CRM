-- Migration 004: Fix all UUID relationships
-- Run this in Supabase SQL Editor AFTER 003_migrate_data_to_uuids.sql

-- ============================================================================
-- STEP 1: Ensure tenants are properly linked to flats
-- ============================================================================
-- The relationship is: tenant.flat_uuid -> flats.uuid
-- This tells us which flat each tenant lives in

UPDATE tenants t
SET flat_uuid = f.uuid
FROM flats f
WHERE t.flat_id = f.id 
  AND t.flat_uuid IS NULL
  AND t.flat_id IS NOT NULL;

-- Verify tenant-flat links
SELECT 
    '1. Tenants → Flats' as relationship,
    COUNT(*) as total_tenants,
    COUNT(flat_uuid) as with_flat_link,
    COUNT(CASE WHEN flat_id IS NOT NULL AND flat_uuid IS NULL THEN 1 END) as missing_link
FROM tenants;

-- ============================================================================
-- STEP 2: Auto-link complaints to tenants based on flat occupancy
-- ============================================================================
-- The logic: If a complaint is for flat X, and tenant Y lives in flat X,
-- then tenant Y created the complaint

UPDATE complaints c
SET tenant_uuid = t.uuid
FROM tenants t
WHERE c.flat_uuid = t.flat_uuid
  AND c.tenant_uuid IS NULL
  AND t.flat_uuid IS NOT NULL;

-- Verify complaint-tenant links
SELECT 
    '2. Complaints → Tenants' as relationship,
    COUNT(*) as total_complaints,
    COUNT(tenant_uuid) as with_tenant_link,
    COUNT(CASE WHEN flat_uuid IS NOT NULL AND tenant_uuid IS NULL THEN 1 END) as flat_but_no_tenant
FROM complaints;

-- ============================================================================
-- STEP 3: Show the complete relationship chain
-- ============================================================================
SELECT 
    f.flat_number,
    f.uuid as flat_uuid,
    t.name as tenant_name,
    t.uuid as tenant_uuid,
    COUNT(c.id) as complaint_count
FROM flats f
LEFT JOIN tenants t ON f.uuid = t.flat_uuid
LEFT JOIN complaints c ON c.tenant_uuid = t.uuid
GROUP BY f.flat_number, f.uuid, t.name, t.uuid
ORDER BY f.flat_number
LIMIT 10;

-- ============================================================================
-- STEP 4: Identify issues
-- ============================================================================
-- Complaints where flat has no tenant assigned
SELECT 
    'Complaints for unoccupied flats' as issue_type,
    c.id as complaint_id,
    f.flat_number,
    c.description as complaint_description
FROM complaints c
LEFT JOIN flats f ON c.flat_uuid = f.uuid
WHERE c.flat_uuid IS NOT NULL 
  AND c.tenant_uuid IS NULL;

-- Tenants without flats
SELECT 
    'Tenants not assigned to any flat' as issue_type,
    t.id as tenant_id,
    t.name as tenant_name,
    t.phone as tenant_phone
FROM tenants t
WHERE t.flat_uuid IS NULL;

-- ============================================================================
-- STEP 5: Final Summary
-- ============================================================================
SELECT 
    'Flats' as table_name, 
    COUNT(*) as total_rows
FROM flats
UNION ALL
SELECT 'Tenants', COUNT(*) FROM tenants
UNION ALL
SELECT 'Tenants linked to flats', COUNT(*) FROM tenants WHERE flat_uuid IS NOT NULL
UNION ALL
SELECT 'Complaints', COUNT(*) FROM complaints
UNION ALL
SELECT 'Complaints linked to tenants', COUNT(*) FROM complaints WHERE tenant_uuid IS NOT NULL
UNION ALL
SELECT 'Complaints linked to flats', COUNT(*) FROM complaints WHERE flat_uuid IS NOT NULL;
