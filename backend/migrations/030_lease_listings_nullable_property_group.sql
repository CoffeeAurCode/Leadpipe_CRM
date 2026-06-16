-- Migration 030: Allow standalone (building-less) units to be listed for lease
--
-- PROBLEM
--   lease_listings.property_group_id was declared NOT NULL (migration 010). It is
--   resolved from the unit's building chain:
--       flats.building_id -> buildings.property_id (= properties_list.id)
--   Standalone units (flats.building_id IS NULL) have no building and therefore no
--   property group. POST /leasing/listings crashed two ways for them:
--     1. The building lookup ran .eq("id", NULL) -> PostgREST sent "None" ->
--        22P02 invalid input syntax for type uuid: "None"
--     2. Even past that, inserting NULL property_group_id violated the NOT NULL.
--
-- FIX
--   Make property_group_id nullable. Standalone listings are still owned (and found)
--   via lease_listings.manager_id, which /leasing/search and /leasing/find-listing
--   already filter on. lease_leads.property_group_id is already nullable, so leads
--   generated from a standalone listing store NULL there without issue.
--
-- Run in: Supabase SQL Editor.

ALTER TABLE lease_listings ALTER COLUMN property_group_id DROP NOT NULL;

-- Verify:
-- SELECT is_nullable FROM information_schema.columns
-- WHERE table_name = 'lease_listings' AND column_name = 'property_group_id';   -- expect YES
