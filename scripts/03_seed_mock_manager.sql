-- ============================================================
-- MIGRATION 03: Seed existing data to a mock manager
-- WHERE TO RUN: Supabase Dashboard > SQL Editor
-- ORDER: Run AFTER 01 and 02
--
-- BEFORE RUNNING:
--   1. Go to Supabase Dashboard > Authentication > Users > Add User
--   2. Create: mock-manager@yourdomain.com with a strong password
--   3. Copy the UUID from the user list
--   4. Replace every '<MOCK_MANAGER_UUID>' below with that UUID
-- ============================================================

-- Assign all existing property groups to mock manager
UPDATE properties_list
SET manager_id = '<MOCK_MANAGER_UUID>'
WHERE manager_id IS NULL;

-- Assign all existing complaints to mock manager
UPDATE complaints
SET assigned_manager_id = '<MOCK_MANAGER_UUID>'
WHERE assigned_manager_id IS NULL;

-- Create the mock manager profile
INSERT INTO manager_profiles (user_id, name, phone)
VALUES ('<MOCK_MANAGER_UUID>', 'Test Manager', '+910000000000')
ON CONFLICT (user_id) DO NOTHING;

-- Create a trial subscription for the mock manager (for testing)
INSERT INTO subscriptions (manager_id, stripe_customer_id, plan, status, trial_ends_at)
VALUES (
  '<MOCK_MANAGER_UUID>',
  'cus_mock_test',
  'trial',
  'trialing',
  now() + interval '14 days'
)
ON CONFLICT DO NOTHING;
