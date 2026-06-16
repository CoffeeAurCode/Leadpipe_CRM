# Plan: Lease Agent v3 — Natural Conversational Flow

## 1. Problems Being Solved

Based on live testing of v2:

| # | Symptom | Root Cause |
|---|---|---|
| P1 | First message is too long; caller can't interrupt naturally | `first_message` is bilingual + full sentence — ~20 words, ~4 seconds of TTS |
| P2 | After first caller word, agent says "let me check that" or "give me a second" then goes silent | `load_listings` has a `request-start` message that fires even though `async: True`; LLM also generates filler text |
| P3 | After the filler, the conversation is broken — agent can't recover smoothly | System prompt doesn't explicitly forbid filler on first turn; LLM defaults to acknowledgement phrases |
| P4 | Multiple-unit handling is not clear enough | System prompt mentions it but doesn't have explicit 1/2–5/>5/0 branching logic |
| P5 | No distinct "polite wait" moment when all preferences are collected and search is running | System prompt only handles the mid-collection case |

---

## 2. Root Cause Analysis

### P1 — Long first_message

Current value (105 characters):
```
"Hey, thanks for calling! I'm Max, your AI leasing assistant. What can I help you find today? / Bonjour, merci d'appeler! Je suis Max, votre assistant de location IA. Comment puis-je vous aider aujourd'hui?"
```

VAPI's `stop_speaking_plan: {numWords: 2}` applies to LLM-generated speech. For a long pre-set `first_message`, interruption is technically possible but the caller has to interrupt mid-sentence, which feels wrong. Fix: make first_message short enough to end before the caller reasonably wants to speak.

### P2 — Tool filler

`load_listings` is configured with:
```python
"async": True,
"messages": [{"type": "request-start", "content": "Give me a second to check what we have available."}]
```

VAPI fires the `request-start` message the instant the LLM decides to call the tool — before the LLM response text is spoken. With sync tools this is required (fills silence while blocked). With **async** tools it is counterproductive: the tool runs in the background and the LLM continues talking, but `request-start` still interrupts with its filler text.

Additionally, if the system prompt doesn't explicitly forbid filler on the first turn, the LLM itself may generate "Let me check what we have available" as a natural acknowledgement before the tool result arrives.

### P3 — Broken flow after filler

Once VAPI speaks the `request-start` filler, the LLM's turn-generation has already completed. The next caller message starts a new turn with the tool result now in context, but the conversational thread is broken because the agent never answered the original question — it only said "let me check." The caller has to repeat themselves.

---

## 3. What Is Not Changing

- `backend/app/routes/leasing.py` — no changes; threshold logic, both endpoints, `_format_listings` all stay
- Path A / Path B architecture — stays exactly as designed in v2
- `submit_lease_lead` tool — unchanged
- Q1–Q7 qualification logic — unchanged
- All 31 unit tests + 30 integration tests — should still pass with no backend changes
- `update_lease_agents.py` script — run as-is after config changes

---

## 4. Changes Required

All changes are in `backend/app/services/vapi_agent_config.py` only.

---

### 4a. `first_message` — Shorten dramatically

**File:** `_lease_assistant_shell` return dict

**Current:**
```python
"first_message": (
    "Hey, thanks for calling! I'm Max, your AI leasing assistant. "
    "What can I help you find today? / "
    "Bonjour, merci d'appeler! Je suis Max, votre assistant de location IA. "
    "Comment puis-je vous aider aujourd'hui?"
),
```

**New:**
```python
"first_message": (
    "Hey, thanks for calling — I'm Max. What are you looking for? / "
    "Bonjour, je suis Max. Qu'est-ce que vous cherchez?"
),
```

**Why:** Under 15 words per language. Spoken in ~2 seconds. Ends with a question so the caller has a natural cue to speak. Easy to interrupt if they want to jump straight to their question.

---

### 4b. Remove `request-start` from `load_listings`

**File:** `_build_lease_tools` → `load_listings` tool dict

**Current:**
```python
"messages": [
    {
        "type": "request-start",
        "content": "Give me a second to check what we have available.",
    }
],
```

**New:** Remove the `messages` key entirely (or set to `[]`). The tool fires silently in the background. No spoken filler. The LLM response is what the caller hears.

```python
# no "messages" key on load_listings
```

**Why:** `async: True` means the tool does not block the LLM. The `request-start` fires BEFORE the LLM response, inserting unwanted filler. Removing it lets the LLM response speak first while the tool resolves quietly.

