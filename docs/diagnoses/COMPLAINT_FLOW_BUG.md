# Pre-Existing Bug: `test_complaint_flow_happy_path`

**File:** `backend/tests/test_complaint_flow.py`
**Status:** Failing (2 bugs, first fixed, second open)
**Root cause:** `decision_engine.py` and `validator.py` drifted apart — they were written together for an early prototype, then `validator.py` was updated for the VAPI flow without updating `decision_engine.py` or its test.

---

## What Fails and Why

### Bug 1 — Already Fixed

`decision_engine.py:20` was unpacking `validate_complaint()`'s return value as a 2-tuple:

```python
# OLD (broken)
is_valid, invalid_fields = validate_complaint(data)
```

But `validate_complaint()` returns a **dict**, not a tuple:

```python
# validator.py — actual return
return {
    "is_complete": bool,
    "missing_fields": list,
    "data": dict,       # ← 3 keys, not 2
}
```

Unpacking a 3-key dict into 2 variables throws:
```
ValueError: too many values to unpack (expected 2)
```

**Fix applied:**
```python
# decision_engine.py:20-21 — now reads
result = validate_complaint(data)
is_valid, invalid_fields = result["is_complete"], result["missing_fields"]
```

---

### Bug 2 — Still Open

After fixing Bug 1, the test fails with:

```
AssertionError: assert 'appointment_date' == 'priority'
```

**The schema mismatch:**

| File | Required fields |
|---|---|
| `validator.py` | `flat_number`, `category`, `appointment_date` |
| `decision_engine.py` `field_order` | `description`, `flat_number`, `category`, `priority` |
| `test_complaint_flow.py` (expected) | `flat_number` → `priority` → RETURN_JSON |

`validator.py` was updated at some point to require `appointment_date` (the VAPI voice flow needs it to schedule a manager visit). `decision_engine.py` and its test were never updated — they still expect `priority` to be collected.

**Trace of what happens today:**

```
Step 1 — message: "There is no electricity since morning"
  extract_fields() → category="electricity", description=text, flat_number=None, priority=None
  validate_complaint() → missing: [flat_number, appointment_date]
  decide_next_action() → field_order scans for "flat_number" → found → ASK flat_number  ✓

Step 2 — message: "512"
  extract_fields() → flat_number="512"
  validate_complaint() → missing: [appointment_date]
  decide_next_action() → field_order scans: description❌ flat_number❌ category❌ priority❌
                          falls back to invalid_fields[0] → ASK appointment_date  ✗ (test expects "priority")

Step 3 — test asserts action["field"] == "priority" → FAIL
```

**Additionally:** even if `appointment_date` were filled, `decide_next_action()` RETURN_JSON path builds:
```python
{
    "flat_number": data["flat_number"],
    "category": data["category"],
    "priority": data["priority"],       # KeyError if priority was never collected
    "description": data["description"],
}
```
This would throw a `KeyError` since `priority` is not in the data dict.

---

## File Map

```
backend/app/ai/validator.py           ← requires flat_number, category, appointment_date
backend/app/ai/decision_engine.py     ← still expects priority; not used anywhere in production
backend/tests/test_complaint_flow.py  ← tests the old flow (priority-based, not appointment-based)
backend/tests/unit/test_validator.py  ← correctly tests current validator (all pass)
backend/app/routes/voice.py:206       ← production caller of validate_complaint (uses dict API correctly)
```

`decision_engine.py` is **not imported anywhere in production code** — only by `test_complaint_flow.py`. It was part of the original rule-based prototype before VAPI was integrated.

---

## Fix Options

### Option A — Mark as deprecated (recommended if decision_engine is dead code)

`decision_engine.py` has no production callers. The VAPI chatbot (`chatbot.py`) and the voice webhook (`voice.py`) both handle the conversation flow directly. If this module is no longer needed:

```python
# test_complaint_flow.py
@pytest.mark.skip(reason="decision_engine.py is superseded by VAPI chatbot flow")
def test_complaint_flow_happy_path():
    ...
```

---

### Option B — Sync decision_engine to current validator

Update `decision_engine.py` to collect `appointment_date` instead of `priority`, and update the test to match.

**`decision_engine.py` changes needed:**

```python
def _get_next_missing_field(invalid_fields: list) -> str:
    field_order = ["description", "flat_number", "category", "appointment_date"]
    #                                                         ^ was "priority"
    for field in field_order:
        if field in invalid_fields:
            return field
    return invalid_fields[0]
```

```python
return {
    "action": "RETURN_JSON",
    "data": {
        "flat_number": data["flat_number"],
        "category": data["category"],
        "appointment_date": data["appointment_date"],   # was "priority"
        "description": data["description"],
    }
}
```

**`test_complaint_flow.py` changes needed:**

Replace the second user message and assertion:
```python
# Step 2: was asking for priority, now asks for appointment_date
user_message_2 = "2026-06-15T10:00:00"
...
assert action["field"] == "appointment_date"   # was "priority"

# Step 3: complete
action = decide_next_action(complaint_data)
assert action["action"] == "RETURN_JSON"
assert action["data"]["appointment_date"] == "2026-06-15T10:00:00"
```

---

## Which Option to Pick

| Factor | Option A (skip) | Option B (fix) |
|---|---|---|
| `decision_engine.py` used in production | No | No |
| VAPI flow already handles conversation | Yes (chatbot.py) | Yes (chatbot.py) |
| Effort | 1 line | ~15 lines across 2 files |
| Keeps dead code alive | No | Yes |

**Recommendation: Option A.** `decision_engine.py` is prototype-era code. The production complaint flow runs through VAPI → `voice.py` → `validate_complaint()` directly. Keeping a parallel rule-based engine in sync adds maintenance burden with no production benefit.
