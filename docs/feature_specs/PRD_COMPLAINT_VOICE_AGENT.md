# PRD: Complaint Voice Agent — Alex (Existing)

**Date:** 2026-05-20 (updated 2026-05-20)
**Author:** Pranav Raj
**Status:** Active — Option B Single Number + Caller Phone Lookup Architecture

---

## 1. Overview

### 1.1 Problem

Property managers cannot be available 24/7 to receive maintenance complaints and schedule repair visits over the phone. Tenants who call outside office hours, or when the manager is busy, have no reliable way to log an issue and book a slot. Complaints get lost, tenants feel ignored, and the manager has no audit trail.

### 1.2 Solution

**Alex** is an AI voice agent deployed on VAPI that handles inbound tenant calls around the clock. Any registered tenant can call the dedicated property management number, verify their identity by flat number, and:

- File a maintenance complaint with a scheduled manager visit
- View their active upcoming appointments
- Reschedule an existing appointment
- Cancel an existing appointment
- Report an emergency situation

Every call is logged. Complaints and appointments are written directly to the database and the manager is notified automatically.

### 1.3 Goals

| Goal | Metric |
|------|--------|
| Capture all inbound maintenance calls | 100% of calls produce a call log record |
| Zero unverified complaints | Phone verification gate before any action |
| Reduce manager manual intake effort | Complaints + appointments created with no manager involvement |
| Manager visibility into all calls | Call logs table: every call, status, transcript |

### 1.4 Non-Goals (v1)

- Outbound proactive notifications to tenants (handled separately via SMS/email)
- Complaint status updates over voice ("is my issue fixed?")
- Multi-language responses (agent always responds in English regardless of caller language)
- Payments, rent queries, or lease renewals over voice
- Manager calling the agent — inbound only (outbound calls are a separate endpoint, not an agent flow)

---

## 2. Architecture

### 2.1 Architecture: Option B — Single Number + Caller Phone Lookup

One VAPI assistant (`Alex`), one global phone number, handles complaint calls for **all property groups**. The caller's `property_group_id` is resolved at call time via `Verify_phone_number` — the backend returns it alongside the verification status. Alex passes this value to every subsequent tool call, routing the complaint to the correct manager automatically.

**No Squad. No RouterAgent. No inter-agent transfers.**

### 2.2 Stack

| Layer | Technology |
|-------|-----------|
| Voice platform | VAPI.ai |
| Transcription | Deepgram nova-3 (multi-language), OpenAI gpt-4o-transcribe (fallback) |
| LLM (agent brain) | OpenAI gpt-5.2-chat-latest |
| TTS (agent voice) | ElevenLabs eleven_turbo_v2_5, Voice ID `1SM7GgM6IMuvQlz2BwM3` |
| Backend | FastAPI on Render — `tenant-management-mvp.onrender.com` |
| Database | Supabase PostgreSQL |
| Notifications | SendGrid (email) via background task |

### 2.3 Agent Identity

**Alex** (single standalone complaint agent)
- **Persona:** Calm, professional, empathetic — one question at a time
- **Background sound:** Office ambience
- **First message:** "Hi, thanks for calling. This is Alex with the property management team. How can I help you today?"
- **Voicemail message:** "Please call back"

### 2.4 Language Handling

Transcriber runs in multi-language mode (Deepgram nova-3, EN + FR). Alex always:
- Responds in English only
- Silently translates French speech to English before writing to any tool
- Never asks the caller which language they prefer

### 2.5 Call Routing

```
Inbound call arrives on global complaint number (+91-XXXX-COMPLAINT)
              ↓
      Alex greets caller
              ↓
      "What's your flat number?"
              ↓
      Verify_phone_number(flat_number, caller_phone)
      → returns { status, property_group_id, datetime }
              ↓
      ┌───────┴───────┐
      │               │
   "valid"      "invalid" / "vacant"
      │               │
      ↓               ↓
  Extract         End call immediately
  property_group_id    (one sentence, no follow-up)
      ↓
  Detect caller intent
      ↓
  Route to one of 5 flows:
    1. Maintenance Request
    2. View Active Appointment
    3. Reschedule Appointment
    4. Cancel Appointment
    5. Emergency Situation
  (Pass property_group_id to all tool calls in the chosen flow)
```

---

## 3. Phone Verification — Handled by Alex

Alex handles verification directly. There is no separate RouterAgent or squad transfer.

The caller's phone number is injected automatically from VAPI call metadata via `{{customer.number}}` — Alex never asks the caller for their phone number.

### Alex verification flow

