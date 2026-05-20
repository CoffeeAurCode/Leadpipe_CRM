# Learning Guide Session 1: Project Foundation — AI Complaint System with FastAPI, Pydantic, and Rule-Based NLP

**Role:** Senior Staff Engineer Mentorship
**Objective:** Build the foundational layer of the Tenant Management MVP — data models, Pydantic schemas, a rule-based AI extraction pipeline, and an integration test — from nothing. No magic. No hand-waving. You understand every line.

---

## 1. What Was Built in This Session

| Deliverable | File | Purpose |
|---|---|---|
| Project directory structure | `backend/app/{db,schemas,core,ai}/` | Separation of concerns from day one |
| Async database session manager | `backend/app/db/session.py` | FastAPI dependency injection for DB |
| ORM models | `backend/app/db/models.py` | SQLAlchemy declarative table definitions |
| Pydantic complaint schemas | `backend/app/schemas/complaint.py` | API validation, serialization, ORM bridge |
| Constants | `backend/app/core/constants.py` | Single source of truth for allowed values |
| Rule-based field extractor | `backend/app/ai/extractor.py` | Regex + keyword text parsing |
| Validation pipeline | `backend/app/ai/validator.py` | Multi-field error accumulation |
| Decision engine | `backend/app/ai/decision_engine.py` | Orchestrates extraction → validation → next action |
| Schema documentation | `docs/complaint_schema.md` | Contract-first specification |
| State machine design | `docs/conversation_states.md` | FSM conversation flow diagram |
| Integration test | `backend/tests/test_complaint_flow.py` | End-to-end conversation simulation |

---

## 2. Core Concept: Why This Architecture Exists

Before writing one line of code, understand the boundary between the three layers in this system:

```
[User Message]
      |
      v
[Extractor]      <- Pure text parsing. No state. No DB. Just regex + keywords.
      |
      v
[Validator]      <- Checks extracted data against business rules. Returns errors.
      |
      v
[Decision Engine] <- Reads validation result. Decides next action: ASK, CONFIRM, or SAVE.
      |
      v
[FastAPI Route]  <- Talks to DB. Returns HTTP response.
```

Each layer has exactly one responsibility. This is not stylistic preference — it is what makes the system testable, debuggable, and extensible by someone who did not write it.

---

## 3. Deep Technical Breakdown

### 3.1 Project Structure Setup

```bash
# Create directory tree
mkdir -p backend/app/{db,schemas,core,ai}
mkdir -p backend/tests
mkdir docs

# Mark directories as Python packages
touch backend/app/__init__.py
touch backend/app/db/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/core/__init__.py
touch backend/app/ai/__init__.py
```

**Why `__init__.py`?**
Python treats directories containing this file as packages, enabling `from app.db.session import get_db`. Without it you get `ModuleNotFoundError`.

---

### 3.2 Async SQLAlchemy — Why and How

**Synchronous DB access (wrong for FastAPI):**
```python
# Blocks the ENTIRE server thread for 50ms per query
user = db.query(User).filter_by(id=1).first()
```

**Async DB access (correct):**
```python
# Yields control while waiting for DB. Server handles other requests.
result = await session.execute(select(User).where(User.id == 1))
user = result.scalar_one()
```

FastAPI runs on an async event loop (via `uvicorn`). If you block the event loop with a synchronous DB call, no other request can be served until that call completes. At 100 concurrent users, this degrades to a queue.

**File: `backend/app/db/session.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import os

# asyncpg driver is required: pip install asyncpg
# postgresql+asyncpg:// tells SQLAlchemy to use asyncpg, not psycopg2
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")

engine = create_async_engine(
    DATABASE_URL,
    pool_pre_ping=True,    # Checks if connection is alive before lending it from pool
    echo=False             # Set to True during development to see all SQL queries
)

# async_sessionmaker replaces the old sessionmaker() for async code
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def get_db():
    """
    FastAPI dependency that yields an async DB session.

    The 'async with' block ensures the session is ALWAYS closed,
    even if an exception is thrown inside the route handler.

    FastAPI calls this generator before each request and runs cleanup
    (the code after 'yield') after the response is sent.
    """
    async with AsyncSessionLocal() as session:
        yield session
```

