-- ============================================================
-- MIGRATION 01: Schema changes for SaaS multi-tenancy
-- WHERE TO RUN: Supabase Dashboard > SQL Editor
-- ORDER: Run this FIRST, before 02_rls_policies.sql
-- ============================================================

-- 1. Manager Profiles table
CREATE TABLE IF NOT EXISTS manager_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Subscriptions table (Stripe billing)
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT NOT NULL,
  stripe_subscription_id TEXT UNIQUE,
  plan TEXT NOT NULL DEFAULT 'trial',
  status TEXT NOT NULL DEFAULT 'trialing',
  -- status values: trialing, active, past_due, canceled, incomplete
  trial_ends_at TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- One active subscription per manager
CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_active_manager
ON subscriptions(manager_id) WHERE status IN ('trialing', 'active');

-- 3. Stripe events log (idempotency — prevents duplicate webhook processing)
CREATE TABLE IF NOT EXISTS stripe_events (
  event_id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT now()
);

-- 4. Add manager_id to properties_list
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

-- 5. Add columns to complaints
ALTER TABLE complaints
  ADD COLUMN IF NOT EXISTS property_group_id UUID REFERENCES properties_list(id);

ALTER TABLE complaints
  ADD COLUMN IF NOT EXISTS assigned_manager_id UUID REFERENCES auth.users(id);

-- 6. Add property_group_id to call_logs (if missing)
ALTER TABLE call_logs
  ADD COLUMN IF NOT EXISTS property_group_id UUID REFERENCES properties_list(id);
