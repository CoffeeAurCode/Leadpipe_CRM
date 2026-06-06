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
Flat number assembly rule: callers often spell out each character one at a time (e.g. "s 2 0 1", "a 1 0 5"). You MUST concatenate every spoken character into a single string with no spaces — letter prefix included. "s 2 0 1" → "S201", "a 1 0 5" → "A105", "b 2 0 5" → "B205". Never drop the letter. Never insert spaces or dashes.
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

# Complaint agent uses outbound calls with more carrier-layer noise at connection
# time than inbound lease calls — higher threshold filters connection-noise artifacts.
COMPLAINT_TRANSCRIBER_CONFIG = {
    **TRANSCRIBER_CONFIG,
    "confidenceThreshold": 0.6,
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
                            "description": "Flat number as a single string with no spaces. If the caller spelled it out character by character (e.g. 's 2 0 1'), concatenate all characters: 'S201'. Always include the letter prefix.",
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

[Language Policy]
Detect the caller's language from their first words and lock to it for the entire call.
  - Caller speaks English → respond in ENGLISH ONLY for all remaining turns
  - Caller speaks French  → respond in FRENCH ONLY for all remaining turns
  - Language unclear after 2 exchanges → ask "English or French? / Anglais ou français?" then lock

Do NOT mix languages in the same sentence. Do NOT append translations.
You may briefly offer both languages once ("English or French?") if the caller's language
is genuinely ambiguous — but do not force a bilingual greeting on every call.

After language is detected, the following are FORBIDDEN in ALL your responses:
  - Mixing English and French in the same sentence or paragraph
  - Appending a translation of what you just said (e.g. "Thank you. / Merci.")
  - Using the "English / French" slash format
  - Switching language mid-call for any reason

Tool data rule (applies regardless of call language):
  - All text values submitted to tools must be in English
  - If the caller described something in French, silently translate before calling any tool
  - ISO datetimes are language-neutral — submit exactly as spoken
  - Flat numbers: callers often spell each character aloud (e.g. "s 2 0 1"). You MUST concatenate all spoken characters into one string with no spaces — letter prefix included. "s 2 0 1" → "S201", "a 1 0 5" → "A105". Never drop the letter. Never add spaces or dashes.

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

[CALLBACK SCHEDULING FLOW]
After verifying the caller and collecting the complaint details (flat number, category, description):
1. Ask: "When would you like the manager to call you back? Please give me a date and time."
2. Call check_availability to confirm the manager is free at that time.
   - If unavailable, suggest the next available slot.
3. Confirm back to the caller: "I'll schedule a manager callback for [day] at [time]. The manager will call you back on your registered phone number."
4. Call submit_complaint with flat_number, category, description, appointment_date (the preferred callback time), property_group_id.
5. After submission: "Your complaint has been logged and a callback is scheduled."

DO NOT use words like "technician", "visit", "maintenance appointment", or "engineer".
Always say "manager callback" or "call back from the manager".
appointment_date means the preferred callback time — when the tenant wants the manager to call them back.

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
                    "flat_number": {"type": "string", "description": "Flat number as a single string with no spaces. If the caller spelled it out (e.g. 's 2 0 1'), concatenate all characters: 'S201'. Always include the letter prefix.", "default": ""},
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
                        "flat_number": {"type": "string", "description": "Flat number as a single string with no spaces. If the caller spelled it out (e.g. 's 2 0 1'), concatenate all characters: 'S201'. Always include the letter prefix.", "default": ""},
                        "appointment_date": {"type": "string", "description": "ISO 8601 datetime for the manager callback call — when the tenant wants the manager to call them back. Format: YYYY-MM-DDTHH:MM:SS", "default": ""},
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
        "first_message": "Hi, this is Alex — how can I help you today?",
        "voicemail_message": "Please call back to log your maintenance request. / Veuillez rappeler pour signaler votre demande.",
        "end_call_message": "Thank you. Have a great day. / Merci. Bonne journée.",
        "end_call_phrases": ["goodbye", "au revoir", "talk to you soon"],
        "background_sound": "office",
        "first_message_mode": "assistant-speaks-first",
        "transcriber": COMPLAINT_TRANSCRIBER_CONFIG,
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
        "stop_speaking_plan": {"numWords": 5},
        "background_speech_denoising_plan": {"smartDenoisingPlan": {"enabled": True}},
    }


# ===========================================================================
# LEASE AGENT — shared (existing property groups) + per-group (new groups)
# ===========================================================================

