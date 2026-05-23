-- Migration 017 — Unassign +12494028641 from manager 02672346-db53-4f2f-9a68-f2bf87ebf95c
-- Run in Supabase SQL editor (service role)
-- Date: 2026-05-23

UPDATE twilio_number_pool
SET
    status              = 'available',
    assigned_manager_id = NULL,
    assigned_at         = NULL
WHERE id = '89c1437e-912d-4e62-8794-f42a583e85c6';

-- Verify
SELECT id, phone_number, status, assigned_manager_id
FROM twilio_number_pool
WHERE id = '89c1437e-912d-4e62-8794-f42a583e85c6';