```
1. Alex asks: "What's your flat number?"
2. Caller provides flat number
3. Alex calls Verify_phone_number with:
   - flat_number (from caller speech)
   - phone_number (automatic from VAPI metadata — never spoken)
4. Tool returns: { status, property_group_id, datetime }
```

| Status | Alex Behaviour |
|--------|---------------|
| `valid` | Extract `property_group_id` and `datetime` from response. Proceed: "Thank you! How can I help you today?" |
| `invalid` | "I'm sorry, the number you're calling from doesn't match our records for that flat. Please contact our office directly. Have a good day." → end call |
| `vacant` | "I'm sorry, that flat doesn't appear to have a registered tenant. Please contact our office for assistance. Have a good day." → end call |

**Rules:**
- `Verify_phone_number` is called exactly once per call — never repeated
- On `invalid` or `vacant`, the call ends immediately — no retries, no alternatives
- If the caller gives an invalid flat number twice, Alex ends politely
- The `property_group_id` from the verify response is passed to **all subsequent tool calls**: `submit_complaint`, `check_availability`, `view_active_appointments`, `update_appointment`, `cancel_appointment`
- The `datetime` from the verify response is used as the call's reference time for all date/time calculations

---

## 4. Call Flows

### 4.1 Maintenance Request (Complaint + Appointment)

The primary flow. Triggered when the caller describes a physical issue or asks for a repair visit.

```
1. GREETING
   "Hi, thanks for calling. This is Alex with the property management team.
   What's your flat number?"
   <wait>

2. PHONE VERIFICATION
   Call Verify_phone_number → handle result (see Section 3)
   On success: extract property_group_id + datetime. "Thank you! How can I help you today?"
   <wait>

3. ISSUE IDENTIFICATION (silent)
   Agent categorises from speech into one of:
   water | electricity | cleaning | noise | maintenance | security | other
   
   Ask: "Can you describe the issue in a bit more detail?"
   <wait>

4. APPOINTMENT SCHEDULING
   Ask: "When would you like the manager to visit? Please share a date and time."
   <wait>

5. AVAILABILITY CHECK
   Extract datetime from natural language → convert to YYYY-MM-DDTHH:MM:SS (IST)
   Call: check_availability with proposed datetime
   
   If status = "unavailable":
     "I'm sorry, the manager already has an appointment around that time. 
     Could you suggest another date or time?"
     <wait> → loop back to Step 4
   
   If status = "available":
     → Proceed to Step 6

6. VERBAL CONFIRMATION
   "Just to confirm, this is for flat {flat_number}, a {category} issue involving 
   {description}, scheduled for {date} at {time}. Is that correct?"
   <wait>

7. COMPLAINT SUBMISSION
   Call: submit_complaint with:
   - flat_number
   - category
   - description
   - appointment_date (YYYY-MM-DDTHH:MM:SS)

8. FINAL CONFIRMATION
   "Your complaint has been filed successfully. The manager will visit on 
   {date} at {time}. If there's anything else you need, I'm here to help."
```

### 4.2 View Active Appointments

Triggered when the caller asks to see or check their scheduled appointments.

```
1. Post-verification:
   Call: view_active_appointments with flat_number

2. If no appointments:
   "There are currently no active appointments scheduled for your flat."

3. If appointments found:
   Read clearly: issue category, scheduled date, scheduled time
   Ask: "Would you like to make any changes to this appointment?"
   <wait>
   → If yes: move to reschedule or cancel flow
   → If no: end politely
```

### 4.3 Reschedule Appointment

Triggered when the caller says they want to change the date/time of an existing appointment.

```
1. Post-verification:
   Call: view_active_appointments with flat_number
   
   If none: inform caller, end.

2. Ask: "What new date and time would you prefer?"
   <wait>

3. Call: check_availability with proposed datetime
   If unavailable: ask for another time (loop)
   If available: proceed

4. Verbal confirmation:
   "Just to confirm, you'd like to reschedule your {category} appointment 
   to {date} at {time}. Is that correct?"
   <wait>

5. Call: update_appointment with:
   - id (from view response)
   - flat_number
   - new_appointment_date (YYYY-MM-DDTHH:MM:SS)

6. "Your appointment has been successfully updated to {date} at {time}. 
   If you need anything else, I'm here to help."
```

### 4.4 Cancel Appointment

Triggered when the caller explicitly asks to cancel a scheduled visit.

