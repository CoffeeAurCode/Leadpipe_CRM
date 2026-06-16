# Plan: Align Lease Agent (Max) with LEASE_AGENT_FLOW.md

## Goal
Rewrite the lease agent's system prompt in `vapi_agent_config.py` (`build_lease_config`) so Max follows the two-branch conversation flow defined in `LEASE_AGENT_FLOW.md`. Dialogues in the flow doc are inspiration only — Max should speak naturally, not recite them verbatim.

---

## What Changes (and What Doesn't)

**Unchanged:**
- All VAPI tool definitions (`find_units`, `search_listings`, `submit_lease_lead`)
- All backend endpoints — no route changes
- Voice / transcriber / model config
- Bilingual policy, currency policy, no-volunteering-info policy

**Changed:**
- System prompt in `build_lease_config` — full rewrite of the conversation behaviour section

---

## New Conversation Flow to Encode in System Prompt

### Branch Decision (happens after greeting)

After the greeting, Max must classify the caller:
- **Branch A — Specific unit:** Caller names a unit number, building, or street address → go to Qualification Flow
- **Branch B — General inquiry:** Caller has no specific unit in mind → go to Discovery Flow

---

### Branch A — Specific Unit

1. Acknowledge the unit and confirm it with the caller ("Got it — Apartment 4B on Rue des Érables, right?")
2. Once confirmed → proceed directly to **Qualification Flow**

---

### Branch B — Discovery Flow (5 questions, one at a time)

Max collects preferences in this order. Ask one question, wait for the answer, then ask the next.

| Step | What to collect | Example phrasing (inspiration) |
|------|----------------|-------------------------------|
| Q1 | City | "Which city or neighbourhood are you looking in?" |
| Q2 | Area / neighbourhood | "Any particular area or street within [city]?" |
| Q3 | Unit size | "What size are you looking for — a 3½, a 4½, or do you prefer to say bedrooms?" |
| Q4 | Monthly budget | "What's the highest monthly rent you're comfortable with?" |
| Q5 | Move-in date | "When are you looking to move in?" |

After Q5 → call `search_listings` silently (CRM / inventory lookup) using the collected params.

**Match found:**
- Pick the best matching unit
- Pitch it naturally: name the size, street, and monthly rent
- Ask if that sounds interesting
  - **Caller says yes** → Begin Qualification Flow
  - **Caller says no** → try the next match in results; loop until results exhausted
  - **Results exhausted** → No-match path

**No match:**
- Acknowledge nothing is available right now
- Offer to pass their info to the team
- Collect: name + phone + email (what they're willing to share)
- Call `submit_lease_lead` with `qualification_status = "unmatched"` and collected contact info
- Close warmly

---

### Qualification Flow (shared by both branches)

Collect the following, one at a time, in a natural conversational order:

1. Employment / income source ("Just to help us match you — what do you do for work?")
2. How many people will be living in the unit
3. Any pets
4. Smoking / non-smoking preference
5. Name, phone, email (confirm what caller is comfortable sharing)

After all collected → call `submit_lease_lead` with `qualification_status = "qualified"` and all data.

Close: let them know the team will be in touch, and thank them.

---

## System Prompt Changes — Key Rules to Add

These are the concrete rules that encode the flow above:

```
1. After the greeting, listen for whether the caller mentions a specific unit/address.
   - If yes: confirm the unit, then move directly to the qualification questions.
   - If no: run the 5-question discovery sequence (city → area → size → budget → move-in),
     then call search_listings silently.

2. When pitching a unit (after search_listings), state only: the size (Quebec notation), 
   the street name, and the monthly rent. Nothing else unprompted.

3. If the caller declines a pitched unit, pitch the next result. If no more results exist,
   take the no-match path.

4. On no-match: acknowledge availability, offer to pass their info to the team, collect
   contact details, then submit an unmatched lead.

5. Qualification questions are asked one at a time after either branch converges.
   Never ask all qualification questions at once.

6. Never say "let me put you through to the team" or imply a live transfer — there is none.
   Use "I'll make sure someone from the team reaches out."
```

---

## Files to Edit

| File | Change |
|------|--------|
| `backend/app/services/vapi_agent_config.py` | Rewrite the system prompt body inside `build_lease_config` — keep all tool definitions unchanged |
| `backend/scripts/update_lease_agents.py` | Run after editing config to push to all active VAPI assistants |

---

## Deployment Step

After editing `vapi_agent_config.py`, run:
```
python backend/scripts/update_lease_agents.py
```
This pushes the updated system prompt to every active per-manager lease assistant via HTTP PATCH to `api.vapi.ai`.

---

## Testing Checklist

- [ ] General inquiry call → Max asks Q1–Q5 in order → calls `search_listings` → pitches a unit
- [ ] Caller declines pitched unit → Max tries next result
- [ ] No results → Max collects contact and submits unmatched lead
- [ ] Caller names a specific unit upfront → Max skips discovery and goes straight to qualification
- [ ] Qualification questions come one at a time (not as a list)
- [ ] `submit_lease_lead` fires with correct `qualification_status` in both paths
- [ ] No hardcoded dialogue lines appear verbatim in Max's speech
