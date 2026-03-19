-- Migration: add 'attended' to appointments status check constraint
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New Query)

ALTER TABLE appointments
    DROP CONSTRAINT IF EXISTS appointments_status_check;

ALTER TABLE appointments
    ADD CONSTRAINT appointments_status_check
    CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled', 'attended'));