```
1. Post-verification:
   Call: view_active_appointments with flat_number
   
   If none: "There are no active appointments to cancel for your flat." → end.

2. Read appointment details (category, date, time)
   Ask: "Which appointment would you like to cancel?"
   <wait>

3. Verbal confirmation:
   "Just to confirm, you'd like to cancel your {category} appointment 
   on {date} at {time}. Is that correct?"
   <wait>

4. Call: cancel_appointment with:
   - id (from view response)
   - flat_number

5. "Your appointment has been successfully cancelled. If you need 
   anything else, I'm here to help."
```

### 4.5 Emergency Handling

Triggered when the caller mentions fire, flooding, gas smell, power outage, or any safety risk.

```
1. Agent asks for explicit confirmation:
   "Just to confirm, are you experiencing [emergency type] right now?"
   <wait>

2. If confirmed:
   Agent does NOT troubleshoot or give instructions
   Proceeds to book an emergency appointment (same flow as 4.1 Steps 4–8)

3. If not confirmed:
   Routes to standard maintenance request flow
```

**Agent rules:** Never attempt to troubleshoot an emergency. Never give instructions beyond booking the appointment. Call cannot end without an appointment scheduled if emergency is confirmed.

---

## 5. Tools

Alex (single standalone agent) has 6 tools. All tool endpoints are injected with `BACKEND_URL` at agent build time via `build_complaint_config(backend_url)` in `backend/app/services/vapi_agent_config.py`.

| Tool | Purpose |
|------|---------|
| `Verify_phone_number` | Verify caller by flat number + phone; returns `property_group_id` |
| `check_availability` | Check if an appointment slot is available |
| `view_active_appointments` | Fetch active appointments for the verified flat |
| `update_appointment` | Reschedule an appointment |
| `cancel_appointment` | Cancel an appointment |
| `submit_complaint` | Async webhook — create complaint + appointment in DB |

### Tool 1: `Verify_phone_number` (apiRequest — POST)

**Endpoint:** `POST /flats/verify-phone?phone_number={{customer.number}}`

**Body:**
```json
{ "flat_number": "<from caller speech>" }
```

**Response fields extracted:**
| Field | Type | Description |
|-------|------|-------------|
| `result` | string | Human-readable explanation |
| `status` | string | `valid` / `invalid` / `vacant` |
| `datetime` | string | Current IST datetime — used as call's time reference |
| `property_group_id` | string | UUID of the property group this flat belongs to — passed to all subsequent tools |

**Contract:** Always returns HTTP 200. Backend normalises flat_number with `.strip().upper()` and compares phone numbers as suffix matches to handle country-code variants (`+91XXXXXXXXXX` vs `XXXXXXXXXX`).

---

### Tool 2: `check_availability` (apiRequest — GET)

**Endpoint:** `GET /appointments/availability?appointment_date={{datetime}}`

**Response fields extracted:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | `available` / `unavailable` |

---

### Tool 3: `view_active_appointments` (apiRequest — GET)

**Endpoint:** `GET /appointments/view?flat_number={{flat_number}}`

**Response fields extracted:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Primary key of the appointment |
| `appointment_id` | string | UUID of the appointment |
| `appointment_date` | string | Scheduled date/time |
| `status` | string | Appointment status |
| `category` | string | Complaint category linked to this appointment |

---

### Tool 4: `update_appointment` (apiRequest — PATCH)

**Endpoint:** `PATCH /appointments/update?id={{id}}&flat_number={{flat_number}}&new_appointment_date={{new_appointment_date}}`

**Response fields extracted:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Appointment primary key |
| `new_appointment_date` | string | Confirmed new datetime |

---

### Tool 5: `cancel_appointment` (apiRequest — PATCH)

**Endpoint:** `PATCH /appointments/cancel?id={{id}}&flat_number={{flat_number}}`

**Response fields extracted:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Appointment primary key |
| `status` | string | Confirmation status |

---

### Tool 6: `submit_complaint` (function / webhook — async)

**Webhook:** `POST /voice/webhook` (timeout: 20s, async: true)

**Parameters:**
| Field | Type | Required | Values |
|-------|------|----------|--------|
| `category` | string | Yes | `water` / `electricity` / `cleaning` / `noise` / `maintenance` / `security` / `other` |
| `description` | string | Yes | Detailed issue description (English) |
| `flat_number` | string | Yes | e.g. `101`, `A105`, `B201` |
| `appointment_date` | string | Yes | ISO 8601: `YYYY-MM-DDTHH:MM:SS` |
| `property_group_id` | string | Yes | UUID from `Verify_phone_number` response — routes complaint to the correct manager |

This tool is async — the agent does not wait for a response before delivering the final confirmation message.

---

## 6. Backend Webhook Processing

