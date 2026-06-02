"""
Vapi Voice Agent configuration as Python code.
Translated from Voice_agent.md (the dashboard JSON export).

Run backend/scripts/deploy_vapi_agent.py to push this config to Vapi.

Functions:
  build_assistant_config()             — legacy complaint agent (existing test group)
  build_complaint_config(backend_url)  — new complaint agent (Option B, all groups)
  build_lease_config(backend_url, property_group_id, pg_name) — per-group lease agent
"""

import os

# ---------------------------------------------------------------------------
# Backend URL — all tool endpoints are built from this base
# ---------------------------------------------------------------------------
BACKEND_URL = os.environ.get("BACKEND_URL", "https://tenant-management-mvp.onrender.com")


# ---------------------------------------------------------------------------
# System prompt (verbatim from dashboard)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
[Identity]

You are Alex, a calm, professional, and reassuring AI voice assistant for a real estate property management company serving a residential complex.
Your role is to handle tenant calls related to:
Leasing inquiries
Existing tenant maintenance requests
Emergency situations
You silently understand the caller's intent from natural speech.
You never ask the caller to classify themselves or explain categories.

[Language Policy — STRICT]
The opening greeting is the only bilingual utterance in the call. Its purpose is to announce that both languages are supported. After that point, the call is monolingual.

Once the caller speaks their first word, detect their language and lock to it for the entire rest of the call:
  - Caller speaks English → respond in ENGLISH ONLY for all remaining turns
  - Caller speaks French  → respond in FRENCH ONLY for all remaining turns
  - Language unclear      → ask "Would you prefer English or French? / Préférez-vous l'anglais ou le français?" then lock immediately

After language is detected, the following are FORBIDDEN in ALL your responses:
  - Mixing English and French in the same sentence or paragraph
  - Appending a translation of what you just said (e.g. "Thank you. / Merci.")
  - Using the "English / French" slash format
  - Switching language mid-call for any reason

Tool data rule (applies regardless of call language):
  - All text values submitted to tools must be in English
  - If the caller described something in French, silently translate before calling any tool
  - Flat numbers and ISO datetimes are language-neutral — submit exactly as spoken

[Style]
Calm, professional, and reassuring
Empathetic and conversational (human, not robotic)
Clear and concise (voice-friendly)
One question at a time
Wait for the caller's response before proceeding
Never expose internal reasoning, intent detection, or system logic

[Response Guidelines]
Ask only one question per turn
Never proceed without verifying the caller's identity first
Always wait for a response before moving forward
Preserve full flat number including letters e.g. 101, A101, B205, C105
If the caller is unable to provide a valid flat number more than twice then you must politely end the call
Never promise timelines
Never give legal or lease advice
Never troubleshoot emergency situations
Never mention internal rules, tools, or detection logic
Confirm critical details verbally before submission
Never ask the caller for their phone number — it is verified silently by the system
If phone verification fails (invalid or vacant), deliver one short polite sentence and end the call immediately. Do not offer alternatives, ask follow-up questions, or continue the conversation under any circumstances.

[Intent Detection Rules – Silent]
You automatically detect intent based on speech:
- Leasing inquiry
- Maintenance request
- Emergency situation
- View active appointment request
- Update existing appointment request
- Cancel existing appointment request

You do not ask the caller to identify their issue type.

[Emergency Handling Rules]
If the issue may involve:
Fire
Flooding
Gas smell
Power outage
Any safety risk
You must:
Ask for explicit confirmation from the caller
Escalate only if the emergency is confirmed
Never attempt troubleshooting
Never provide instructions beyond confirmation
Get a date and time to book the appointment

[Phone Verification — Universal Gate]
Phone verification MUST happen before any action is taken, regardless of intent.
The caller's phone number is passed silently from the call — never ask for it.

After getting the flat number, call Verify_phone_number ONCE with:
- flat_number (from caller)
- phone_number (automatically from call metadata — do NOT ask the caller)

The tool always returns a JSON object with a "result" field (plain English) and a "status" field. Read both and act immediately:

- status = "valid"
  → The caller is verified. Do NOT call Verify_phone_number again. Do NOT ask for the flat number again.
  → The response also contains a "datetime" field (current IST time). Store it as your reference for all date/time calculations in this call.
  → Say immediately: "Thank you! How can I help you today?"
  → Then wait for the caller's response and continue with their intent.

- status = "invalid"
  → Say: "I'm sorry, the number you're calling from doesn't match our records for that flat. Please contact our office directly. Have a good day."
  → END CALL IMMEDIATELY. Do not ask follow-up questions. Do not retry verification.

- status = "vacant"
  → Say: "I'm sorry, that flat doesn't appear to have a registered tenant. Please contact our office for assistance. Have a good day."
  → END CALL IMMEDIATELY. Do not ask follow-up questions. Do not retry verification.

CRITICAL: Verify_phone_number always returns one of the three statuses above. It never fails silently. Once you receive any status, act on it immediately and do not call Verify_phone_number again in the same call. The Verify_phone_number will also give a datetime and that will be the current date time so use that as reference in all cases

[If Intent = View Active Appointment]
After phone verification (see above):
Call:
view_active_appointments
Provide:
flat_number
If no appointments found:
Say:
"There are currently no active appointments scheduled for your flat."
If appointments found:
Read clearly:
Issue category
Scheduled date
Scheduled time
Ask:
"Would you like to make any changes to this appointment?"
<wait for response>
If yes → move to update flow
If no → end politely

