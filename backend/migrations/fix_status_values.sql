-- ============================================================================
-- Migration: Fix Status Value Inconsistency
-- ============================================================================
-- Purpose: Normalize all status values to canonical format and add constraint
-- Date: 2026-02-13
-- 
-- Canonical Status Values:
--   - 'pending'
--   - 'in-progress'
--   - 'resolved'
--
-- This migration will:
--   1. Convert all 'in_progress' and 'in - progress' to 'in-progress'
--   2. Add CHECK constraint to enforce only canonical values
--   3. Prevent future inconsistent values from being stored
-- ============================================================================

-- Step 1: Show current status values (for verification)
SELECT 
    status, 
    COUNT(*) as count 
FROM complaints 
GROUP BY status 
ORDER BY status;

-- Step 2: Normalize existing data
-- Convert any underscore variants to hyphenated format
UPDATE complaints 
SET status = 'in-progress' 
WHERE status IN ('in_progress', 'in - progress', 'in progress');

-- Step 3: Verify normalization worked
SELECT 
    status, 
    COUNT(*) as count 
FROM complaints 
GROUP BY status 
ORDER BY status;

-- Step 4: Add CHECK constraint to enforce canonical values
ALTER TABLE complaints 
ADD CONSTRAINT complaints_status_check 
CHECK (status IN ('pending', 'in-progress', 'resolved'));

-- Step 5: Verify constraint was added
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conname = 'complaints_status_check';

-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check 1: Ensure only canonical values exist
SELECT DISTINCT status FROM complaints;
-- Expected: Only 'pending', 'in-progress', 'resolved'

-- Check 2: Try to insert invalid status (should FAIL)
-- Uncomment to test:
-- INSERT INTO complaints (category, priority, description, status, source)
-- VALUES ('maintenance', 'medium', 'Test complaint', 'in_progress', 'test');
-- Expected Error: new row for relation "complaints" violates check constraint

-- ============================================================================
-- Rollback Script (if needed)
-- ============================================================================
-- ALTER TABLE complaints DROP CONSTRAINT IF EXISTS complaints_status_check;