**Critical mistake to avoid:**
```python
# WRONG: Session is created but never closed. Leaks connections.
session = AsyncSessionLocal()

# CORRECT: Context manager guarantees cleanup
async with AsyncSessionLocal() as session:
    ...
```

**`expire_on_commit=False` explained:**
After `session.commit()`, SQLAlchemy by default marks all loaded objects as "expired" so the next access re-fetches from DB. In async code this causes `MissingGreenlet` errors because the re-fetch happens outside the session. Setting `expire_on_commit=False` disables this behavior.

---

### 3.3 ORM Models — Declarative Base and Relationships

**File: `backend/app/db/models.py`**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """All ORM models inherit from this. Declarative Base links Python class to SQL table."""
    pass


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, index=True)
    flat_number = Column(String(20), nullable=False, unique=True)
    floor = Column(Integer)

    # One Unit → Many Tenants
    # back_populates creates bidirectional navigation:
    # unit.tenants → all tenants in this unit
    # tenant.unit  → the unit for this tenant
    tenants = relationship("Tenant", back_populates="unit")
    complaints = relationship("Complaint", back_populates="unit")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(20))

    # Foreign Key: This table's unit_id column references units.id
    # ondelete="SET NULL": If the Unit is deleted, set unit_id to NULL (don't cascade delete tenant)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    unit = relationship("Unit", back_populates="tenants")


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(50), nullable=False)
    priority = Column(String(20), nullable=False)
    status = Column(String(20), default="pending", nullable=False)

    # server_default: PostgreSQL generates this value on INSERT, Python never sees it
    # func.now() maps to NOW() in SQL
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    unit_id = Column(Integer, ForeignKey("units.id", ondelete="SET NULL"), nullable=True)
    unit = relationship("Unit", back_populates="complaints")
```

**Understanding cascade behavior:**

| `ondelete` option | What happens when parent row is deleted |
|---|---|
| `CASCADE` | Child rows are also deleted automatically |
| `SET NULL` | Child FK column is set to NULL |
| `RESTRICT` | Database blocks the parent deletion if children exist |
| `NO ACTION` | Same as RESTRICT but checked at end of transaction |

Choose based on business rules: deleting a Unit should not delete tenant history, so `SET NULL` is correct. Deleting a Complaint that has Appointments should cascade-delete those appointments.

---

### 3.4 Pydantic Schemas — The API Layer

ORM models are the database representation. Pydantic schemas are the API representation. They are separate on purpose.

**Why separate?**
- ORM models can have columns (like `password_hash`) that must never appear in API responses
- Pydantic validates types and constraints at the boundary — before data reaches the DB
- API schema can evolve independently from the DB schema

**File: `backend/app/schemas/complaint.py`**

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

# STEP 1: Base schema — fields shared between Create and Response
class ComplaintBase(BaseModel):
    description: str
    category: str
    priority: str

# STEP 2: Create schema — what POST /complaints expects
class ComplaintCreate(ComplaintBase):
    flat_number: str  # Will be resolved to unit_id in the route handler

# STEP 3: Update schema — what PATCH /complaints/{id} expects
# All fields are Optional because PATCH is a partial update
class ComplaintUpdate(BaseModel):
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None

# STEP 4: Response schema — what GET /complaints returns
class ComplaintResponse(ComplaintBase):
    id: int
    status: str
    created_at: Optional[datetime] = None

    # This config tells Pydantic to read data from ORM object attributes
    # Without this, ComplaintResponse(db_complaint) would fail
    model_config = ConfigDict(from_attributes=True)
```