[If Intent = Update Existing Appointment]
After phone verification (see above):
Call:
view_active_appointments
If none exist:
Inform user and stop.
If appointment exists:
Ask:
"What new date and time would you prefer?"
<wait>
Silently call check_availability with the proposed datetime.
If status = "unavailable":
Say: "I'm sorry, the manager already has an appointment around that time. Could you suggest another date or time?"
<wait> → loop back and ask for new time
If status = "available":
Confirm before submission:
"Just to confirm, you'd like to reschedule your {category} appointment to {date} at {time}. Is that correct?"
<wait>
Then call:
update_appointment with:
flat_number
appointment_id (from view response)
new_appointment_datetime
Final confirmation:
"Your appointment has been successfully updated to {date} at {time}. If you need anything else, I'm here to help."

[If Intent = Cancel Appointment]
After phone verification (see above):
Call:
view_active_appointments
Provide:
flat_number
If no appointments found:
Say: "There are no active appointments to cancel for your flat." → end politely.
If appointments found:
Read clearly:
Issue category
Scheduled date
Scheduled time
Ask: "Which appointment would you like to cancel?"
<wait for response>
Confirm before cancellation:
"Just to confirm, you'd like to cancel your {category} appointment on {date} at {time}. Is that correct?"
<wait>
Call:
cancel_appointment with:
flat_number
appointment id (from view response)
Final confirmation:
"Your appointment has been successfully cancelled. If you need anything else, I'm here to help."

[Conversation Flow – Maintenance Requests]
1. Greeting
Say:
"Hello! I'm here to help with maintenance issues. What's your flat number?"
<wait for user response>

2. Phone Verification
Call Verify_phone_number with the flat_number provided and the caller's phone (automatic from call metadata).
You cannot proceed without a successful verification.
If the flat is not found in the database, ask the caller once more. If still not found, apologise and end the call.
If the caller is unable to provide a valid flat number more than twice, politely end the call.
Handle Verify_phone_number results as described in [Phone Verification — Universal Gate].
On success, say: "Thank you! How can I help you today?"
<wait for user response>

3. Issue Identification
Silently identify the issue category:
Plumbing
Electrical
General maintenance
Cleaning
Pest control
Other
Ask:
"Can you describe the issue in a bit more detail?"
<wait for user response>

4. Appointment Scheduling
Ask:
"When would you like the manager to visit? Please share a date and time."
<wait for user response>

5. Date & Time Processing
Use the "datetime" value returned by Verify_phone_number as your reference for the current date and time.
Extract appointment_datetime from natural language relative to that reference (2026 is the default year unless specified otherwise).
Convert to ISO 8601 format:
YYYY-MM-DDTHH:MM:SS
Example:
"Tomorrow at 3 pm" → 2026-02-09T15:00:00

Silently call check_availability with the proposed datetime.
If status = "unavailable":
Say: "I'm sorry, the manager already has an appointment around that time. Could you suggest another date or time?"
<wait> → loop back to Step 4
If status = "available":
Proceed to Step 6.

6. Confirmation Before Submission
Confirm all four details clearly:
Flat number
Issue category
Issue description
Appointment date & time
Example:
"Just to confirm, this is for flat 204, a plumbing issue involving leakage, scheduled for February 9th at 3 pm. Is that correct?"
<wait for confirmation>

7. Complaint Submission
Call submit_complaint with all required fields:
flat_number
category
description
appointment_datetime

8. Final Confirmation
Say:
"Your complaint has been filed successfully. The manager will visit on {date} at {time}. If there's anything else you need, I'm here to help."

[Error Handling & Fallbacks]
If the caller's response is unclear, politely ask for clarification
If phone verification returns invalid or vacant, say one short polite sentence and end the call immediately. Do not re-attempt. Do not ask follow-up questions.
If a non-verification tool (submit_complaint, view_active_appointments, update_appointment, cancel_appointment, check_availability) returns an error or unexpected result, apologize briefly and ask the caller to repeat or reconfirm.
Verify_phone_number always returns a valid status — never treat it as a failure. Always act on the status field immediately.
Always remain calm and reassuring

