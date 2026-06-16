-- =============================================================
-- LEASE LISTINGS + TEST APPOINTMENTS
-- Run AFTER importing seed_properties.csv and seed_tenants.csv
-- Run in: Supabase SQL Editor (service role)
-- =============================================================
-- All UUIDs are resolved dynamically from flat_number and property name.
-- No hardcoded IDs needed.
-- =============================================================

DO $$
DECLARE
  v_pg   UUID;
  v_mgr  UUID;
  v_cmp1 UUID := gen_random_uuid();
  v_cmp2 UUID := gen_random_uuid();
BEGIN
  SELECT id, manager_id INTO v_pg, v_mgr
  FROM properties_list
  WHERE name = 'Clearview Heights TEST'
  LIMIT 1;

  IF v_pg IS NULL THEN
    RAISE EXCEPTION 'Property group not found. Import seed_properties.csv first.';
  END IF;

  -- ============================================================
  -- LEASE LISTINGS (20 total)
  -- Each INSERT...SELECT resolves flat_uuid by flat_number.
  -- custom_rules drives agent-side silent filtering:
  --   pets_allowed: "yes" | "no" | "small_only"
  --   non_smoking:  true | false
  --   max_occupants: int | absent = no cap
  -- ============================================================

  -- TST01: Studio, $900, pets ok, smoking ok, no cap
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'TST01', 'Studio Tower A Floor 1', 900.00, '2026-07-01', true, 420,
    ARRAY['Heat','Water']::text[], 'None', 'Shared on floor',
    '{"pets_allowed":"yes","non_smoking":false,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'TST01' AND b.property_id = v_pg;

  -- TST02: Studio, $1050, no pets, non-smoking, max 1
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'TST02', 'Studio Non-Smoking Solo Only', 1050.00, '2026-07-01', true, 440,
    ARRAY['Heat','Water','Internet']::text[], 'None', 'Shared on floor',
    '{"pets_allowed":"no","non_smoking":true,"max_occupants":1,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'TST02' AND b.property_id = v_pg;

  -- T1B01: 1-bed, $1200, pets ok, smoking ok, max 2
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T1B01', '1-Bed Pet Friendly Floor 1', 1200.00, '2026-07-01', true, 560,
    ARRAY['Heat','Water']::text[], 'None', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":2,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T1B01' AND b.property_id = v_pg;

  -- T1B02: 1-bed, $1350, small pets only, smoking ok, max 2, available Jul 15
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T1B02', '1-Bed Small Pets OK', 1350.00, '2026-07-15', true, 575,
    ARRAY['Heat','Water']::text[], 'None', 'In-unit',
    '{"pets_allowed":"small_only","non_smoking":false,"max_occupants":2,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T1B02' AND b.property_id = v_pg;

  -- T1B03: 1-bed, $1400, no pets, non-smoking, max 2
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T1B03', '1-Bed Non-Smoking No Pets', 1400.00, '2026-07-01', true, 580,
    ARRAY['Heat','Water','Internet']::text[], 'None', 'In-unit',
    '{"pets_allowed":"no","non_smoking":true,"max_occupants":2,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T1B03' AND b.property_id = v_pg;

  -- T1B04: 1-bed, $1100, pets ok, smoking ok, max 1 (solo only)
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T1B04', '1-Bed Solo Occupant Only', 1100.00, '2026-07-01', true, 545,
    ARRAY['Heat']::text[], 'None', 'Shared on floor',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":1,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T1B04' AND b.property_id = v_pg;

  -- T2B01: 2-bed, $1700, pets ok, smoking ok, max 4, parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B01', '2-Bed Pet Friendly Parking', 1700.00, '2026-07-01', true, 850,
    ARRAY['Heat','Water']::text[], '1 underground spot', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":4,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B01' AND b.property_id = v_pg;

  -- T2B02: 2-bed, $1800, pets ok, non-smoking, max 3, parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B02', '2-Bed Non-Smoking Parking', 1800.00, '2026-07-01', true, 880,
    ARRAY['Heat','Water']::text[], '1 underground spot', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":true,"max_occupants":3,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B02' AND b.property_id = v_pg;

  -- T2B03: 2-bed, $1950, no pets, non-smoking, max 3, available Aug 1
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B03', '2-Bed Non-Smoking No Pets Aug 1', 1950.00, '2026-08-01', true, 900,
    ARRAY['Heat','Water','Internet']::text[], 'None', 'In-unit',
    '{"pets_allowed":"no","non_smoking":true,"max_occupants":3,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B03' AND b.property_id = v_pg;

  -- T2B04: 2-bed, $1600, small pets only, smoking ok, max 4
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B04', '2-Bed Small Pets OK', 1600.00, '2026-07-01', true, 840,
    ARRAY['Heat','Water']::text[], 'None', 'Shared on floor',
    '{"pets_allowed":"small_only","non_smoking":false,"max_occupants":4,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B04' AND b.property_id = v_pg;

  -- T2B05: 2-bed, $2100, pets ok, smoking ok, max 5, 2 parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B05', '2-Bed Large Household 2 Parking', 2100.00, '2026-07-01', true, 950,
    ARRAY['Heat','Water']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":5,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B05' AND b.property_id = v_pg;

  -- T2B06: 2-bed, $2200, no pets, smoking ok, max 3, available Aug 15
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T2B06', '2-Bed No Pets Available Aug 15', 2200.00, '2026-08-15', true, 920,
    ARRAY['Heat','Water']::text[], '1 underground spot', 'In-unit',
    '{"pets_allowed":"no","non_smoking":false,"max_occupants":3,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T2B06' AND b.property_id = v_pg;

  -- T3B01: 3-bed, $2400, pets ok, smoking ok, max 6, 2 parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T3B01', '3-Bed Spacious 2 Parking', 2400.00, '2026-07-01', true, 1200,
    ARRAY['Heat','Water']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":6,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T3B01' AND b.property_id = v_pg;

  -- T3B02: 3-bed, $2600, pets ok, non-smoking, max 5, 2 parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T3B02', '3-Bed Non-Smoking High Floor', 2600.00, '2026-07-01', true, 1250,
    ARRAY['Heat','Water','Internet']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":true,"max_occupants":5,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T3B02' AND b.property_id = v_pg;

  -- T3B03: 3-bed, $2800, no pets, non-smoking, max 4, available Aug 1
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T3B03', '3-Bed Non-Smoking No Pets Aug 1', 2800.00, '2026-08-01', true, 1300,
    ARRAY['Heat','Water','Internet']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"no","non_smoking":true,"max_occupants":4,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T3B03' AND b.property_id = v_pg;

  -- T3B04: 3-bed, $2500, small pets only, smoking ok, max 5, available Jul 15
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T3B04', '3-Bed Small Pets OK Budget Option', 2500.00, '2026-07-15', true, 1180,
    ARRAY['Heat','Water']::text[], 'None', 'Shared on floor',
    '{"pets_allowed":"small_only","non_smoking":false,"max_occupants":5,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T3B04' AND b.property_id = v_pg;

  -- T3B05: 3-bed, $3000, pets ok, smoking ok, no occupancy cap, 2 parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T3B05', '3-Bed Premium No Occupancy Cap', 3000.00, '2026-07-01', true, 1350,
    ARRAY['Heat','Water']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T3B05' AND b.property_id = v_pg;

  -- T4B01: 4-bed, $3200, pets ok, smoking ok, max 8, 2 parking
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T4B01', '4-Bed Family Home 2 Parking', 3200.00, '2026-07-01', true, 1600,
    ARRAY['Heat','Water']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":false,"max_occupants":8,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T4B01' AND b.property_id = v_pg;

  -- T4B02: 4-bed, $3500, pets ok, non-smoking, max 6, available Aug 1
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T4B02', '4-Bed Non-Smoking Premium Aug 1', 3500.00, '2026-08-01', true, 1700,
    ARRAY['Heat','Water','Internet']::text[], '2 underground spots', 'In-unit',
    '{"pets_allowed":"yes","non_smoking":true,"max_occupants":6,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T4B02' AND b.property_id = v_pg;

  -- T4B03: 4-bed, $2900, no pets, non-smoking, max 6
  INSERT INTO lease_listings (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent, available_from, is_active, square_footage, included_utilities, parking, laundry, custom_rules, manager_id)
  SELECT gen_random_uuid(), v_pg, f.uuid, 'T4B03', '4-Bed No Pets Non-Smoking', 2900.00, '2026-07-01', true, 1580,
    ARRAY['Heat','Water','Internet']::text[], 'None', 'In-unit',
    '{"pets_allowed":"no","non_smoking":true,"max_occupants":6,"lease_term_months":12}'::jsonb, v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T4B03' AND b.property_id = v_pg;

  -- ============================================================
  -- TEST COMPLAINTS + APPOINTMENTS
  -- cmp1: T202 real complaint for view/reschedule/cancel tests (C05-C09)
  -- cmp2: T102 blocker complaint anchoring the 2026-07-15 14:00 slot
  --       (check_availability uses a +-1hr window; booking 14:00 or 14:30 returns unavailable)
  -- ============================================================

  INSERT INTO complaints (uuid, flat_uuid, flat_number, category, priority, description, status, source, manager_id)
  SELECT v_cmp1, f.uuid, 'T202', 'maintenance', 'medium',
    'Bathroom faucet dripping continuously needs replacement',
    'pending', 'web', v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T202' AND b.property_id = v_pg;

  INSERT INTO complaints (uuid, flat_uuid, flat_number, category, priority, description, status, source, manager_id)
  SELECT v_cmp2, f.uuid, 'T102', 'other', 'low',
    'TEST BLOCKER - Placeholder anchoring unavailability at 2026-07-15 14:00',
    'pending', 'web', v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T102' AND b.property_id = v_pg;

  INSERT INTO appointments (uuid, complaint_uuid, flat_number, flat_uuid, appointment_date, status, notes, manager_id)
  SELECT gen_random_uuid(), v_cmp1, 'T202', f.uuid,
    '2026-07-10T10:00:00', 'scheduled',
    'Manager callback - faucet issue. Test seed for C05-C09.', v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T202' AND b.property_id = v_pg;

  INSERT INTO appointments (uuid, complaint_uuid, flat_number, flat_uuid, appointment_date, status, notes, manager_id)
  SELECT gen_random_uuid(), v_cmp2, 'T102', f.uuid,
    '2026-07-15T14:00:00', 'scheduled',
    'TEST BLOCKER - Blocks availability at July 15 14:00. Delete with seed cleanup.', v_mgr
  FROM flats f JOIN buildings b ON f.building_id = b.id
  WHERE f.flat_number = 'T102' AND b.property_id = v_pg;

  RAISE NOTICE 'Seed complete. 20 listings, 2 complaints, 2 appointments inserted.';
  RAISE NOTICE 'Blocker appointment: 2026-07-15T14:00 -- use this time in scenario C08.';

END $$;


-- Verify: count seeded listings (should be 20)
SELECT COUNT(*) AS listings_seeded
FROM lease_listings ll
JOIN buildings b ON ll.flat_uuid IN (SELECT uuid FROM flats WHERE building_id = b.id)
JOIN properties_list pg ON b.property_id = pg.id
WHERE pg.name = 'Clearview Heights TEST';

-- Verify: appointments for T202 and T102
SELECT flat_number, appointment_date, status
FROM appointments
WHERE flat_number IN ('T202', 'T102')
ORDER BY appointment_date;