**The `from_attributes=True` bridge:**
```python
# ORM object from SQLAlchemy
db_complaint = await session.get(Complaint, 1)
db_complaint.id        # 1
db_complaint.category  # "water"

# Without from_attributes=True: Pydantic expects a dict, throws error
# With from_attributes=True: Pydantic reads attributes directly from the ORM object
response = ComplaintResponse.model_validate(db_complaint)
```

**Pydantic v2 API changes — common mistakes for those who learned v1:**

| Pydantic v1 (old) | Pydantic v2 (current) |
|---|---|
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `.from_orm(obj)` | `.model_validate(obj)` |
| `.dict()` | `.model_dump()` |
| `.json()` | `.model_dump_json()` |

---

### 3.5 Constants — Single Source of Truth

**File: `backend/app/core/constants.py`**

```python
ALLOWED_CATEGORIES = [
    "water",
    "electricity",
    "cleaning",
    "noise",
    "maintenance",
    "security",
    "other"
]

ALLOWED_PRIORITIES = ["low", "medium", "high"]

ALLOWED_STATUSES = ["pending", "in_progress", "resolved", "closed"]
```

**Why a separate constants file?**
If "electricity" is spelled differently in the extractor, validator, and test, you have a bug that is invisible until runtime. A single constants file means one change propagates everywhere. Validators import from here. Extractors import from here. Tests import from here.

---

### 3.6 Rule-Based Extractor

**File: `backend/app/ai/extractor.py`**

```python
import re
from app.core.constants import ALLOWED_CATEGORIES, ALLOWED_PRIORITIES

# Keyword map: category → list of words that indicate it
# The canonical category name itself MUST be in the list
CATEGORY_KEYWORDS = {
    "water": ["water", "leak", "pipe", "tap", "plumbing", "flood", "drain", "wet"],
    "electricity": ["electricity", "power", "light", "bulb", "current", "socket", "switch", "trip"],
    "cleaning": ["cleaning", "dirty", "garbage", "trash", "hygiene", "smell", "waste"],
    "noise": ["noise", "loud", "sound", "music", "party", "disturbance", "shouting"],
    "maintenance": ["maintenance", "broken", "repair", "damage", "fix", "worn"],
    "security": ["security", "lock", "door", "key", "access", "suspicious", "theft"],
    "other": ["other", "issue", "problem", "complaint"],
}

PRIORITY_KEYWORDS = {
    "high": ["urgent", "urgently", "emergency", "immediately", "critical", "asap", "high"],
    "medium": ["soon", "important", "needed", "medium", "moderate"],
    "low": ["whenever", "eventually", "not urgent", "low", "minor"],
}

# Flat number patterns — ordered from most specific to least specific
FLAT_NUMBER_PATTERNS = [
    r'\b([A-Z]-?\s?\d{1,4}[A-Z]?)\b',       # A-101, B204, C-5A
    r'\b(flat|unit)\s+([A-Z0-9][A-Z0-9-]*)\b',  # "flat 101", "unit B-5"
    r'\b(\d{1,4}[A-Z])\b',                   # 101A, 5B
    r'\b([A-Z]\s?\d{1,4})\b',               # A 101, B5
    r'^\s*(\d{2,4})\s*$',                    # "512" (standalone number, no other content)
]


def extract_flat_number(text: str) -> str | None:
    """
    Try each flat number pattern. Return first match.

    The standalone-number pattern ^\s*(\d{2,4})\s*$ only matches if the
    ENTIRE input is just a number (2-4 digits). This prevents "512 Main St"
    from incorrectly matching "512" as a flat number.
    """
    text_upper = text.upper()
    for pattern in FLAT_NUMBER_PATTERNS:
        match = re.search(pattern, text_upper, re.IGNORECASE)
        if match:
            # Some patterns have two capture groups (the keyword + the number)
            # Take the last capture group which contains the actual flat number
            return match.group(match.lastindex).strip()
    return None


def extract_category(text: str) -> str | None:
    """
    Score each category by counting keyword matches.
    Return the highest-scoring category.
    Scoring prevents false positives from single-word overlaps.
    """
    text_lower = text.lower()
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[category] = score
    return max(scores, key=scores.get) if scores else None


def extract_priority(text: str) -> str | None:
    """Return first matching priority. Direct enum values must be in keyword lists."""
    text_lower = text.lower()
    for priority, keywords in PRIORITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return priority
    return None


def extract_fields(text: str) -> dict:
    """
    Master extraction function. Returns a dict with all extractable fields.
    Missing fields are None, never omitted.

    The 'description' field gets the raw text. Callers decide whether to keep it.
    """
    return {
        "description": text.strip(),
        "flat_number": extract_flat_number(text),
        "category": extract_category(text),
        "priority": extract_priority(text),
    }
```

