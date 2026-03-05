-- Migration: Add lease and rent tracking fields to tenants table
-- Apply this in the Supabase SQL Editor

ALTER TABLE tenants
  ADD COLUMN IF NOT EXISTS lease_start_date DATE,
  ADD COLUMN IF NOT EXISTS lease_end_date   DATE,
  ADD COLUMN IF NOT EXISTS rent_status      TEXT CHECK (rent_status IN ('On-time', 'Upcoming', 'Overdue', 'At Risk')),
  ADD COLUMN IF NOT EXISTS payment_schedule TEXT CHECK (payment_schedule IN ('monthly', 'quarterly', 'custom')),
  ADD COLUMN IF NOT EXISTS manager_notes    TEXT;

-- Note: rent_amount and due_date are NOT stored here.
-- They are fetched dynamically from rents.monthly_rent and rents.effective_from
-- where rents.flat_uuid = tenants.flat_uuid AND rents.is_active = true.