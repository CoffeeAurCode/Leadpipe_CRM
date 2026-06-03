# Lease Agent Improvement Plan

**Date:** 2026-06-03  
**Trigger:** Test call revealed agent was too rushed — dumped all units immediately without gathering preferences, language opener was forced-bilingual, no graceful out-of-scope handling.

---

## Problems Identified

### P1 — Forced bilingual first message
`first_message` used slash-format EN/FR opener even when caller's language was obvious from
context. Same anti-pattern as complaint agent (now fixed). Makes the first turn long and rigid.

### P2 — No role explanation for callers who don't know
Caller picking up the phone doesn't always know what "the leasing line" does. There was no
graceful path for a caller who wanted maintenance, billing, or something else. Agent would
apologise but not explain its own purpose clearly.

### P3 — Agent dumped all units immediately (PATH A)
When `load_listings` returned `has_more=false` (small portfolio ≤10 units), the system prompt
told the agent to answer "what do you have?" by listing all units. A caller saying "Hi, what
do you have?" got a wall of unit descriptions before sharing a single preference.

### P4 — `search_listings` was large-portfolio-only
The tool description said "Filtered search for large portfolios." For a small portfolio with
`has_more=false`, the agent was supposed to filter manually from `load_listings` results —
but had no guidance on HOW to filter. Result: no filtering at all, all units presented.

### P5 — Custom rules checked AFTER unit was presented
`pets_allowed`, `non_smoking`, `max_occupants` were checked during qualification — after
the agent already committed to a unit with the caller. If the unit didn't allow pets and the
caller had a dog, the agent would present it, then disqualify. Bad experience.

### P6 — Preference-first vs query-first tension not resolved
PATH A had no mechanism to delay presentation until preferences were collected.
PATH B had the right instinct (gather preferences → search) but only applied to large portfolios.
Neither path said: gather ALL relevant preferences in background while query runs, THEN present.

### P7 — Lead logging not universal for all call outcomes
The `[Lead Capture]` section implied logging happened for matched/qualified callers.
Out-of-scope callers, early hang-ups, and callers with no matching unit were not explicitly
mandated to be logged with their stated preferences.

---

## Fixes Applied

### Fix 1 — Language Policy
Replaced `[Language Policy — STRICT]` with `[Language Policy]`:
- No forced bilingual opener on every call
- Detect from first words and lock immediately
- Only offer both if genuinely ambiguous ("English or French?")
- Tool data always in English regardless of call language

### Fix 2 — First Message
Old: `"Hey, thanks for calling — I'm Max. What are you looking for? / Bonjour, je suis Max. Qu'est-ce que vous cherchez?"`  
New: `"Hi, this is Max — I help people find rental units here. What are you looking for today?"`

Why: English-only, explains role upfront so any caller knows immediately what Max does.

### Fix 3 — Out-of-Scope Handling
New `[Out-of-Scope Calls]` section:
- Politely explains Max's role if caller asks about maintenance/billing/complaints
- Directs them to property management team
- Asks if anything on the leasing side can be helped
- If not: captures name, logs lead with notes on what they called about

### Fix 4 — Preference-First Flow (replaces Two Paths)
New `[Background Query Strategy]`:
- `load_listings` still fires async on first message (unchanged)
- Agent NEVER presents units immediately, regardless of `has_more` value
- As soon as bedrooms OR budget is known: fires `search_listings` async
- Both tools run in background while agent continues gathering preferences
- Units are only presented AFTER: (a) results available AND (b) at least one preference collected

Old PATH A ("dump all units for small portfolios") is completely removed.
The `has_more` flag is now irrelevant to when units get presented — preferences always come first.

### Fix 5 — Custom Rules Filtering (Agent-Side, Silent)
New `[Custom Rules Filtering]` section:
- After results arrive, agent filters the list before presenting
- Pets: exclude `pets_allowed="no"` units if caller has pets
- Large pets: exclude `pets_allowed="small_only"` units
- Smoking: exclude `non_smoking=true` units if caller smokes
- Occupancy: exclude units where stated occupants > `max_occupants`
- Filtering is silent — caller never knows a unit was excluded
- These checks happen BEFORE presentation, not during qualification

### Fix 6 — search_listings Now Universal
Tool description updated: `search_listings` is no longer "large portfolios only."
It fires as soon as bedrooms OR budget is known, for any portfolio size.
`load_listings` provides the initial count and fallback data; `search_listings` is the primary
source for presenting units once preferences are known.

### Fix 7 — Lead Capture for ALL Calls
`[Lead Capture]` renamed to `[Lead Capture — ALL CALLS, NO EXCEPTIONS]`.
`submit_lease_lead` must be called for: matched, unmatched, disqualified, and out-of-scope callers.
All stated preferences must be included in `notes` so the team can follow up meaningfully.

---

## Conversation Flow — After Fix

```
Call connects
│
├── Max: "Hi, this is Max — I help people find rental units here. What are you looking for today?"
│   [load_listings fires async silently]
│
├── Caller speaks
│   ├── Out-of-scope (maintenance/billing) → explain role, offer leasing help, log lead
│   └── Leasing inquiry → continue
│
├── Gather preferences naturally (one question per turn):
│   ├── Size (bedrooms)?          [once known → search_listings fires async]
│   ├── Budget?                   [if known → search_listings fires with budget]
│   ├── Move-in timeline?
│   ├── Occupants?
│   ├── Pets?                     ← asked early; affects filtering
│   └── Specifics (parking, floor, laundry)?
│
│   [search_listings resolves in background during above conversation]
│
├── Filter results silently (custom rules: pets, smoking, occupancy)
│
├── Present 1–3 best-fit units (after preferences + results both available)
│   ├── 1 match → describe directly
│   ├── 2–5 matches → brief list, ask which interests them
│   ├── 6+ matches → ask one more narrowing question, show top 3
│   └── 0 matches → offer closest; if nothing → honest close + lead logged
│
├── Qualification (after interest confirmed):
│   ├── Move-in timeline (if not collected)
│   ├── Landlord aware? (risk flag)
│   ├── Unit questions (answer from listing data)
│   ├── Employment status
│   └── Any remaining disqualifying custom_rules checks
│
├── Get caller name (at natural pause, not at the very end)
│
└── submit_lease_lead (ALWAYS — one call, all preferences included)
    └── Close call
```

---

## File Changes

| File | Change |
|---|---|
| `backend/app/services/vapi_agent_config.py` | Full rewrite of `_LEASE_SYSTEM_PROMPT_BASE` |
| `backend/app/services/vapi_agent_config.py` | `first_message` in `_lease_assistant_shell` |
| Run `backend/scripts/update_shared_agents.py` | Push new config to VAPI |

---

## Testing Checklist

- [ ] English greeting → agent stays English throughout
- [ ] French greeting ("bonjour") → agent switches to French and stays
- [ ] Caller says "hi" (ambiguous) → agent responds in English, doesn't force bilingual
- [ ] Caller calls about maintenance → agent explains leasing role, logs lead
- [ ] Small portfolio (≤10 units): agent asks preferences BEFORE listing any units
- [ ] Caller says "what do you have?" → agent asks size/budget first, doesn't dump units
- [ ] Caller has pets → agent only presents pet-friendly units (silent filter)
- [ ] Caller has no preference on budget → agent notes it, moves on without pushing
- [ ] All callers get a lead logged (matched, unmatched, wrong-number)
- [ ] Multiple interested units → all UUIDs appear in `interested_listing_ids`
- [ ] No awkward pauses; tools run in background during natural conversation
