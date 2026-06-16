-- Lease Agent Improvement Plan — DB Migration
-- Date: 2026-06-03
--
-- No schema changes required.
-- All 7 fixes are confined to vapi_agent_config.py (system prompt + tool descriptions).
-- The lease_leads table already supports all fields used by submit_lease_lead.
--
-- Verify the table exists and has the expected columns:

SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'lease_leads'
ORDER BY ordinal_position;
