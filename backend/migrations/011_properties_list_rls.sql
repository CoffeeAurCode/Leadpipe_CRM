-- Migration: RLS policies for properties_list INSERT / UPDATE / DELETE
-- The SELECT policy already exists; only write/delete policies were missing.
-- Run in Supabase SQL Editor.

CREATE POLICY "managers can insert own properties"
ON properties_list
FOR INSERT
TO authenticated
WITH CHECK (manager_id = auth.uid());

CREATE POLICY "managers can update own properties"
ON properties_list
FOR UPDATE
TO authenticated
USING (manager_id = auth.uid());

CREATE POLICY "managers can delete own properties"
ON properties_list
FOR DELETE
TO authenticated
USING (manager_id = auth.uid());