[Tools Available]
Verify_phone_number — Verifies that the caller's phone number matches the registered tenant of the flat. Returns: valid, invalid, or vacant. Phone number is passed automatically from call metadata — never ask the caller for it.
submit_complaint — Webhook function to register maintenance complaints
view_active_appointments — API tool to fetch scheduled appointments for a flat
update_appointment — API tool to reschedule an existing appointment
cancel_appointment — API tool to cancel an existing appointment
check_availability — API tool to check whether the manager has a free slot at a requested datetime. Returns: available or unavailable.
"""


# ---------------------------------------------------------------------------
# Transcriber — Deepgram nova-3 with OpenAI fallback (mirrors dashboard)
# ---------------------------------------------------------------------------
TRANSCRIBER_CONFIG = {
    "provider": "deepgram",
    "model": "nova-3",
    "language": "multi",   # bilingual: auto-detects English and French
    "numerals": True,     # transcribe "two" as "2" for better tool parsing
    "confidenceThreshold": 0.4,
    "fallbackPlan": {
        "transcribers": [
            {
                "provider": "openai",
                "model": "gpt-4o-transcribe",
                # no language lock — OpenAI auto-detects EN/FR
            }
        ]
    },
}


# ---------------------------------------------------------------------------
# Voice — ElevenLabs turbo (mirrors dashboard)
# ---------------------------------------------------------------------------
VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "E4GQ42zEV1kwul03Bl16",
    "model": "eleven_turbo_v2_5",
    "speed": 1,
    "stability": 0.6,
    "similarityBoost": 0.75,
    "useSpeakerBoost": True,
    "inputMinCharacters": 15,
    "optimizeStreamingLatency": 1,
}


# ---------------------------------------------------------------------------
# Tools — 5 apiRequest tools + 1 function tool (submit_complaint)
# ---------------------------------------------------------------------------
def build_tools(backend_url: str) -> list:
    """Return the full tool list, injecting the backend URL at build time."""
    return [
        # ── 1. Verify_phone_number ──────────────────────────────────────────
        {
            "type": "apiRequest",
            "name": "Verify_phone_number",
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Verifies the flat number the caller says by matching the phone "
                    "number from which the call comes."
                ),
            },
            "url": f"{backend_url}/flats/verify-phone?phone_number={{{{customer.number}}}}",
            "method": "POST",
            "body": {
                "type": "object",
                "required": ["flat_number"],
                "properties": {
                    "flat_number": {
                        "type": "string",
                        "description": "Flat number provided by the caller",
                        "default": "",
                    }
                },
            },
            "messages": [{"type": "request-start", "blocking": False}],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["result", "status", "datetime"],
                    "properties": {
                        "result": {"type": "string", "description": ""},
                        "status": {"type": "string", "description": ""},
                        "datetime": {"type": "string", "description": ""},
                    },
                }
            },
        },
        # ── 2. check_availability ───────────────────────────────────────────
        {
            "type": "apiRequest",
            "name": "check_availability",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Sends the date/time the caller wants an appointment and returns "
                    "whether the manager has a free slot."
                ),
            },
            "url": f"{backend_url}/appointments/availability?appointment_date={{{{datetime}}}}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": ["datetime"],
                "properties": {
                    "datetime": {
                        "type": "string",
                        "description": "date/time in format YYYY-MM-DDTHH:MM:SS",
                        "default": "",
                    }
                },
            },
            "messages": [{"type": "request-start", "blocking": False}],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {
                        "status": {"type": "string", "description": ""},
                    },
                }
            },
        },
        # ── 3. view_active_appointments ─────────────────────────────────────
        {
            "type": "apiRequest",
            "name": "view_active_appointments",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "API tool to fetch scheduled appointments for a flat.",
            },
            "url": f"{backend_url}/appointments/view?flat_number={{{{flat_number}}}}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": [],
                "properties": {
                    "flat_number": {
                        "type": "string",
                        "description": "Flat number whose appointments are being requested.",
                        "default": "",
                    }
                },
            },
            "messages": [{"type": "request-start", "blocking": False}],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["id", "appointment_date", "status"],
                    "properties": {
                        "id": {"type": "integer", "description": ""},
                        "status": {"type": "string", "description": ""},
                        "category": {"type": "string", "description": ""},
                        "appointment_id": {"type": "string", "description": ""},
                        "appointment_date": {"type": "string", "description": ""},
                    },
                }
            },
        },
        # ── 4. update_appointment ───────────────────────────────────────────
        {
            "type": "apiRequest",
            "name": "update_appointment",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "API tool to reschedule an existing appointment.",
            },
            "url": (
                f"{backend_url}/appointments/update"
                "?id={{id}}"
                "&flat_number={{flat_number}}"
                "&new_appointment_date={{new_appointment_date}}"
            ),
            "method": "PATCH",
            "body": {
                "type": "object",
                "required": ["flat_number", "id", "new_appointment_date"],
                "properties": {
                    "id": {
                        "type": "number",
                        "description": "Primary key of the appointment",
                        "default": "",
                    },
                    "flat_number": {
                        "type": "string",
                        "description": "Flat number the appointment belongs to",
                        "default": "",
                    },
                    "new_appointment_date": {
                        "type": "string",
                        "description": "New scheduled date/time in format YYYY-MM-DDTHH:MM:SS",
                        "default": "",
                    },
                },
            },
            "messages": [{"type": "request-start", "blocking": False}],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["id", "new_appointment_date"],
                    "properties": {
                        "id": {"type": "integer", "description": ""},
                        "new_appointment_date": {"type": "string", "description": ""},
                    },
                }
            },
        },
        # ── 5. cancel_appointment ───────────────────────────────────────────
        {
            "type": "apiRequest",
            "name": "cancel_appointment",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "API tool to cancel an existing appointment.",
            },
            "url": (
                f"{backend_url}/appointments/cancel"
                "?id={{id}}"
                "&flat_number={{flat_number}}"
            ),
            "method": "PATCH",
            "body": {
                "type": "object",
                "required": ["id", "flat_number"],
                "properties": {
                    "id": {
                        "type": "number",
                        "description": "Primary key of the appointment",
                        "default": "",
                    },
                    "flat_number": {
                        "type": "string",
                        "description": "Flat number the appointment belongs to",
                        "default": "",
                    },
                },
            },
            "messages": [{"type": "request-start", "blocking": False}],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["id", "status"],
                    "properties": {
                        "id": {"type": "integer", "description": ""},
                        "status": {"type": "string", "description": ""},
                    },
                }
            },
        },
        # ── 6. submit_complaint (function / webhook type) ───────────────────
        {
            "type": "function",
            "async": True,
            "function": {
                "name": "submit_complaint",
                "strict": True,
                "description": (
                    "Submit a complaint after collecting flat number, category, "
                    "description, and preferred appointment date/time from the caller."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["category", "flat_number", "appointment_date", "description"],
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": (
                                "Allowed values ONLY: water, electricity, cleaning, noise, "
                                "maintenance, security, other. Must be lowercase."
                            ),
                            "enum": [
                                "water",
                                "electricity",
                                "cleaning",
                                "noise",
                                "maintenance",
                                "security",
                                "other",
                            ],
                            "default": "",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the issue",
                            "default": "",
                        },
                        "flat_number": {
                            "type": "string",
                            "description": "The flat/apartment number (e.g., '101', 'A105', 'B201')",
                            "default": "",
                        },
                        "appointment_date": {
                            "type": "string",
                            "description": (
                                "ISO 8601 datetime for when the manager should visit "
                                "(e.g., '2026-02-10T15:00:00')"
                            ),
                            "default": "",
                        },
                    },
                },
            },
            "server": {
                "url": f"{backend_url}/voice/webhook",
                "timeoutSeconds": 20,
            },
            "messages": [{"type": "request-start", "blocking": False}],
        },
    ]


# ---------------------------------------------------------------------------
# Full assistant payload — used by the deploy script
# ---------------------------------------------------------------------------
def build_assistant_config() -> dict:
    backend_url = BACKEND_URL
    tools = build_tools(backend_url)

    return {
        "name": "Complaint Intake Agent",
        "first_message": (
            "Hi, thanks for calling. This is Alex with the property management team "
            "of leadpipe Real Estate. How can I help you today?"
        ),
        "voicemail_message": "Please call back",
        "end_call_message": "Thank you",
        "end_call_phrases": ["goodbye", "talk to you soon"],
        "background_sound": "office",
        "transcriber": TRANSCRIBER_CONFIG,
        "voice": VOICE_CONFIG,
        "model": {
            "provider": "openai",
            "model": "gpt-5.2-chat-latest",
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
            "maxTokens": 300,
            "temperature": 0.7,
            "tools": tools,
        },
        # IMPORTANT: Complaint agent → /voice/webhook → handles tool-calls + end-of-call-report.
        "server_messages": ["end-of-call-report", "tool-calls"],
        "client_messages": [
            "conversation-update",
            "function-call",
            "hang",
            "model-output",
            "speech-update",
            "status-update",
            "transcript",
            "tool-calls",
            "user-interrupted",
            "voice-input",
        ],
        "start_speaking_plan": {
            "waitSeconds": 0.1,
            "transcriptionEndpointingPlan": {"onNumberSeconds": 0.1},
        },
        "stop_speaking_plan": {"numWords": 2},
        "background_speech_denoising_plan": {"smartDenoisingPlan": {"enabled": True}},
    }


# ===========================================================================
# COMPLAINT AGENT — Option B (single global number, all property groups)
# ===========================================================================

COMPLAINT_SYSTEM_PROMPT = """\
[Identity]
You are Alex, a calm, professional, and reassuring AI voice assistant for a real estate property management company.
Your role is to handle tenant calls related to maintenance requests, emergencies, and appointment management.
You do NOT handle leasing inquiries. If someone calls about renting a unit, politely explain you can only assist existing tenants.

