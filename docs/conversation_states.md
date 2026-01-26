# Conversation States (AI Complaint Intake FSM)

## Overview

This document defines the **authoritative finite state machine (FSM)** for AI-driven complaint intake in the Tenant Management System.

### Design Philosophy

The AI operates as a **state-driven data collector**, not a conversational chatbot.

**Core Principles:**
- **Think in states, not messages** — each state has a clear purpose and transition condition
- **Collect only what is required** — no small talk, no extra data
- **Validate in real-time** — reject invalid input immediately and stay in the current state
- **Never skip required states** — all fields must be collected in order
- **Never collect twice** — once a valid field is captured, move forward

**This FSM ensures:**
- Predictable AI behavior
- Reliable data collection
- Fast complaint submission
- Easy testing and debugging

---

## State Flow Diagram

```
GREETING → ISSUE_DESCRIPTION → FLAT_NUMBER → CATEGORY → PRIORITY → CONFIRMATION → DONE
            ↑                      ↑             ↑          ↑            ↓
            └──────────────────────┴─────────────┴──────────┘          (on "No")
                              (correction loop)
```

**Legend:**
- `→` Normal forward flow
- `↓` Confirmation rejected, return to specific state
- `↑` Invalid input, stay in current state

---

## State Definitions

### 1. GREETING

**Purpose:**  
Welcome the user and initiate the complaint intake process.

**AI Action:**  
Greet the user and ask them to describe their issue.

**Expected Input:**  
User provides a description of their complaint (free text).

**Validation Rules:**  
- Input must be a non-empty string
- Minimum length: 10 characters (validates against schema requirement)

**Transition Logic:**
- **Valid input** → Move to `FLAT_NUMBER`
- **Invalid input** (too short or empty) → Stay in `GREETING`, prompt again with hint about minimum length

**Example Prompts:**
- "Hello! I'm here to help you log a complaint. Please describe the issue you're facing."
- (If invalid) "Please provide more details. The description should be at least 10 characters."

---

### 2. ISSUE_DESCRIPTION

**Purpose:**  
*(Note: This state is merged with GREETING for MVP efficiency. The description is collected during greeting.)*

**Status:** Implicit — handled in `GREETING` state.

---

### 3. FLAT_NUMBER

**Purpose:**  
Identify the unit/flat where the issue is located.

**AI Action:**  
Ask the user for their flat or unit number.

**Expected Input:**  
Any string representing a flat identifier (e.g., "A-101", "12B", "Flat 302").

**Validation Rules:**  
- Required (cannot be empty)
- Type: string
- Accepts any format
- Trimmed of leading/trailing whitespace

**Transition Logic:**
- **Valid input** → Move to `CATEGORY`
- **Invalid input** (empty) → Stay in `FLAT_NUMBER`, ask again

**Example Prompts:**
- "Which flat or unit number is this complaint for?"
- (If invalid) "Please provide a valid flat number."

---

### 4. CATEGORY

**Purpose:**  
Classify the complaint into a specific domain.

**AI Action:**  
Ask the user to select or specify a category for their complaint.

**Expected Input:**  
One of the allowed category values (case-insensitive).

**Validation Rules:**  
- Required
- Must be one of: `water`, `electricity`, `cleaning`, `noise`, `maintenance`, `security`, `other`
- Reference: `app/core/constants.py::ALLOWED_CATEGORIES`
- Case-insensitive on input
- Normalized to lowercase before storage

**Transition Logic:**
- **Valid category** → Move to `PRIORITY`
- **Invalid category** → Stay in `CATEGORY`, show allowed options and ask again

**Example Prompts:**
- "What category does this complaint fall under? (water, electricity, cleaning, noise, maintenance, security, other)"
- (If invalid) "That's not a valid category. Please choose from: water, electricity, cleaning, noise, maintenance, security, or other."

---

### 5. PRIORITY

**Purpose:**  
Determine the urgency level of the complaint.

**AI Action:**  
Ask the user to specify the priority of their complaint.

**Expected Input:**  
One of `low`, `medium`, or `high` (case-insensitive).

**Validation Rules:**  
- Required
- Must be exactly one of: `low`, `medium`, `high`
- Reference: `app/core/constants.py::PRIORITY_ENUM`
- Case-insensitive on input
- Normalized to lowercase before storage
- No free-form text allowed

**Transition Logic:**
- **Valid priority** → Move to `CONFIRMATION`
- **Invalid priority** → Stay in `PRIORITY`, show allowed options and ask again

**Example Prompts:**
- "What is the priority level of this complaint? (low, medium, high)"
- (If invalid) "Please choose a valid priority: low, medium, or high."

---

### 6. CONFIRMATION

**Purpose:**  
Review all collected data with the user and request explicit confirmation before submission.

**AI Action:**  
Summarize all collected information in a clear format and ask for confirmation.

**Expected Input:**  
User confirms with "yes" or requests changes with "no" (or similar affirmative/negative responses).

**Validation Rules:**  
- Input must be interpreted as yes/no
- Accept variations: "yes", "y", "correct", "confirm" → YES
- Accept variations: "no", "n", "change", "edit" → NO

**Transition Logic:**
- **User confirms (yes)** → Move to `DONE`
- **User rejects (no)** → Ask which field to correct, then transition to the appropriate state:
  - Description → `GREETING`
  - Flat number → `FLAT_NUMBER`
  - Category → `CATEGORY`
  - Priority → `PRIORITY`

**Summary Format:**
```
Here's what I have:
- Flat Number: [flat_number]
- Category: [category]
- Priority: [priority]
- Description: [description]

Is this correct?
```

