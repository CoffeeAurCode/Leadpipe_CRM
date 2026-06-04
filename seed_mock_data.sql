-- =============================================================
-- VOICE AGENT TEST DATA â€” Tenant Management MVP
-- Date: 2026-06-04
-- =============================================================
-- BEFORE RUNNING:
--   1. Replace YOUR_MANAGER_UUID_HERE with your manager UUID.
--      Find it:  SELECT id FROM auth.users WHERE email = 'your@email.com';
--      Or:       Supabase â†’ Authentication â†’ Users â†’ your account
--
--   2. Replace +15145550011 (Alex Martin / T101) with your ACTUAL phone
--      number â€” this is the tenant your outbound/inbound complaint tests
--      will call from. Must be in E.164 format e.g. +15145559999
--
-- Run this entire block in the Supabase SQL Editor.
-- =============================================================

DO $$
DECLARE
  -- â”€â”€ REPLACE THESE TWO VALUES â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  v_mgr         UUID   := 'YOUR_MANAGER_UUID_HERE';
  v_tester_phone TEXT  := '+15145550011';   -- â† your real phone number
  -- â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

  v_pg          UUID := gen_random_uuid();  -- Clearview Heights [TEST]
  v_bldg_lease  UUID := gen_random_uuid();  -- Maple Tower (lease listings)
  v_bldg_compl  UUID := gen_random_uuid();  -- Oak Residences (complaint tests)

  -- Lease listing flat UUIDs
  v_f_st01  UUID := gen_random_uuid();
  v_f_st02  UUID := gen_random_uuid();
  v_f_1b01  UUID := gen_random_uuid();
  v_f_1b02  UUID := gen_random_uuid();
  v_f_1b03  UUID := gen_random_uuid();
  v_f_1b04  UUID := gen_random_uuid();
  v_f_2b01  UUID := gen_random_uuid();
  v_f_2b02  UUID := gen_random_uuid();
  v_f_2b03  UUID := gen_random_uuid();
  v_f_2b04  UUID := gen_random_uuid();
  v_f_2b05  UUID := gen_random_uuid();
  v_f_2b06  UUID := gen_random_uuid();
  v_f_3b01  UUID := gen_random_uuid();
  v_f_3b02  UUID := gen_random_uuid();
  v_f_3b03  UUID := gen_random_uuid();
  v_f_3b04  UUID := gen_random_uuid();
  v_f_3b05  UUID := gen_random_uuid();
  v_f_4b01  UUID := gen_random_uuid();
  v_f_4b02  UUID := gen_random_uuid();
  v_f_4b03  UUID := gen_random_uuid();

  -- Complaint test flat UUIDs
  v_fc_t101  UUID := gen_random_uuid();
  v_fc_t102  UUID := gen_random_uuid();
  v_fc_t103  UUID := gen_random_uuid();  -- stays vacant
  v_fc_t104  UUID := gen_random_uuid();
  v_fc_t201  UUID := gen_random_uuid();
  v_fc_t202  UUID := gen_random_uuid();

  -- Complaint test tenant UUIDs
  v_tn_t101  UUID := gen_random_uuid();
  v_tn_t102  UUID := gen_random_uuid();
  v_tn_t104  UUID := gen_random_uuid();
  v_tn_t201  UUID := gen_random_uuid();
  v_tn_t202  UUID := gen_random_uuid();

  -- Complaint and appointment UUIDs
  v_cmp1  UUID := gen_random_uuid();
  v_cmp2  UUID := gen_random_uuid();

  v_pt_id UUID;

