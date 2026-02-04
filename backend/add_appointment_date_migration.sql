-- Migration to add appointment_date to existing complaints table
-- Run this in your Supabase SQL Editor

-- Add appointment_date column to complaints table
ALTER TABLE complaints 
ADD COLUMN IF NOT EXISTS appointment_date TIMESTAMP WITH TIME ZONE;

-- Add a comment to document the column
COMMENT ON COLUMN complaints.appointment_date IS 'Scheduled date/time for manager to visit and fix the issue';

-- Optional: Add an index for faster queries by appointment_date
CREATE INDEX IF NOT EXISTS idx_complaints_appointment_date ON complaints(appointment_date);
