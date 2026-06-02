# Plan: Lease Agent v2 — Conversational, Scale-Aware, Interruption-Ready

## 1. Goals

The current lease agent works (after the `load_listings` fix) but the conversation is rigid —
a numbered list of questions read top-to-bottom. The upgraded agent should:

- **Follow the script's intent, not its words.** All 7 questions still get asked, but naturally,
  in the flow of conversation — not recited like a form.
- **Be caller-centric.** Discover what the caller actually wants (bedroom count, budget, move-in
  window), then suggest specific units that match. The caller drives; Max follows.
- **Allow interruptions cleanly.** If Max is mid-sentence and the caller talks, Max stops,
  addresses what the caller said, then continues from where the conversation left off.
- **Scale gracefully.** If the manager has a small portfolio (≤10 listings), load everything
  immediately while talking. If the portfolio is large (>10 listings), gather preferences first
  and run a filtered search(do the best with the preferences you have) — ideally while still talking so there's no waiting pause.
- **Save the lead** with all collected data before ending.

---

## 2. Current State

| Component | Current behaviour |
|---|---|
| `load_listings` tool | Fires once after first caller message, returns ALL listings regardless of count |
| System prompt | Linear step-by-step flow (1–11), no count-awareness, no preference-gathering |
| Interruption | VAPI `stop_speaking_plan: {numWords: 2}` handles the signal; prompt doesn't instruct recovery |
| Qualification questions | Present (Q1–Q7) but asked in fixed order, not woven into conversation |
| Scale problem | If manager has 50 listings, the full JSON is loaded and shoved into LLM context |

The `load_listings` architecture is correct. This plan extends it — not replaces it.

---

## 3. Architecture: Two Conversation Paths

### Path A — Small portfolio (≤ THRESHOLD listings)

```
Caller dials in
     │
     ▼
Max greets caller + fires load_listings ASYNC (threshold-aware)
     │                         │
     │ (agent is talking)      │ (HTTP call in flight)
     │                         ▼
     │              Backend returns: count=5, has_more=false, listings=[...]
     │
     ▼
Caller says first preference / question
     │
     ▼
Max has all listing data in context — matches LLM-side, presents best fit
     │
     ▼
Preference discovery + Q1–Q7 woven into conversation
     │
     ▼
submit_lease_lead
```

Max buys time by continuing the opening exchange while the tool resolves. By the time the
caller answers "which unit are you looking for?", listings are already in context.

### Path B — Large portfolio (> THRESHOLD listings)

```
Caller dials in
     │
     ▼
Max greets caller + fires load_listings ASYNC (returns count only, no listings)
     │                         │
     │ (agent is talking)      │ (lightweight count-only response in ~200ms)
     │                         ▼
     │              Backend returns: count=28, has_more=true, listings=[]
     │
     ▼
Max discovers preferences: "What size unit are you looking for?" / "What's your monthly budget?"
     │
     ▼  (fires search_listings ASYNC with bedrooms + budget while confirming preferences back to caller)
     │
     ▼
Results arrive; Max presents 2–3 matching units
     │
     ▼
Preference discovery + Q1–Q7 woven into conversation
     │
     ▼
submit_lease_lead
```

