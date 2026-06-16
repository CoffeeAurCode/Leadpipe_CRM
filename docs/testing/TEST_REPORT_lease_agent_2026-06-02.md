# Lease Agent Manual Test Report — 2026-06-02

**Tester:** Pranav Raj  
**Time (UTC):** ~12:53  
**Call ID:** `019e8864-c642-711d-8fa7-0811eb1aea9c`  
**Caller phone:** `+919998064026`  
**Caller name:** Prana Raj  
**Result:** Lead saved as `unmatched` — **INCORRECT** (a matching unit existed)

---

## What the Caller Asked For

"3 bedroom unit"

---

## What Was Available in the DB

| Flat | Bedrooms | Rent (₹/mo) | Available From | Custom Rules |
|------|----------|-------------|----------------|--------------|
| A101 | 1 | 20,000 | 2026-05-22 | none |
| B202 | 2 | 38,000 | 2026-06-01 | none |
| **C301** | **3** | **65,000** | **2026-05-22** | **none** |
| D404 | 2 | 42,000 | 2026-05-22 | no pets |
| E501 | 2 | 55,000 | 2026-05-22 | income verification required |

**C301 was a direct match.** The agent should have found it, presented it, and saved the lead as `qualified` or `unmatched` only if the caller explicitly rejected it.

---

## Call Sequence (from logs)

```
12:53:38  GET /leasing/find-listing?query=3%20bedroom&manager_id=28c43c77-...   200 OK
12:53:51  POST /voice/lease-lead-direct?call_id=...&phone=+919998064026         200 OK
```

Lead saved:
```json
{
  "qualification_status": "unmatched",
  "notes": "Unit not found in listings: 3 bedroom",
  "bedrooms": 3,
  "budget_max": 0,
  "listing_uuid": "",
  "interested_listing_ids": [],
  "address_preference": "3 bedroom"
}
```

---

## Bug 1 — Agent Called the Wrong Tool

**Severity: High (caused the failure)**

The agent called `find_listing` with `query=3 bedroom`.

`find_listing` (`GET /leasing/find-listing`) searches by:
1. Flat number ilike (`"3 bedroom"` does not match `"A101"`, `"C301"`, etc.)
2. Listing title ilike (all 5 listings have **empty titles** → zero matches)
3. Building name / flat address text (`"3 bedroom"` not present in `"Sunrise Heights"` → no match)

All three paths fail → `{"found": false}` → agent concludes no units exist → saves as `unmatched`.

**Correct tool:** `search_available_listings` (`GET /leasing/search?bedrooms=3&manager_id=...`), which filters by bedroom count directly in the DB and would have returned C301.

---

## Bug 2 — All Listing Titles Are Empty

**Severity: Medium (makes `find_listing` path 2 permanently dead)**

Every listing in `lease_listings` has `title = NULL / ""`. This means:
- Path 2 of `find_listing` (title ilike) can never return results.
- When the agent or a human tries to search by a descriptive phrase, nothing matches.
- The lease agent's `find_listing` tool is essentially a flat-number-only lookup until titles are populated.

**Fix:** Populate `title` on all listings. Minimum useful format: `"3-Bedroom Unit – Sunrise Heights, Floor 3"`. Either do it manually in Supabase or add auto-generation in `POST /leasing/listings` when title is blank.

---

## Bug 3 — `listing_uuid` Saved as Empty String Instead of `null`

**Severity: Low (data quality)**

The lead row has `listing_uuid: ""`. The column is a UUID FK — an empty string is not a valid UUID. This should be `null` when no listing was matched.

Check: does the current `lease-lead-direct` handler coerce `""` to `null` before the INSERT?

```python
# leasing.py / voice.py — wherever the lead is inserted:
listing_uuid = data.get("listing_uuid") or None   # ← must be this
# NOT:
listing_uuid = data.get("listing_uuid", "")       # ← this causes ""
```

---

## Bug 4 — `address_preference` Misused

**Severity: Low (data quality)**

The agent stored `"3 bedroom"` in `address_preference`. That field is for floor or location preferences (e.g., `"ground floor"`, `"near elevator"`). The bedroom count is already correctly in `bedrooms: 3`.

This points to the agent not fully understanding when to set `address_preference`. The system prompt / tool description should clarify: `address_preference` = floor or location preference only, never bedroom count.

---

## Root Cause Summary

| # | Root Cause | Impact |
|---|-----------|--------|
| 1 | Agent used `find_listing` (text search) instead of `search_available_listings` (structured bedroom/budget filter) | Lead wrongly saved as `unmatched` |
| 2 | All listing titles are empty → `find_listing` path 2 always returns zero results | Makes text-based fallback permanently dead |
| 3 | `listing_uuid: ""` instead of `null` in lead insert | FK data quality; may cause query issues |
| 4 | `address_preference` field set to bedroom count string | Minor data pollution |

---

## Recommended Fixes

### Fix 1 — Strengthen tool descriptions in `vapi_agent_config.py`

In `build_lease_config()`, update the `find_listing` tool description to be explicit:

```
Use find_listing ONLY when the caller gives you a specific flat number (e.g. "A101", "unit 202").
Do NOT use it for bedroom count, budget, or general requests like "3 bedroom unit".
For those, use search_available_listings.
```

And in `search_available_listings` description:

```
Use this for ANY search based on bedrooms, budget, or general availability.
Pass bedrooms=3 for "3 bedroom", pass 0 when not specified.
```

### Fix 2 — Populate listing titles (Supabase SQL)

```sql
UPDATE lease_listings l
SET title = (
  SELECT
    f.bedrooms || '-Bedroom Unit – ' ||
    COALESCE(f.address, '') ||
    CASE WHEN f.floor_number IS NOT NULL
         THEN ', Floor ' || f.floor_number
         ELSE '' END
  FROM flats f
  WHERE f.uuid = l.flat_uuid
)
WHERE title IS NULL OR title = '';
```

After running: A101 → `"1-Bedroom Unit – Sunrise Heights, Floor 1"`, C301 → `"3-Bedroom Unit – Sunrise Heights, Floor 3"`, etc.

### Fix 3 — Coerce empty `listing_uuid` to `null` in lead handler

In the `lease-lead-direct` (and `lease-lead-webhook`) handler, before inserting:

```python
listing_uuid = data.get("listing_uuid") or None
```

### Fix 4 — Agent system prompt clarification for `address_preference`

Add one line to the `submit_lease_lead` tool's parameter description:

```
address_preference: floor or location preference only (e.g. "ground floor", "near elevator").
Leave empty if the caller only mentioned bedroom count.
```

---

## Expected Behavior After Fixes

1. Caller says "3 bedroom"
2. Agent calls `search_available_listings?bedrooms=3&manager_id=...`
3. Backend returns C301: 3 bed, ₹65,000, available 2026-05-22
4. Agent presents C301 to caller, captures name/phone/move-in timeline
5. Lead saved: `qualification_status=qualified`, `listing_uuid=b9f94428-...`, `bedrooms=3`, `interested_listing_ids=[b9f94428-...]`