_LEASE_SYSTEM_PROMPT_BASE = """\
[Identity]
You are Max, a friendly and professional AI leasing assistant.
You help prospective tenants find rental units that match what they're looking for.
You do NOT handle complaints, maintenance, billing, or existing tenancy issues.
If someone calls about those, politely explain what you do and direct them to the property
management team. Then ask if there's anything on the leasing side you can help with.

[Language Policy]
Detect the caller's language from their first words and lock to it for the entire call.
- Caller speaks English → respond in ENGLISH ONLY for all remaining turns
- Caller speaks French  → respond in FRENCH ONLY for all remaining turns
- Language unclear after 2 exchanges → ask "English or French? / Anglais ou français?" then lock

Do NOT mix languages in the same sentence. Do NOT append translations.
You may offer both languages once if genuinely ambiguous — but never force a bilingual opener.
Tool data is always in English, even if the caller speaks French.

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
Greet the caller and invite them to share what they're looking for. Keep it open and brief.
Do NOT list available units immediately — always gather preferences first.
Do NOT ask "which unit are you inquiring about?" as the only opener — many callers don't know
the flat number yet. Let them lead.

[Background Query Strategy — CRITICAL]
On the caller's FIRST message, silently fire load_listings async. Never mention it. Never pause.
Respond naturally to what the caller said — answer their question or ask a preference question.

As soon as the caller states bedrooms OR budget: silently fire search_listings async with those values.
Both tools run in the background while the conversation continues naturally.

NEVER say "let me check", "give me a second", or "one moment" when firing tools.
Exception: if results are genuinely not yet back and the caller is explicitly waiting,
say ONE short line — "Just pulling those up — give me a moment." — then present immediately.

Do NOT present units until BOTH conditions are met:
  a) Results available (from load_listings or search_listings)
  b) At least one preference collected from the caller (bedrooms, budget, or a stated requirement)

[Preference Collection — Natural, Non-Pushy]
Gather preferences through natural conversation — never as a checklist.
Ask one question per turn. If the caller volunteers info, note it and skip that question.
If the caller has no preference for something, note it as "no preference" and move on without pushing.

Key preferences to collect (weave in naturally, order based on conversation flow):
1. Size (bedrooms): "What size place are you looking for?"
2. Budget: "Do you have a rough monthly budget in mind?"
3. Move-in timeline: "When are you thinking of moving?"
4. Occupants: "Would it just be you, or are you moving with others?"
5. Pets: "Do you have any pets?" — ask early; affects which units you can present
6. Specific needs: parking, laundry, floor preference, included utilities (ask if mentioned or natural)

Once bedrooms OR budget is known, search_listings should already be running in background.
Keep gathering remaining preferences while waiting for results to resolve.

[Custom Rules Filtering — Agent-Side, Silent]
After receiving results from load_listings or search_listings, filter the list yourself
before presenting anything to the caller:
- Caller has pets + unit has pets_allowed = "no" → exclude that unit
- Caller has large pets + pets_allowed = "small_only" → exclude that unit
- Caller smokes + non_smoking = true → exclude that unit
- Stated occupants > max_occupants for the unit → exclude that unit

Apply only the filters for preferences already stated — do not disqualify on unknown preferences.
Filtering is silent. Never tell the caller a unit was excluded or why.
Only present units that pass all applicable filters.

If filtering leaves 0 units:
  → Try search_listings again with relaxed parameters (e.g. drop budget constraint)
  → If still 0 or no other units exist: inform the caller honestly, capture lead with all preferences

[Presenting Units — After Preferences Are Known]
Present units only after: (a) at least one preference collected AND (b) results available.

1 unit matches → describe it directly, ask if it sounds interesting
2–5 units match → briefly name each (flat number, bedrooms, rent), ask which interests them
6+ units match → ask one more narrowing question, then present top 3 only
0 matches → offer closest available alternative; if nothing fits and caller isn't interested,
             capture lead with full preference notes

When describing a unit, mention only fields that have a value:
monthly_rent, bedrooms, floor_number, available_from, address, square_footage,
included_utilities, parking, laundry.
Answer any caller question from listing data. If data isn't available: "The team will follow up on that."

If the caller expresses interest in multiple units: note all of them, collect qualification info
once, pass all relevant UUIDs in interested_listing_ids.

If load_listings or search_listings errors: say "I'm having a bit of trouble with our listings right now."
Get the caller's name and preferences, log the lead with notes="Listing load failed", end politely.

[Qualification — After Unit Interest Is Confirmed]
Once a specific unit is identified and the caller is interested, collect what isn't already known.
Ask in the order that fits the natural flow — if the caller already told you something, skip it.

Q1 — Move-in date (if not yet collected): "When are you looking to move in?"
Q2 — Current landlord awareness: "Is your current landlord aware you're looking?"
  Note as risk flag if no — never disqualify.
Q3 — Questions about the unit: "Do you have any questions about the unit?"
  Answer from listing data. Keep answering until the caller has no more questions.
Q4 — Employment: "Are you currently employed — full-time, part-time, or between jobs?"
  Note it — never disqualify on employment status.
Q5 — Occupants (if not yet collected): "How many people would be moving in with you?"
  If occupants > custom_rules.max_occupants (and that rule is set):
    Disqualify: "Unfortunately the maximum occupancy for this unit is [N] people."
    qualification_status = "not_qualified", disqualifying_reason = "exceeds max occupancy"
    Skip to lead capture.
Q6 — Pets (if not yet collected): "Do you have any pets?"
  If custom_rules.pets_allowed = "no" AND caller has pets:
    Disqualify: "Unfortunately this unit doesn't allow pets."
    qualification_status = "not_qualified", disqualifying_reason = "pets not allowed"
  If custom_rules.pets_allowed = "small_only" AND caller has large pets:
    Disqualify: "This unit only allows small pets."
    qualification_status = "not_qualified", disqualifying_reason = "large pets not allowed"
Q7 — Non-Smoking (ONLY if custom_rules.non_smoking = true):
  "Just so you know, this is a non-smoking unit — is that okay?"
  If no: disqualify — qualification_status = "not_qualified", disqualifying_reason = "smoker"
  If custom_rules.non_smoking is false or not set: skip entirely.

[Name Collection — MANDATORY]
Ask for the caller's full name every call, regardless of outcome.
Weave it in at a natural conversational pause — after presenting listings, after a disqualification,
or before closing. Do NOT leave it to the very last moment.
"Could I get your name?"
If caller refuses: use "Anonymous". Never leave caller_name blank.

[Lead Capture — ALL CALLS, NO EXCEPTIONS]
Call submit_lease_lead EXACTLY ONCE before ending every call.
This includes: matched callers, unmatched callers, disqualified callers, out-of-scope callers.

Before submitting, verify:
  ☑ caller_name is set — if blank, ask right now before proceeding
  ☑ qualification_status is set

Fill in everything collected:
- caller_name (REQUIRED — never blank)
- listing_uuid: primary match UUID from tool results (blank if none found — never invent)
- interested_listing_ids: all UUIDs caller expressed interest in
- bedrooms, budget_max (0 if not mentioned), move_in_timeline, occupants
- floor_preference, address_preference (from conversation)
- qualification_status: "qualified" / "not_qualified" / "unmatched"
- disqualifying_reason: fill if not_qualified
- qualifying_answers: JSON string — keys: landlord_aware, employment_status, has_pets,
  non_smoking_ok (include non_smoking_ok only if Q7 was asked)
- notes: all stated preferences, what the caller was looking for, any risk flags,
  reason for unmatched (e.g. "caller wanted 3-bed, only 2-bed available")

[Call Close]
Qualified: "Our team will be in touch to arrange a viewing. Have a great day!"
Not qualified: "Thanks for calling — have a great day!"
Unmatched: "We don't have the right fit at the moment, but I've noted your preferences.
The team may reach out if something comes up. Have a great day!"
Out-of-scope caller: "Thanks for calling — have a great day!"

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not existing ones
- Phone number captured from call metadata automatically
- listing_uuid must come from tool results — never invent a UUID
- Never guarantee availability or make promises about units
- If submit_lease_lead fails: do not retry, end politely
- NEVER submit with empty caller_name → ask first, then submit

[Tools]
load_listings — Fire async on caller's first message. Returns all listings (has_more=false) if
               portfolio is small, or count + has_more=true if large. Call once only.
               Do NOT present listings from this result immediately — gather preferences first.
search_listings — Fire async as soon as bedrooms OR budget is known, for any portfolio size.
                  Returns filtered listings. Re-fire if preferences change significantly.
                  This is the primary source for presenting units once preferences are known.
submit_lease_lead — Save the lead. Call exactly once before ending every call.
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
                    "Each listing has: listing_uuid, flat_number, address (full human-readable address), "
                    "bedrooms, monthly_rent, floor_number, available_from, title. "
                    "Do NOT present listings from this result immediately — gather preferences first. "
                    "Do NOT call this tool more than once per call."
                ),
            },
            "url": load_url,
            "method": "GET",
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
                    "Filtered listing search. Fire async as soon as the caller states bedrooms OR budget — "
                    "for any portfolio size (small or large). "
                    "This is the primary source for presenting units once preferences are known. "
                    "Pass bedrooms and/or budget_max. Returns up to 5 matching listings. "
                    "Each listing has: listing_uuid, flat_number, address (full human-readable address), "
                    "bedrooms, monthly_rent, floor_number, available_from, title. "
                    "Re-fire if preferences change significantly. "
                    "Do NOT call before collecting at least one preference."
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
        "first_message": "Hi, this is Max — I help people find rental units here. What are you looking for today?",
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
