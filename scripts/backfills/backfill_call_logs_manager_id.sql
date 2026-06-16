-- Step 1: Add manager_id column to call_logs
ALTER TABLE call_logs
ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

-- Step 2: Backfill from linked complaints
UPDATE call_logs cl
SET manager_id = c.manager_id
FROM complaints c
WHERE cl.complaint_id = c.id
  AND cl.manager_id IS NULL
  AND c.manager_id IS NOT NULL;

-- Step 3: Check results
SELECT
    COUNT(*) FILTER (WHERE manager_id IS NOT NULL) AS with_manager,
    COUNT(*) FILTER (WHERE manager_id IS NULL)     AS still_null,
    COUNT(*)                                        AS total
FROM call_logs;
