-- Migration 027: RLS policies for lease_listings and lease_leads
-- Both tables were created in 010 without RLS, causing authenticated-client
-- queries to silently return empty rows — listing cleanup in tenant assignment
-- paths was never firing.

ALTER TABLE lease_listings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "managers_own_listings"
ON lease_listings FOR ALL
TO authenticated
USING (manager_id = auth.uid())
WITH CHECK (manager_id = auth.uid());

ALTER TABLE lease_leads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "managers_own_leads"
ON lease_leads FOR ALL
TO authenticated
USING (manager_id = auth.uid())
WITH CHECK (manager_id = auth.uid());
