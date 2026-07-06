-- Backfill: normalize tenants.phone to E.164 (+<country><digits>)
--
-- WHY
--   The CSV importers (POST /import/tenants, /import/properties) and the
--   create-flat / manage-tenant routes inserted phone numbers verbatim, so rows
--   like '514-555-0130' and '15149841671' reached the DB. TenantResponse
--   validates phone as strict E.164, so GET /tenants raised
--   ResponseValidationError (HTTP 500) for any manager owning such a row —
--   their tenant page showed "Failed to load tenants". Write paths now
--   normalize via app/core/phone.py; this repairs rows created before that fix.
--
-- SAFETY
--   Mirrors normalize_phone_e164(): strip non-digits; 10 digits => assume NANP
--   (+1); 11-15 digits not starting with 0 => assume country code included.
--   Rows that cannot be normalized, or whose normalized value would collide
--   with an existing phone (unique column), are left untouched — find them with
--   the verify query and fix manually.
--
-- Run in: Supabase SQL Editor.

-- 1. Inspect first — see which rows will change:
-- WITH cleaned AS (
--   SELECT uuid, name, phone, regexp_replace(phone, '[^0-9]', '', 'g') AS digits
--   FROM tenants
--   WHERE phone !~ '^\+[1-9][0-9]{9,14}$'
-- )
-- SELECT uuid, name, phone AS old_phone,
--        CASE
--          WHEN length(digits) = 10 THEN '+1' || digits
--          WHEN length(digits) BETWEEN 11 AND 15 AND digits !~ '^0' THEN '+' || digits
--        END AS new_phone
-- FROM cleaned;

-- 2. Apply:
WITH cleaned AS (
  SELECT uuid, regexp_replace(phone, '[^0-9]', '', 'g') AS digits
  FROM tenants
  WHERE phone !~ '^\+[1-9][0-9]{9,14}$'
),
mapped AS (
  SELECT uuid,
         CASE
           WHEN length(digits) = 10 THEN '+1' || digits
           WHEN length(digits) BETWEEN 11 AND 15 AND digits !~ '^0' THEN '+' || digits
         END AS new_phone
  FROM cleaned
)
UPDATE tenants t
SET phone = m.new_phone
FROM mapped m
WHERE t.uuid = m.uuid
  AND m.new_phone IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM tenants x WHERE x.phone = m.new_phone AND x.uuid <> t.uuid)
  AND (SELECT count(*) FROM mapped d WHERE d.new_phone = m.new_phone) = 1;

-- 3. Verify (expect 0 rows; any remainder needs manual fixing):
-- SELECT uuid, name, phone FROM tenants WHERE phone !~ '^\+[1-9][0-9]{9,14}$';
