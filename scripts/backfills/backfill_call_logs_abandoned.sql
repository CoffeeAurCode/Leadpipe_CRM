-- Backfill manager_id on abandoned call_logs (no complaint linked)
-- by tracing: call_logs.phone_number → tenants → flats → buildings → properties_list → manager_id

UPDATE call_logs cl
SET manager_id = pg.manager_id
FROM tenants t
JOIN flats f       ON f.uuid = t.flat_uuid
JOIN buildings b   ON b.id::text = f.building_id::text
JOIN properties_list pg ON pg.id::text = b.property_id::text
WHERE cl.phone_number = t.phone
  AND cl.manager_id IS NULL
  AND pg.manager_id IS NOT NULL;

-- Check final state
SELECT
    COUNT(*) FILTER (WHERE manager_id IS NOT NULL) AS with_manager,
    COUNT(*) FILTER (WHERE manager_id IS NULL)     AS still_null,
    COUNT(*)                                        AS total
FROM call_logs;
