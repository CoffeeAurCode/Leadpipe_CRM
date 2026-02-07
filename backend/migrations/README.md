# Database Migrations

This directory contains SQL migration scripts for the Tenant Management MVP database.

## How to Run Migrations

### Prerequisites
- Access to Supabase SQL Editor
- Backup of current database (recommended)

### Migration Order

**IMPORTANT:** Run these scripts in order!

#### 1. Add UUID Columns
```sql
-- Run: migrations/001_add_uuid_columns.sql
```
**What it does:**
- Adds `uuid` column to flats, tenants, complaints, and appointments
- Generates UUIDs for all existing rows
- Creates indexes on UUID columns
- Adds `created_at` to tenants table

**Expected result:** All tables now have UUIDs

#### 2. Add UUID Foreign Keys
```sql
-- Run: migrations/002_add_uuid_foreign_keys.sql
```
**What it does:**
- Adds `flat_uuid` to tenants table
- Adds `tenant_uuid` and `flat_uuid` to complaints table
- Adds `complaint_uuid` and `flat_uuid` to appointments table
- Creates foreign key constraints
- Creates indexes on FK columns

**Expected result:** New UUID-based relationships established

#### 3. Migrate Existing Data
```sql
-- Run: migrations/003_migrate_data_to_uuids.sql
```
**What it does:**
- Populates `flat_uuid` in tenants from old `flat_id`
- Populates `flat_uuid` and `tenant_uuid` in complaints
- Populates `flat_uuid` and `complaint_uuid` in appointments
- Verifies all data migrated correctly
- Shows summary of migration results

**Expected result:** All existing data now uses UUID references

## Verification

After running all migrations, verify:

```sql
-- Check UUID columns exist and are populated
SELECT 
    'flats' as table_name, 
    COUNT(*) as total, 
    COUNT(uuid) as with_uuid 
FROM flats
UNION ALL
SELECT 'tenants', COUNT(*), COUNT(uuid) FROM tenants
UNION ALL
SELECT 'complaints', COUNT(*), COUNT(uuid) FROM complaints
UNION ALL
SELECT 'appointments', COUNT(*), COUNT(uuid) FROM appointments;

-- Check foreign keys work
SELECT 
    c.uuid as complaint_uuid,
    t.name as tenant_name,
    f.flat_number
FROM complaints c
LEFT JOIN tenants t ON c.tenant_uuid = t.uuid
LEFT JOIN flats f ON c.flat_uuid = f.uuid
LIMIT 5;
```

## Rollback

If you need to rollback:

```sql
-- Remove UUID foreign key columns
ALTER TABLE tenants DROP COLUMN IF EXISTS flat_uuid;
ALTER TABLE complaints DROP COLUMN IF EXISTS tenant_uuid;
ALTER TABLE complaints DROP COLUMN IF EXISTS flat_uuid;
ALTER TABLE appointments DROP COLUMN IF EXISTS complaint_uuid;
ALTER TABLE appointments DROP COLUMN IF EXISTS flat_uuid;

-- Remove UUID columns
ALTER TABLE flats DROP COLUMN IF EXISTS uuid;
ALTER TABLE tenants DROP COLUMN IF EXISTS uuid;
ALTER TABLE complaints DROP COLUMN IF EXISTS uuid;
ALTER TABLE appointments DROP COLUMN IF EXISTS uuid;
```

## Post-Migration

After successful migration:
1. Update backend Pydantic schemas to include UUID fields
2. Update API endpoints to accept/return UUIDs
3. Test all CRUD operations
4. Monitor for issues for 1 week
5. Deprecate old columns (future task)

## Notes

- **Non-breaking:** Old columns (flat_number, tenant_id, etc.) are kept for backward compatibility
- **Data safety:** All existing data is preserved
- **Performance:** Indexes created on all UUID columns for fast lookups
- **Constraints:** CASCADE delete on flat references, SET NULL on tenant/complaint references
