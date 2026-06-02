# Fix: Lease Agent Listing Lookup

## Problem

The lease agent failed to find a matching 3-bedroom unit (C301, ₹65,000) when the caller said "3 bedroom."

Root cause: the agent called `find_listing` — a text search endpoint — with the query `"3 bedroom"`.
That endpoint matches flat numbers, listing titles, and building addresses. It cannot match bedroom counts.
All listing titles are also empty, so the text match fails on three paths and returns `found: false`.
The agent concludes no units exist and saves the lead as `unmatched`.

---

## Proposed Fix

Replace the fragile mid-call `find_listing` tool with a single `load_listings` call that happens
**once, right after the caller's first message**. The backend returns all active listings for this
manager. The agent uses its own LLM reasoning to match the caller's words to the right unit —
whether the caller says a flat number, a bedroom count, a budget, or just "what do you have."

This removes the tool selection problem entirely: there is only one lookup tool, it always returns
everything, and the agent decides what matches rather than a dumb string endpoint.

---

## Honest Assessment

| Question | Answer |
|---|---|
| Is the idea correct? | Yes — pre-loading all listings per call is strictly better for this scale |
| Is it doable? | Yes — one new backend endpoint + tool swap + system prompt update |
| Any real constraints? | If a manager has 50+ listings the JSON gets large (fine for MVP; note it now) |
| Does it break anything? | No — `submit_lease_lead` is unchanged; only `find_listing` is removed |
| Does it need VAPI changes? | No — same `apiRequest` tool type, same server_messages config |

---

## What Changes

```
1. New backend endpoint    GET /leasing/listings-for-agent?manager_id=
2. vapi_agent_config.py    Replace find_listing tool with load_listings tool
3. vapi_agent_config.py    Update _LEASE_SYSTEM_PROMPT_BASE — new step 2 logic
4. Deploy                  Run update_lease_agents.py to push config to all active agents
```

---

## Step 1 — New Backend Endpoint

**File:** `backend/app/routes/leasing.py`

Add this route **before** the manager CRUD section, alongside the other VAPI tool endpoints:

```python
@router.get("/listings-for-agent")
async def listings_for_agent(
    manager_id: Optional[str] = Query(None),
    db: Client = Depends(get_service_db),
):
    """
    VAPI tool endpoint — returns ALL active listings for a manager in one call.
    No auth, no subscription gate. Always returns HTTP 200.
    """
    try:
        q = (
            db.table("lease_listings")
            .select(
                "uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                "square_footage, included_utilities, parking, laundry, "
                "flats!inner(bedrooms, floor_number, address, buildings(name, address))"
            )
            .eq("is_active", True)
        )
        if manager_id:
            q = q.eq("manager_id", manager_id)

        results = q.order("created_at").execute()

        listings = []
        for r in (results.data or []):
            flat = r.get("flats") or {}
            building = flat.get("buildings") or {}
            utilities = r.get("included_utilities") or []
            listings.append({
                "listing_uuid": r["uuid"],
                "flat_number": r["flat_number"],
                "address": " ".join(filter(None, [
                    flat.get("address") or "",
                    building.get("name") or "",
                    building.get("address") or "",
                ])).strip(),
                "bedrooms": flat.get("bedrooms"),
                "monthly_rent": float(r["monthly_rent"]),
                "floor_number": str(flat.get("floor_number") or ""),
                "available_from": str(r.get("available_from") or ""),
                "square_footage": r.get("square_footage"),
                "included_utilities": ", ".join(utilities) if utilities else "not specified",
                "parking": r.get("parking") or "not specified",
                "laundry": r.get("laundry") or "not specified",
                "custom_rules": json.dumps(r.get("custom_rules") or {}),
            })

        return {"count": len(listings), "listings": listings}

    except Exception as e:
        print(f"[ERROR] listings_for_agent: {e}")
        return {"count": 0, "listings": []}
```

**No changes needed to `main.py`** — this route is in `leasing.py` which is already registered.

---

## Step 2 — Update `vapi_agent_config.py`

### 2a — Replace `find_listing` tool with `load_listings`

In `_build_lease_tools()`, **remove** the entire `find_listing` dict and **replace** it with:

