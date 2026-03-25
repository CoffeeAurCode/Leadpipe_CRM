"""
Vapi Voice Agent configuration as Python code.
Translated from Voice_agent.md (the dashboard JSON export).

Run backend/scripts/deploy_vapi_agent.py to push this config to Vapi.
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
    "language": "en",
    "numerals": False,
    "confidenceThreshold": 0.4,
    "fallbackPlan": {
        "transcribers": [
            {
                "provider": "openai",
                "model": "gpt-4o-transcribe",
                "language": "en",
            }
        ]
    },
}


# ---------------------------------------------------------------------------
# Voice — ElevenLabs turbo (mirrors dashboard)
# ---------------------------------------------------------------------------
VOICE_CONFIG = {
    "provider": "11labs",
    "voiceId": "1SM7GgM6IMuvQlz2BwM3",
    "model": "eleven_turbo_v2_5",
    "stability": 0.5,
    "similarityBoost": 0.75,
    "inputMinCharacters": 5,
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
            "waitSeconds": 0.4,
            "smartEndpointingEnabled": "livekit",
        },
        "background_speech_denoising_plan": {
            "smartDenoisingPlan": {"enabled": True},
        },
    }
