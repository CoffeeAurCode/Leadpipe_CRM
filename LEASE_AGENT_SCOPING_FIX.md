# Plan: Lease Agent Scoping Fix

Two independent fixes to the lease agent: reliable manager scoping for lead submission, and broader unit search coverage.

---

## Fix 1 — Bake `manager_id` into `submit_lease_lead` URL

### Problem

`find_units` and `search_listings` both have `manager_id` baked into their tool URLs at config time, so listing searches are already scoped to the right manager. But `submit_lease_lead` does not:

```
/voice/lease-lead-direct?call_id={{call.id}}&phone={{customer.number}}
```

The backend falls back through `listing_uuid → assistant_id → phone_number_id` to resolve `manager_id`. For unmatched leads (no `listing_uuid`), this fallback can misattribute or fail silently.

### Fix

**File:** `backend/app/services/vapi_agent_config.py` — `_build_lease_tools`

Add `manager_id` to the `submit_lease_lead` URL:

```python
"url": f"{backend_url}/voice/lease-lead-direct?call_id={{{{call.id}}}}&phone={{{{customer.number}}}}&manager_id={manager_id or ''}",
```

**File:** `backend/app/routes/voice.py` — `lease_lead_direct`

Read the new `manager_id` query param and use it directly when `listing_uuid` resolution fails:

```python
manager_id_param: Optional[str] = Query(None),
```

Resolution order:
1. `listing_uuid` → `lease_listings.manager_id` (unchanged — most reliable)
2. `manager_id` query param (new — direct from tool URL)
3. `assistant_id` fallback (existing — kept as last resort)

### Why this over runtime phone lookup

Each per-manager assistant already has `manager_id` compiled into its config. Using it directly in the URL is the same pattern as `find_units` and `search_listings`, requires no extra DB lookup at call time, and doesn't depend on any VAPI template variable for the called number.

---

## Fix 2 — Expand `find_units` search to include `address_line`

### Problem

The current `find_units` endpoint builds a haystack from:
- `flat_number`, `title`, `street_address`, `city`, `state`, `country`
- `buildings.name`, `properties_list.name`

If a location is stored in `buildings.address_line` or `flats.address_line` (the structured address extra line), a caller query for that location returns 0 results even though the unit exists.

The AI does not need to classify caller input by field type — the backend searches all fields simultaneously. The system prompt already handles 0-result retries and polite hold messages.

### Fix

**File:** `backend/app/routes/leasing.py` — `find_units`

In the building lookup, also fetch `address_line`:

```python
b_res = db.table("buildings").select("id, name, address_line, property_id").in_("id", building_ids).execute()
```

Add `building.get("address_line") or ""` to the haystack:

```python
haystack = " ".join(filter(None, [
    r.get("flat_number") or "",
    r.get("title") or "",
    r.get("street_address") or "",
    r.get("city") or "",
    r.get("state") or "",
    r.get("country") or "",
    building.get("name") or "",
    building.get("address_line") or "",   # ← new
    prop_group.get("name") or "",
])).lower()
```

No change to the tool schema, no change to the system prompt, no AI field-classification logic needed.

---

## Implementation Checklist

- [ ] `vapi_agent_config.py` — add `&manager_id={manager_id or ''}` to `submit_lease_lead` URL
- [ ] `voice.py` (`lease_lead_direct`) — read `manager_id` query param; use as fallback after `listing_uuid` resolution, before `assistant_id` fallback
- [ ] `leasing.py` (`find_units`) — add `address_line` to building SELECT and haystack
- [ ] Run `python backend/scripts/update_lease_agents.py` to push updated tool URL to VAPI
- [ ] Test: make a call with no listing confirmed → lead appears under correct manager
- [ ] Test: query a location stored only in `address_line` → `find_units` returns the unit