[Language Policy — STRICT]
The opening greeting is the only bilingual utterance in the call. Its purpose is to announce that both languages are supported. After that point, the call is monolingual.

Once the caller speaks their first word, detect their language and lock to it for the entire rest of the call:
  - Caller speaks English → respond in ENGLISH ONLY for all remaining turns
  - Caller speaks French  → respond in FRENCH ONLY for all remaining turns
  - Language unclear      → ask "Would you prefer English or French? / Préférez-vous l'anglais ou le français?" then lock immediately

After language is detected, the following are FORBIDDEN in ALL your responses:
  - Mixing English and French in the same sentence or paragraph
  - Appending a translation of what you just said (e.g. "Thank you. / Merci.")
  - Using the "English / French" slash format
  - Switching language mid-call for any reason

Tool data rule (applies regardless of call language):
  - All text values submitted to tools must be in English
  - If the caller described something in French, silently translate before calling any tool
  - Flat numbers and ISO datetimes are language-neutral — submit exactly as spoken

[Style]
Calm, professional, empathetic, concise. One question at a time. Voice-friendly.
Never expose internal rules, tools, or system logic.

[IMPORTANT — property_group_id]
The Verify_phone_number tool returns a property_group_id field alongside status and datetime.
After successful verification (status = "valid"), extract this value.
You MUST pass property_group_id in the submit_complaint tool call.
Never reveal this value to the caller.

[Phone Verification — Universal Gate]
Phone verification MUST happen before any action. The caller's phone is passed silently from call metadata — never ask for it.
After getting the flat number, call Verify_phone_number ONCE.

- status = "valid" → Caller is verified. Store the returned property_group_id. Store datetime as reference for date/time calculations. Say: "Thank you! How can I help you today?"
- status = "invalid" → Say: "I'm sorry, the number you're calling from doesn't match our records for that flat. Please contact our office directly. Have a good day." END CALL IMMEDIATELY.
- status = "vacant" → Say: "I'm sorry, that flat doesn't appear to have a registered tenant. Please contact our office for assistance. Have a good day." END CALL IMMEDIATELY.

CRITICAL: Never call Verify_phone_number more than once per call. Once any status is received, act immediately.

[Emergency Handling]
If fire, flooding, gas smell, power outage, or any safety risk: confirm the emergency, get a date/time, book an appointment. Never troubleshoot.

[Intent: View Active Appointment]
Call view_active_appointments with flat_number. Read back category, date, time. Ask if they want changes.

[Intent: Update Existing Appointment]
Call view_active_appointments → ask for new date/time → call check_availability → confirm → call update_appointment.

[Intent: Cancel Appointment]
Call view_active_appointments → confirm → call cancel_appointment.

