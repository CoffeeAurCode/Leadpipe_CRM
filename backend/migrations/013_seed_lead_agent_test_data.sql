-- Migration / Seed: Lead Agent test data for leadpipecrm@gmail.com
-- Run in the Supabase SQL Editor.
--
-- What this does:
--   1. Finds the property group(s) owned by leadpipecrm@gmail.com
--   2. Picks the first building under that group (creates one if none exists)
--   3. Deletes ALL lease_listings for this manager
--   4. Removes flats from the manager's buildings that are NOT in the 5 test units
--      (only if they have no tenant assigned — occupied flats are left untouched)
--   5. Upserts the 5 test flats with correct bedrooms / floor_number
--   6. Inserts the 5 lease listings exactly as specified in LEAD_AGENT_TEST_PLAN.md
--
-- Safe to re-run (idempotent via ON CONFLICT).

DO $$
DECLARE
  v_manager_id   UUID := '28c43c77-8c9c-496f-8d1e-39ffa9d619e3';
  v_pg_id        UUID;
  v_building_id  UUID;
  v_uuid_A101    UUID;
  v_uuid_B202    UUID;
  v_uuid_C301    UUID;
  v_uuid_D404    UUID;
  v_uuid_E501    UUID;
BEGIN

  -- ── 1. Resolve property group ─────────────────────────────────────────────
  SELECT id INTO v_pg_id
  FROM   properties_list
  WHERE  manager_id = v_manager_id
  ORDER  BY created_at
  LIMIT  1;

  IF v_pg_id IS NULL THEN
    RAISE EXCEPTION
      'No property group found for manager %. '
      'Log in as leadpipecrm@gmail.com and create a property group via the UI first.',
      v_manager_id;
  END IF;
  RAISE NOTICE 'property_group_id = %', v_pg_id;

  -- ── 2. Resolve building ───────────────────────────────────────────────────
  SELECT id INTO v_building_id
  FROM   buildings
  WHERE  property_id = v_pg_id
  ORDER  BY created_at
  LIMIT  1;

  IF v_building_id IS NULL THEN
    INSERT INTO buildings (property_id, name, address)
    VALUES (v_pg_id, 'Sunrise Heights', 'Sunrise Heights')
    RETURNING id INTO v_building_id;
    RAISE NOTICE 'Created building %', v_building_id;
  ELSE
    RAISE NOTICE 'Using building %', v_building_id;
  END IF;

  -- ── 3. Wipe all lease_listings for this manager ───────────────────────────
  -- Nullify the FK in lease_leads first so the delete doesn't violate the
  -- lease_leads_listing_uuid_fkey constraint.
  UPDATE lease_leads
  SET    listing_uuid = NULL
  WHERE  listing_uuid IN (
    SELECT uuid FROM lease_listings WHERE manager_id = v_manager_id
  );

  DELETE FROM lease_listings WHERE manager_id = v_manager_id;
  RAISE NOTICE 'Deleted existing lease_listings';

  -- ── 4. Remove extra flats in the manager's building (vacant only) ─────────
  DELETE FROM flats
  WHERE  building_id = v_building_id
    AND  flat_number NOT IN ('A101', 'B202', 'C301', 'D404', 'E501')
    AND  tenant_uuid IS NULL;
  RAISE NOTICE 'Removed non-test vacant flats from building';

  -- ── 5. Upsert the 5 test flats ────────────────────────────────────────────
  --
  -- flat_number has a UNIQUE constraint, so ON CONFLICT keeps this idempotent.
  -- We always set building_id, bedrooms, floor_number to the required values.

  INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
  VALUES ('A101', v_building_id, 1, 1, 'Sunrise Heights', false)
  ON CONFLICT (flat_number) DO UPDATE
    SET building_id  = EXCLUDED.building_id,
        floor_number = EXCLUDED.floor_number,
        bedrooms     = EXCLUDED.bedrooms,
        address      = EXCLUDED.address,
        occupied     = false
  RETURNING uuid INTO v_uuid_A101;

  IF v_uuid_A101 IS NULL THEN
    SELECT uuid INTO v_uuid_A101 FROM flats WHERE flat_number = 'A101';
  END IF;

  INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
  VALUES ('B202', v_building_id, 2, 2, 'Sunrise Heights', false)
  ON CONFLICT (flat_number) DO UPDATE
    SET building_id  = EXCLUDED.building_id,
        floor_number = EXCLUDED.floor_number,
        bedrooms     = EXCLUDED.bedrooms,
        address      = EXCLUDED.address,
        occupied     = false
  RETURNING uuid INTO v_uuid_B202;

  IF v_uuid_B202 IS NULL THEN
    SELECT uuid INTO v_uuid_B202 FROM flats WHERE flat_number = 'B202';
  END IF;

  INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
  VALUES ('C301', v_building_id, 3, 3, 'Sunrise Heights', false)
  ON CONFLICT (flat_number) DO UPDATE
    SET building_id  = EXCLUDED.building_id,
        floor_number = EXCLUDED.floor_number,
        bedrooms     = EXCLUDED.bedrooms,
        address      = EXCLUDED.address,
        occupied     = false
  RETURNING uuid INTO v_uuid_C301;

  IF v_uuid_C301 IS NULL THEN
    SELECT uuid INTO v_uuid_C301 FROM flats WHERE flat_number = 'C301';
  END IF;

  INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
  VALUES ('D404', v_building_id, 4, 2, 'Sunrise Heights', false)
  ON CONFLICT (flat_number) DO UPDATE
    SET building_id  = EXCLUDED.building_id,
        floor_number = EXCLUDED.floor_number,
        bedrooms     = EXCLUDED.bedrooms,
        address      = EXCLUDED.address,
        occupied     = false
  RETURNING uuid INTO v_uuid_D404;

  IF v_uuid_D404 IS NULL THEN
    SELECT uuid INTO v_uuid_D404 FROM flats WHERE flat_number = 'D404';
  END IF;

  INSERT INTO flats (flat_number, building_id, floor_number, bedrooms, address, occupied)
  VALUES ('E501', v_building_id, 5, 2, 'Sunrise Heights', false)
  ON CONFLICT (flat_number) DO UPDATE
    SET building_id  = EXCLUDED.building_id,
        floor_number = EXCLUDED.floor_number,
        bedrooms     = EXCLUDED.bedrooms,
        address      = EXCLUDED.address,
        occupied     = false
  RETURNING uuid INTO v_uuid_E501;

  IF v_uuid_E501 IS NULL THEN
    SELECT uuid INTO v_uuid_E501 FROM flats WHERE flat_number = 'E501';
  END IF;

  RAISE NOTICE 'Flat UUIDs — A101:% B202:% C301:% D404:% E501:%',
    v_uuid_A101, v_uuid_B202, v_uuid_C301, v_uuid_D404, v_uuid_E501;

  -- ── 6. Insert the 5 lease listings ───────────────────────────────────────
  --
  -- P1 · A101 · 1 BHK · ₹20,000 · available immediately · no rules
  INSERT INTO lease_listings
    (property_group_id, flat_uuid, flat_number, monthly_rent,
     available_from, custom_rules, is_active, manager_id)
  VALUES
    (v_pg_id, v_uuid_A101, 'A101', 20000,
     CURRENT_DATE, '{}', true, v_manager_id);

  -- P2 · B202 · 2 BHK · ₹38,000 · available 2026-06-01 · no rules
  INSERT INTO lease_listings
    (property_group_id, flat_uuid, flat_number, monthly_rent,
     available_from, custom_rules, is_active, manager_id)
  VALUES
    (v_pg_id, v_uuid_B202, 'B202', 38000,
     '2026-06-01', '{}', true, v_manager_id);

  -- P3 · C301 · 3 BHK · ₹65,000 · available immediately · no rules
  INSERT INTO lease_listings
    (property_group_id, flat_uuid, flat_number, monthly_rent,
     available_from, custom_rules, is_active, manager_id)
  VALUES
    (v_pg_id, v_uuid_C301, 'C301', 65000,
     CURRENT_DATE, '{}', true, v_manager_id);

  -- P4 · D404 · 2 BHK · ₹42,000 · available immediately · no pets
  INSERT INTO lease_listings
    (property_group_id, flat_uuid, flat_number, monthly_rent,
     available_from, custom_rules, is_active, manager_id)
  VALUES
    (v_pg_id, v_uuid_D404, 'D404', 42000,
     CURRENT_DATE, '{"pets_allowed": "no"}', true, v_manager_id);

  -- P5 · E501 · 2 BHK · ₹55,000 · available immediately · min income 3× rent
  INSERT INTO lease_listings
    (property_group_id, flat_uuid, flat_number, monthly_rent,
     available_from, custom_rules, is_active, manager_id)
  VALUES
    (v_pg_id, v_uuid_E501, 'E501', 55000,
     CURRENT_DATE,
     '{"income_required": true, "custom_question": "Can you confirm monthly income of at least ₹1,65,000 (3× the monthly rent of ₹55,000)?"}',
     true, v_manager_id);

  RAISE NOTICE 'Done — 5 lease listings created.';

END $$;

-- ── Verification query ────────────────────────────────────────────────────────
SELECT
  ll.flat_number,
  f.bedrooms,
  f.floor_number,
  ll.monthly_rent,
  COALESCE(ll.available_from::text, 'Immediately') AS available_from,
  ll.custom_rules,
  ll.uuid AS listing_uuid
FROM  lease_listings ll
JOIN  flats f ON f.uuid = ll.flat_uuid
WHERE ll.manager_id = '28c43c77-8c9c-496f-8d1e-39ffa9d619e3'
ORDER BY ll.flat_number;
