-- Verification & Fix: Ensure tenants are properly linked to flats
-- Run this to check and fix the tenant-flat connections

-- STEP 1: Check current state
SELECT 
    'Tenants Status' as check_type,
    COUNT(*) as total_tenants,
    COUNT(flat_uuid) as tenants_with_flat_uuid,
    COUNT(flat_id) as tenants_with_old_flat_id,
    COUNT(unit_id) as tenants_with_unit_id
FROM tenants;

-- STEP 2: Show tenants that need migration
SELECT 
    id,
    name,
    phone,
    flat_id,
    unit_id,
    flat_uuid,
    'Missing flat_uuid' as issue
FROM tenants
WHERE flat_uuid IS NULL
  AND (flat_id IS NOT NULL OR unit_id IS NOT NULL);

-- STEP 3: Fix tenants.flat_uuid from flat_id
UPDATE tenants t
SET flat_uuid = f.uuid
FROM flats f
WHERE t.flat_id = f.id 
  AND t.flat_uuid IS NULL
  AND t.flat_id IS NOT NULL;

-- STEP 4: Show flats with their tenants (verify relationship works)
SELECT 
    f.flat_number,
    f.uuid as flat_uuid,
    t.name as tenant_name,
    t.phone as tenant_phone,
    t.uuid as tenant_uuid
FROM flats f
LEFT JOIN tenants t ON f.uuid = t.flat_uuid
ORDER BY f.flat_number;

-- STEP 5: Count tenants per flat
SELECT 
    f.flat_number,
    COUNT(t.uuid) as tenant_count
FROM flats f
LEFT JOIN tenants t ON f.uuid = t.flat_uuid
GROUP BY f.flat_number, f.uuid
ORDER BY f.flat_number;

-- STEP 6: Final verification
SELECT 
    'After Fix' as status,
    COUNT(*) as total_tenants,
    COUNT(flat_uuid) as with_flat_uuid,
    COUNT(CASE WHEN flat_id IS NOT NULL AND flat_uuid IS NULL THEN 1 END) as missing_flat_uuid
FROM tenants;