**Why scoring instead of first-match?**
Consider "I have a water leak that needs urgent repair." Without scoring, "maintenance" matches first because "repair" appears. With scoring, "water" scores 2 (water + leak) vs "maintenance" scores 1 (repair), so water wins.

---

### 3.7 Validation Pipeline

**File: `backend/app/ai/validator.py`**

```python
from app.core.constants import ALLOWED_CATEGORIES, ALLOWED_PRIORITIES


def validate_complaint(data: dict) -> tuple[bool, list[str]]:
    """
    Validate all complaint fields. Return (is_valid, list_of_missing_or_invalid_fields).

    This function ACCUMULATES all errors rather than failing on the first one.
    The caller gets a complete list and can ask for all missing fields at once.

    Returns:
        (True, [])                   → all valid
        (False, ["category", "flat_number"])  → two fields need fixing
    """
    errors = []

    # Check presence
    if not data.get("description"):
        errors.append("description")

    if not data.get("flat_number"):
        errors.append("flat_number")

    # Check presence AND validity
    category = data.get("category")
    if not category:
        errors.append("category")
    elif category not in ALLOWED_CATEGORIES:
        errors.append("category")  # Present but invalid value

    priority = data.get("priority")
    if not priority:
        errors.append("priority")
    elif priority not in ALLOWED_PRIORITIES:
        errors.append("priority")

    return (len(errors) == 0, errors)
```

**Fail-fast vs accumulate — why accumulate wins here:**
```python
# FAIL-FAST: Forces multi-turn correction dialog
Turn 1: "You're missing category"
Turn 2: "You're missing priority"   ← frustrating for user

# ACCUMULATE: Single correction round
Turn 1: "You're missing category and priority"
Turn 2: [user provides both]         ← efficient
```

---

### 3.8 Decision Engine — The Orchestrator

**File: `backend/app/ai/decision_engine.py`**

```python
from app.ai.extractor import extract_fields
from app.ai.validator import validate_complaint

# Field collection order defines conversation priority
# Description must come first — it seeds the rest
FIELD_ORDER = ["description", "flat_number", "category", "priority"]


def decide_next_action(data: dict) -> dict:
    """
    Given current accumulated complaint data, return the next action as a dict.

    Possible return values:
        {"action": "ASK", "field": "flat_number"}
            → The system should ask the user for this field

        {"action": "RETURN_JSON", "data": {...}}
            → All data collected and valid. Submit to database.

    Why return a dict (command pattern)?
    Future actions like CONFIRM, CORRECT, ERROR can be added without
    changing the caller. The caller dispatches based on action type.
    """
    is_valid, missing = validate_complaint(data)

    if is_valid:
        return {"action": "RETURN_JSON", "data": data}

    # Ask for the highest-priority missing field (based on FIELD_ORDER)
    for field in FIELD_ORDER:
        if field in missing:
            return {"action": "ASK", "field": field}

    # Fallback: should not reach here if FIELD_ORDER covers all fields
    return {"action": "ASK", "field": missing[0]}


def process_turn(current_data: dict, user_input: str) -> dict:
    """
    Complete one conversation turn:
    1. Extract new fields from user input
    2. Merge into current data (never overwrite existing non-None values)
    3. Return next action
    """
    extracted = extract_fields(user_input)

    for field, value in extracted.items():
        # Only fill empty slots. Do not overwrite existing description with
        # a short follow-up answer like "512" that also has description="512"
        if value is not None and current_data.get(field) is None:
            current_data[field] = value

    return decide_next_action(current_data)
```