**File:** `backend/app/routes/voice.py`

VAPI sends many webhook events per call (status updates, transcripts, etc.). The backend filters to only two final event types: `tool-calls` and `end-of-call-report`.

### Processing Pipeline (in order)

| Step | Action |
|------|--------|
| 1 | **Event type filter** — ignore all non-final events, return `{"status": "ignored"}` |
| 2 | **Extract call metadata** — `call_id` and `phone_number` from message or payload |
| 3 | **Extract transcript** — from `messagesOpenAIFormatted`, `transcript`, or `messages` (fallback chain) |
| 4 | **Detect `submit_complaint` tool call** — only on `tool-calls` events |
| 5 | **Validate complaint data** — check all 4 required fields are present |
| 6 | **Idempotency check** — look up existing `call_logs` by `call_id` |
| 7 | **Determine call log status** |
| 8 | **Persist call log** (always — even for abandoned/incomplete calls) |
| 9 | **Feature flag check** — `voice_calls` feature must be enabled for the flat |
| 10 | **Create complaint** — POST to `/complaints` |
| 11 | **Create appointment** — insert into `appointments` table linked to complaint |
| 12 | **Update call log** with complaint_id and final status |
| 13 | **Trigger notification** — background task emails the manager |

**Critical rule:** Every step returns HTTP 200, even on errors. VAPI marks calls as failed when the webhook returns non-200.

### Call Log Statuses

| Status | Meaning |
|--------|---------|
| `created` | Complaint and appointment successfully created |
| `incomplete` | Agent called `submit_complaint` but required fields were missing |
| `abandoned` | Call ended (`end-of-call-report`) with no `submit_complaint` call |
| `failed` | `submit_complaint` was called and valid, but DB write failed |
| `blocked_by_feature_flag` | Voice calls feature disabled for this flat — complaint blocked |

---

## 7. Supporting Endpoints

### `GET /voice/call-status`

Returns the ISO timestamp of the last `end-of-call-report` received. The frontend polls this every 10 seconds and refreshes the complaints and appointments views when the timestamp changes.

```json
{ "last_call_ended_at": "2026-05-20T10:15:32.412Z" }
```

### `POST /voice/call/outbound`

Initiates an outbound call to a tenant via VAPI. The same agent workflow applies — verification, complaints, appointments.

**Request body:**
```json
{
  "customer_number": "+919876543210",
  "first_message": "Hi, this is Alex calling about your recent maintenance request..."
}
```

Requires `PRIVATE_VAPI_API`, `VAPI_ASSISTANT_ID`, and `VAPI_NUMBER_ID` env vars.

---

## 8. Database Schema — Affected Tables

### `call_logs`

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `call_id` | text | VAPI call UUID (idempotency key) |
| `phone_number` | text | Caller's phone number (E.164) |
| `transcript` | text | Caller speech extracted from artifact |
| `raw_event_type` | text | `tool-calls` or `end-of-call-report` |
| `complaint_status` | text | See status table above |
| `complaint_id` | integer | FK to `complaints.id` (nullable) |

### `complaints`

| Column | Type | Description |
|--------|------|-------------|
| `flat_number` | text | Normalised flat number (uppercase) |
| `category` | text | One of the 7 allowed categories |
| `priority` | text | `medium` (hardcoded for voice complaints) |
| `description` | text | Issue description (English, max 1000 chars) |
| `status` | text | `pending` on creation |
| `source` | text | `voice` |

### `appointments`

| Column | Type | Description |
|--------|------|-------------|
| `flat_number` | text | Flat the appointment belongs to |
| `flat_uuid` | uuid | FK to `flats.uuid` |
| `complaint_uuid` | uuid | FK to `complaints.uuid` |
| `appointment_date` | text | ISO datetime (YYYY-MM-DDTHH:MM:SS) in IST |
| `status` | text | `scheduled` on creation |

---

## 9. Feature Flag

The `voice_calls` feature flag is checked per flat before creating any complaint. If disabled:

- The call log is updated to `blocked_by_feature_flag`
- No complaint or appointment is created
- VAPI still receives HTTP 200 (the agent already said "filed successfully" before the async webhook ran)

**Service:** `backend/app/services/feature_service.py` — `FeatureService.is_feature_enabled(flat_id, Feature.VOICE_CALLS)`

---

## 10. Key Files

### Backend

