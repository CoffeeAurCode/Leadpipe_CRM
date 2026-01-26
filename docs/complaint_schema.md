# Complaint Schema (MVP – Frozen)

## Purpose

This document defines the **authoritative complaint input schema** for the AI Complaint Management System MVP.

This schema is the contract between:
- AI conversation layer
- API validation layer
- Database ingestion
- Manager dashboard

**This schema is frozen for MVP and must not be modified without team approval.**

---

## JSON Schema Definition

```json
{
  "flat_number": "string",
  "category": "string",
  "priority": "low | medium | high",
  "description": "string"
}
```

---

## Field-by-Field Specification

### `flat_number`

**Purpose:** Identifies the unit/flat where the issue is located.

**Type:** `string`

**Validation Rules:**
- Required (cannot be null or empty)
- Accepts any format: `"A-101"`, `"12B"`, `"Flat 302"`, etc.
- Trimmed of leading/trailing whitespace

**Examples:**
- ✅ `"B-204"`
- ✅ `"12B"`
- ✅ `"Flat 302"`
- ❌ `""` (empty)
- ❌ `null`

---

### `category`

**Purpose:** Classifies the complaint into a specific domain.

**Type:** `string` (enum)

**Validation Rules:**
- Required
- Must be one of the following allowed values:
  - `water`
  - `electricity`
  - `cleaning`
  - `noise`
  - `maintenance`
  - `security`
  - `other`
- Case-insensitive on input
- Normalized to lowercase before storage

**Examples:**
- ✅ `"water"`
- ✅ `"Electricity"` → normalized to `"electricity"`
- ✅ `"CLEANING"` → normalized to `"cleaning"`
- ✅ `"noise"`
- ❌ `"plumbing"` (not in allowed list)
- ❌ `""` (empty)

---

### `priority`

**Purpose:** Indicates urgency level of the complaint.

**Type:** `string` (enum)

**Validation Rules:**
- Required
- Must be exactly one of: `low`, `medium`, `high`
- Case-insensitive on input
- Normalized to lowercase before storage
- No free-form text allowed

**Examples:**
- ✅ `"high"`
- ✅ `"Medium"` → normalized to `"medium"`
- ✅ `"LOW"` → normalized to `"low"`
- ❌ `"urgent"` (not allowed)
- ❌ `"critical"` (not allowed)
- ❌ `""` (empty)

---

### `description`

**Purpose:** Provides a detailed explanation of the complaint.

**Type:** `string`

**Validation Rules:**
- Required
- Minimum length: 10 characters
- Should clearly describe the problem
- Trimmed of leading/trailing whitespace

**Examples:**
- ✅ `"Water is leaking continuously from the kitchen sink."`
- ✅ `"The hallway light on the 3rd floor has been out for 2 days."`
- ❌ `"Broken"` (too short)
- ❌ `""` (empty)
- ❌ `null`

---

## Example Valid Complaint

```json
{
  "flat_number": "B-204",
  "category": "water",
  "priority": "high",
  "description": "Water is leaking continuously from the kitchen sink."
}
```

---

## Example Invalid Complaints

### Missing `flat_number`

```json
{
  "category": "electricity",
  "priority": "medium",
  "description": "Light not working in bedroom."
}
```
**Error:** `flat_number` is required.

---

### Invalid `priority`

```json
{
  "flat_number": "C-101",
  "category": "security",
  "priority": "urgent",
  "description": "Main gate lock is broken."
}
```
**Error:** `priority` must be one of: `low`, `medium`, `high`.

---

### Description Too Short

```json
{
  "flat_number": "A-305",
  "category": "maintenance",
  "priority": "low",
  "description": "Broken"
}
```
**Error:** `description` must be at least 10 characters.

---

### Invalid `category`

```json
{
  "flat_number": "D-202",
  "category": "plumbing",
  "priority": "high",
  "description": "No water supply in the flat since morning."
}
```
**Error:** `category` must be one of: `water`, `electricity`, `cleaning`, `noise`, `maintenance`, `security`, `other`.

---

## Notes for AI & Backend

### For AI Conversation Layer
- AI must collect all four required fields before submitting a complaint
- If any field is missing or invalid, AI must ask clarifying questions
- AI should validate input in real-time and prompt user to correct invalid values
- AI must normalize category and priority to lowercase before submission

### For Backend API
- All fields are mandatory — reject requests with missing fields (400 Bad Request)
- Validate category against allowed list
- Validate priority against enum values
- Validate description length (minimum 10 characters)
- Return clear validation errors with field-specific messages

### For Database
- Backend maps `flat_number` to `unit_id` via lookup
- Additional fields (`status`, `source`, `tenant_id`, timestamps) are added by backend
- This schema represents only the **input contract**, not the full database model

---

## Contract Guarantee

**This schema is the single source of truth for complaint creation.**

Any component that accepts, processes, or validates complaint input must adhere to this exact specification.