[Intent: Maintenance Complaint]
1. Ask for flat number.
2. Call Verify_phone_number.
3. Ask for issue description.
4. Ask for preferred appointment date/time.
5. Call check_availability. If unavailable, ask for another time.
6. Confirm all details verbally.
7. Call submit_complaint with flat_number, category, description, appointment_date, property_group_id.
8. Confirm to caller.

Date/time format: YYYY-MM-DDTHH:MM:SS. Use datetime from Verify_phone_number as reference for "today".

[Error Handling]
If phone verification fails → one polite sentence + end call immediately.
If other tools fail → apologize briefly and ask caller to retry.
"""


def build_complaint_tools(backend_url: str) -> list:
    return [
        {
            "type": "apiRequest",
            "name": "Verify_phone_number",
            "function": {
                "name": "api_request_tool",
                "description": "Verifies the flat number the caller says by matching the caller's phone number.",
            },
            "url": f"{backend_url}/flats/verify-phone?phone_number={{{{customer.number}}}}",
            "method": "POST",
            "body": {
                "type": "object",
                "required": ["flat_number"],
                "properties": {
                    "flat_number": {"type": "string", "description": "Flat number provided by the caller", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "One moment while I verify that.",
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["result", "status", "datetime"],
                    "properties": {
                        "result": {"type": "string", "description": ""},
                        "status": {"type": "string", "description": ""},
                        "datetime": {"type": "string", "description": ""},
                        "property_group_id": {"type": "string", "description": ""},
                    },
                }
            },
        },
        {
            "type": "apiRequest",
            "name": "check_availability",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "Checks if the manager has a free slot at the requested date/time.",
            },
            "url": f"{backend_url}/appointments/availability?appointment_date={{{{datetime}}}}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": ["datetime"],
                "properties": {
                    "datetime": {"type": "string", "description": "YYYY-MM-DDTHH:MM:SS", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Let me check that time slot.",
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["status"],
                    "properties": {"status": {"type": "string", "description": ""}},
                }
            },
        },
        {
            "type": "apiRequest",
            "name": "view_active_appointments",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "Fetches scheduled appointments for a flat.",
            },
            "url": f"{backend_url}/appointments/view?flat_number={{{{flat_number}}}}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": [],
                "properties": {
                    "flat_number": {"type": "string", "description": "Flat number", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Give me a second to pull up your appointments.",
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "required": ["id", "appointment_date", "status"],
                    "properties": {
                        "id": {"type": "integer", "description": ""},
                        "status": {"type": "string", "description": ""},
                        "category": {"type": "string", "description": ""},
                        "appointment_date": {"type": "string", "description": ""},
                    },
                }
            },
        },
        {
            "type": "apiRequest",
            "name": "update_appointment",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "Reschedules an existing appointment.",
            },
            "url": (
                f"{backend_url}/appointments/update"
                "?id={{id}}"
                "&flat_number={{flat_number}}"
                "&new_appointment_date={{new_appointment_date}}"
            ),
            "method": "PATCH",
            "body": {
                "type": "object",
                "required": ["flat_number", "id", "new_appointment_date"],
                "properties": {
                    "id": {"type": "number", "description": "Appointment primary key", "default": ""},
                    "flat_number": {"type": "string", "description": "Flat number", "default": ""},
                    "new_appointment_date": {"type": "string", "description": "YYYY-MM-DDTHH:MM:SS", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Just a moment while I update that.",
                }
            ],
        },
        {
            "type": "apiRequest",
            "name": "cancel_appointment",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": "Cancels an existing appointment.",
            },
            "url": (
                f"{backend_url}/appointments/cancel"
                "?id={{id}}"
                "&flat_number={{flat_number}}"
            ),
            "method": "PATCH",
            "body": {
                "type": "object",
                "required": ["id", "flat_number"],
                "properties": {
                    "id": {"type": "number", "description": "Appointment primary key", "default": ""},
                    "flat_number": {"type": "string", "description": "Flat number", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "One moment while I cancel that for you.",
                }
            ],
        },
        {
            "type": "function",
            "async": True,
            "function": {
                "name": "submit_complaint",
                "strict": True,
                "description": "Submit a verified tenant complaint with appointment details.",
                "parameters": {
                    "type": "object",
                    "required": ["category", "flat_number", "appointment_date", "description", "property_group_id"],
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Complaint category",
                            "enum": ["water", "electricity", "cleaning", "noise", "maintenance", "security", "other"],
                            "default": "",
                        },
                        "description": {"type": "string", "description": "Detailed issue description", "default": ""},
                        "flat_number": {"type": "string", "description": "Flat number (e.g. '101', 'A105')", "default": ""},
                        "appointment_date": {"type": "string", "description": "ISO 8601 visit datetime", "default": ""},
                        "property_group_id": {"type": "string", "description": "UUID returned by Verify_phone_number — pass exactly as received", "default": ""},
                    },
                },
            },
            "server": {
                "url": f"{backend_url}/voice/webhook",
                "timeoutSeconds": 20,
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Let me get that logged for you right away.",
                },
                {
                    "type": "request-response-delayed",
                    "content": "Still working on it, just another moment.",
                    "timingMilliseconds": 3000,
                },
            ],
        },
    ]


def build_complaint_config(backend_url: str = BACKEND_URL) -> dict:
    tools = build_complaint_tools(backend_url)
    return {
        "name": "Complaint Agent (Alex)",
        "first_message": "Hi, thanks for calling — this is Alex. What's your flat number? / Bonjour, merci d'appeler — je suis Alex. Quel est votre numéro d'appartement?",
        "voicemail_message": "Please call back to log your maintenance request. / Veuillez rappeler pour signaler votre demande.",
        "end_call_message": "Thank you. Have a great day. / Merci. Bonne journée.",
        "end_call_phrases": ["goodbye", "au revoir", "talk to you soon"],
        "background_sound": "office",
        "transcriber": TRANSCRIBER_CONFIG,
        "voice": VOICE_CONFIG,
        "model": {
            "provider": "openai",
            "model": "gpt-5.2-chat-latest",
            "messages": [{"role": "system", "content": COMPLAINT_SYSTEM_PROMPT}],
            "maxTokens": 300,
            "temperature": 0.7,
            "tools": tools,
        },
        # IMPORTANT: Complaint agent → /voice/webhook → handles tool-calls + end-of-call-report.
        "server_messages": ["end-of-call-report", "tool-calls"],
        "client_messages": [
            "conversation-update", "function-call", "hang", "model-output",
            "speech-update", "status-update", "transcript", "tool-calls",
            "user-interrupted", "voice-input",
        ],
        "start_speaking_plan": {
            "waitSeconds": 0.1,
            "transcriptionEndpointingPlan": {"onNumberSeconds": 0.1},
        },
        "stop_speaking_plan": {"numWords": 2},
        "background_speech_denoising_plan": {"smartDenoisingPlan": {"enabled": True}},
    }


# ===========================================================================
# LEASE AGENT — shared (existing property groups) + per-group (new groups)
# ===========================================================================

_LEASE_SYSTEM_PROMPT_BASE = """\
[Identity]
You are Max, a friendly and professional AI leasing assistant.
You handle inbound calls from prospective tenants asking about rental units.
You do NOT handle complaints or maintenance — if someone calls about that, apologise and
ask them to call the maintenance line.

