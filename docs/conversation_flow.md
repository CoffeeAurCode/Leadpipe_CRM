# Conversation Flow Diagram

## Purpose

This diagram defines the **authoritative conversation flow** for the AI Complaint Intake system.

It represents the exact state transitions and decision logic used by:
- AI prompt engineering
- Backend orchestration
- Demo walkthroughs
- System validation

**This flow is frozen for MVP.**

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `[STATE]` | Conversation state or action |
| `{condition?}` | Decision point / conditional check |
| `→` | State transition |
| `├─` / `└─` | Decision branch |
| `↓` | Sequential flow |
| `↑` | Return/loop back |

---

## Main Flow

```
[START]
   ↓
[GREETING]
   │
   │ AI: "Hello! Please describe the issue you're facing."
   │
   ↓
[USER_PROVIDES_DESCRIPTION]
   │
   │ Validate: description.length >= 10
   │
   ├─ INVALID → Stay in state, re-prompt
   │              ↑___________________|
   │
   └─ VALID
        ↓
[EXTRACT_CATEGORY]
   │
   │ AI attempts to extract category from description
   │
   ├─ Extraction successful → category identified
   │
   └─ Extraction failed or ambiguous
        ↓
   [ASK_CATEGORY]
        │
        │ AI: "What category? (water, electricity, cleaning, noise, maintenance, security, other)"
        │
        ├─ INVALID → Stay in state, show allowed list
        │              ↑___________________________|
        │
        └─ VALID → category confirmed
                    ↓
{flat_number present?}
   │
   ├─ NO
   │   ↓
   │ [ASK_FLAT_NUMBER]
   │   │
   │   │ AI: "Which flat or unit number is this for?"
   │   │
   │   ├─ INVALID (empty) → Stay in state, re-prompt
   │   │                      ↑__________________|
   │   │
   │   └─ VALID → flat_number captured
   │                ↓
   │                (continue below)
   │
   └─ YES → flat_number already known
              ↓
{priority present?}
   │
   ├─ NO
   │   ↓
   │ [ASK_PRIORITY]
   │   │
   │   │ AI: "What is the priority? (low, medium, high)"
   │   │
   │   ├─ INVALID → Stay in state, show allowed values
   │   │              ↑___________________________|
   │   │
   │   └─ VALID → priority captured
   │                ↓
   │                (continue below)
   │
   └─ YES → priority already known
              ↓
[CONFIRMATION]
   │
   │ AI: "Here's what I have:
   │      - Flat Number: [value]
   │      - Category: [value]
   │      - Priority: [value]
   │      - Description: [value]
   │      Is this correct?"
   │
   ├─ USER: "No" or requests change
   │   │
   │   ↓
   │ [ASK_WHICH_FIELD_TO_CHANGE]
   │   │
   │   ├─ description → Return to [GREETING]
   │   ├─ flat_number → Return to [ASK_FLAT_NUMBER]
   │   ├─ category → Return to [ASK_CATEGORY]
   │   └─ priority → Return to [ASK_PRIORITY]
   │        │
   │        └─ (After correction, flow returns to CONFIRMATION)
   │
   └─ USER: "Yes" or confirms
        ↓
[RETURN_STRUCTURED_JSON]
   │
   │ Format:
   │ {
   │   "flat_number": "string",
   │   "category": "string",
   │   "priority": "low|medium|high",
   │   "description": "string"
   │ }
   │
   ↓
[SUBMIT_TO_BACKEND]
   │
   ↓
[DONE]
   │
   │ AI: "Thank you! Your complaint has been logged successfully."
   │
   ↓
[END]
```

---

## Critical Flow Rules

### 1. Never Re-Ask Valid Fields
- Once a field is validated and stored, it is never requested again
- Only invalid or missing fields trigger questions
- Correction flow is explicit (user must say "no" in confirmation)

### 2. One Question at a Time
- AI asks for exactly one missing field per turn
- Never batch questions
- User provides one answer, AI validates, then moves forward

### 3. Category Extraction (MVP Intelligence)
- AI attempts to extract category from the description using NLP/keywords
- If extraction is confident → use extracted value, skip asking
- If extraction fails or ambiguous → explicitly ask user to select from list

### 4. Validation Happens Immediately
- Every user input is validated before state transition
- Invalid input → stay in current state, re-prompt with guidance
- Valid input → store value, move to next decision point

---

## Validation Points

| State | Validation Rule | Reference |
|-------|----------------|-----------|
| `GREETING` (description) | Length ≥ 10 characters | `complaint_schema.md` |
| `ASK_CATEGORY` | Must be in `ALLOWED_CATEGORIES` | `constants.py` |
| `ASK_FLAT_NUMBER` | Non-empty string | `complaint_schema.md` |
| `ASK_PRIORITY` | Must be in `PRIORITY_ENUM` | `constants.py` |
| `CONFIRMATION` | Interpret yes/no from user | User intent parsing |

**On Validation Failure:**
- AI stays in current state
- AI provides helpful error message (e.g., "Please choose from: water, electricity, ...")
- AI re-prompts for same field
- AI does NOT move forward until valid input received

---

## JSON Return Point

**Only after successful CONFIRMATION**, the AI constructs and returns structured JSON:

```json
{
  "flat_number": "B-204",
  "category": "water",
  "priority": "high",
  "description": "Water is leaking continuously from the kitchen sink."
}
```

**This JSON is:**
- Validated against `complaint_schema.md`
- Submitted to the backend API
- Used to create a database record
- The single source of truth for the complaint

**No JSON is returned before CONFIRMATION.**

---

## Correction Loop Example

```
[CONFIRMATION]
   │
   │ AI: "Here's what I have: ... Is this correct?"
   │
   └─ USER: "No, the priority should be high"
        ↓
   [ASK_WHICH_FIELD_TO_CHANGE]
        │
        └─ Identify: user wants to change "priority"
             ↓
   [ASK_PRIORITY]
        │
        │ AI: "What is the priority? (low, medium, high)"
        │
        └─ USER: "high"
             └─ Validate → VALID
                  ↓
   [CONFIRMATION] (return with updated value)
        │
        │ AI: "Here's what I have: ... (priority now = high) ... Is this correct?"
        │
        └─ USER: "Yes"
             ↓
   [RETURN_STRUCTURED_JSON]
```

**Key:** Only the changed field is re-collected. All other valid fields remain unchanged.

---

## Decision Flow Summary

1. **START** → Greet user
2. **Collect Description** → Validate length
3. **Extract/Ask Category** → Validate against allowed list
4. **Check & Ask for Missing Fields:**
   - flat_number (if not present)
   - priority (if not present)
5. **Confirm All Data** → Show summary, get yes/no
6. **Return JSON** → Only after confirmation
7. **DONE** → Thank user, end conversation

---

## Notes for Implementation

### For AI Prompt Engineering
- System prompt must define state tracking
- Each state should have explicit transition conditions
- AI must maintain conversation context (previously collected fields)

### For Backend Orchestration
- Backend tracks current state and collected fields
- Backend validates AI output before DB insertion
- Backend maps `flat_number` to `unit_id` via database lookup
- Backend adds system fields: `status`, `source`, `tenant_id`, `created_at`

### For Demo & Testing
- Test correction loops at each state
- Test invalid input handling (stay in state, re-prompt)
- Test category extraction success and failure paths
- Verify JSON is only returned after confirmation

---

## Contract Guarantee

**This flow is the authoritative specification for AI behavior.**

Any deviation from this flow is a bug and must be corrected.

This diagram reflects the actual MVP implementation, not an idealized design.
