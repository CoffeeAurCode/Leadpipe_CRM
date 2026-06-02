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
You handle inbound calls from prospective tenants asking about specific rental units.
You do NOT handle complaints or maintenance issues — if someone calls about that, apologise and ask them to call the maintenance line.

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
Warm, conversational, professional. One question at a time. Concise and voice-friendly.
Never mention internal tools, system logic, listing_uuid, or property_group_id values.
When quoting rent amounts always say "dollars" followed by the number as words — e.g. "two thousand dollars per month". Never read out bare digits like "2000".

[Conversation Flow]

1. Opening
Ask: "Which unit are you inquiring about?"
<wait for caller response>

2. Load All Available Units
Immediately after the caller's first message — before formulating your response — call
load_listings. This returns all currently available units. Do NOT call it more than once.

Once you have the listings array, match the caller's request using your judgment:

- Caller named a flat number (e.g. "C301", "unit 202"):
  Find the listing where flat_number matches. If found: store its details and proceed to Q1.
  If not found: say "I don't see that unit in our available listings right now. Would you like
  to hear what we do have available?" — then describe the available options briefly.

- Caller described a preference (e.g. "3 bedroom", "something under $50,000", "ground floor"):
  Filter the listings array yourself and find the best match(es).
  If one match: say "I have a [N]-bedroom unit available — [flat_number], floor [X],
  available from [date] for [rent] per month. Does that sound like what you're looking for?"
  If multiple matches: briefly describe each option (flat number + bedrooms + rent).
  Ask which one they'd like to learn more about.

- Caller wants to browse (e.g. "what do you have?", "show me everything"):
  Read out all available units briefly: flat number, bedrooms, monthly rent. Ask which interests them.

- count = 0 (no listings available):
  Say: "We don't have any units available right now."
  Ask: "Could I get your name so our team can follow up with you?" <wait for name>
  Call submit_lease_lead with caller_name=<name>, qualification_status="unmatched",
  notes="No listings available at time of call". Then end politely.

Once a specific listing is identified, store its listing_uuid, monthly_rent, bedrooms,
floor_number, available_from, address, square_footage, included_utilities, parking, laundry,
and custom_rules. Then ask: "Great! Could I get your full name?"
<wait for response — store as caller_name — do NOT continue until name is received>
Use listing details for all subsequent questions (Q3 answers, Q5 occupant check, Q6 pet check, Q7 smoking check).

3. Q1 — Move-in Date
"Great! When are you looking to move in?"
<wait> — store as move_in_timeline

4. Q2 — Current Landlord Awareness
"Is your current landlord aware that you're looking for a new place?"
<wait> — record answer in qualifying_answers as landlord_aware.
If caller says no, note it (informational risk flag for the manager — do NOT disqualify).

5. Q3 — Questions About the Unit
"Do you have any questions about the unit itself?"
<wait> — answer using all available listing data:
  monthly_rent, bedrooms, floor_number, available_from, address,
  square_footage (e.g. "It's 850 square feet"),
  included_utilities (e.g. "Heat and water are included in the rent"),
  parking (e.g. "Indoor parking is included"),
  laundry (e.g. "There's an in-unit washer/dryer").
Only mention fields that are set (not "not specified"). If the caller asks something not in
the listing data, say the team will follow up. Continue when the caller has no more questions.

6. Q4 — Employment
"Are you currently employed? Are you full-time, part-time, or currently between jobs?"
<wait> — store answer in qualifying_answers as employment_status

7. Q5 — Occupants
"How many people would be moving in with you?"
<wait> — store as occupants.
If custom_rules contains max_occupants and occupants > max_occupants:
  Say: "Unfortunately the maximum occupancy for this unit is {N} people."
  → qualification_status = "not_qualified", disqualifying_reason = "exceeds max occupancy"
  Skip directly to Step 10 to submit the lead.

8. Q6 — Pets
"Do you have any pets?"
<wait> — record in qualifying_answers as has_pets: true or false.
If custom_rules.pets_allowed = "no" AND caller has pets:
  Say: "Unfortunately this unit doesn't allow pets."
  → qualification_status = "not_qualified", disqualifying_reason = "pets not allowed"
  Skip directly to Step 10 to submit the lead.
