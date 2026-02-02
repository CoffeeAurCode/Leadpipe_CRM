-- Tenant Management MVP Database Schema
-- Run this in Supabase SQL Editor

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    role VARCHAR(20) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    CONSTRAINT users_role_check CHECK (role IN ('admin', 'manager'))
);

-- Create units table
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    flat_number VARCHAR(20) NOT NULL,
    building_name VARCHAR(100) NOT NULL
);

-- Create tenants table
CREATE TABLE IF NOT EXISTS tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    unit_id INTEGER REFERENCES units(id) ON DELETE SET NULL
);

-- Create complaints table
CREATE TABLE IF NOT EXISTS complaints (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id) ON DELETE CASCADE,
    flat_number VARCHAR(20),
    category VARCHAR(50) NOT NULL,
    priority VARCHAR(20) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'AI_AGENT',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create call_logs table
CREATE TABLE IF NOT EXISTS call_logs (
    id SERIAL PRIMARY KEY,
    call_id VARCHAR(100) UNIQUE,
    phone_number VARCHAR(20),
    transcript TEXT,
    raw_event_type VARCHAR(50),
    complaint_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    complaint_id INTEGER REFERENCES complaints(id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_complaints_status ON complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON complaints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_call_logs_call_id ON call_logs(call_id);
CREATE INDEX IF NOT EXISTS idx_tenants_phone ON tenants(phone);

-- Insert sample data (optional)
INSERT INTO complaints (tenant_id, flat_number, category, priority, description, status, source)
VALUES 
    (NULL, '101', 'plumbing', 'high', 'Water leaking from ceiling', 'pending', 'voice'),
    (NULL, '202', 'electrical', 'medium', 'Light fixture not working', 'in-progress', 'web')
ON CONFLICT DO NOTHING;

-- Verify tables created
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public'
ORDER BY table_name;
