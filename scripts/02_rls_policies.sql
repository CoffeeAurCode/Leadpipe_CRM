-- ============================================================
-- MIGRATION 02: Row Level Security policies on ALL tables
-- WHERE TO RUN: Supabase Dashboard > SQL Editor
-- ORDER: Run AFTER 01_schema_migration.sql
-- ============================================================

-- ── manager_profiles ────────────────────────────────────────
ALTER TABLE manager_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "managers_see_own_profile"
ON manager_profiles FOR ALL
USING (user_id = auth.uid());

-- Allow insert during signup (user creates their own profile)
CREATE POLICY "managers_insert_own_profile"
ON manager_profiles FOR INSERT
WITH CHECK (user_id = auth.uid());

-- ── subscriptions ───────────────────────────────────────────
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- Managers can only READ their own subscription (writes via service role only)
CREATE POLICY "managers_see_own_subscription"
ON subscriptions FOR SELECT
USING (manager_id = auth.uid());

-- ── properties_list ─────────────────────────────────────────
ALTER TABLE properties_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_properties"
ON properties_list FOR ALL
USING (manager_id = auth.uid())
WITH CHECK (manager_id = auth.uid());

-- ── buildings ───────────────────────────────────────────────
ALTER TABLE buildings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_buildings"
ON buildings FOR ALL
USING (
  property_id IN (SELECT id FROM properties_list WHERE manager_id = auth.uid())
);

-- ── flats ───────────────────────────────────────────────────
ALTER TABLE flats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_flats"
ON flats FOR ALL
USING (
  building_id IN (
    SELECT b.id FROM buildings b
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- ── tenants ─────────────────────────────────────────────────
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_tenants"
ON tenants FOR ALL
USING (
  flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- ── complaints ──────────────────────────────────────────────
ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_complaints"
ON complaints FOR ALL
USING (assigned_manager_id = auth.uid());

-- ── appointments ────────────────────────────────────────────
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_appointments"
ON appointments FOR ALL
USING (
  complaint_uuid IN (
    SELECT uuid FROM complaints WHERE assigned_manager_id = auth.uid()
  )
);

-- ── rents ───────────────────────────────────────────────────
ALTER TABLE rents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_rents"
ON rents FOR ALL
USING (
  flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- ── call_logs ───────────────────────────────────────────────
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_call_logs"
ON call_logs FOR ALL
USING (
  property_group_id IN (SELECT id FROM properties_list WHERE manager_id = auth.uid())
);

-- ── property_features ───────────────────────────────────────
ALTER TABLE property_features ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_property_features"
ON property_features FOR ALL
USING (
  unit_id IN (
    SELECT f.id FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);