**Example Prompts:**
- "Here's what I have: Flat Number: B-204, Category: water, Priority: high, Description: Water is leaking continuously from the kitchen sink. Is this correct?"
- (If no) "What would you like to change? (description, flat number, category, or priority)"

---

### 7. DONE

**Purpose:**  
Signal that complaint intake is complete and ready for submission.

**AI Action:**  
Confirm successful completion and thank the user.

**Expected Input:**  
None (terminal state).

**Validation Rules:**  
N/A — no further validation required.

**Transition Logic:**
- **Terminal state** — no further transitions
- Complaint data is passed to backend for submission
- Conversation ends

**Example Prompts:**
- "Thank you! Your complaint has been logged successfully. We'll address it soon."
- "All set! Your complaint has been recorded."

---

## Example Conversation Walkthrough

### Scenario: Successful Submission

**State: GREETING**  
**AI:** Hello! I'm here to help you log a complaint. Please describe the issue you're facing.  
**User:** Water is leaking from my kitchen sink continuously.  
**Transition:** Valid (>10 chars) → `FLAT_NUMBER`

**State: FLAT_NUMBER**  
**AI:** Which flat or unit number is this complaint for?  
**User:** B-204  
**Transition:** Valid → `CATEGORY`

**State: CATEGORY**  
**AI:** What category does this complaint fall under? (water, electricity, cleaning, noise, maintenance, security, other)  
**User:** water  
**Transition:** Valid → `PRIORITY`

**State: PRIORITY**  
**AI:** What is the priority level of this complaint? (low, medium, high)  
**User:** high  
**Transition:** Valid → `CONFIRMATION`

**State: CONFIRMATION**  
**AI:** Here's what I have:
- Flat Number: B-204
- Category: water
- Priority: high
- Description: Water is leaking from my kitchen sink continuously.

Is this correct?  
**User:** Yes  
**Transition:** Confirmed → `DONE`

**State: DONE**  
**AI:** Thank you! Your complaint has been logged successfully. We'll address it soon.  
**Conversation ends.**

---

### Scenario: Invalid Input + Correction Loop

**State: GREETING**  
**AI:** Hello! I'm here to help you log a complaint. Please describe the issue you're facing.  
**User:** Broken  
**Validation:** FAILED (too short, <10 chars)  
**Transition:** Stay in `GREETING`

**AI:** Please provide more details. The description should be at least 10 characters.  
**User:** The light in my bedroom is not working since yesterday.  
**Transition:** Valid → `FLAT_NUMBER`

**State: FLAT_NUMBER**  
**AI:** Which flat or unit number is this complaint for?  
**User:** A-305  
**Transition:** Valid → `CATEGORY`

**State: CATEGORY**  
**AI:** What category does this complaint fall under? (water, electricity, cleaning, noise, maintenance, security, other)  
**User:** lights  
**Validation:** FAILED (not in allowed list)  
**Transition:** Stay in `CATEGORY`

**AI:** That's not a valid category. Please choose from: water, electricity, cleaning, noise, maintenance, security, or other.  
**User:** electricity  
**Transition:** Valid → `PRIORITY`

**State: PRIORITY**  
**AI:** What is the priority level of this complaint? (low, medium, high)  
**User:** urgent  
**Validation:** FAILED (not in enum)  
**Transition:** Stay in `PRIORITY`

**AI:** Please choose a valid priority: low, medium, or high.  
**User:** medium  
**Transition:** Valid → `CONFIRMATION`

**State: CONFIRMATION**  
**AI:** Here's what I have:
- Flat Number: A-305
- Category: electricity
- Priority: medium
- Description: The light in my bedroom is not working since yesterday.

Is this correct?  
**User:** No, the priority should be high  
**Transition:** User rejects → Return to `PRIORITY`

**State: PRIORITY**  
**AI:** What is the priority level of this complaint? (low, medium, high)  
**User:** high  
**Transition:** Valid → `CONFIRMATION`

**State: CONFIRMATION**  
**AI:** Here's what I have:
- Flat Number: A-305
- Category: electricity
- Priority: high
- Description: The light in my bedroom is not working since yesterday.

Is this correct?  
**User:** Yes  
**Transition:** Confirmed → `DONE`

**State: DONE**  
**AI:** Thank you! Your complaint has been logged successfully. We'll address it soon.  
**Conversation ends.**

---

## State Validation Reference

| State | Validates Against | Error Handling |
|-------|------------------|----------------|
| `GREETING` | `description` length ≥ 10 | Re-prompt with hint |
| `FLAT_NUMBER` | Non-empty string | Re-prompt |
| `CATEGORY` | `ALLOWED_CATEGORIES` (constants.py) | Show allowed list, re-prompt |
| `PRIORITY` | `PRIORITY_ENUM` (constants.py) | Show allowed list, re-prompt |
| `CONFIRMATION` | Yes/No interpretation | If No, ask which field to change |
| `DONE` | N/A | Terminal state |

---

## Notes for Implementation

### For AI Prompt Engineering
- Each state should have a distinct system prompt or instruction
- AI must validate input before transitioning
- AI must never assume or auto-fill values
- AI must track current state explicitly

### For Backend Orchestration
- Backend should maintain conversation state
- Backend validates AI output against schema before DB insert
- Backend maps `flat_number` (string) to `unit_id` (FK) via lookup
- Backend adds system fields: `status`, `source`, `tenant_id`, `created_at`

### For Voice/Chat Agents
- Voice agents must support retry logic for invalid inputs
- Chat agents should show category/priority options as buttons/quick replies
- Confirmation state should always display a formatted summary

---

## Contract Guarantee

**This FSM is frozen for MVP.**

Any AI agent, voice interface, or orchestration layer must strictly follow this state flow.

Deviations from this FSM are considered bugs and must be corrected.