| File | Purpose |
|------|---------|
| `backend/app/services/vapi_agent_config.py` | Agent configs: `build_complaint_config()` + lease configs + legacy |
| `backend/app/routes/voice.py` | `/voice/webhook` (complaint), `/voice/lease-lead-webhook`, call status poll, outbound call |
| `backend/app/routes/flats.py` | `POST /flats/verify-phone` — phone verification (returns `property_group_id`) |
| `backend/app/routes/appointments.py` | Appointment VAPI tools: view, update, cancel, availability check |
| `backend/app/routes/complaints.py` | `POST /complaints` — complaint creation (called via HTTP from webhook) |
| `backend/app/routes/property_groups.py` | `POST /{uuid}/provision-voice` — retry lease agent provisioning for new groups |
| `backend/app/ai/validator.py` | Validates complaint data completeness before DB write |
| `backend/app/services/notifications.py` | Manager notification email triggered after appointment created |
| `backend/app/core/features.py` | Feature flag constants (`Feature.VOICE_CALLS`) |
| `backend/app/services/feature_service.py` | Feature flag evaluation per flat |

### Deployment / Scripts

| File | Purpose |
|------|---------|
| `backend/scripts/deploy_vapi_agent.py` | Legacy — redeploys the single global assistant for the test PropertyGroup only |
| `backend/scripts/test_complaint_endpoints.sh` | Curl tests: verify-phone, appointments, voice webhook |
| `backend/scripts/test_provisioning.sh` | Curl test: retry provisioning endpoint |

---

## 11. Agent Behaviour Rules (Summary)

| Rule | Detail |
|------|--------|
| One question at a time | Never asks multiple questions in a single turn |
| No phone number request | Caller's phone is always from VAPI metadata — never asked |
| Forward `property_group_id` | Extracted from `Verify_phone_number` response; passed to every subsequent tool call |
| No promises on timelines | Books a visit but never commits to resolution time |
| No legal or lease advice | Declines anything outside scope |
| No internal logic exposed | Never mentions tools, tool names, or system rules to the caller |
| No troubleshooting | Never guides tenants through self-repair — only books visits |
| Flat number normalisation | Flat numbers preserved with letters (e.g. A101, B205) |
| Max two flat-number attempts | If caller can't provide a valid flat after two tries, call ends politely |
| Date reference | Current IST datetime from `Verify_phone_number` response used for all relative date calculations |
| Date format | All datetimes submitted to tools are `YYYY-MM-DDTHH:MM:SS` |

---

## 12. Risks & Known Limitations

| Risk | Current State |
|------|---------------|
| Complaint creation via HTTP within webhook | Calls `https://tenant-management-mvp.onrender.com/complaints` internally — breaks with multiple workers. Acceptable for single-worker Render deploy; must be replaced with direct service call before multi-worker scaling. |
| `_last_call_ended_at` is in-memory | Resets on server restart; not shared across workers. Frontend may miss a refresh if server restarts mid-call. |
| Async `submit_complaint` — agent confirms before webhook runs | If the webhook fails, the tenant was told "filed successfully" but nothing was saved. Idempotency check mitigates retry duplicates; failures are visible in call logs. |
| No call recording storage | Transcripts are extracted from VAPI artifact but not stored in a separate auditable store. |
| French translation accuracy | Translation is done implicitly by the LLM — no explicit translation step or validation. |
| Feature flag checked after agent confirmation | Because `submit_complaint` is async, the agent already says "filed" before the feature flag check runs. Blocked complaints show in call logs as `blocked_by_feature_flag`. |
| `property_group_id` not forwarded | If Alex forgets to pass `property_group_id` to a tool (LLM non-determinism), the complaint may be created without a group association. System prompt rule and complaint validator should guard against this. |
| Wrong tenant calls single global number | With one number for all groups, a caller who doesn't know their flat number has no fallback routing. Max two flat-number attempts then polite end-call is the guard. |

---

## 13. Open Items (Future Improvements)

| Item | Notes |
|------|-------|
| Replace internal HTTP call with direct service function | Avoids multi-worker issues; refactor `POST /voice/webhook` → call `ComplaintService.create()` directly |
| Distributed call status store | Move `_last_call_ended_at` to Redis or Supabase so it persists across restarts and workers |
| Call recording playback | Store VAPI recording URL in `call_logs`; surface in Voice Stats tab |
| Complaint status updates over voice | Caller could ask "what's the status of my repair?" — requires lookup tool |
| Tenant SMS confirmation | Send SMS to tenant after complaint filed (Twilio infra already exists) |
| Priority escalation for emergencies | Emergency calls create complaint with `priority = "high"` instead of `"medium"` |
| Configurable voice per PropertyGroup | Today voice ID is hardcoded; managers could pick from a set of voices |
