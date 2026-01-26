# AI Complaint Management System

Hey! Welcome to the codebase. If you're reading this, you're probably trying to understand how this thing works. Let me walk you through it.

## What Does This System Do?

Imagine a building manager getting hundreds of WhatsApp messages like:
- "bro water leaking in my flat pls fix"
- "No light since morning 512"
- "The noise from 3rd floor is unbearable"

This system takes that messy, unstructured text and turns it into clean, structured data that can be stored in a database and acted upon. No more manually reading every message and filling out forms.

## The Big Picture

```
User sends message: "No electricity in flat 512, urgent!"
         ↓
    Extractor (regex + keywords) → {flat: "512", category: "electricity", priority: None}
         ↓
    Validator → "Missing priority"
         ↓
    Decision Engine → "Ask for priority"
         ↓
User: "high"
         ↓
    [cycle repeats]
         ↓
Final JSON: {"flat_number": "512", "category": "electricity", "priority": "high", "description": "..."}
```

## Project Structure

```
backend/
├── app/
│   ├── db/              # Database stuff
│   ├── schemas/         # API input/output models
│   ├── core/            # Frozen constants
│   └── ai/              # The brains of the system
├── tests/               # Integration tests
docs/                    # Written specs (READ THESE FIRST!)
prompts/                 # AI system prompt
```

### Where to Start Reading Code

If you're new here, read in this order:

1. **`docs/complaint_schema.md`** - Understand what data we're collecting
2. **`app/core/constants.py`** - See the allowed values
3. **`docs/conversation_flow.md`** - Understand the conversation logic
4. **`app/ai/extractor.py`** - See how we parse text
5. **`app/ai/validator.py`** - See how we validate
6. **`app/ai/decision_engine.py`** - See how we route

## The Core Components

### 1. Database Layer (`app/db/`)

**`session.py`** - Database connection factory
- Creates async SQLAlchemy engine
- Provides session management for FastAPI
- Handles connection pooling

**`models.py`** - Database table definitions
- `User` - Manager/admin accounts
- `Unit` - Flats/apartments in the building
- `Tenant` - People living in units
- `Complaint` - The complaints themselves
- `CallLog` - Transcript of phone calls (if using voice)

**Key Relationships:**
- One Unit → Many Tenants
- One Tenant → Many Complaints
- One Complaint → One CallLog

### 2. API Schemas (`app/schemas/`)

**`complaint.py`** - Pydantic models for API

Think of these as the "shape" of data going in and out of our API:

- `ComplaintBase` - Shared fields (category, priority, description)
- `ComplaintCreate` - What we need from the user to create a complaint
- `ComplaintUpdate` - What fields can be changed (all optional)
- `ComplaintResponse` - What we send back (includes ID, timestamps)