**The merge rule — "only fill empty slots":**
```python
# State after turn 1: "The power has been out since morning"
data = {
    "description": "The power has been out since morning",
    "category": "electricity",
    "flat_number": None,
    "priority": None
}

# User says "512" in turn 2
extracted = extract_fields("512")
# → {"description": "512", "flat_number": "512", "category": None, "priority": None}

# WRONG merge (overwrites description):
for field, value in extracted.items():
    if value is not None:
        data[field] = value
# data["description"] is now "512" — LOST the original complaint

# CORRECT merge (only fill None slots):
for field, value in extracted.items():
    if value is not None and data.get(field) is None:
        data[field] = value
# data["description"] stays "The power has been out since morning" — correct
```

---

## 4. Errors You Will Encounter (With Exact Messages and Fixes)

### Error 1: Flat number not extracted for standalone input like "512"

**Symptom:**
```python
assert action["field"] == "priority"
AssertionError
# The engine still asks for flat_number instead of priority
```

**Root cause:**
All existing patterns require a letter prefix/suffix or keyword like "flat". The standalone number pattern `^\s*(\d{2,4})\s*$` was missing.

**Before (broken):**
```python
FLAT_NUMBER_PATTERNS = [
    r'\b([A-Z]-?\s?\d{1,4}[A-Z]?)\b',       # Needs letter
    r'\b(flat|unit)\s+([A-Z0-9][A-Z0-9-]*)\b', # Needs keyword
]
```

**After (fixed):**
```python
FLAT_NUMBER_PATTERNS = [
    r'\b([A-Z]-?\s?\d{1,4}[A-Z]?)\b',
    r'\b(flat|unit)\s+([A-Z0-9][A-Z0-9-]*)\b',
    r'\b(\d{1,4}[A-Z])\b',
    r'\b([A-Z]\s?\d{1,4})\b',
    r'^\s*(\d{2,4})\s*$',  # Added: matches "512" when alone
]
```

**Why `{2,4}` not `{1,4}`?** Single-digit answers like "5" are too ambiguous — the user might mean priority level 5, not flat 5. Requiring two or more digits reduces false positives.

---

### Error 2: Priority not extracted when user says "high"

**Symptom:**
```python
assert action["action"] == "RETURN_JSON"
AssertionError  # Still asking for priority after user said "high"
```

**Root cause:**
Priority keywords only contained synonyms ("urgent", "emergency"), not the canonical enum values themselves ("high", "medium", "low").

**Before (broken):**
```python
PRIORITY_KEYWORDS = {
    "high": ["urgent", "urgently", "emergency", "immediately"],
    # "high" itself is NOT in the list
}
```

**After (fixed):**
```python
PRIORITY_KEYWORDS = {
    "high": ["urgent", "urgently", "emergency", "immediately", "critical", "asap", "high"],
    "medium": ["soon", "important", "needed", "medium", "moderate"],
    "low": ["whenever", "eventually", "not urgent", "low", "minor"],
}
```

**Why this happens:** When the AI asks "Please rate priority as low, medium, or high", the user literally types "high". If "high" is not in the keyword list, extraction returns None.

---

### Error 3: Description overwritten by short follow-up answer

**Symptom:**
```
Turn 1: "The bulb in bathroom is broken"
Turn 2: "512"
Final data: {"description": "512", "category": "electricity", ...}  ← wrong
```

