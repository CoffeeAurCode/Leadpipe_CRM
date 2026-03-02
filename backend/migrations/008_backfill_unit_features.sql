-- Migration 008: Backfill existing flats with default features
--
-- This script runs through every flat in the `flats` table
-- and inserts the default feature configurations into the new
-- `property_features` unit-centric table.
--
-- Run this in the Supabase SQL Editor AFTER running 007.

-- Insert defaults for every flat that does NOT already have features.
-- We use a CROSS JOIN with the defined default features.

INSERT INTO property_features (unit_id, feature_key, enabled)
SELECT 
    f.id as unit_id,
    defaults.feature_key,
    defaults.enabled
FROM 
    flats f
CROSS JOIN (
    VALUES 
        ('rent_management', true),
        ('rent_due_date', false),
        ('flat_details', true),
        ('voice_calls', false),
        ('sms_reminders', false),
        ('email_reminders', false),
        ('tenant_details', true),
        ('tenant_documents', false)
) AS defaults(feature_key, enabled)
ON CONFLICT (unit_id, feature_key) DO NOTHING;

-- Verify the result
SELECT 
    'Backfill complete' AS status,
    COUNT(*) as total_feature_rows_created 
FROM property_features;