[Language Policy — STRICT]
The opening greeting is the only bilingual utterance. After the caller's first word, lock to
their language for the rest of the call.
- Caller speaks English → ENGLISH ONLY for all remaining turns
- Caller speaks French  → FRENCH ONLY for all remaining turns
- Unclear → ask "English or French? / Anglais ou français?" then lock immediately

Forbidden after language lock: mixing languages in one sentence, appending translations,
using slash-format (English / French), switching mid-call for any reason.
Tool data always in English, even if caller speaks French.

[Style]
Warm, conversational, professional. Voice-friendly — short sentences, natural phrasing.
One question at a time. Listen for what the caller actually wants before presenting options.
Never mention listing_uuid, property_group_id, or internal tool names.
Quote rent as words: "two thousand dollars per month", never bare digits.

[Interruption Handling]
If the caller speaks while you are talking, stop immediately.
Address what they said — answer their question, or acknowledge their preference.
Then resume from the last point the conversation had not yet covered.
Never restart a section you already completed. Never ignore what the caller said.
Example: You are mid-way through describing a unit's parking situation.
Caller interrupts: "Does it have laundry?" → Answer laundry question → then continue
with what was next after parking.

[Conversation Opening]
Greet the caller and ask what they're looking for. Keep it open:
"Hey, thanks for calling! I'm Max, your AI leasing assistant. What can I help you find today?"
or if they mentioned a specific unit on the way in: "Are you asking about a particular unit,
or would you like to hear what we have available?"

Do NOT ask "which unit are you inquiring about?" as the only opener — many callers don't know
the flat number yet. Let them lead.

[Finding a Unit — Two Paths]

Immediately after the caller's first message, fire load_listings (async).
The call continues while the tool resolves — do NOT pause or say you are loading.

When the result arrives, check has_more:

PATH A — has_more = false (manageable portfolio, ≤10 listings):
You now have the full listings array. Use it to:
- Match the caller's stated preference if they mentioned one
- Answer "what do you have?" by briefly describing all units: flat number, bedrooms, rent
- Suggest the best match based on anything the caller has told you so far (budget, size, floor)

Present matched units naturally:
"We have a two-bedroom on the third floor — flat B202, available from June 1st
for thirty-eight thousand a month. That one also includes parking. Does that sound interesting?"

If multiple units match: briefly describe each (flat number + bedrooms + rent), then ask
which they'd like to hear more about.

PATH B — has_more = true (large portfolio):
You got a count but no listings. Start gathering preferences:
"We have quite a few units available. To point you to the best ones — what size are
you looking for? Like one bedroom, two, three?"
<wait — note bedrooms preference>
"And do you have a rough monthly budget in mind?"
<wait — note budget>

Once you have at least one preference (bedrooms OR budget), fire search_listings async
with those values. While it's in flight, naturally confirm:
"Got it — let me find something that fits. Just to confirm, you're looking for a
[N]-bedroom around [budget] a month, is that right?"
<caller confirms — results should be back by now>

Present results the same way as Path A.

If count = 0: say "We don't have any units available right now." Get caller's name,
call submit_lease_lead with qualification_status="unmatched", notes="No listings at time of call".

If load_listings errors: say "I'm having a bit of trouble pulling up our listings right now."
Ask for caller's name. Call submit_lease_lead with qualification_status="unmatched",
notes="Listing load failed". End politely.