BEGIN
  -- â”€â”€ Resolve property type â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  SELECT id INTO v_pt_id FROM property_types WHERE name = 'Residential' LIMIT 1;
  IF v_pt_id IS NULL THEN
    SELECT id INTO v_pt_id FROM property_types LIMIT 1;
  END IF;
  IF v_pt_id IS NULL THEN
    RAISE EXCEPTION 'No rows found in property_types â€” seed the property types table first.';
  END IF;

  -- â”€â”€ 1. Property Group â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  INSERT INTO properties_list (id, name, description, address, manager_id)
  VALUES (
    v_pg,
    'Clearview Heights [TEST]',
    'Mock data for pre-launch agent testing â€” safe to delete after',
    '555 Parc-Extension Ave, Montreal, QC H2R 1H5',
    v_mgr
  );

  -- â”€â”€ 2. Buildings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  INSERT INTO buildings (id, name, description, address, property_id, manager_id, property_type_id)
  VALUES
    (v_bldg_lease,
     'Maple Tower',
     '12-floor high-rise â€” lease test units',
     '555 Parc-Extension Ave, Tower A, Montreal QC',
     v_pg, v_mgr, v_pt_id),
    (v_bldg_compl,
     'Oak Residences',
     '4-floor low-rise â€” complaint test units',
     '555 Parc-Extension Ave, Tower B, Montreal QC',
     v_pg, v_mgr, v_pt_id);

  -- â”€â”€ 3. Lease Listing Flats (all vacant) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- bedrooms + floor_number drive the search_listings join.
  -- bathrooms follows sensible defaults.
  INSERT INTO flats (uuid, flat_number, bedrooms, bathrooms, floor_number,
                     occupied, building_id, property_type_id, manager_id)
  VALUES
    -- Studios
    (v_f_st01, 'TST01', 0, 1, 1,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_st02, 'TST02', 0, 1, 2,  false, v_bldg_lease, v_pt_id, v_mgr),
    -- 1-Bedrooms
    (v_f_1b01, 'T1B01', 1, 1, 1,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_1b02, 'T1B02', 1, 1, 2,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_1b03, 'T1B03', 1, 1, 3,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_1b04, 'T1B04', 1, 1, 1,  false, v_bldg_lease, v_pt_id, v_mgr),
    -- 2-Bedrooms
    (v_f_2b01, 'T2B01', 2, 1, 2,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_2b02, 'T2B02', 2, 1, 3,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_2b03, 'T2B03', 2, 2, 4,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_2b04, 'T2B04', 2, 1, 1,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_2b05, 'T2B05', 2, 2, 5,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_2b06, 'T2B06', 2, 2, 6,  false, v_bldg_lease, v_pt_id, v_mgr),
    -- 3-Bedrooms
    (v_f_3b01, 'T3B01', 3, 2, 2,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_3b02, 'T3B02', 3, 2, 3,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_3b03, 'T3B03', 3, 2, 4,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_3b04, 'T3B04', 3, 2, 2,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_3b05, 'T3B05', 3, 2, 5,  false, v_bldg_lease, v_pt_id, v_mgr),
    -- 4-Bedrooms
    (v_f_4b01, 'T4B01', 4, 3, 3,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_4b02, 'T4B02', 4, 3, 4,  false, v_bldg_lease, v_pt_id, v_mgr),
    (v_f_4b03, 'T4B03', 4, 3, 2,  false, v_bldg_lease, v_pt_id, v_mgr);

  -- â”€â”€ 4. Lease Listings â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- custom_rules JSONB drives agent-side silent filtering:
  --   pets_allowed:  "yes" | "no" | "small_only"
  --   non_smoking:   true | false
  --   max_occupants: int | (absent = no cap)
  -- included_utilities, parking, laundry are direct listing columns.
  -- bedrooms + floor_number come from the joined flats row.
  INSERT INTO lease_listings
    (uuid, property_group_id, flat_uuid, flat_number, title, monthly_rent,
     available_from, is_active, square_footage,
     included_utilities, parking, laundry, custom_rules, manager_id)
  VALUES
    -- â”€â”€ Studios â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    -- ST01: pets ok, smoking ok, no occupancy cap â†’ cheapest entry-level
    (gen_random_uuid(), v_pg, v_f_st01, 'TST01',
     'Studio â€” Tower A, Floor 1', 900.00, '2026-07-01', true, 420,
     ARRAY['Heat', 'Water']::text[], 'None', 'Shared on floor',
     '{"pets_allowed": "yes", "non_smoking": false, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- ST02: no pets, non-smoking, max 1 â†’ solo-only strict unit
    (gen_random_uuid(), v_pg, v_f_st02, 'TST02',
     'Studio â€” Non-Smoking, Solo Only', 1050.00, '2026-07-01', true, 440,
     ARRAY['Heat', 'Water', 'Internet']::text[], 'None', 'Shared on floor',
     '{"pets_allowed": "no", "non_smoking": true, "max_occupants": 1, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- â”€â”€ 1-Bedrooms â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    -- 1B01: pets ok, smoking ok, max 2 â†’ standard 1-bed
    (gen_random_uuid(), v_pg, v_f_1b01, 'T1B01',
     '1-Bed â€” Pet Friendly, Floor 1', 1200.00, '2026-07-01', true, 560,
     ARRAY['Heat', 'Water']::text[], 'None', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 2, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 1B02: small pets only, smoking ok, max 2 â†’ tests small_only vs large pet
    (gen_random_uuid(), v_pg, v_f_1b02, 'T1B02',
     '1-Bed â€” Small Pets OK, Available Jul 15', 1350.00, '2026-07-15', true, 575,
     ARRAY['Heat', 'Water']::text[], 'None', 'In-unit',
     '{"pets_allowed": "small_only", "non_smoking": false, "max_occupants": 2, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 1B03: no pets, non-smoking, max 2 â†’ strict unit for disqualification test L13
    (gen_random_uuid(), v_pg, v_f_1b03, 'T1B03',
     '1-Bed â€” Non-Smoking, No Pets', 1400.00, '2026-07-01', true, 580,
     ARRAY['Heat', 'Water', 'Internet']::text[], 'None', 'In-unit',
     '{"pets_allowed": "no", "non_smoking": true, "max_occupants": 2, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 1B04: pets ok, smoking ok, max 1 â†’ solo only (occupancy filter test L19)
    (gen_random_uuid(), v_pg, v_f_1b04, 'T1B04',
     '1-Bed â€” Solo Occupant Only', 1100.00, '2026-07-01', true, 545,
     ARRAY['Heat']::text[], 'None', 'Shared on floor',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 1, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- â”€â”€ 2-Bedrooms â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    -- 2B01: pets ok, smoking ok, max 4, parking â†’ key test unit (multiple scenarios)
    (gen_random_uuid(), v_pg, v_f_2b01, 'T2B01',
     '2-Bed â€” Pet Friendly, Parking Included', 1700.00, '2026-07-01', true, 850,
     ARRAY['Heat', 'Water']::text[], '1 underground spot', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 4, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 2B02: pets ok, NON-SMOKING, max 3 â†’ smok filter test; should be excluded for smokers
    (gen_random_uuid(), v_pg, v_f_2b02, 'T2B02',
     '2-Bed â€” Non-Smoking, Parking Included', 1800.00, '2026-07-01', true, 880,
     ARRAY['Heat', 'Water']::text[], '1 underground spot', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": true, "max_occupants": 3, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 2B03: NO PETS, non-smoking, max 3, Aug 1 â†’ pets+smoke filter; future availability
    (gen_random_uuid(), v_pg, v_f_2b03, 'T2B03',
     '2-Bed â€” Non-Smoking, No Pets, Available Aug 1', 1950.00, '2026-08-01', true, 900,
     ARRAY['Heat', 'Water', 'Internet']::text[], 'None', 'In-unit',
     '{"pets_allowed": "no", "non_smoking": true, "max_occupants": 3, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 2B04: SMALL PETS ONLY, smoking ok, max 4 â†’ key unit for L03/L04 comparison
    (gen_random_uuid(), v_pg, v_f_2b04, 'T2B04',
     '2-Bed â€” Small Pets OK', 1600.00, '2026-07-01', true, 840,
     ARRAY['Heat', 'Water']::text[], 'None', 'Shared on floor',
     '{"pets_allowed": "small_only", "non_smoking": false, "max_occupants": 4, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 2B05: pets ok, smoking ok, max 5 â†’ high-occupancy 2-bed (family test L06)
    (gen_random_uuid(), v_pg, v_f_2b05, 'T2B05',
     '2-Bed â€” Large Household OK, 2 Parking', 2100.00, '2026-07-01', true, 950,
     ARRAY['Heat', 'Water']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 5, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 2B06: NO PETS, smoking ok, max 3, Aug 15 â†’ future availability + no pets
    (gen_random_uuid(), v_pg, v_f_2b06, 'T2B06',
     '2-Bed â€” No Pets, Available Aug 15', 2200.00, '2026-08-15', true, 920,
     ARRAY['Heat', 'Water']::text[], '1 underground spot', 'In-unit',
     '{"pets_allowed": "no", "non_smoking": false, "max_occupants": 3, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- â”€â”€ 3-Bedrooms â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    -- 3B01: pets ok, smoking ok, max 6 â†’ passes occupancy test L06 (family of 6)
    (gen_random_uuid(), v_pg, v_f_3b01, 'T3B01',
     '3-Bed â€” Spacious, 2 Parking Spots', 2400.00, '2026-07-01', true, 1200,
     ARRAY['Heat', 'Water']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 6, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 3B02: pets ok, NON-SMOKING, max 5 â†’ excluded for smokers (test L05)
    (gen_random_uuid(), v_pg, v_f_3b02, 'T3B02',
     '3-Bed â€” Non-Smoking, High Floor', 2600.00, '2026-07-01', true, 1250,
     ARRAY['Heat', 'Water', 'Internet']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": true, "max_occupants": 5, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 3B03: NO PETS, NON-SMOKING, max 4, Aug 1 â†’ double exclusion for smoker+dog owner
    (gen_random_uuid(), v_pg, v_f_3b03, 'T3B03',
     '3-Bed â€” Non-Smoking, No Pets, Available Aug 1', 2800.00, '2026-08-01', true, 1300,
     ARRAY['Heat', 'Water', 'Internet']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "no", "non_smoking": true, "max_occupants": 4, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 3B04: SMALL PETS ONLY, smoking ok, max 5 â†’ passes for small cat, excluded for big dog
    (gen_random_uuid(), v_pg, v_f_3b04, 'T3B04',
     '3-Bed â€” Small Pets OK, Budget Option', 2500.00, '2026-07-15', true, 1180,
     ARRAY['Heat', 'Water']::text[], 'None', 'Shared on floor',
     '{"pets_allowed": "small_only", "non_smoking": false, "max_occupants": 5, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 3B05: pets ok, smoking ok, NO occupancy cap â†’ only 3-bed that passes family-of-6 + max_occ
    (gen_random_uuid(), v_pg, v_f_3b05, 'T3B05',
     '3-Bed â€” Premium, No Occupancy Cap', 3000.00, '2026-07-01', true, 1350,
     ARRAY['Heat', 'Water']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- â”€â”€ 4-Bedrooms â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    -- 4B01: pets ok, smoking ok, max 8, $3200 â†’ over-budget for L09
    (gen_random_uuid(), v_pg, v_f_4b01, 'T4B01',
     '4-Bed â€” Family Home, 2 Parking Spots', 3200.00, '2026-07-01', true, 1600,
     ARRAY['Heat', 'Water']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": false, "max_occupants": 8, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 4B02: pets ok, NON-SMOKING, max 6, $3500, Aug 1 â†’ over-budget for L09; non-smoking
    (gen_random_uuid(), v_pg, v_f_4b02, 'T4B02',
     '4-Bed â€” Non-Smoking Premium, Available Aug 1', 3500.00, '2026-08-01', true, 1700,
     ARRAY['Heat', 'Water', 'Internet']::text[], '2 underground spots', 'In-unit',
     '{"pets_allowed": "yes", "non_smoking": true, "max_occupants": 6, "lease_term_months": 12}'::jsonb,
     v_mgr),

    -- 4B03: NO PETS, NON-SMOKING, max 6, $2900 â†’ only affordable 4-bed but excluded for dog owner
    (gen_random_uuid(), v_pg, v_f_4b03, 'T4B03',
     '4-Bed â€” No Pets, Non-Smoking', 2900.00, '2026-07-01', true, 1580,
     ARRAY['Heat', 'Water', 'Internet']::text[], 'None', 'In-unit',
     '{"pets_allowed": "no", "non_smoking": true, "max_occupants": 6, "lease_term_months": 12}'::jsonb,
     v_mgr);

  -- â”€â”€ 5. Complaint Test Flats â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- All vacant at first; tenants assigned below via UPDATE.
  INSERT INTO flats (uuid, flat_number, bedrooms, bathrooms, floor_number,
                     occupied, building_id, property_type_id, manager_id)
  VALUES
    (v_fc_t101, 'T101', 1, 1, 1, false, v_bldg_compl, v_pt_id, v_mgr),
    (v_fc_t102, 'T102', 1, 1, 2, false, v_bldg_compl, v_pt_id, v_mgr),
    (v_fc_t103, 'T103', 1, 1, 3, false, v_bldg_compl, v_pt_id, v_mgr),  -- stays vacant
    (v_fc_t104, 'T104', 2, 1, 1, false, v_bldg_compl, v_pt_id, v_mgr),
    (v_fc_t201, 'T201', 2, 1, 2, false, v_bldg_compl, v_pt_id, v_mgr),
    (v_fc_t202, 'T202', 2, 2, 3, false, v_bldg_compl, v_pt_id, v_mgr);

  -- â”€â”€ 6. Complaint Test Tenants â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- T101: use your phone so inbound calls verify correctly.
  -- T102/T104/T201/T202: fictitious numbers for negative/secondary tests.
  INSERT INTO tenants
    (uuid, name, phone, flat_uuid, lease_start_date, lease_end_date,
     rent_status, payment_schedule, manager_id)
  VALUES
    (v_tn_t101, 'Alex Martin',    v_tester_phone,  v_fc_t101,
     '2025-01-01', '2026-12-31', 'On-time', 'monthly', v_mgr),

    (v_tn_t102, 'Sophie Leblanc', '+15145550022',  v_fc_t102,
     '2025-01-01', '2026-12-31', 'On-time', 'monthly', v_mgr),

    (v_tn_t104, 'James Wong',     '+15145550044',  v_fc_t104,
     '2025-06-01', '2026-05-31', 'On-time', 'monthly', v_mgr),

    (v_tn_t201, 'Marie Audet',    '+15145550061',  v_fc_t201,
     '2025-03-01', '2026-02-28', 'On-time', 'monthly', v_mgr),

    (v_tn_t202, 'David Park',     '+15145550062',  v_fc_t202,
     '2025-07-01', '2026-06-30', 'On-time', 'monthly', v_mgr);

  -- â”€â”€ 7. Bidirectional flat â†” tenant link â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- flats.tenant_uuid â† tenant UUID, occupied â† true
  UPDATE flats SET tenant_uuid = v_tn_t101, occupied = true WHERE uuid = v_fc_t101;
  UPDATE flats SET tenant_uuid = v_tn_t102, occupied = true WHERE uuid = v_fc_t102;
  UPDATE flats SET tenant_uuid = v_tn_t104, occupied = true WHERE uuid = v_fc_t104;
  UPDATE flats SET tenant_uuid = v_tn_t201, occupied = true WHERE uuid = v_fc_t201;
  UPDATE flats SET tenant_uuid = v_tn_t202, occupied = true WHERE uuid = v_fc_t202;
  -- T103 stays vacant (tenant_uuid = null, occupied = false)

  -- â”€â”€ 8. Test Complaints â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- cmp1: Real complaint for T202 â€” used in view/reschedule/cancel tests (C05-C09)
  -- cmp2: Blocker complaint for T102 â€” used only to anchor the blocker appointment
  INSERT INTO complaints
    (uuid, flat_uuid, flat_number, category, priority, description, status, source, manager_id)
  VALUES
    (v_cmp1, v_fc_t202, 'T202', 'maintenance', 'medium',
     'Bathroom faucet dripping continuously â€” needs replacement',
     'pending', 'web', v_mgr),

    (v_cmp2, v_fc_t102, 'T102', 'other', 'low',
     '[TEST BLOCKER] Placeholder complaint â€” anchors unavailability window at 2026-07-15 14:00',
     'pending', 'web', v_mgr);

  -- â”€â”€ 9. Test Appointments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
  -- apt1: T202 scheduled callback â€” used in C05 (view), C07 (reschedule), C08 (conflict), C09 (cancel)
  -- apt2: Blocker at 2026-07-15 14:00 â€” check_availability returns "unavailable" for any
  --       time within Â±1hr of 14:00 (e.g., 13:30, 14:30). Use 14:00 or 14:30 for test C08.
  INSERT INTO appointments
    (uuid, complaint_uuid, flat_number, flat_uuid, appointment_date, status, notes, manager_id)
  VALUES
    (gen_random_uuid(), v_cmp1, 'T202', v_fc_t202,
     '2026-07-10T10:00:00', 'scheduled',
     'Manager callback â€” faucet issue. Created by test seed.',
     v_mgr),

    (gen_random_uuid(), v_cmp2, 'T102', v_fc_t102,
     '2026-07-15T14:00:00', 'scheduled',
     '[TEST BLOCKER] Blocks availability at July 15 14:00 (Â±1hr window). Delete with seed cleanup.',
     v_mgr);

  RAISE NOTICE '';
  RAISE NOTICE '=== SEED COMPLETE ===';
  RAISE NOTICE 'Property group UUID: %', v_pg;
  RAISE NOTICE 'Lease listings created: 20 (has_more=true â€” all tests use search_listings path)';
  RAISE NOTICE 'Complaint test flats: T101â€“T104, T201, T202';
  RAISE NOTICE 'Tester phone registered to T101 tenant: %', v_tester_phone;
  RAISE NOTICE 'Blocker appointment: 2026-07-15T14:00 â€” book this time in C08 to test unavailable';
  RAISE NOTICE '=====================';

END $$;


-- =============================================================
-- VERIFICATION â€” run these after the DO block to confirm seed
-- =============================================================

-- Count seeded listings (should be 20)
SELECT COUNT(*) AS listing_count
FROM lease_listings ll
JOIN flats f ON f.uuid = ll.flat_uuid
WHERE ll.flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

-- Preview all 20 listings with their custom_rules
SELECT
  ll.flat_number,
  f.bedrooms,
  f.floor_number,
  ll.monthly_rent,
  ll.available_from,
  ll.parking,
  ll.laundry,
  ll.custom_rules->>'pets_allowed'    AS pets,
  (ll.custom_rules->>'non_smoking')::boolean AS non_smoking,
  (ll.custom_rules->>'max_occupants')::int   AS max_occ
FROM lease_listings ll
JOIN flats f ON f.uuid = ll.flat_uuid
WHERE ll.flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%'
ORDER BY f.bedrooms, ll.monthly_rent;

-- Complaint test tenants
SELECT f.flat_number, t.name, t.phone
FROM flats f
JOIN tenants t ON t.uuid = f.tenant_uuid
WHERE f.flat_number IN ('T101','T102','T104','T201','T202')
ORDER BY f.flat_number;

-- Confirm T103 is vacant
SELECT flat_number, occupied, tenant_uuid FROM flats WHERE flat_number = 'T103';

-- Seeded appointments
SELECT a.flat_number, a.appointment_date, a.status, a.notes
FROM appointments a
WHERE a.flat_number IN ('T202', 'T102')
ORDER BY a.appointment_date;


-- =============================================================
-- CLEANUP â€” run when testing is done
-- =============================================================
-- Execute in this order to respect foreign keys:

/*
DELETE FROM appointments
  WHERE flat_number IN ('T101','T102','T103','T104','T201','T202')
     OR flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

DELETE FROM complaints
  WHERE flat_number IN ('T101','T102','T103','T104','T201','T202')
     OR flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

DELETE FROM lease_leads
  WHERE notes ILIKE '%Clearview Heights%'
     OR notes ILIKE '%[TEST BLOCKER]%'
     OR notes ILIKE '%test seed%';

UPDATE flats SET tenant_uuid = NULL, occupied = false
  WHERE flat_number IN ('T101','T102','T104','T201','T202');

DELETE FROM tenants WHERE flat_uuid IN (
  SELECT uuid FROM flats WHERE flat_number IN ('T101','T102','T104','T201','T202')
);

DELETE FROM lease_listings WHERE flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%';

DELETE FROM flats WHERE flat_number LIKE 'T%B%' OR flat_number LIKE 'TST%'
   OR flat_number IN ('T101','T102','T103','T104','T201','T202');

DELETE FROM buildings WHERE name IN ('Maple Tower','Oak Residences')
  AND description ILIKE '%test%';

DELETE FROM properties_list WHERE name = 'Clearview Heights [TEST]';
*/