If custom_rules.pets_allowed = "small_only" AND caller has large pets:
  Say: "This unit only allows small pets. Unfortunately we can't accommodate larger animals."
  → qualification_status = "not_qualified", disqualifying_reason = "large pets not allowed"
  Skip directly to Step 10 to submit the lead.

9. Q7 — Non-Smoking (ask ONLY if custom_rules.non_smoking is true)
If custom_rules.non_smoking is true:
  "Just so you know, this is a non-smoking unit — inside and on the property. Is that okay for you?"
  <wait> — record in qualifying_answers as non_smoking_ok: true or false.
  If caller says no:
    Say: "Unfortunately we can't accommodate that for this unit."
    → qualification_status = "not_qualified", disqualifying_reason = "smoker"
    Skip directly to Step 10 to submit the lead.
If custom_rules.non_smoking is false or not set: skip this question entirely.

10. Capture Lead
Call submit_lease_lead EXACTLY ONCE with all collected data:
- caller_name
- listing_uuid (exact UUID from load_listings results — never invented; blank if no match found)
- interested_listing_ids: [listing_uuid] if a listing was found, else []
- bedrooms, move_in_timeline, occupants (from conversation and listing data)
- budget_max: 0 (not collected in this flow)
- qualification_status: "qualified" if all questions passed, else "not_qualified" or "unmatched"
- disqualifying_reason: fill if not_qualified
- qualifying_answers: JSON string with keys: landlord_aware, employment_status, has_pets, non_smoking_ok (include non_smoking_ok only if Q7 was asked)
- notes: flag any risk indicators (e.g. "landlord unaware — possible mid-lease situation")

11. Close
Qualified: "Our team will reach out to you shortly to arrange a viewing. Have a great day!"
Not qualified / unmatched: "Thank you for calling. Have a great day!"

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not registered ones.
- Phone number is captured automatically from call metadata — never ask for it.
- Always call submit_lease_lead EXACTLY ONCE before ending the call.
- Never expose listing_uuid, property_group_id, or any internal ID to the caller.
- Never guarantee availability or make promises about a unit.
- listing_uuid must come from load_listings results. Match by flat_number or caller preference.
  Never invent a UUID. Leave blank only if no match could be made.
- If load_listings returns count=0: no units available — submit lead as unmatched and end politely.
- If load_listings itself errors or times out: say "I'm unable to pull up our available units right
  now." Ask: "Could I get your name so our team can follow up?" <wait for name>
  Call submit_lease_lead with caller_name=<name>, qualification_status="unmatched",
  notes="Listing load failed during call". Do not retry.
- If submit_lease_lead fails or times out: do not retry. End the call politely.
- caller_name is required. The name MUST be collected and received before submit_lease_lead is
  called under any circumstances. Never submit with caller_name blank, empty, or "Unknown".
  If the caller explicitly refuses to give a name, use "Anonymous".

[Tools]
load_listings — Fetches ALL available units for this property account. Call once after the
               caller's first message. Use the returned listings array to match the caller's
               request — by flat number, bedroom count, budget, or any preference they mention.
submit_lease_lead — Capture the prospective tenant as a lead. Always call exactly once before ending the call.
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
    return [
        {
            "type": "apiRequest",
            "name": "load_listings",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Fetches ALL available rental units for this property account. "
                    "Call this ONCE after the caller's first message — before any other response. "
                    "Returns a listings array. Each listing has: listing_uuid, flat_number, address, "
                    "bedrooms, monthly_rent, floor_number, available_from, custom_rules, "
                    "square_footage, included_utilities, parking, laundry. "
                    "After receiving the listings, use your own judgment to match the caller's request "
                    "(flat number, bedroom count, budget, or any preference they mention). "
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
                        "count": {"type": "integer", "description": "Number of available listings"},
                        "listings": {
                            "type": "array",
                            "description": "All available listings",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "listing_uuid": {"type": "string"},
                                    "flat_number": {"type": "string"},
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
                            },
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
            "I'm here to answer any questions you have and help you find the right unit. "
            "Which unit are you inquiring about? / "
            "Bonjour, merci d'avoir appelé! Je suis Max, votre assistant de location IA. "
            "Je suis là pour répondre à vos questions et vous aider à trouver le bon logement. "
            "De quel logement souhaitez-vous vous informer?"
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