---

### 4c. Remove `request-start` from `search_listings`

**File:** `_build_lease_tools` → `search_listings` tool dict

**Current:**
```python
"messages": [
    {
        "type": "request-start",
        "content": "Let me look for units that match that — give me just a second.",
    }
],
```

**New:** Remove the `messages` key entirely. The system prompt instructs Max to say the bridge text as its own LLM-generated response: "Got it — let me find something that fits. Just to confirm, you're looking for a [N]-bedroom around [budget] a month, is that right?" That LLM-generated line IS the wait — the caller answers while the query runs.

**Why:** Same reason as `load_listings`. For Path B `search_listings`, the system prompt already provides the bridge. A separate `request-start` message would overlap with or cut off the LLM's natural confirmation.

---

### 4d. System Prompt — Three targeted additions

**File:** `_LEASE_SYSTEM_PROMPT_BASE`

#### Addition 1: Explicit "no filler on first turn" instruction

Add immediately after `[Finding a Unit — Two Paths]`, before the PATH A / PATH B block:

```
CRITICAL — first caller message:
When the caller first speaks, fire load_listings async and then respond IMMEDIATELY
to what they actually said. Do NOT say "let me check", "give me a second", "one moment",
or any variant. The tool runs silently — you do not acknowledge it.
If the caller asked "what do you have?" → ask them a preference question back while
the tool runs (e.g. "Sure! What size are you looking for?").
If the caller stated a preference → acknowledge it and ask the next qualification
question (e.g. "Two bedrooms — nice. And do you have a budget in mind?").
The listing data will be in your context by the time you need it.
```

#### Addition 2: [Unit Match Resolution] section

Add after the existing `Present results the same way as Path A` line in PATH B, as a new section:

```
[Unit Match Resolution]

Once you have listings from either path, apply this logic:

EXACTLY 1 MATCH:
Present it directly and proceed to qualification.
"We have one unit that fits — flat B202, two bedrooms, third floor, available
June 1st for thirty-eight thousand a month. That also has parking. Sound good?"

2–5 MATCHES:
Name each briefly (flat number + bedrooms + rent), then ask which interests them.
"We have two options in that range: B202, two bedrooms for thirty-eight thousand
with parking; and C104, two bedrooms for forty thousand with in-unit laundry.
Which one sounds more interesting?"
If the caller wants both or can't decide → note interest in all of them;
collect qualification info once; pass all UUIDs in interested_listing_ids.

MORE THAN 5 MATCHES:
Ask one more narrowing question before presenting.
"We have quite a few that fit — do you have a preference on floor, or parking,
or anything else that matters?" Then present top 3 only.

0 MATCHES but other units exist:
Suggest the closest available option. Do not end the call without presenting
something.
"We don't have any [X] right now, but we do have [closest option] — would
that be worth a look?"
If caller still not interested → capture name + lead with notes on what they
wanted, qualification_status="unmatched".

0 MATCHES and no other units at all:
"We don't have any units available right now." Capture name + lead,
qualification_status="unmatched", notes="No listings at time of call".
```

#### Addition 3: Explicit polite-wait for Path B when all preferences are in hand

Add inside the PATH B block, after the `search_listings` firing instruction:

```
PATH B — polite wait moment:
After firing search_listings, stay in the conversation. The confirmation question
("Just to confirm, you're looking for a [N]-bedroom around [budget]?") is your bridge
— the caller answers while the query runs. This is almost always enough time.
If the caller confirms and you still don't have results (slow connection), say:
"Perfect — just pulling those up now, give me two seconds."
Do NOT ask another question to fill time — just the one short wait line, then present
results as soon as they arrive.
```

---

## 5. Conversation Flow After These Changes

### Path A — Small portfolio, first-time caller

```
[first_message]
Max:    "Hey, thanks for calling — I'm Max. What are you looking for?"
        [load_listings fires SILENTLY in background]

Caller: "I'm looking for a two-bedroom."
        [load_listings result arrives: 5 listings, has_more=false, B202 + C104 match]

Max:    "Two bedrooms — great! We have two options in that range: B202 on
         the third floor for thirty-eight thousand with parking, and C104
         on the second floor for forty thousand with in-unit laundry.
         Which one sounds more interesting?"

Caller: "The one with laundry."

Max:    "C104 it is. When are you thinking of moving in?"
...
```