**Why separate from ORM models?**
- Security (don't expose `password_hash` in API)
- Flexibility (API can differ from database structure)
- Validation (Pydantic validates incoming data)

### 3. Constants (`app/core/`)

**`constants.py`** - Single source of truth

```python
ALLOWED_CATEGORIES = ["water", "electricity", "cleaning", "noise", "maintenance", "security", "other"]
PRIORITY_ENUM = ["low", "medium", "high"]
```

**Why freeze these?**
- Prevents typos ("electrcity" vs "electricity")
- Easy to update everywhere at once
- Works with database constraints
- AI knows what to look for

**Want to add a new category?** Just add it here and to the keyword mappings in `extractor.py`.

### 4. AI Components (`app/ai/`)

This is where the magic happens. Three files, three responsibilities.

#### `extractor.py` - "Let me guess what you mean"

**What it does:** Takes raw text and tries to extract structured fields

**How it works:**

**Flat Numbers (Regex Patterns):**
```python
"A-101" → matches
"512"   → matches (standalone numbers)
"Flat 302" → matches
"B 204" → matches
```

We try multiple regex patterns in order and return the first match. If you're not familiar with regex, think of it as "pattern matching for text" - like wildcard searches on steroids.

**Categories (Keyword Matching):**
```python
"The water is leaking" → keywords: ["water", "leak"] → category: "water"
"No power since morning" → keywords: ["power"] → category: "electricity"
```

We have dictionaries mapping keywords to categories. The category with the most keyword matches wins.

**Priority (Keyword Inference):**
```python
"urgent issue" → "high"
"whenever you can" → "low"
```

We look for urgency indicators in the text.

**Important:** This is deterministic (same input = same output) and doesn't use AI/ML. It's just smart pattern matching.

#### `validator.py` - "Is this actually valid?"

**What it does:** Checks if we have all required fields and if they're correct

**Returns:** `(is_valid: bool, invalid_fields: list)`

**Example:**
```python
data = {"flat_number": "512", "category": "water", "priority": None, "description": "leak"}

validate_complaint(data)
# Returns: (False, ["priority"])
```

**Why not raise exceptions?** We want to collect ALL errors at once, not one at a time. Better UX.

**Validation Rules:**
- All 4 fields required (flat_number, category, priority, description)
- Category must be in `ALLOWED_CATEGORIES`
- Priority must be in `PRIORITY_ENUM`
- Description must be >10 characters

#### `decision_engine.py` - "What do we ask next?"

**What it does:** Decides the next action based on validation results

**Returns machine-readable commands:**
```python
{"action": "ASK", "field": "priority"}
# or
{"action": "RETURN_JSON", "data": {...}}
```

**Why dictionaries?** Makes it easy to add new action types later (CONFIRM, ERROR, etc.)

**Field Priority Order:**
1. description (always collect first)
2. flat_number
3. category
4. priority

We ask for missing fields in this order, one at a time.

**Why this order?** 
- Description sets context (we can auto-extract category from it)
- Flat number identifies the location
- Category groups the issue
- Priority determines urgency

## How a Conversation Works (Step by Step)

Let's trace through a real example:

**Turn 1:**
```
User: "There is no electricity since morning"

→ extractor.extract_fields()
   Returns: {flat_number: None, category: "electricity", priority: None, description: "..."}

→ validator.validate_complaint()
   Returns: (False, ["flat_number", "priority"])

→ decision_engine.decide_next_action()
   Returns: {"action": "ASK", "field": "flat_number"}  # First missing field

AI asks: "Which flat number?"
```

**Turn 2:**
```
User: "512"

→ extractor.extract_fields()
   Returns: {flat_number: "512", category: None, priority: None, description: "512"}

→ Merge with existing data (only if field was None before):
   {flat_number: "512", category: "electricity", priority: None, description: "There is no electricity since morning"}

→ validator.validate_complaint()
   Returns: (False, ["priority"])

→ decision_engine.decide_next_action()
   Returns: {"action": "ASK", "field": "priority"}

AI asks: "What's the priority? (low, medium, high)"
```

**Turn 3:**
```
User: "high"

→ extractor.extract_fields()
   Returns: {flat_number: None, category: None, priority: "high", description: "high"}

→ Merge with existing:
   {flat_number: "512", category: "electricity", priority: "high", description: "There is no electricity since morning"}

→ validator.validate_complaint()
   Returns: (True, [])  # All valid!

→ decision_engine.decide_next_action()
   Returns: {
       "action": "RETURN_JSON",
       "data": {
           "flat_number": "512",
           "category": "electricity",
           "priority": "high",
           "description": "There is no electricity since morning"
       }
   }

Done! Ready to submit to API.
```

## Key Design Decisions (And Why)

### Why Async SQLAlchemy?

**Short answer:** FastAPI is async, so our database layer should be too.

**Long answer:** When you make a database query, it takes time (10-100ms). In synchronous code, your entire thread blocks while waiting. In async code, you can handle other requests while waiting. With 1000 concurrent users, this makes a HUGE difference.

### Why Separate Extractor/Validator/Decision Engine?

**Could we combine them?** Sure. **Should we?** No.

- **Extractor** = "Here's what I think you mean" (suggestions)
- **Validator** = "Is this actually correct?" (rules enforcement)
- **Decision** = "What do we do next?" (routing logic)

Each has a single responsibility. Easy to test. Easy to modify. Easy to understand.

### Why Rule-Based Instead of ML?

**Pros of our approach:**
- ✅ Deterministic (same input = same output)
- ✅ No training data needed
- ✅ Easy to debug (just read the rules)
- ✅ Fast (no model inference)
- ✅ Good enough for MVP

**Cons:**
- ❌ Doesn't handle novel phrases
- ❌ Requires manual keyword updates
- ❌ Can't learn from data

**For production:** You'd probably add ML on top for category detection, but keep the rule-based as fallback.


## Common Gotchas

### 1. Field Merging in Conversations

**Problem:** When user says "512", extractor sets `description = "512"`, overwriting the original complaint!

**Solution:** Only merge if target field is `None`:
```python
if value is not None and data[field] is None:
    data[field] = value
```

### 2. Regex Lookaheads

**This doesn't match standalone "512":**
```python
r'\b\d{2,4}\b'  # Word boundaries don't work how you think
```

**This does:**
```python
r'^\s*\d{2,4}\s*$'  # Start of string → digits → end of string
```

### 3. Priority Keywords

Don't forget to include the enum values themselves:
```python
"high": ["urgent", "emergency", "high"]  # Include "high" itself!
```

Users might say "high" instead of "urgent".

### 4. Windows Unicode

```python
print("✓ Passed")  # Fails on Windows console
print("[PASS] Test passed")  # Works everywhere
```

Always use ASCII for terminal output.

## Testing

We have one integration test: `tests/test_complaint_flow.py`

**What it tests:**
- Full conversation flow (3 turns)
- Extractor → Validator → Decision pipeline
- Field merging logic
- Final JSON correctness

**How to run:**
```bash
cd backend
python tests/test_complaint_flow.py
```

**Expected output:**
```
[PASS] Test passed: Complete conversation flow works correctly
[PASS] Final JSON: {...}
```

**What's NOT tested yet:**
- Invalid input handling
- Correction loops
- Database integration
- API endpoints

## How to Extend This

### Add a New Category

1. Add to `app/core/constants.py`:
```python
ALLOWED_CATEGORIES = [..., "heating"]
```

2. Add keywords to `app/ai/extractor.py`:
```python
"heating": ["heater", "radiator", "cold", "temperature", "heat"]
```

3. Update `docs/complaint_schema.md`

4. Test it:
```python
assert extract_fields("The heater is broken")["category"] == "heating"
```

### Add Email Collection

1. Update schema docs
2. Add to database model
3. Add to Pydantic schema
4. Add extraction logic (regex for email pattern)
5. Update validator
6. Update conversation flow

### Connect to Real AI (OpenAI/Anthropic)

The system prompt is ready at `prompts/complaint_agent_system.txt`.

Just wire it up to your LLM API:
```python
async def handle_message(user_message, conversation_state):
    # Call LLM with system prompt
    ai_response = await openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    )
    
    # Extract fields from conversation_state
    # Validate
    # Decide next question
    # Send AI response
```

## Questions?

If something's unclear, check:
1. The docs/ folder (especially `conversation_flow.md`)
2. The learning guide (`LEARNING_GUIDE_SESSION_1.md`)
3. The code comments (docstrings)

Still stuck? The code is simpler than you think. Just trace through `test_complaint_flow.py` with a debugger and watch what happens at each step.

---

**Remember:** This is MVP code. It's meant to be simple, readable, and *good enough*. Not perfect. Good enough.

Now go build something! 🚀