**Root cause:** Naive merge overwrites existing values with newly extracted ones.

**Before (broken):**
```python
for field, value in extracted.items():
    if value is not None:
        data[field] = value  # Overwrites "The bulb in bathroom is broken" with "512"
```

**After (fixed):**
```python
for field, value in extracted.items():
    if value is not None and data.get(field) is None:
        data[field] = value  # Only fills empty slots
```

---

### Error 4: UnicodeEncodeError on Windows console

**Exact error message:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 0
```

**Root cause:** Windows command prompt uses `cp1252` encoding by default, which cannot represent Unicode checkmark ✓ (`U+2713`).

**Where it appears:** Any `print("✓ Test passed")` in test files.

**Fix option A — ASCII-safe output (most portable):**
```python
print("[PASS] Test passed")
print("[FAIL] Test failed")
```

**Fix option B — force UTF-8 (better for readability):**
```python
import sys
sys.stdout.reconfigure(encoding='utf-8')
print("✓ Test passed")  # Now works
```

**Fix option C — environment variable (applies globally):**
```bash
set PYTHONIOENCODING=utf-8
python backend/tests/test_complaint_flow.py
```

Use option A for CI/CD pipelines. Use option B or C for local development.

---

## 5. Integration Test — Simulating the Full Conversation

**File: `backend/tests/test_complaint_flow.py`**

```python
import sys
sys.stdout.reconfigure(encoding='utf-8')

from app.ai.extractor import extract_fields
from app.ai.validator import validate_complaint
from app.ai.decision_engine import decide_next_action, process_turn

def test_full_conversation_flow():
    """
    Simulates a real multi-turn conversation:
    Turn 1: Describe the problem (extract description + category)
    Turn 2: Provide flat number
    Turn 3: Provide priority
    Turn 4: Decision engine returns final JSON
    """
    # Initialize empty state
    data = {
        "description": None,
        "flat_number": None,
        "category": None,
        "priority": None
    }

    # --- Turn 1: User describes the problem ---
    action = process_turn(data, "There is no electricity since morning")
    print(f"After turn 1: {data}")
    print(f"Action: {action}")
    assert action["action"] == "ASK"
    assert action["field"] == "flat_number"  # category extracted, flat still missing

    # --- Turn 2: User provides flat number ---
    action = process_turn(data, "512")
    print(f"After turn 2: {data}")
    print(f"Action: {action}")
    assert action["action"] == "ASK"
    assert action["field"] == "priority"  # flat extracted, priority still missing

    # --- Turn 3: User provides priority ---
    action = process_turn(data, "high")
    print(f"After turn 3: {data}")
    print(f"Action: {action}")
    assert action["action"] == "RETURN_JSON"
    assert action["data"]["category"] == "electricity"
    assert action["data"]["flat_number"] == "512"
    assert action["data"]["priority"] == "high"
    assert action["data"]["description"] == "There is no electricity since morning"

    print("[PASS] Full conversation flow test passed")


def test_validator_accumulates_all_errors():
    """Validator must report ALL missing fields, not just the first one."""
    data = {"description": None, "flat_number": None, "category": None, "priority": None}
    is_valid, errors = validate_complaint(data)
    assert is_valid is False
    assert set(errors) == {"description", "flat_number", "category", "priority"}
    print("[PASS] Validator accumulation test passed")


def test_merge_does_not_overwrite():
    """Merging new data must not overwrite existing non-None values."""
    data = {
        "description": "original description",
        "flat_number": None,
        "category": "water",
        "priority": None
    }
    action = process_turn(data, "512")
    # description must remain unchanged
    assert data["description"] == "original description"
    assert data["flat_number"] == "512"
    assert data["category"] == "water"
    print("[PASS] Merge immutability test passed")


