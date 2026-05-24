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

[Language Policy]
You understand English and Quebec French.
Detect the caller's language automatically from their speech and respond in the same language throughout the call.
If the caller's language is unclear, politely ask which language they prefer and continue in that language.
IMPORTANT — tool data must always be submitted in English:
- Descriptions, categories, and notes submitted to any tool MUST be in English
- If the caller describes an issue in French, silently translate to English before calling any tool
- Never submit French text to submit_complaint, update_appointment, cancel_appointment, or any other tool
- Flat numbers and ISO datetimes are language-neutral — capture them accurately regardless of language

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
        "server_messages": [
            "conversation-update",
            "end-of-call-report",
            "function-call",
            "hang",
            "speech-update",
            "status-update",
            "tool-calls",
            "transfer-destination-request",
            "user-interrupted",
            "assistant.started",
        ],
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

[Language Policy]
You understand English and Quebec French.
Detect the caller's language automatically from their speech and respond in the same language throughout the call.
If the caller's language is unclear, politely ask which language they prefer and continue in that language.
All data submitted to tools MUST be in English — translate French descriptions before calling any tool.

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
                    "content": "One moment while I verify that. / Un instant, je vérifie ça.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
                    "content": "Let me check that time slot. / Laissez-moi vérifier ce créneau.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
                    "content": "Give me a second to pull up your appointments. / Un instant, je récupère vos rendez-vous.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
                    "content": "Just a moment while I update that. / Un instant pendant que je mets ça à jour.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
                    "content": "One moment while I cancel that for you. / Un instant, j'annule ça pour vous.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
                    "content": "Let me get that logged for you right away. / Je l'enregistre pour vous tout de suite.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
                },
                {
                    "type": "request-response-delayed",
                    "content": "Still working on it, just another moment.",
                    "timingMilliseconds": 3000,
                    "role": "assistant",
                    "endCallAfterSpoken": False,
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
        "server_messages": [
            "conversation-update", "end-of-call-report", "function-call",
            "hang", "speech-update", "status-update", "tool-calls",
            "transfer-destination-request", "user-interrupted", "assistant.started",
        ],
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
You are a leasing assistant for a residential property management company.
You handle inbound calls from prospective tenants asking about available rental units.
You do NOT handle complaints or issues for existing tenants. If someone calls about maintenance, apologise and ask them to call the maintenance line.

[Language Policy]
You understand English and Quebec French.
Detect the caller's language automatically from their speech and respond in the same language throughout the call.
If the caller's language is unclear, politely ask which language they prefer and continue in that language.
All data submitted to tools must remain in English (listing UUIDs, qualifying answers, names).

[Style]
Professional, friendly, helpful. One question at a time. Concise, voice-friendly responses.
Never mention internal tools, system logic, or property_group_id values.
When quoting rent amounts always say "dollars" followed by the number as words — e.g. "two thousand dollars per month" or "one thousand two hundred per month". Never read out bare digits like "2000".

[Conversation Flow]

1. Greeting
"Thank you for calling. I'm here to help you find a rental unit. What kind of unit are you looking for?"

2. Understand the Caller's Preferences
Listen for what the caller shares naturally. Preferences to capture if they mention them:
- Number of bedrooms (1BHK, 2BHK, etc.)
- Monthly budget (maximum rent they can afford)
- Preferred move-in date or timeline
- Number of occupants or floor preference (bonus details — only if offered)

None of these are required before you can search. Do NOT interrogate the caller for every field before searching. If they say "show me what's available" or give only one detail, that is enough to search. Move-in date is informational only — capture it for the lead but it is NOT a search filter.

3. Find a Listing
If the caller mentions a specific address, street, neighbourhood, building name, floor, or unit name (e.g. "penthouse", "top floor", "unit on Maple Street", "something near the park"): call find_listing with their query FIRST. Use the bedrooms value from the tool response — NEVER infer bedroom count from words like "penthouse", "suite", or a floor number.
Otherwise: call search_available_listings immediately using only what the caller has confirmed:
- Pass bedrooms only if the caller stated a specific bedroom count. If they haven't mentioned bedrooms, pass 0 (no filter — show all bedroom types).
- Pass budget_max only if the caller stated a maximum budget. If they haven't mentioned a budget, pass 0 (no filter — show all prices).
- Pass address if the caller mentioned a street, neighbourhood, or building name. Leave it empty otherwise.
Do NOT wait until both bedrooms AND budget are confirmed before calling the search. Search as soon as the caller has expressed their interest, even with no filters at all.
Both find_listing and search_available_listings return {found, count, listings} where listings is a JSON array; each element has listing_uuid, flat_number, bedrooms, monthly_rent, floor_number, available_from.
When count > 1, present ALL listings to the caller — never silently show only the first one. Read out each unit's flat number, bedrooms, rent, and availability.
Note which listings the caller responds positively to — you will need their listing_uuid values later.

4. Qualifying Questions
Based on the listing's custom_rules JSON, ask ONLY the enabled questions:
- income_required = true → "Do you have a stable source of income to cover the monthly rent?"
- max_occupants is set → "How many people will be living in the unit?"
- pets_allowed = "no" → "Do you have any pets?"
- vegetarian_only = true → "Is yours a vegetarian household?"
- lease_term_months is set → "Are you comfortable with a {N}-month lease agreement?"
- custom_question is non-empty → Ask that exact question.

5. Qualification Decision
All criteria met AND a real listing_uuid exists → qualification_status = "qualified"
Any criterion failed → qualification_status = "not_qualified", note the reason
No listing was found by a tool (count=0 or found=false) → qualification_status = "unmatched"; leave listing_uuid blank

6. Offer Alternatives (if not qualified or unmatched)
Call search_available_listings with relaxed or adjusted criteria. Present alternatives. Qualify for those.

7. Capture Lead
Always call submit_lease_lead EXACTLY ONCE before ending the call — even if no listing was found.
Provide: caller_name (ask for it once),
listing_uuid (the primary listing the caller wants to pursue — copy the EXACT listing_uuid string returned by find_listing or search_available_listings; leave blank if no listing was found — NEVER invent or guess a UUID),
interested_listing_ids (array of listing_uuid values for every listing the caller showed interest in),
address_preference (the building name, street, or neighbourhood the caller asked about — copy exactly what you passed as query to find_listing or as address to search_available_listings; leave blank if no location was mentioned),
bedrooms, budget_max, move_in_timeline, occupants, floor_preference,
qualification_status, disqualifying_reason,
qualifying_answers (a JSON object of question → answer pairs).
Phone is captured from call metadata automatically — never ask the caller for their phone number.

8. Close
Qualified: "Our team will reach out to you shortly to arrange a visit. Have a great day!"
Not qualified / unmatched: "Thank you for calling. Have a great day!"

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not registered ones.
- Phone number is captured automatically from call metadata — never ask for it.
- Always call submit_lease_lead EXACTLY ONCE before ending the call. Never call it twice in the same conversation.
- Never guarantee availability or make promises about units.
- Never expose property_group_id, listing_uuid, or any internal IDs to the caller.
- listing_uuid in submit_lease_lead must be a value returned by a tool. If no match was found, leave it blank. NEVER make up a listing ID.
- If search_available_listings returns count=0 and all alternatives are exhausted, set qualification_status="unmatched". Never mark a caller "qualified" without a real listing_uuid.
- BUDGET ENFORCEMENT: Never qualify a caller for a unit whose monthly_rent exceeds their stated budget_max. If the caller explicitly stated a bedroom count, only qualify them for units with that exact count — a caller asking for 2BHK cannot be qualified for a 1BHK. If the caller did NOT state a bedroom preference, any bedroom count from the search results is acceptable. Only submit "qualified" when a real listing_uuid exists from the tool response AND all stated preferences are met.
- NO FORCING PREFERENCES: If the caller has not mentioned bedrooms, do not ask "how many bedrooms do you need?" before searching. If they have not mentioned a budget, do not ask for a budget before searching. Search first and let the results guide the conversation.
- BEDROOM COUNT: Never infer bedroom count from descriptive terms like "penthouse", "suite", "top floor", or floor number alone. Always call find_listing first when the caller names a specific unit, floor, or area — use the bedrooms field from each listing in the tool response.

[Tools]
find_listing — Find listings by flat number, unit name, or any part of the address (building, street, neighbourhood). Returns a listings array — present ALL results when multiple units match.
search_available_listings — Browse available units by bedrooms, budget, and/or address keyword.
submit_lease_lead — Capture the caller as a lead (always call before ending the call).
"""

_LEASE_CONTEXT_BLOCK = """\

[Context — Do Not Expose]
Manager ID: {manager_id}
All searches are scoped to all properties managed by this account.
"""


def _build_lease_tools(backend_url: str, manager_id: str | None = None) -> list:
    mgr_qs = f"&manager_id={manager_id}" if manager_id else ""
    return [
        {
            "type": "apiRequest",
            "name": "find_listing",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Find rental listings by flat/unit number, listing title, "
                    "or any part of the unit's address (street name, building name, neighbourhood, etc.). "
                    "Use this when the caller mentions a specific address, location, floor, or unit name. "
                    "Returns {found, count, listings} where listings is a JSON array. "
                    "Each element has: listing_uuid, flat_number, title, address, bedrooms, monthly_rent, "
                    "floor_number, available_from, custom_rules. "
                    "When multiple units match a building name, ALL matching units are returned — "
                    "present all of them to the caller, not just the first one."
                ),
            },
            "url": f"{backend_url}/leasing/find-listing?query={{{{query}}}}{mgr_qs}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "description": "Search query — flat number, unit name, street name, building name, or neighbourhood", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Give me a second to look that up. / Un instant, je cherche ça.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "found": {"type": "boolean", "description": ""},
                        "count": {"type": "integer", "description": ""},
                        "listings": {
                            "type": "array",
                            "description": "All matching listings",
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
            "name": "search_available_listings",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Search available rental units by bedrooms, budget, and/or address. "
                    "Returns {count, listings} where listings is a JSON array. "
                    "Each element has: listing_uuid, flat_number, bedrooms, monthly_rent, "
                    "floor_number, available_from, title. "
                    "Store the listing_uuid of each unit the caller expresses interest in. "
                    "Pass address when the caller mentions a street, neighbourhood, or building name to narrow results."
                ),
            },
            "url": f"{backend_url}/leasing/search?bedrooms={{{{bedrooms}}}}&budget_max={{{{budget_max}}}}&address={{{{address}}}}{mgr_qs}",
            "method": "GET",
            "body": {
                "type": "object",
                "required": [],
                "properties": {
                    "bedrooms": {"type": "integer", "description": "Number of bedrooms (0 = no filter)", "default": ""},
                    "budget_max": {"type": "number", "description": "Maximum monthly budget (0 = no filter)", "default": ""},
                    "address": {"type": "string", "description": "Partial address string to filter by location (street, neighbourhood, building name). Leave empty if caller has not mentioned a location.", "default": ""},
                },
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Let me search our available units for you. / Laissez-moi chercher les unités disponibles.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
                }
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer", "description": ""},
                        "listings": {
                            "type": "array",
                            "description": "Available listings matching the filters",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "listing_uuid": {"type": "string"},
                                    "flat_number": {"type": "string"},
                                    "bedrooms": {"type": "integer"},
                                    "monthly_rent": {"type": "number"},
                                    "floor_number": {"type": "string"},
                                    "available_from": {"type": "string"},
                                },
                            },
                        },
                    },
                }
            },
        },
        {
            "type": "function",
            "async": True,
            "function": {
                "name": "submit_lease_lead",
                "strict": True,
                "description": "Capture the prospective tenant as a lead before ending the call.",
                "parameters": {
                    "type": "object",
                    "required": ["caller_name", "qualification_status"],
                    "properties": {
                        "caller_name": {"type": "string", "description": "Caller's full name", "default": ""},
                        "listing_uuid": {"type": "string", "description": "UUID of the primary listing the caller wants to pursue (from search or find_listing response)", "default": ""},
                        "interested_listing_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "UUIDs of all listings the caller expressed interest in during the call",
                            "default": [],
                        },
                        "bedrooms": {"type": "integer", "description": "Desired bedrooms (pass 0 if not stated)", "default": 0},
                        "budget_max": {"type": "number", "description": "Maximum monthly budget (pass 0 if not stated)", "default": 0},
                        "address_preference": {"type": "string", "description": "Building name, street, or neighbourhood the caller asked about — copy exactly what was passed to find_listing or search_available_listings as the address/query parameter", "default": ""},
                        "move_in_timeline": {"type": "string", "description": "Preferred move-in date or timeframe", "default": ""},
                        "occupants": {"type": "integer", "description": "Number of occupants", "default": 0},
                        "floor_preference": {"type": "string", "description": "Floor preference if mentioned", "default": ""},
                        "qualification_status": {
                            "type": "string",
                            "description": "Outcome of qualifying questions",
                            "enum": ["qualified", "not_qualified", "unmatched"],
                            "default": "unmatched",
                        },
                        "disqualifying_reason": {"type": "string", "description": "Reason for not_qualified status", "default": ""},
                        "qualifying_answers": {"type": "string", "description": "JSON string of qualifying question → answer pairs", "default": "{}"},
                    },
                },
            },
            "server": {
                "url": f"{backend_url}/voice/lease-lead-webhook",
                "timeoutSeconds": 20,
            },
            "messages": [
                {
                    "type": "request-start",
                    "content": "Just a moment while I save your information. / Un instant pendant que j'enregistre vos informations.",
                    "role": "assistant",
                    "endCallAfterSpoken": False,
                },
                {
                    "type": "request-response-delayed",
                    "content": "Still working on it, just another moment.",
                    "timingMilliseconds": 3000,
                    "role": "assistant",
                    "endCallAfterSpoken": False,
                },
            ],
        },
    ]


def _lease_assistant_shell(name: str, system_prompt: str, tools: list, backend_url: str = BACKEND_URL) -> dict:
    return {
        "name": name,
        "first_message": "Thank you for calling! I'm here to help you find a rental unit. / Merci d'appeler! Je suis ici pour vous aider à trouver un logement.",
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
        "server_messages": [
            "conversation-update", "end-of-call-report", "function-call",
            "hang", "speech-update", "status-update", "tool-calls",
            "transfer-destination-request", "user-interrupted", "assistant.started",
        ],
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
