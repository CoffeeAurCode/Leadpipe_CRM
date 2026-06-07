# Plan: Lease Agent Flow Overhaul + Complaint Phone Fix

## Overview

Two independent issues:

1. **Lease agent overhaul** — new query-first conversation flow, concise responses, answer only what caller asks
2. **Complaint phone fix** — +14382567782 not connected to any VAPI assistant

---

## Issue 1: Lease Agent Flow Overhaul

### What changes

**Current behaviour (broken)**
Agent fires `load_listings` in background, gathers preferences first, then presents units with full details all at once — floods the caller.

**Target behaviour**
- Bilingual greeting asks "which unit are you calling about?"
- Caller mentions any identifying info (unit number, building name, property name, address, city, country, etc.)
- Agent runs `find_units` tool silently (or with one brief "one moment" line)
- Results: agent reads back just the names/identifiers — not full details
- Caller confirms which unit
- Agent answers **only** what the caller specifically asks — never volunteers extra info
- Lead capture at end as before

---

### Step 1 — New backend endpoint: `GET /leasing/find-units`

**File:** `backend/app/routes/leasing.py`

Add after the existing `/find-listing` endpoint. The key difference from `find-listing`:
- Searches building name and property group name (not just flat_number/title/address)
- Returns compact list (identifiers only) — not full listing details
- Uses two extra DB queries to resolve building and property names

```python
@router.get("/find-units")
async def find_units(
    query: str = Query(...),
    manager_id: Optional[str] = Query(None),
    db: Client = Depends(get_service_db),
):
    try:
        q = (
            db.table("lease_listings")
            .select(
                "uuid, flat_number, title, monthly_rent, available_from, "
                "street_address, city, state, country, "
                "flats!inner(bedrooms, bathrooms, floor_number, building_id)"
            )
            .eq("is_active", True)
        )
        if manager_id:
            q = q.eq("manager_id", manager_id)

        results = q.limit(50).execute()
        listings = results.data or []
        if not listings:
            return {"found": False, "count": 0, "units": []}

        # Resolve building and property group names
        building_ids = list({
            r["flats"]["building_id"]
            for r in listings
            if r.get("flats") and r["flats"].get("building_id")
        })
        building_rows, property_rows = {}, {}
        if building_ids:
            b_res = db.table("buildings").select("id, name, property_id").in_("id", building_ids).execute()
            for b in (b_res.data or []):
                building_rows[b["id"]] = b
            property_ids = list({b["property_id"] for b in building_rows.values() if b.get("property_id")})
            if property_ids:
                p_res = db.table("properties_list").select("id, name").in_("id", property_ids).execute()
                for p in (p_res.data or []):
                    property_rows[p["id"]] = p

        query_lower = query.lower()
        matches = []
        for r in listings:
            flat = r.get("flats") or {}
            bid = flat.get("building_id")
            building = building_rows.get(bid, {})
            prop_group = property_rows.get(building.get("property_id"), {})

            haystack = " ".join(filter(None, [
                r.get("flat_number") or "",
                r.get("title") or "",
                r.get("street_address") or "",
                r.get("city") or "",
                r.get("state") or "",
                r.get("country") or "",
                building.get("name") or "",
                prop_group.get("name") or "",
            ])).lower()

            if query_lower in haystack:
                matches.append({
                    "listing_uuid": r["uuid"],
                    "flat_number": r["flat_number"],
                    "building_name": building.get("name") or "",
                    "property_name": prop_group.get("name") or "",
                    "address": ", ".join(filter(None, [
                        r.get("street_address") or "",
                        r.get("city") or "",
                        r.get("state") or "",
                    ])),
                    "bedrooms": flat.get("bedrooms"),
                    "bathrooms": flat.get("bathrooms"),
                    "floor_number": str(flat.get("floor_number") or ""),
                    "monthly_rent": float(r["monthly_rent"]),
                    "available_from": str(r.get("available_from") or ""),
                })

        matches = matches[:5]
        return {"found": bool(matches), "count": len(matches), "units": matches}

    except Exception as e:
        print(f"[ERROR] find_units: {e}")
        return {"found": False, "count": 0, "units": []}
```

---

### Step 2 — Manager name in greeting

The greeting says "I'm Max, the leasing assistant for [Manager's Name]."

**2a. Update `build_lease_config` signature** in `vapi_agent_config.py`:
```python
def build_lease_config(backend_url: str, manager_id: str, manager_name: str = "our property management team") -> dict:
```

