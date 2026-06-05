-- Backfill manager_id on call_logs rows that have a linked complaint.
-- Run once in the Supabase SQL Editor after deploying the voice.py fix.
--
-- Rows without a complaint (abandoned calls) cannot be backfilled automatically
-- because manager_id was never resolved for them. They will remain hidden from
-- the VoiceStatsTab but all future calls will be correctly attributed.

UPDATE call_logs cl
SET manager_id = c.manager_id
FROM complaints c
WHERE cl.complaint_id = c.id
  AND cl.manager_id IS NULL
  AND c.manager_id IS NOT NULL;

-- Check how many rows were updated:
SELECT
    COUNT(*) FILTER (WHERE manager_id IS NOT NULL) AS with_manager,
    COUNT(*) FILTER (WHERE manager_id IS NULL)     AS still_null,
    COUNT(*)                                        AS total
FROM call_logs;