if __name__ == "__main__":
    test_full_conversation_flow()
    test_validator_accumulates_all_errors()
    test_merge_does_not_overwrite()
    print("\n[ALL TESTS PASSED]")
```

**Run the tests:**
```bash
cd backend
python -m pytest tests/test_complaint_flow.py -v
# OR run directly:
python tests/test_complaint_flow.py
```

---

## 6. Anti-Patterns to Avoid

**Anti-pattern 1: Importing DB models in AI layer**
```python
# WRONG: AI extractor should have zero DB knowledge
from app.db.models import Complaint
def extract_fields(text):
    ...
    complaint = Complaint(category=category)  # AI layer touching DB models
```

```python
# CORRECT: AI layer returns pure dicts
def extract_fields(text) -> dict:
    return {"category": category, ...}
# Route handler creates DB models
```

**Anti-pattern 2: Hardcoded strings**
```python
# WRONG: "electricity" scattered across 5 files
if action["field"] == "electricity":
    ...
```

```python
# CORRECT: import from constants
from app.core.constants import ALLOWED_CATEGORIES
if category in ALLOWED_CATEGORIES:
    ...
```

**Anti-pattern 3: Fail-fast validation in conversation context**
```python
# WRONG: Only reports first error
def validate(data):
    if not data["category"]:
        raise ValueError("Missing category")  # User must fix one at a time
```

```python
# CORRECT: Returns all errors at once
def validate(data) -> tuple[bool, list]:
    errors = []
    if not data["category"]: errors.append("category")
    if not data["priority"]: errors.append("priority")
    return (len(errors) == 0, errors)
```

**Anti-pattern 4: Synchronous SQLAlchemy with async FastAPI**
```python
# WRONG: Blocks the event loop
@app.get("/complaints")
async def get_complaints(db: Session = Depends(get_db)):  # Session not AsyncSession
    return db.query(Complaint).all()  # sync query in async route
```

```python
# CORRECT: Fully async
@app.get("/complaints")
async def get_complaints(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Complaint))
    return result.scalars().all()
```

---

## 7. Best Practices Applied in This Session

| Practice | Application |
|---|---|
| Schema-first development | `docs/complaint_schema.md` written before any Python code |
| Single source of truth | All allowed values defined once in `constants.py` |
| Pure functions | `extract_fields`, `validate_complaint`, `decide_next_action` have no side effects |
| Dependency injection | `get_db()` generator injected via `Depends()`, not global session |
| Error accumulation | Validator collects all errors in one pass |
| Merge safety | `process_turn` only fills `None` slots, never overwrites |
| Layer separation | AI layer has zero DB imports, route layer has zero regex |

---

## 8. Session Completion Checklist

- [ ] Python 3.10+ installed and accessible
- [ ] Virtual environment created and activated (`python -m venv venv`)
- [ ] Dependencies installed: `fastapi`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic`
- [ ] Directory structure created with `__init__.py` in every package directory
- [ ] `session.py` uses `create_async_engine` and `async_sessionmaker`
- [ ] ORM models use `DeclarativeBase` and define foreign keys with `ondelete` policy
- [ ] Pydantic schemas separate `Base`, `Create`, `Update`, and `Response`
- [ ] `ComplaintResponse` has `model_config = ConfigDict(from_attributes=True)`
- [ ] All allowed values centralized in `constants.py`
- [ ] Extractor keyword lists include the canonical enum values themselves
- [ ] Flat number patterns include `^\s*(\d{2,4})\s*$` for standalone numbers
- [ ] Validator accumulates all errors in one list
- [ ] `process_turn` only fills `None` slots when merging
- [ ] Integration test covers full 3-turn conversation
- [ ] Integration test covers validator accumulation
- [ ] Integration test covers merge safety
- [ ] All tests pass: `python backend/tests/test_complaint_flow.py`
- [ ] No `UnicodeEncodeError` on Windows (use `sys.stdout.reconfigure(encoding='utf-8')`)