The `search_listings` tool fires while Max is still talking (e.g. "Got it — let me find something
in that range for you."). By the time the caller responds, results are ready.

**THRESHOLD = 10** (configurable constant in backend). Rationale: 10 units takes ~45 seconds to
read aloud in full detail, which is too long. The threshold is about what's practical to present
verbally, not what fits technically.

---

## 4. Changes Required

### 4a. Backend — `leasing.py`

#### Change 1: Add threshold logic to `GET /leasing/listings-for-agent`

Current endpoint returns all listings unconditionally. New behaviour:

```python
LISTING_THRESHOLD = 10

@router.get("/listings-for-agent")
async def listings_for_agent(
    manager_id: Optional[str] = Query(None),
    db: Client = Depends(get_service_db),
):
    try:
        # Count query first (cheap)
        count_q = db.table("lease_listings").select("uuid", count="exact").eq("is_active", True)
        if manager_id:
            count_q = count_q.eq("manager_id", manager_id)
        count_result = count_q.execute()
        total = count_result.count or 0

        if total > LISTING_THRESHOLD:
            # Large portfolio — return count signal only; agent will use search_listings
            return {"count": total, "has_more": True, "listings": []}

        # Small portfolio — return full listing details
        q = (
            db.table("lease_listings")
            .select("uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                    "square_footage, included_utilities, parking, laundry, "
                    "flats!inner(bedrooms, floor_number, address, buildings(name, address))")
            .eq("is_active", True)
        )
        if manager_id:
            q = q.eq("manager_id", manager_id)
        results = q.order("created_at").execute()

        listings = _format_listings(results.data or [])
        return {"count": len(listings), "has_more": False, "listings": listings}

    except Exception as e:
        print(f"[ERROR] listings_for_agent: {e}")
        return {"count": 0, "has_more": False, "listings": []}
```

Add `_format_listings(rows)` helper to avoid duplicating the row-to-dict logic between
this endpoint and the new search endpoint below.

#### Change 2: New `GET /leasing/search-listings` filtered endpoint

```python
@router.get("/search-listings")
async def search_listings(
    manager_id: Optional[str] = Query(None),
    bedrooms: Optional[int] = Query(None),
    budget_max: Optional[float] = Query(None),
    available_before: Optional[str] = Query(None),   # ISO date string
    db: Client = Depends(get_service_db),
):
    """
    VAPI tool endpoint — filtered listing search. Used when portfolio is too large
    to load in full. Always returns HTTP 200.
    """
    try:
        q = (
            db.table("lease_listings")
            .select("uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                    "square_footage, included_utilities, parking, laundry, "
                    "flats!inner(bedrooms, floor_number, address, buildings(name, address))")
            .eq("is_active", True)
        )
        if manager_id:
            q = q.eq("manager_id", manager_id)
        if budget_max:
            q = q.lte("monthly_rent", budget_max)
        if bedrooms is not None:
            q = q.eq("flats.bedrooms", bedrooms)
        if available_before:
            q = q.lte("available_from", available_before)

        results = q.order("monthly_rent").limit(5).execute()
        listings = _format_listings(results.data or [])
        return {"count": len(listings), "listings": listings}

    except Exception as e:
        print(f"[ERROR] search_listings: {e}")
        return {"count": 0, "listings": []}
```

Note: `limit(5)` caps the result intentionally. Max can always ask the caller to narrow further
if 5 results are too many to present verbally.

---

### 4b. `vapi_agent_config.py` — Tools

#### Change 1: `load_listings` → `async: True`

Existing tool, one change: `"async": True`. This fires the API call the moment the caller's
first message is transcribed, without pausing Max's speech. The response lands in context by
the time Max needs to reference listings.

Also add `has_more` to the `variableExtractionPlan` schema so the agent can read it:

```python
"variableExtractionPlan": {
    "schema": {
        "type": "object",
        "properties": {
            "count": {"type": "integer"},
            "has_more": {"type": "boolean"},
            "listings": {
                "type": "array",
                "items": { ... }  # unchanged
            },
        },
    }
},
```

#### Change 2: New `search_listings` tool

Add to `_build_lease_tools()`:

```python
{
    "type": "apiRequest",
    "name": "search_listings",
    "async": True,
    "function": {
        "name": "api_request_tool",
        "description": (
            "Filtered listing search. Use this ONLY when load_listings returned has_more=true "
            "(large portfolio). Call it once you have at least one preference from the caller "
            "(bedrooms OR budget_max). Pass bedrooms and/or budget_max as query params. "
            "Returns up to 5 best-matching listings. Do NOT call before collecting any preferences."
        ),
    },
    "url": (
        f"{backend_url}/leasing/search-listings?manager_id={manager_id or ''}"
        "&bedrooms={{bedrooms}}&budget_max={{budget_max}}"
    ),
    "method": "GET",
    "body": {
        "type": "object",
        "required": [],
        "properties": {
            "bedrooms": {"type": "integer", "description": "Desired bedroom count", "default": 0},
            "budget_max": {"type": "number", "description": "Max monthly rent caller mentioned", "default": 0},
        },
    },
    "messages": [
        {
            "type": "request-start",
            "content": "Let me look for units that match that — give me just a second.",
        }
    ],
    "variableExtractionPlan": {
        "schema": {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "listings": {
                    "type": "array",
                    "items": { ... }  # same shape as load_listings items
                },
            },
        }
    },
},
```

---

### 4c. System Prompt — `_LEASE_SYSTEM_PROMPT_BASE`

Full replacement. The new prompt has three structural differences from the current one:

1. **No numbered steps.** Conversation sections replace the numbered flow. The agent reasons about
   where it is in the conversation, not what step number it's on.

2. **Interruption recovery block.** Explicit instruction: if the caller speaks mid-response, address
   what they said first, then resume from the last unanswered point.

3. **Count-aware listing strategy.** Two branches in the "Finding a Unit" section depending on
   whether `has_more` is true or false.

Full new prompt text is in **Section 5** below.

---

## 5. New System Prompt (full text)

```
[Identity]
You are Max, a friendly and professional AI leasing assistant.
You handle inbound calls from prospective tenants asking about rental units.
You do NOT handle complaints or maintenance — if someone calls about that, apologise and
ask them to call the maintenance line.

[Language Policy — STRICT]
The opening greeting is the only bilingual utterance. After the caller's first word, lock to
their language for the rest of the call.
- Caller speaks English → ENGLISH ONLY for all remaining turns
- Caller speaks French  → FRENCH ONLY for all remaining turns
- Unclear → ask "English or French? / Anglais ou français?" then lock immediately

Forbidden after language lock: mixing languages in one sentence, appending translations,
using slash-format (English / French), switching mid-call for any reason.
Tool data always in English, even if caller speaks French.

[Style]
Warm, conversational, professional. Voice-friendly — short sentences, natural phrasing.
One question at a time. Listen for what the caller actually wants before presenting options.
Never mention listing_uuid, property_group_id, or internal tool names.
Quote rent as words: "two thousand dollars per month", never bare digits.

[Interruption Handling]
If the caller speaks while you are talking, stop immediately.
Address what they said — answer their question, or acknowledge their preference.
Then resume from the last point the conversation had not yet covered.
Never restart a section you already completed. Never ignore what the caller said.
Example: You are mid-way through describing a unit's parking situation.
Caller interrupts: "Does it have laundry?" → Answer laundry question → then continue
with what was next after parking.

[Conversation Opening]
Greet the caller and ask what they're looking for. Keep it open:
"Hey, thanks for calling! I'm Max, your AI leasing assistant. What can I help you find today?"
or if they mentioned a specific unit on the way in: "Are you asking about a particular unit,
or would you like to hear what we have available?"

Do NOT ask "which unit are you inquiring about?" as the only opener — many callers don't know
the flat number yet. Let them lead.

[Finding a Unit — Two Paths]

Immediately after the caller's first message, fire load_listings (async).
The call continues while the tool resolves — do NOT pause or say you are loading.

When the result arrives, check has_more:

PATH A — has_more = false (manageable portfolio, ≤10 listings):
You now have the full listings array. Use it to:
- Match the caller's stated preference if they mentioned one
- Answer "what do you have?" by briefly describing all units: flat number, bedrooms, rent
- Suggest the best match based on anything the caller has told you so far (budget, size, floor)

Present matched units naturally:
"We have a two-bedroom on the third floor — flat B202, available from June 1st
for thirty-eight thousand a month. That one also includes parking. Does that sound interesting?"

If multiple units match: briefly describe each (flat number + bedrooms + rent), then ask
which they'd like to hear more about.

PATH B — has_more = true (large portfolio):
You got a count but no listings. Start gathering preferences:
"We have quite a few units available. To point you to the best ones — what size are
you looking for? Like one bedroom, two, three?"
<wait — note bedrooms preference>
"And do you have a rough monthly budget in mind?"
<wait — note budget>

Once you have at least one preference (bedrooms OR budget), fire search_listings async
with those values. While it's in flight, naturally confirm:
"Got it — let me find something that fits. Just to confirm, you're looking for a
[N]-bedroom around [budget] a month, is that right?"
<caller confirms — results should be back by now>

Present results the same way as Path A.

If count = 0: say "We don't have any units available right now." Get caller's name,
call submit_lease_lead with qualification_status="unmatched", notes="No listings at time of call".

If load_listings errors: say "I'm having a bit of trouble pulling up our listings right now."
Ask for caller's name. Call submit_lease_lead with qualification_status="unmatched",
notes="Listing load failed". End politely.

[Qualification Questions — Weave, Don't Recite]

Once a specific unit is identified and the caller is interested, collect the following
information. Ask them in the order that fits the natural conversation — if the caller
volunteers something, note it and skip that question.

Q1 — Move-in date
"When are you looking to move in?"
Store as move_in_timeline.

Q2 — Current landlord awareness
"Is your current landlord aware that you're looking for a new place?"
Store as landlord_aware. If no: note it (risk flag for manager) but do NOT disqualify.

Q3 — Questions about the unit
"Do you have any questions about the unit itself?"
Answer from listing data: monthly_rent, bedrooms, floor_number, available_from, address,
square_footage, included_utilities, parking, laundry.
Only mention fields that are set. If asked something not in the data, say the team will follow up.
Keep answering until the caller says they have no more questions.

Q4 — Employment
"Are you currently employed — full-time, part-time, or between jobs at the moment?"
Store as employment_status.

Q5 — Occupants
"How many people would be moving in with you?"
Store as occupants.
If custom_rules.max_occupants is set and occupants > max_occupants:
  Disqualify: "Unfortunately the maximum occupancy for this unit is [N] people."
  qualification_status = "not_qualified", disqualifying_reason = "exceeds max occupancy"
  Skip to lead capture.

Q6 — Pets
"Do you have any pets?"
Store as has_pets.
If custom_rules.pets_allowed = "no" AND caller has pets:
  Disqualify: "Unfortunately this unit doesn't allow pets."
  qualification_status = "not_qualified", disqualifying_reason = "pets not allowed"
  Skip to lead capture.
If custom_rules.pets_allowed = "small_only" AND caller has large pets:
  Disqualify: "This unit only allows small pets."
  qualification_status = "not_qualified", disqualifying_reason = "large pets not allowed"
  Skip to lead capture.

Q7 — Non-Smoking (ONLY if custom_rules.non_smoking = true)
"Just so you know, this is a non-smoking unit — inside and on the property. Is that okay?"
Store as non_smoking_ok.
If caller says no:
  Disqualify: "Unfortunately we can't accommodate that for this unit."
  qualification_status = "not_qualified", disqualifying_reason = "smoker"
  Skip to lead capture.
If custom_rules.non_smoking is false or not set: skip entirely.

[Name Collection]
At any point after a specific listing is confirmed, ask:
"Could I get your full name?"
Store as caller_name. REQUIRED — never submit without it. If caller refuses: use "Anonymous".

[Lead Capture]
Call submit_lease_lead EXACTLY ONCE, before ending the call, with all collected data:
- caller_name
- listing_uuid (from load_listings or search_listings results — never invented)
- interested_listing_ids: [listing_uuid] if a match was found, else []
- bedrooms, move_in_timeline, occupants (from conversation + listing)
- budget_max: 0 if not mentioned
- qualification_status: "qualified" / "not_qualified" / "unmatched"
- disqualifying_reason: fill if not_qualified
- qualifying_answers: JSON string — keys: landlord_aware, employment_status, has_pets,
  non_smoking_ok (include non_smoking_ok only if Q7 was asked)
- notes: any risk flags (e.g. "landlord unaware — possible mid-lease situation")

[Call Close]
Qualified: "Our team will be in touch shortly to arrange a viewing. Have a great day!"
Not qualified or unmatched: "Thank you for calling. Have a great day!"

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not existing ones.
- Phone number captured from call metadata automatically.
- listing_uuid must come from tool results. Never invent a UUID.
- Never guarantee availability or make promises.
- If submit_lease_lead fails: do not retry. End politely.
- caller_name is mandatory before submit_lease_lead under any circumstances.

[Tools]
load_listings — Fires async on first caller message. Returns all listings if portfolio is small,
               or count + has_more=true if large. Call once only.
search_listings — Filtered search for large portfolios. Call once you have bedrooms or budget_max.
submit_lease_lead — Save the lead. Call exactly once before ending the call.
```

---

## 6. Conversation Flow Examples

### Example A — Small portfolio, caller knows what they want

```
Max:    "Hey, thanks for calling! I'm Max, your AI leasing assistant.
         What can I help you find today?"
         [load_listings fires async]

Caller: "I'm looking for a 3 bedroom."

        [load_listings result arrives: count=5, has_more=false, C301 matches]

Max:    "I have a three-bedroom available right now — flat C301, third floor,
         available from the 22nd for sixty-five thousand a month. Sounds like it
         could work?"

Caller: "Yeah. Does it have parking?"

Max:    "It does — indoor parking is included. Any other questions about the unit?"

Caller: "No, that's it."

Max:    "Could I get your full name?"

Caller: "Priya Mehta."

Max:    "When are you looking to move in, Priya?"
...
```

### Example B — Large portfolio, preference gathering

```
Max:    "Hey, thanks for calling! I'm Max. What can I help you find today?"
        [load_listings fires async]

Caller: "Just browsing what you have."

        [load_listings result arrives: count=24, has_more=true, listings=[]]

Max:    "We have quite a few units available. What size are you thinking —
         one bedroom, two, three?"

Caller: "Probably two bedrooms."
        [search_listings fires async: bedrooms=2]

Max:    "And do you have a rough monthly budget in mind?"

Caller: "Around forty thousand."
        [budget noted; results likely back]

Max:    "Got it. We have a couple of two-bedrooms in that range — B202 on the
         second floor for thirty-eight thousand, and D404 for forty-two thousand.
         D404 includes parking. Which one sounds more interesting?"
...
```

### Example C — Caller interrupts mid-description

```
Max:    "B202 is on the second floor, about 750 square feet, available from
         June 1st. Heat and water are included in the—"

Caller: "Does it have in-unit laundry?"

Max:    "It does — there's an in-unit washer and dryer. So as I was saying,
         heat and water are included in the rent, and the monthly is thirty-eight
         thousand. Any other questions about the unit?"
```

---

## 7. Code Changes Summary

| File | Change |
|---|---|
| `backend/app/routes/leasing.py` | Add `LISTING_THRESHOLD = 10` constant; add count-only path to `listings_for_agent`; extract `_format_listings()` helper; add new `search_listings` endpoint |
| `backend/app/services/vapi_agent_config.py` | `load_listings` → `async: True`, add `has_more` to variableExtractionPlan; add `search_listings` tool to `_build_lease_tools()`; replace `_LEASE_SYSTEM_PROMPT_BASE` entirely |
| `backend/scripts/update_lease_agents.py` | No changes — run as-is after config update |

No frontend changes. No DB migrations. No new tables.

---

## 8. Deployment Steps

1. Update `leasing.py` — add threshold logic + `search_listings` endpoint
2. Deploy backend (Render auto-deploys on push, or `git push`)
3. Verify endpoints:
   ```bash
   # Small portfolio test
   curl "https://tenant-management-mvp.onrender.com/leasing/listings-for-agent?manager_id=<id>"
   # Expected: count=5, has_more=false, listings=[...]

   # Large portfolio test (temporarily set LISTING_THRESHOLD=2 in code, revert after)
   curl "https://tenant-management-mvp.onrender.com/leasing/listings-for-agent?manager_id=<id>"
   # Expected: count=5, has_more=true, listings=[]

   # Filtered search
   curl "https://tenant-management-mvp.onrender.com/leasing/search-listings?manager_id=<id>&bedrooms=2"
   # Expected: count=2, listings=[B202, D404]
   ```
4. Update `vapi_agent_config.py` — new tools + new prompt
5. Run `python backend/scripts/update_lease_agents.py`
6. Verify in VAPI dashboard: `load_listings` + `search_listings` present, `find_listing` absent

---

## 9. Test Scenarios

| Test | Caller input | Expected Max behaviour |
|---|---|---|
| Flat by number | "I'm asking about C301" | Path A: loads C301 details, presents it |
| By bedroom count | "3 bedroom" | Path A: finds C301, presents it |
| By budget | "Under 40k a month" | Path A: suggests A101 and B202 |
| Browse all | "What do you have?" | Path A: brief list of all 5 units |
| Large portfolio — bedroom | "2 bedrooms" (with 24 listings) | Path B: search_listings, returns top matches |
| Large portfolio — budget | "Under 50 thousand" (with 24 listings) | Path B: search_listings with budget_max=50000 |
| Interruption mid-sentence | Interrupt with "Does it have parking?" | Max answers, resumes description |
| Disqualify — pets | Asks about unit with pets=no, has dog | Max informs no pets, skips to lead |
| Disqualify — occupants | Unit max=2, says 5 people moving in | Max informs occupancy limit, skips to lead |
| No listings | (no active listings) | Max says unavailable, gets name, submits unmatched |
| Tool error | (simulate 500 from backend) | Max apologises, gets name, submits unmatched |
| Full qualified call | Complete all 7 Qs, no disqualifiers | Lead saved as qualified with all fields |

---

## 10. Open Questions (Decide Before Implementing)

1. **Threshold value.** 10 is proposed. Should it be hardcoded in `leasing.py` or pulled from
   a config/env var? Env var makes it easier to tune without a deploy.

2. **search_listings limit.** Currently proposed at 5. If 5 results are still too many to present
   verbally, reduce to 3. If the caller wants more options, they can narrow preferences.

3. **Budget collection in Path B.** The plan asks for bedrooms then budget. If the caller gives
   only one preference (e.g. just bedrooms), is that enough to fire search_listings? Proposed:
   yes — any single preference is enough. The filter is additive, not required.

4. **async tool behaviour confirmation.** VAPI async tools inject the result on the *next turn*.
   The plan assumes this is fast enough. If the backend is cold (Render cold start), the result
   may arrive 3–5 seconds late. Mitigate by keeping the backend warm (already done via cron/health
   check calls), or add a `request-response-delayed` message to `load_listings` as a fallback.
