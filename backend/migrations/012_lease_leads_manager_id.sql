-- Migration 012: Add manager_id to lease_leads
--
-- Root cause: lease_leads was created (migration 010) without a manager_id column.
-- Every other table (flats, tenants, complaints, call_logs, etc.) has manager_id
-- directly on the row so GET endpoints can filter with a single WHERE clause.
-- lease_leads was the only exception — forcing a fragile two-hop lookup through
-- properties_list.manager_id that silently returned [] whenever that column was NULL.
--
-- Fix: add manager_id, backfill from auth.users (single-tenant MVP has one manager),
-- and add an index to match query performance of other tables.
--
-- Run in: Supabase SQL Editor

-- ── 1. Add manager_id column ─────────────────────────────────────────────────

ALTER TABLE lease_leads
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

CREATE INDEX IF NOT EXISTS idx_leads_manager ON lease_leads(manager_id);

-- ── 2. Backfill manager_id for all existing rows ──────────────────────────────
-- Uses manager_profiles as the authoritative source (the account that actually
-- owns data). LIMIT 1 without ORDER BY was the original bug — it picked whichever
-- row postgres returned first, which was a mock account, not the real manager.

UPDATE lease_leads
SET manager_id = (SELECT user_id FROM manager_profiles LIMIT 1)
WHERE manager_id IS NULL;

-- ── 3. Fix properties_list.manager_id (data integrity) ───────────────────────
-- The property group row was created manually in Supabase, bypassing the API,
-- so manager_id was never set. This causes the primary resolution path in
-- the webhook to return NULL for Path 2/3. Fix it once here.

UPDATE properties_list
SET manager_id = (SELECT user_id FROM manager_profiles LIMIT 1)
WHERE manager_id IS NULL;

-- ── 4. Verify ─────────────────────────────────────────────────────────────────
-- Run this block to confirm the migration worked before closing the editor.
--
-- SELECT
--   (SELECT COUNT(*) FROM lease_leads WHERE manager_id IS NULL)     AS leads_still_null,
--   (SELECT COUNT(*) FROM lease_leads WHERE manager_id IS NOT NULL)  AS leads_backfilled,
--   (SELECT COUNT(*) FROM properties_list WHERE manager_id IS NULL)  AS groups_still_null;
--
-- Expected: leads_still_null = 0, leads_backfilled = total row count, groups_still_null = 0
