-- Migration: Voice Agents — Lease listings and leads tables
-- Run in Supabase SQL editor (or via psql)

-- ── 1. properties_list — Lease Agent Columns ─────────────────────────────────

ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS vapi_lease_assistant_id    TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number_id       TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number          TEXT,
  ADD COLUMN IF NOT EXISTS vapi_provisioning_status   TEXT DEFAULT 'not_applicable'
    CHECK (vapi_provisioning_status IN (
      'not_applicable', 'pending', 'active', 'failed'
    ));

-- All rows at migration time are existing groups using shared lease number
UPDATE properties_list
  SET vapi_provisioning_status = 'not_applicable'
  WHERE vapi_provisioning_status IS NULL;

-- ── 2. lease_listings table ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lease_listings (
  id                SERIAL PRIMARY KEY,
  uuid              UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id UUID NOT NULL REFERENCES properties_list(id),
  flat_uuid         UUID NOT NULL REFERENCES flats(uuid),
  flat_number       TEXT NOT NULL,
  title             TEXT,
  monthly_rent      NUMERIC NOT NULL,
  description       TEXT,
  available_from    DATE,
  photo_urls        TEXT[]  DEFAULT '{}',
  is_active         BOOLEAN DEFAULT true,
  custom_rules      JSONB   DEFAULT '{}',
  manager_id        UUID,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ll_active ON lease_listings(is_active) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_ll_flat   ON lease_listings(flat_uuid);
CREATE INDEX IF NOT EXISTS idx_ll_pg     ON lease_listings(property_group_id);

-- ── 3. lease_leads table ─────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS lease_leads (
  id                    SERIAL PRIMARY KEY,
  uuid                  UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id     UUID REFERENCES properties_list(id),
  listing_uuid          UUID REFERENCES lease_listings(uuid),
  interested_listing_ids UUID[] DEFAULT '{}',
  caller_name           TEXT NOT NULL,
  phone                 TEXT NOT NULL,
  email                 TEXT,
  bedrooms              INTEGER,
  budget_max            NUMERIC,
  move_in_timeline      TEXT,
  occupants             INTEGER,
  floor_preference      TEXT,
  qualification_status  TEXT NOT NULL DEFAULT 'unmatched'
    CHECK (qualification_status IN (
      'qualified','not_qualified','unmatched','contacted','toured','converted','lost'
    )),
  disqualifying_reason  TEXT,
  qualifying_answers    JSONB    DEFAULT '{}',
  notes                 TEXT,
  source                TEXT NOT NULL DEFAULT 'voice',
  call_id               TEXT,
  call_duration_seconds INTEGER,
  manager_notes         TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leads_status  ON lease_leads(qualification_status);
CREATE INDEX IF NOT EXISTS idx_leads_listing ON lease_leads(listing_uuid);
CREATE INDEX IF NOT EXISTS idx_leads_pg      ON lease_leads(property_group_id);
CREATE INDEX IF NOT EXISTS idx_leads_created ON lease_leads(created_at DESC);