```python
{
    "type": "apiRequest",
    "name": "load_listings",
    "async": False,
    "function": {
        "name": "api_request_tool",
        "description": (
            "Fetches ALL available rental units for this property account. "
            "Call this ONCE after the caller's first message — before any other response. "
            "Returns a listings array. Each listing has: listing_uuid, flat_number, address, "
            "bedrooms, monthly_rent, floor_number, available_from, custom_rules, "
            "square_footage, included_utilities, parking, laundry. "
            "After receiving the listings, use your own judgment to match the caller's request "
            "(flat number, bedroom count, budget, or any preference they mention). "
            "Do NOT call this tool more than once per call."
        ),
    },
    "url": f"{backend_url}/leasing/listings-for-agent?manager_id={manager_id}" if manager_id else f"{backend_url}/leasing/listings-for-agent",
    "method": "GET",
    "body": {
        "type": "object",
        "required": [],
        "properties": {},
    },
    "messages": [
        {
            "type": "request-start",
            "content": "Give me a second to check what we have available.",
        }
    ],
    "variableExtractionPlan": {
        "schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "Number of available listings"},
                "listings": {
                    "type": "array",
                    "description": "All available listings",
                    "items": {
                        "type": "object",
                        "properties": {
                            "listing_uuid": {"type": "string"},
                            "flat_number": {"type": "string"},
                            "address": {"type": "string"},
                            "bedrooms": {"type": "integer"},
                            "monthly_rent": {"type": "number"},
                            "floor_number": {"type": "string"},
                            "available_from": {"type": "string"},
                            "square_footage": {"type": "integer"},
                            "included_utilities": {"type": "string"},
                            "parking": {"type": "string"},
                            "laundry": {"type": "string"},
                            "custom_rules": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
},
```

Note: the URL no longer uses a template variable (`{{query}}`) — the manager_id is baked in at
build time just like the existing `manager_id` injection pattern in `_build_lease_tools`.

### 2b — Update `_LEASE_SYSTEM_PROMPT_BASE`

Replace **Step 2 — Look Up the Unit** entirely. The old step assumed the caller gives a flat number
and the agent does a text search. The new step pre-loads everything, then matches.

**Remove this block from `_LEASE_SYSTEM_PROMPT_BASE`:**
```
2. Look Up the Unit
Call find_listing with the unit number or address/query the caller mentioned.
- If the tool responds AND found=true (count>=1): store the first matching listing's details
  ... (all the find_listing logic) ...
- "Search tool unavailable" note is ONLY for when find_listing throws a hard error or times out
  (not for found=false). Do NOT use that note when found=false.
```

**Replace with:**
```
2. Load All Available Units
Immediately after the caller's first message — before formulating your response — call
load_listings. This returns all currently available units. Do NOT call it more than once.

Once you have the listings array, match the caller's request using your judgment:

- Caller named a flat number (e.g. "C301", "unit 202"):
  Find the listing where flat_number matches. If found: store its details and proceed to Q1.
  If not found: say "I don't see that unit in our available listings right now. Would you like
  to hear what we do have available?" — then describe the available options briefly.

- Caller described a preference (e.g. "3 bedroom", "something under $50,000", "ground floor"):
  Filter the listings array yourself and find the best match(es).
  If one match: say "I have a [N]-bedroom unit available — [flat_number], floor [X],
  available from [date] for [rent] per month. Does that sound like what you're looking for?"
  If multiple matches: briefly describe each option (flat number + bedrooms + rent).
  Ask which one they'd like to learn more about.

- Caller wants to browse (e.g. "what do you have?", "show me everything"):
  Read out all available units briefly: flat number, bedrooms, monthly rent. Ask which interests them.

- count = 0 (no listings available):
  Say: "We don't have any units available right now. I'll make sure our team follows up with you."
  Call submit_lease_lead with qualification_status="unmatched",
  notes="No listings available at time of call". Then end politely.

Once a specific listing is identified, store its listing_uuid, monthly_rent, bedrooms,
floor_number, available_from, address, square_footage, included_utilities, parking, laundry,
and custom_rules. Use these for all subsequent questions (Q3 answers, Q5 occupant check, Q6 pet check, Q7 smoking check).
```