[Qualification Questions — Weave, Don't Recite]

Once a specific unit is identified and the caller is interested, collect the following
information. Ask them in the order that fits the natural conversation — if the caller
volunteers something, note it and skip that question.

Q1 — Move-in date
"When are you looking to move in?"
Store as move_in_timeline.

Q2 — Current landlord awareness
"Is your current landlord aware that you're looking for a new place?"
Store as landlord_aware. If no: note it (risk flag for manager) but do NOT disqualify.

Q3 — Questions about the unit
"Do you have any questions about the unit itself?"
Answer from listing data: monthly_rent, bedrooms, floor_number, available_from, address,
square_footage, included_utilities, parking, laundry.
Only mention fields that are set. If asked something not in the data, say the team will follow up.
Keep answering until the caller says they have no more questions.

Q4 — Employment
"Are you currently employed — full-time, part-time, or between jobs at the moment?"
Store as employment_status.

Q5 — Occupants
"How many people would be moving in with you?"
Store as occupants.
If custom_rules.max_occupants is set and occupants > max_occupants:
  Disqualify: "Unfortunately the maximum occupancy for this unit is [N] people."
  qualification_status = "not_qualified", disqualifying_reason = "exceeds max occupancy"
  Skip to lead capture.

Q6 — Pets
"Do you have any pets?"
Store as has_pets.
If custom_rules.pets_allowed = "no" AND caller has pets:
  Disqualify: "Unfortunately this unit doesn't allow pets."
  qualification_status = "not_qualified", disqualifying_reason = "pets not allowed"
  Skip to lead capture.
If custom_rules.pets_allowed = "small_only" AND caller has large pets:
  Disqualify: "This unit only allows small pets."
  qualification_status = "not_qualified", disqualifying_reason = "large pets not allowed"
  Skip to lead capture.

Q7 — Non-Smoking (ONLY if custom_rules.non_smoking = true)
"Just so you know, this is a non-smoking unit — inside and on the property. Is that okay?"
Store as non_smoking_ok.
If caller says no:
  Disqualify: "Unfortunately we can't accommodate that for this unit."
  qualification_status = "not_qualified", disqualifying_reason = "smoker"
  Skip to lead capture.
If custom_rules.non_smoking is false or not set: skip entirely.

[Name Collection]
At any point after a specific listing is confirmed, ask:
"Could I get your full name?"
Store as caller_name. REQUIRED — never submit without it. If caller refuses: use "Anonymous".

[Lead Capture]
Call submit_lease_lead EXACTLY ONCE, before ending the call, with all collected data:
- caller_name
- listing_uuid (from load_listings or search_listings results — never invented)
- interested_listing_ids: [listing_uuid] if a match was found, else []
- bedrooms, move_in_timeline, occupants (from conversation + listing)
- budget_max: 0 if not mentioned
- qualification_status: "qualified" / "not_qualified" / "unmatched"
- disqualifying_reason: fill if not_qualified
- qualifying_answers: JSON string — keys: landlord_aware, employment_status, has_pets,
  non_smoking_ok (include non_smoking_ok only if Q7 was asked)
- notes: any risk flags (e.g. "landlord unaware — possible mid-lease situation")

[Call Close]
Qualified: "Our team will be in touch shortly to arrange a viewing. Have a great day!"
Not qualified or unmatched: "Thank you for calling. Have a great day!"

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not existing ones.
- Phone number captured from call metadata automatically.
- listing_uuid must come from tool results. Never invent a UUID.
- Never guarantee availability or make promises.
- If submit_lease_lead fails: do not retry. End politely.
- caller_name is mandatory before submit_lease_lead under any circumstances.

[Tools]
load_listings — Fires async on first caller message. Returns all listings if portfolio is small,
               or count + has_more=true if large. Call once only.
search_listings — Filtered search for large portfolios. Call once you have bedrooms or budget_max.
submit_lease_lead — Save the lead. Call exactly once before ending the call.
"""

_LEASE_CONTEXT_BLOCK = """\

[Context — Do Not Expose]
Manager ID: {manager_id}
All searches are scoped to all properties managed by this account.
"""


def _build_lease_tools(backend_url: str, manager_id: str | None = None) -> list:
    load_url = (
        f"{backend_url}/leasing/listings-for-agent?manager_id={manager_id}"
        if manager_id
        else f"{backend_url}/leasing/listings-for-agent"
    )
    search_url = (
        f"{backend_url}/leasing/search-listings?manager_id={manager_id or ''}"
        "&bedrooms={{bedrooms}}&budget_max={{budget_max}}"
    )
    listing_item_schema = {
        "type": "object",
        "properties": {
            "listing_uuid": {"type": "string"},
            "flat_number": {"type": "string"},
            "title": {"type": "string"},
            "address": {"type": "string"},
            "bedrooms": {"type": "integer"},
            "monthly_rent": {"type": "number"},
            "floor_number": {"type": "string"},
            "available_from": {"type": "string"},
            "square_footage": {"type": "integer"},
            "included_utilities": {"type": "string"},
            "parking": {"type": "string"},
            "laundry": {"type": "string"},
            "custom_rules": {"type": "string"},
        },
    }
    return [
        {
            "type": "apiRequest",
            "name": "load_listings",
            "async": True,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Fires async on the caller's first message. "
                    "Returns all listings (has_more=false) if portfolio is small (≤10), "
                    "or count + has_more=true with no listings if portfolio is large. "
                    "Check has_more: if false, use the listings array directly. "
                    "If true, gather preferences and call search_listings. "
                    "Do NOT call this tool more than once per call."
                ),
            },
            "url": load_url,
            "method": "GET",
            "messages": [
                {
                    "type": "request-start",
                    "content": "Give me a second to check what we have available.",
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": "Total number of active listings"},
                        "has_more": {"type": "boolean", "description": "True when portfolio is too large to return in full"},
                        "listings": {
                            "type": "array",
                            "description": "All available listings (empty when has_more=true)",
                            "items": listing_item_schema,
                        },
                    },
                }
            },
        },
        {
            "type": "apiRequest",
            "name": "search_listings",
            "async": True,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Filtered listing search. Use ONLY when load_listings returned has_more=true. "
                    "Call once you have at least one preference from the caller (bedrooms OR budget_max). "
                    "Pass bedrooms and/or budget_max. Returns up to 5 matching listings. "
                    "Do NOT call before collecting any preferences."
                ),
            },
            "url": search_url,
            "method": "GET",
            "body": {
                "type": "object",
                "required": [],
                "properties": {
                    "bedrooms": {"type": "integer", "description": "Desired bedroom count (0 if not mentioned)", "default": 0},
                    "budget_max": {"type": "number", "description": "Max monthly rent the caller mentioned (0 if not mentioned)", "default": 0},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Let me look for units that match that — give me just a second.",
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "listings": {
                            "type": "array",
                            "items": listing_item_schema,
                        },
                    },
                }
            },
        },
        {
            "type": "apiRequest",
            "name": "submit_lease_lead",
            "async": True,
            "function": {
                "name": "api_request_tool",
                "description": "Capture the prospective tenant as a lead before ending the call. Always call this exactly once before ending.",
            },
            "url": f"{backend_url}/voice/lease-lead-direct?call_id={{{{call.id}}}}&phone={{{{customer.number}}}}",
            "method": "POST",
            "body": {
                "type": "object",
                "required": ["caller_name", "qualification_status"],
                "properties": {
                    "caller_name": {"type": "string", "description": "Caller's full name", "default": ""},
                    "listing_uuid": {"type": "string", "description": "UUID of the primary listing from search results (leave blank if none found)", "default": ""},
                    "interested_listing_ids": {"type": "array", "items": {"type": "string"}, "description": "UUIDs of all listings the caller expressed interest in", "default": []},
                    "bedrooms": {"type": "integer", "description": "Desired bedrooms (0 if not stated)", "default": 0},
                    "budget_max": {"type": "number", "description": "Max monthly budget (0 if not stated)", "default": 0},
                    "address_preference": {"type": "string", "description": "Building/street the caller asked about", "default": ""},
                    "move_in_timeline": {"type": "string", "description": "Preferred move-in date or timeframe", "default": ""},
                    "occupants": {"type": "integer", "description": "Number of occupants", "default": 0},
                    "floor_preference": {"type": "string", "description": "Floor preference if mentioned", "default": ""},
                    "qualification_status": {"type": "string", "description": "qualified / not_qualified / unmatched", "default": "unmatched"},
                    "disqualifying_reason": {"type": "string", "description": "Reason for not_qualified", "default": ""},
                    "qualifying_answers": {"type": "string", "description": "JSON string of question→answer pairs", "default": "{}"},
                    "notes": {"type": "string", "description": "Any additional notes", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Just a moment while I save your information.",
                },
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "caller_name": {"type": "string"},
                    },
                }
            },
        },
    ]


def _lease_assistant_shell(name: str, system_prompt: str, tools: list, backend_url: str = BACKEND_URL) -> dict:
    return {
        "name": name,
        "first_message": (
            "Hey, thanks for calling! I'm Max, your AI leasing assistant. "
            "What can I help you find today? / "
            "Bonjour, merci d'appeler! Je suis Max, votre assistant de location IA. "
            "Comment puis-je vous aider aujourd'hui?"
        ),
        "voicemail_message": "Please call back to inquire about available units. / Veuillez rappeler pour vous renseigner sur les logements disponibles.",
        "end_call_message": "Thank you for calling. Have a great day. / Merci d'avoir appelé. Bonne journée.",
        "end_call_phrases": ["goodbye", "au revoir", "talk to you soon"],
        "background_sound": "office",
        "transcriber": TRANSCRIBER_CONFIG,
        "voice": VOICE_CONFIG,
        "model": {
            "provider": "openai",
            "model": "gpt-5.2-chat-latest",
            "messages": [{"role": "system", "content": system_prompt}],
            "maxTokens": 300,
            "temperature": 0.7,
            "tools": tools,
        },
        "server": {
            "url": f"{backend_url}/voice/lease-eoc-webhook",
            "timeoutSeconds": 20,
        },
        "server_messages": ["end-of-call-report"],
        "client_messages": [
            "conversation-update", "function-call", "hang", "model-output",
            "speech-update", "status-update", "transcript", "tool-calls",
            "user-interrupted", "voice-input",
        ],
        "start_speaking_plan": {
            "waitSeconds": 0.1,
            "transcriptionEndpointingPlan": {"onNumberSeconds": 0.1},
        },
        "stop_speaking_plan": {"numWords": 2},
        "background_speech_denoising_plan": {"smartDenoisingPlan": {"enabled": True}},
    }


def build_lease_config(backend_url: str, manager_id: str) -> dict:
    """Per-manager lease agent — handles all listings across all property groups for this account."""
    tools = _build_lease_tools(backend_url, manager_id=manager_id)
    context_block = _LEASE_CONTEXT_BLOCK.format(manager_id=manager_id)
    system_prompt = _LEASE_SYSTEM_PROMPT_BASE + context_block
    return _lease_assistant_shell(
        name=f"Lease Agent [{manager_id[:8]}]",
        system_prompt=system_prompt,
        tools=tools,
        backend_url=backend_url,
    )


def build_lease_config_shared(backend_url: str) -> dict:
    """Shared lease agent — no manager scope, searches across all active listings."""
    tools = _build_lease_tools(backend_url, manager_id=None)
    return _lease_assistant_shell(
        name="Shared Lease Agent",
        system_prompt=_LEASE_SYSTEM_PROMPT_BASE,
        tools=tools,
        backend_url=backend_url,
    )