**2b. Update `_LEASE_CONTEXT_BLOCK`** to include manager name:
```python
_LEASE_CONTEXT_BLOCK = """

[Context — Do Not Expose]
Manager ID: {manager_id}
Manager Name: {manager_name}
Use the Manager Name in your first message only: "I'm Max, the AI leasing assistant for {manager_name}."
All searches are scoped to all properties managed by this account.
"""
```
And format it: `_LEASE_CONTEXT_BLOCK.format(manager_id=manager_id, manager_name=manager_name)`

**2c. Update `vapi_provisioning.py`** — fetch manager name before building config:
```python
profile_res = svc_db.table("manager_profiles").select("name").eq("user_id", manager_id).maybe_single().execute()
manager_name = (profile_res.data or {}).get("name") or "our property management team"
config = build_lease_config(backend_url, manager_id, manager_name=manager_name)
```

**2d. Update `update_lease_agents.py`** — fetch manager names in the loop:
```python
for row in agents:
    manager_id = row["manager_id"]
    assistant_id = row.get("vapi_lease_assistant_id")
    if not assistant_id:
        continue
    profile = db.table("manager_profiles").select("name").eq("user_id", manager_id).maybe_single().execute()
    manager_name = (profile.data or {}).get("name") or "our property management team"
    cfg = build_lease_config(BACKEND_URL, manager_id, manager_name=manager_name)
    ...
```

---

### Step 3 — Rewrite lease agent system prompt in `vapi_agent_config.py`

Replace `_LEASE_SYSTEM_PROMPT_BASE` with a new query-first, concise prompt.

Key changes from current:
- Remove `[Background Query Strategy]` section (no more background `load_listings`)
- Remove `[Preference Collection]` as the primary flow — now secondary
- Add `[Step 1 — Opening]` that asks "which unit?" immediately
- Add `[Step 2 — Find the unit]` using `find_units` tool
- Add **CRITICAL style rule**: answer only what's asked, one fact per response
- Remove all the "present unit details" sections that dump everything at once

New `_LEASE_SYSTEM_PROMPT_BASE`:

```
[Identity]
You are Max, a professional AI leasing assistant. Help callers find out about available rental units.
You handle leasing inquiries only — not complaints, billing, or maintenance.
If caller mentions a non-leasing issue, direct them to the property management team and ask if there's anything leasing-related you can help with.

[Language Policy]
Detect caller's language on their first word and lock to it for the entire call.
- English → respond in ENGLISH ONLY
- French → respond in FRENCH ONLY
- Ambiguous after 2 turns → ask "English or French? / Anglais ou français?" then lock

Never mix languages. Never append translations. All tool data must be in English regardless of call language.

[Style — CRITICAL]
- SHORT responses. One sentence where possible.
- Answer ONLY what the caller specifically asks. Never volunteer extra info.
  → "How much is the rent?" → "It's two thousand dollars per month."  (stop there)
  → "When is it available?" → "Available from July first."  (stop there)
- Never narrate what you're doing ("Let me check", "I'm searching for that").
- If a tool is running and the caller is clearly waiting, one line max: "One moment." — then deliver results immediately.
- Quote rent as words: "two thousand dollars per month" — never bare digits, never "rupees".

[Conversation Flow]

Step 1 — Opening (bilingual, only first line)
Say: "Hey, thanks for calling! / Merci d'avoir appelé! I'm Max, the AI leasing assistant for {manager_name}.
Which unit or property are you calling about? / De quel logement ou propriété m'appelez-vous?"

After the caller's first word, detect language and lock. The rest of the call is monolingual.
Wait for their response.

Step 2 — Find the unit
As soon as the caller says anything identifying — unit number, building name, property name, street, city, country, any part of an address — call find_units with their words as the query. Do not ask for more info first.

While the tool runs, keep conversation going naturally. Do NOT say "searching" or "looking it up."
If the caller is clearly waiting: "One moment." (max one line) — then deliver.

Results handling:
- 0 matches → "I couldn't find a match for that. Can you tell me the building name or address?"
  → Wait for clarification. Retry find_units once.
  → If still no match: "We may not have that unit listed. Can I take your name and have someone follow up?"
- 1 match → "I found [flat_number] at [building_name] — is that the one?" (one short sentence)
  → Wait for confirmation.
- 2–5 matches → List just the unit numbers and building names. Example:
  "I found a few: Unit 4B at Maple Building, and Unit 6A at Elm Tower. Which one?"
  → Wait for caller to pick.

Step 3 — Answer what's asked
Once caller confirms a unit, STOP. Do NOT describe the unit. Wait for their question.

Answer each question with the shortest accurate response from the listing data:
- Rent → "[amount] per month"
- Availability → "Available from [date]"
- Bedrooms → "[N] bedrooms"
- Floor → "Floor [N]"
- Bathrooms, parking, laundry, pets → answer from listing data
- Data not available → "I don't have that detail — the team will follow up."

Keep answering until the caller has no more questions. Then proceed to Step 4.

Step 4 — Lead capture
Collect caller's name if not yet known: "Could I get your name?"
Then call submit_lease_lead exactly once with everything collected.

Close:
- Interested/qualified: "Our team will be in touch to arrange a viewing. Have a great day!"
- Disqualified: "Thanks for calling — have a great day!"
- No match: "I've noted your interest. The team may reach out if something comes up. Have a great day!"

[Preference-Based Browsing — Secondary Flow]
If a caller explicitly says they're looking for something (not a specific unit): "I'm looking for a 2-bedroom" / "I want something under $1,500" — use search_listings with those filters.
Present results concisely: just unit number, building name, rent, bedrooms.
Let caller ask follow-up questions — do not describe everything upfront.

[Disqualification]
Apply only rules from the confirmed listing's custom_rules:
- pets_allowed="no" + caller has pets → "That unit doesn't allow pets."
- max_occupants exceeded → "The max for that unit is [N] people."
Set qualification_status="not_qualified" + disqualifying_reason. Still capture lead.

[Lead Capture — ALL CALLS, NO EXCEPTIONS]
Call submit_lease_lead EXACTLY ONCE before ending every call, even if no unit was found.
- caller_name: REQUIRED. Ask if blank.
- listing_uuid: UUID from find_units result (blank if none confirmed — never invent)
- interested_listing_ids: all units caller asked about
- qualification_status: "qualified" / "not_qualified" / "unmatched"
- notes: what they asked about, any preferences mentioned

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not existing tenants
- listing_uuid comes from tool results only — never invent a UUID
- Never guarantee availability, pricing, or make promises
- If submit_lease_lead fails: do not retry, end politely
```