**Also update the `[Tools]` section at the bottom of the prompt:**

Remove:
```
find_listing — Look up a unit by flat number, unit name, or any part of the address...
```

Replace with:
```
load_listings — Fetches ALL available units for this property account. Call once after the
               caller's first message. Use the returned listings array to match the caller's
               request — by flat number, bedroom count, budget, or any preference they mention.
submit_lease_lead — Capture the prospective tenant as a lead. Always call exactly once before ending the call.
```

**Also update `[Critical Rules]`:**

Remove:
```
- listing_uuid must come from find_listing. If no listing found, leave it blank. NEVER invent a UUID.
- If find_listing returns found=false twice (HTTP 200 but no listings): ...
- If find_listing itself errors or times out (no HTTP response): ...
```

Replace with:
```
- listing_uuid must come from load_listings results. Match by flat_number or caller preference.
  Never invent a UUID. Leave blank only if no match could be made.
- If load_listings returns count=0: no units available — submit lead as unmatched and end politely.
- If load_listings itself errors or times out: say "I'm unable to pull up our available units right
  now. Our team will follow up with you." Call submit_lease_lead with qualification_status="unmatched",
  notes="Listing load failed during call". Do not retry.
```

---

## Step 3 — Deploy

```bash
python backend/scripts/update_lease_agents.py
```

This script already iterates all `manager_vapi_config` rows with `status = active` and pushes
the latest config from `build_lease_config()`. No changes needed to the script itself.

After running, verify with the VAPI dashboard that the `load_listings` tool appears and
`find_listing` is gone from the active agent.

---

## Step 4 — Verify the Endpoint Before Deploying

Before pushing to VAPI, confirm the new endpoint works:

```bash
curl "https://tenant-management-mvp.onrender.com/leasing/listings-for-agent?manager_id=28c43c77-8c9c-496f-8d1e-39ffa9d619e3"
```

Expected response:
```json
{
  "count": 5,
  "listings": [
    {"listing_uuid": "...", "flat_number": "A101", "bedrooms": 1, "monthly_rent": 20000.0, ...},
    {"listing_uuid": "...", "flat_number": "B202", "bedrooms": 2, "monthly_rent": 38000.0, ...},
    {"listing_uuid": "b9f94428-...", "flat_number": "C301", "bedrooms": 3, "monthly_rent": 65000.0, ...},
    ...
  ]
}
```

C301 must appear with `bedrooms: 3`.

---

## Step 5 — Test Call Checklist

After deploying, call the lease number and test each path:

| Test | Input | Expected |
|------|-------|----------|
| Unit by number | "I'm asking about C301" | Agent finds C301 (3 bed, ₹65k), presents details |
| Unit by bedrooms | "I'm looking for a 3 bedroom" | Agent finds C301, presents it |
| Unit by budget | "Something under 40,000 a month" | Agent suggests A101 (₹20k) or B202 (₹38k) |
| Browse all | "What do you have available?" | Agent lists all 5 units briefly |
| Disqualify — pets | Ask about D404, say you have pets | Agent says pets not allowed, saves not_qualified |
| No listings edge case | (test with no active listings) | Agent says nothing available, saves unmatched |
| Lead save | Complete full call | lead_uuid saved, listing_uuid = correct UUID |

---

## What This Does Not Fix

- **Empty listing titles** — the titles are still empty. Not a problem after this fix (the agent
  no longer does title text-search), but titles should still be populated for the manager dashboard
  and CSV exports to be readable. That's a separate data task.

- **`listing_uuid: ""`** in the lead handler — should still be coerced to `null`. That's a
  one-line fix in the `lease-lead-direct` handler and independent of this change.

---

## Why This Is Better Than the Previous Fix Suggestion

The previous report suggested fixing `find_listing`'s tool description and populating titles.
That still relies on the agent picking the right tool at the right time and on the text-search
returning useful results. Both are fragile.

This fix removes the fragility at the source:
- One tool, not two
- No tool selection decision
- LLM reasoning over structured data (better at "3 bedroom" than a string ilike query)
- Works even with empty titles
- Works for any natural language description of what the caller wants
