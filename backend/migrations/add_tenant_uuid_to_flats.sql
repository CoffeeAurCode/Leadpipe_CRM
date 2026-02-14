-- Migration: Add tenant_uuid foreign key to flats table
-- This creates a reverse relationship: flats -> tenant (who occupies this flat)
-- Run this in Supabase SQL Editor

-- Step 1: Add tenant_uuid column to flats table
ALTER TABLE flats 
ADD COLUMN IF NOT EXISTS tenant_uuid UUID;

-- Step 2: Add foreign key constraint
ALTER TABLE flats 
DROP CONSTRAINT IF EXISTS fk_flats_tenant_uuid;

ALTER TABLE flats 
ADD CONSTRAINT fk_flats_tenant_uuid 
    FOREIGN KEY (tenant_uuid) 
    REFERENCES tenants(uuid) 
    ON DELETE SET NULL;

-- Step 3: Create index for better query performance
CREATE INDEX IF NOT EXISTS idx_flats_tenant_uuid 
ON flats(tenant_uuid);

-- Step 4: Populate tenant_uuid from existing tenants.flat_uuid relationship
-- This syncs the reverse relationship based on existing data
UPDATE flats f
SET tenant_uuid = t.uuid
FROM tenants t
WHERE t.flat_uuid = f.uuid
  AND f.tenant_uuid IS NULL;

-- Step 5: Verify the results
SELECT 
    f.flat_number,
    f.tenant_uuid,
    t.name as tenant_name,
    t.uuid as tenant_uuid_check
FROM flats f
LEFT JOIN tenants t ON f.tenant_uuid = t.uuid
ORDER BY f.flat_number
LIMIT 20;

-- Step 6: Count statistics
SELECT 
    'Total flats' as metric, 
    COUNT(*) as count 
FROM flats
UNION ALL
SELECT 
    'Flats with tenant', 
    COUNT(*) 
FROM flats 
WHERE tenant_uuid IS NOT NULL
UNION ALL
SELECT 
    'Vacant flats', 
    COUNT(*) 
FROM flats 
WHERE tenant_uuid IS NULL;