---

### Step 4 — Update tools in `_build_lease_tools`

**Remove:** `load_listings` tool (background loading is replaced by `find_units`)

**Add:** `find_units` tool:
```python
{
    "type": "apiRequest",
    "name": "find_units",
    "async": False,
    "function": {
        "name": "api_request_tool",
        "description": (
            "Find available units by any caller-stated text: unit number, building name, "
            "property name, street address, city, state, or country. "
            "Pass the caller's exact words as the query. "
            "Returns up to 5 matches: listing_uuid, flat_number, building_name, property_name, "
            "address, bedrooms, monthly_rent, available_from. "
            "After receiving results, read back only the unit/building names to the caller — "
            "do NOT describe rent, floors, or any other details until the caller confirms a unit "
            "AND explicitly asks about those details."
        ),
    },
    "url": f"{backend_url}/leasing/find-units?manager_id={manager_id or ''}&query={{{{query}}}}",
    "method": "GET",
    "body": {
        "type": "object",
        "required": ["query"],
        "properties": {
            "query": {
                "type": "string",
                "description": "The caller's words — unit number, building name, property name, address, city, etc.",
                "default": "",
            }
        },
    },
    "variableExtractionPlan": {
        "schema": {
            "type": "object",
            "properties": {
                "found": {"type": "boolean"},
                "count": {"type": "integer"},
                "units": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "listing_uuid": {"type": "string"},
                            "flat_number": {"type": "string"},
                            "building_name": {"type": "string"},
                            "property_name": {"type": "string"},
                            "address": {"type": "string"},
                            "bedrooms": {"type": "integer"},
                            "bathrooms": {"type": "integer"},
                            "floor_number": {"type": "string"},
                            "monthly_rent": {"type": "number"},
                            "available_from": {"type": "string"},
                        },
                    },
                },
            },
        }
    },
}
```

**Keep:** `search_listings` (preference-based browsing, secondary flow) + `submit_lease_lead` (unchanged)

---

### Step 5 — Let the AI generate the first message (model-generated mode)

Instead of a hardcoded `first_message`, set VAPI to model-generated mode and put the opening inspiration in the system prompt.

**In `_lease_assistant_shell`:**
- Remove the `"first_message"` field entirely (or set to `""`)
- Set `"first_message_mode": "assistant-speaks-first-with-model-generated-message"`

```python
# Remove this line:
# "first_message": "...",

# Add this line:
"first_message_mode": "assistant-speaks-first-with-model-generated-message",
```

**In the system prompt (`Step 1 — Opening`)**, replace the hardcoded instruction with inspiration-style guidance:

```
Step 1 — Opening (bilingual, only your first line)
Open the call with a warm bilingual greeting. Be inspired by this style:
"Hey, thanks for calling! / Merci d'avoir appelé! I'm Max, the AI leasing assistant for {manager_name}.
Je suis Max, l'assistant de location IA de {manager_name}.
Which unit are you inquiring about? / De quel logement souhaitez-vous vous informer?"

Generate your own natural variation — don't read this verbatim. Keep it short, warm, bilingual,
and end with the "which unit?" question. After the caller's first word, detect language and lock.
```

This way the AI produces a fresh, natural-sounding opening on every call rather than repeating the same literal string.

---

### Step 6 — Deploy

```bash
python backend/scripts/update_lease_agents.py
```

Then verify in VAPI dashboard: `firstMessageMode` is `assistant-speaks-first-with-model-generated-message`, `first_message` is absent/empty, `load_listings` tool is gone, `find_units` tool is present.

---

## Issue 2: +14382567782 Complaint Agent Not Connected

The number exists in VAPI as a phone number resource but has no assistant (`assistantId`) assigned.

### Step 1 — Find the VAPI phone number ID

Run from project root (one-time):
```python
import os, httpx
from dotenv import load_dotenv
load_dotenv("backend/.env")

resp = httpx.get(
    "https://api.vapi.ai/phone-number",
    headers={"Authorization": f"Bearer {os.environ['PRIVATE_VAPI_API']}"},
    timeout=10,
)
for n in resp.json():
    if n.get("number") == "+14382567782":
        print("id:", n["id"])
        print("assistantId:", n.get("assistantId"))
        print("name:", n.get("name"))
```

Expected: shows the number's `id` and that `assistantId` is null/missing.

### Step 2 — Connect it to the complaint assistant

```python
import os, httpx
from dotenv import load_dotenv
load_dotenv("backend/.env")

phone_number_id = "<id from Step 1>"
complaint_assistant_id = os.environ["VAPI_COMPLAINT_ASSISTANT_ID"]

resp = httpx.patch(
    f"https://api.vapi.ai/phone-number/{phone_number_id}",
    headers={
        "Authorization": f"Bearer {os.environ['PRIVATE_VAPI_API']}",
        "Content-Type": "application/json",
    },
    json={"assistantId": complaint_assistant_id},
    timeout=10,
)
print(resp.status_code, resp.json())
```

Expected: 200 response, `assistantId` is now set.

### Step 3 — DB tracking

Check if the number is in `twilio_number_pool`:
```sql
SELECT * FROM twilio_number_pool WHERE phone_number = '+14382567782';
```

If not, insert it:
```sql
INSERT INTO twilio_number_pool (phone_number, vapi_phone_number_id, status, notes)
VALUES ('+14382567782', '<vapi_id_from_step1>', 'assigned', 'second complaint line');
```

### Step 4 — Decide: secondary or replacement complaint number

- If **secondary** (both +14382314283 and +14382567782 active): no `.env` change needed. Document in `CODEBASE_CONTEXT.md`.
- If **replacement** (new primary complaint number): update `VAPI_COMPLAINT_NUMBER_ID` and `VAPI_COMPLAINT_PHONE_NUMBER` in Render's environment variables, and update `CODEBASE_CONTEXT.md`.

### Step 5 — Verify

Call +14382567782. The complaint agent (Alex) should answer:
> "Hi, this is Alex — how can I help you today?"

---

## Implementation Checklist

### Lease Agent
- [x] `leasing.py` — add `GET /leasing/find-units` endpoint
- [x] `vapi_agent_config.py` — add `manager_name` param to `build_lease_config`
- [x] `vapi_agent_config.py` — update `_LEASE_CONTEXT_BLOCK` to include manager name
- [x] `vapi_agent_config.py` — rewrite `_LEASE_SYSTEM_PROMPT_BASE` (query-first, concise)
- [x] `vapi_agent_config.py` — update `_build_lease_tools`: add `find_units`, remove `load_listings`
- [x] `vapi_agent_config.py` — remove `first_message`, set `first_message_mode` to `assistant-speaks-first-with-model-generated-message` in `_lease_assistant_shell`; add opening inspiration to system prompt
- [x] `vapi_provisioning.py` — fetch manager name, pass to `build_lease_config`
- [x] `update_lease_agents.py` — fetch manager names, pass to `build_lease_config`
- [x] Run `python backend/scripts/update_lease_agents.py`
- [ ] Verify: call lease line — Max answers bilingually, asks "which unit?"

### Complaint Phone
- [ ] Run Step 1 script — find VAPI phone number ID for +14382567782
- [ ] Run Step 2 script — connect to `VAPI_COMPLAINT_ASSISTANT_ID`
- [ ] Check/update `twilio_number_pool` in DB
- [ ] Decide secondary vs replacement, update `.env` if replacement
- [ ] Verify: call +14382567782 — Alex answers
