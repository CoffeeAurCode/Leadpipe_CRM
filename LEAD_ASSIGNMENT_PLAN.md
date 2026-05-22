# Lead Assignment — Implementation Plan

## What the Logic Is Supposed to Be

```
Caller phones a number assigned to a property group
    ↓
Agent looks through lease listings in that property group
    ↓
Finds listings that match caller's requirements (bedrooms, budget, floor, etc.)
    ↓
Captures which listings the caller is interested in
    ↓
Lead is created and assigned to those specific listings
    ↓
All IDs on the lead (manager_id, property_group_id, listing_uuid) come from those listings
```

## What Is Actually Happening Right Now

```
Caller phones
    ↓
Agent collects requirements conversationally
    ↓
Agent calls search_available_listings → gets back PLAIN TEXT SUMMARY (no UUIDs)
    ↓
Agent cannot extract listing UUIDs from text → listing_uuid stays NULL
    ↓
interested_listing_ids is NEVER populated (field exists in schema, never written)
    ↓
Lead is created with:
    - listing_uuid = NULL
    - interested_listing_ids = []
    - manager_id = resolved from property group (not from matched listing)
    - property_group_id = resolved from phone/assistant
```

## Gap Summary

| What Should Happen | What Happens Now | Gap |
|---|---|---|
| Agent gets structured listing results with UUIDs | Agent gets plain-text summary, no UUIDs | `search_available_listings` returns unstructured text |
| All matching listings captured in `interested_listing_ids` | Field always empty | No tool for multi-listing capture, no backend write |
| Primary matched listing in `listing_uuid` | Usually NULL | Agent has no way to extract UUID from text response |
| `manager_id` derived from matched listing | Derived from property group (incidental) | Works only because all listings in a group share a manager |
| Lead shown under its matched property in UI | Leads shown in flat list, no listing link visible | Frontend doesn't display matched listing(s) |

---

## Implementation Plan

### Phase 1 — Fix `search_available_listings` to Return Structured Data

**File**: `backend/app/routes/leasing.py` — `GET /leasing/search`

Currently returns:
```python
{"count": 3, "listings": "Unit A101: 2 BHK, ₹45000/month, Floor 1..."}
```

Change to return structured array with UUIDs:
```python
{
  "count": 3,
  "listings": [
    {
      "listing_uuid": "abc-123",
      "flat_number": "A101",
      "bedrooms": 2,
      "monthly_rent": 45000,
      "floor_number": 1,
      "available_from": "2026-06-01",
      "title": "Spacious 2BHK"
    },
    ...
  ]
}
```

Also update `find_listing` (`GET /leasing/find-listing`) to include `listing_uuid` in the response
(it currently returns listing data but the VAPI tool description doesn't make UUID extraction
explicit to the agent).

**VAPI tool schema update** in `vapi_agent_config.py`: update the `search_available_listings`
tool description to tell the agent the response contains `listing_uuid` fields it must use
when calling `submit_lease_lead`.

---

### Phase 2 — Add `interested_listing_ids` to `submit_lease_lead` Tool Schema

**File**: `backend/app/services/vapi_agent_config.py` — `_build_lease_tools()`

Add to `submit_lease_lead` parameters:
```python
"interested_listing_ids": {
    "type": "array",
    "items": {"type": "string"},
    "description": "UUIDs of all listings the caller expressed interest in",
    "default": []
},
```

The `listing_uuid` field (already present) becomes the PRIMARY matched listing — the one
the caller was most interested in or best qualified for. `interested_listing_ids` captures all
listings discussed.

Update the system prompt conversation flow:

```
Step 3 (Find Listings):
  - Call search_available_listings with caller's bedrooms + budget_max
  - The response includes listing_uuid for each result
  - Present options to caller
  - Note which listings the caller responds positively to

Step 5 (Capture Lead):
  - Set listing_uuid = the primary listing caller wants to pursue
  - Set interested_listing_ids = all listing UUIDs caller showed interest in
```

---

### Phase 3 — Update Webhook Handler to Write `interested_listing_ids`

**File**: `backend/app/routes/voice.py` — `submit_lease_lead` handler (lines ~602–622)

Currently:
```python
lead_payload = {
    ...
    "listing_uuid": str(listing_uuid) if listing_uuid else None,
    # interested_listing_ids never written
}
```

Change to:
```python
interested_ids = lead_data.get("interested_listing_ids") or []
# Validate they are real UUIDs (strip empties)
interested_ids = [i for i in interested_ids if i and len(i) == 36]

lead_payload = {
    ...
    "listing_uuid": str(listing_uuid) if listing_uuid else None,
    "interested_listing_ids": interested_ids,
}
```

Also: when `listing_uuid` is set, resolve `manager_id` FROM the listing row rather than from
the property group, so the lead's manager is guaranteed to match the listing's owner:

```python
if listing_uuid:
    listing_row = db.table("lease_listings")
        .select("property_group_id")
        .eq("uuid", str(listing_uuid))
        .limit(1).execute()
    if listing_row.data:
        # resolve property_group_id from listing (more accurate than phone/assistant path)
        property_group_id = listing_row.data[0]["property_group_id"]

# then resolve manager_id from property_group_id as before
```

---

### Phase 4 — Frontend: Show Matched Listings on Lead

**File**: `frontend/src/components/LeadDetailModal.jsx`

Add a "Matched Listings" section after the Preferences block:

```
Matched Listings
  Primary:   Unit A101 — 2 BHK, ₹45,000/mo  [link/badge]
  Also interested in:  A203, B105            [smaller badges]
```

Fields to display:
- `listing_uuid` → look up flat_number + monthly_rent from the listings array (already fetched
  in LeasingTab state)
- `interested_listing_ids` → show as chips, same lookup

**File**: `frontend/src/components/LeasingTab.jsx`

Lead cards / table rows should show the primary matched listing (`listing_uuid`) as a column
so managers can filter and see at a glance which unit the lead is for.

---

### Phase 5 — GET /leasing/leads: Support Filtering by Multiple Listings

**File**: `backend/app/routes/leasing.py` — `GET /leasing/leads`

Current filter only supports `listing_uuid` (exact match on primary listing).

Add support for `interested_listing_ids` contains query so a manager can pull all leads that
mentioned a given listing even if it wasn't the primary:

```python
if listing_uuid:
    q = q.or_(
        f"listing_uuid.eq.{listing_uuid},"
        f"interested_listing_ids.cs.{{{listing_uuid}}}"
    )
```

---

## Execution Order

```
1. Phase 1  — search endpoint returns structured JSON with UUIDs
              (backend only, no schema change needed)

2. Phase 2  — update VAPI tool schema + system prompt
              (redeploy agent config)

3. Phase 3  — webhook writes interested_listing_ids
              (backend, no DB migration needed — column already exists)

4. Phase 4  — frontend shows matched listings in modal + table
              (frontend only)

5. Phase 5  — GET /leads supports filtering by interested listings
              (backend, small query change)
```

Phases 1 + 2 must ship together (tool response format and agent instructions are coupled).
Phases 3–5 are independent and can ship in any order after that.

---

## What Stays the Same

- Property group resolution (3-path fallback in voice.py) — works correctly
- `manager_id` resolution from property group — correct for leads where listing_uuid is NULL
- `qualification_status` set by agent — already working
- `qualifying_answers` (custom_rules answers) — already working
- Existing leads in DB — no migration needed, `interested_listing_ids` defaults to `[]`
