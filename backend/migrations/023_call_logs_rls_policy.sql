-- Migration 023: RLS SELECT policy for call_logs
--
-- Root cause: call_logs has RLS enabled but no SELECT policy. Supabase default-deny
-- means authenticated queries via get_authenticated_db return 0 rows even though
-- the webhook inserts rows correctly via get_service_db (service role bypasses RLS).
-- Result: /call_logs/stats always returns {"total": 0, ...} for authenticated managers.
--
-- Fix: add a SELECT policy so managers can read their own call log rows.
-- No other policies are needed — inserts are done by the service role (webhook),
-- and there is no manager-facing write path for call_logs.
--
-- Run in: Supabase SQL Editor

-- ── 1. Ensure RLS is enabled ─────────────────────────────────────────────────
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- ── 2. Allow managers to read their own call logs ─────────────────────────────
CREATE POLICY "managers_read_own_call_logs"
ON call_logs
FOR SELECT
TO authenticated
USING (manager_id = auth.uid());

-- ── 3. Verify ─────────────────────────────────────────────────────────────────
-- Run this block to confirm the policy was created before closing the editor.
--
-- SELECT policyname, cmd, qual
-- FROM pg_policies
-- WHERE tablename = 'call_logs';
--
-- Expected: one row with policyname = 'managers_read_own_call_logs', cmd = 'SELECT'