No filler. No pause. Tool result is in context before Max needs it.

---

### Path A — Caller interrupts first_message

```
Max:    "Hey, thanks for calling — I'm Max—"

Caller: [interrupts] "Yeah hi, I want to ask about a three-bedroom."
        [load_listings fires SILENTLY]

Max:    "Three bedrooms — absolutely. [results arrive] We have one available:
         flat C301, third floor, sixty-five thousand a month, available from
         the 22nd. Interested?"
...
```

Short first_message means the interruption point is natural. Tool fires on the interrupt turn.

---

### Path B — Large portfolio, preference gathering

```
[first_message]
Max:    "Hey, thanks for calling — I'm Max. What are you looking for?"
        [load_listings fires SILENTLY]

Caller: "Just browsing what you have."
        [load_listings returns: count=24, has_more=true, listings=[]]

Max:    "We have quite a few units right now. What size are you thinking —
         one bedroom, two, three?"

Caller: "Two bedrooms."
        [search_listings fires SILENTLY with bedrooms=2]

Max:    "Nice. And do you have a rough monthly budget in mind?"

Caller: "Around forty thousand."
        [budget noted; results likely back — if not, use polite wait]

Max:    [results arrived] "Perfect. We have two two-bedrooms in that range:
         B202 for thirty-eight thousand and D404 for forty-two thousand,
         which includes parking. Which one catches your eye?"
...
```

---

### Path B — Results slightly delayed (slow connection)

```
Caller: "Around forty thousand."

Max:    "Just to confirm — two bedrooms, budget around forty thousand, right?"

Caller: "Yeah."
        [results now back]

Max:    "Perfect. We have two options: B202 at thirty-eight thousand..."
```

If still not back after confirmation:

```
Caller: "Yeah."

Max:    "Perfect — just pulling those up now, give me two seconds."
        [results arrive ~1-2s later]
Max:    "Okay, here's what we have: B202 at thirty-eight thousand..."
```

---

## 6. Files Changed

| File | Change |
|---|---|
| `backend/app/services/vapi_agent_config.py` | Shorten `first_message`; remove `messages` from `load_listings`; remove `messages` from `search_listings`; add 3 sections to `_LEASE_SYSTEM_PROMPT_BASE` |

**No other files change.** No backend routes, no DB, no tests.

After updating the config:
```
python backend/scripts/update_lease_agents.py
```

---

## 7. Test Scenarios (additions to existing suite)

| Test | Action | Expected |
|---|---|---|
| First-message interruption | Interrupt within first 2 seconds | Max stops, acknowledges, fires load_listings, responds naturally |
| No filler on first turn | Say "I want a 2 bedroom" | Max responds with follow-up question immediately, no "let me check" |
| Single match | Portfolio has 1 two-bedroom, caller asks for two-bedroom | Max presents it directly, moves to qualification |
| Two matches | Portfolio has 2 two-bedrooms, caller asks for two-bedroom | Max names both briefly, asks which interests caller |
| Caller wants both | Caller says "both sound good" | Max gets name once, collects info, passes both UUIDs to submit_lease_lead |
| No match, alternatives exist | Ask for 4-bedroom, none exist | Max suggests closest available (e.g. 3-bedroom) |
| Path B, fast connection | Large portfolio, caller gives preferences | Max presents results without explicit wait line |
| Path B, slow connection | Large portfolio, simulate 3s search delay | Max uses confirmation question as bridge, only says "give me two seconds" if that's not enough |

---

## 8. Decisions / Open Questions

1. **Should `search_listings` keep a `request-response-delayed` fallback message?**
   Proposed: No — the system prompt handles it. But if live testing shows results arrive too slowly for the confirmation-question bridge to cover, add `{"type": "request-response-delayed", "timingMilliseconds": 4000, "content": "Just a moment longer..."}` to `search_listings` only. Do not add it to `load_listings`.

2. **first_message bilingual split.** The `/` separator is how VAPI currently sees both languages in a single string. Confirm whether VAPI speaks the full string (both languages) or detects and picks one. If it speaks both: current approach is correct. If it picks one: we may need to test with a French caller.

3. **load_listings fires on first caller message vs. first_message completion.** VAPI fires tool calls when the LLM generates a response. The `first_message` is not LLM-generated, so `load_listings` cannot fire until the caller speaks. This is the correct behavior and requires no change.
