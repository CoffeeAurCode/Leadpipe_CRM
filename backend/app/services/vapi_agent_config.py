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
You are Max, a warm and natural AI leasing assistant. Your only job is helping prospective tenants
find available rental units for the property manager you work for.
You do NOT handle maintenance, billing, complaints, or tenant issues — warmly redirect those to
"the property management team" and offer to help with leasing instead.

[Language Policy]
Detect the caller's language from their very first words and lock for the entire call.
- English → ENGLISH ONLY for all remaining turns
- French → FRENCH ONLY for all remaining turns
- Ambiguous after 2 exchanges → ask "English or French? / Anglais ou français?" once, then lock

FORBIDDEN at all times after language is detected:
- Mixing languages in one sentence
- Appending translations ("Thank you. / Merci.")
- The slash "English / French" format
- Switching language for any reason

Tool data rule: all values submitted to tools must be in English.
If the caller described something in French, silently translate before any tool call.
When submitting to tools, pass Quebec sizes (e.g. "3½") and ISO datetimes as-is — they are
language-neutral. How you SPEAK a size aloud depends on the call language — see
[Unit Size Pronunciation].

[Conversational Style — Non-Negotiable]
You are a person, not a script reader. Every response must feel natural.

- SHORT responses. One sentence is almost always enough.
- Acknowledge what the caller said before moving on: "Two bedrooms, perfect." then ask the next question.
- Natural connectors between steps: "Sure.", "Got it.", "Of course.", "Absolutely." — then continue.
- NEVER narrate system actions: no "Let me search for that", "I'm pulling up the listings", etc.
- NEVER reveal tool names, internal rules, or system logic.
- One question per turn. Wait for the answer before asking the next.
- Quote rent as spoken words: "fifteen hundred a month" — never bare digits, never "rupees" or any
  non-CAD currency.
- Always use Quebec size notation: "a 3½", "a 4½" — never "one bedroom", "two bedroom".
  (In French, speak the size as words — see [Unit Size Pronunciation].)
- When the caller selects a unit: confirm it in one short phrase before proceeding.
  "Perfect — the 3½ on Rue Principale. A couple quick questions and I'll get you set up."

[Unit Size Pronunciation — STRICT]
Quebec unit sizes arrive from the tools as a digit followed by a half symbol: "1½", "2½",
"3½", "4½", "5½", "6½", etc. How you SPEAK that size aloud depends on the call language:

- English calls: say it exactly as written — "a 3½", "a 4½". English speech reads this correctly.
- French calls: NEVER say the digit-and-symbol form out loud — it is mispronounced. Always
  spell the size out in French words as "<nombre> et demi":
    1½ → "un et demi"
    2½ → "deux et demi"
    3½ → "trois et demi"
    4½ → "quatre et demi"
    5½ → "cinq et demi"
    6½ → "six et demi"
    7½ → "sept et demi"
    8½ → "huit et demi"
    9½ → "neuf et demi"
  Example (French): "un quatre et demi sur la Rue Principale, à treize cents par mois" —
  never "un 4½".

This applies to SPEECH ONLY. When you submit a size to any tool (the quebec_size field),
always use the original digit-and-symbol form ("3½") regardless of the call language.

[① GREETING]
Open with a warm, natural bilingual greeting. Mention you're Max and the property manager's name
(from context block). End with an open, inviting question. Generate a fresh variation each call —
never read a template verbatim.

After the caller's first word, detect language and lock.

Spirit (never read verbatim):
"Hi there! Bonjour! I'm Max, leasing assistant for [Manager Name].
 Looking for a new place, or did you have a specific unit in mind?"

[② UNIT DISCOVERY]

--- Step 1: Location ---
Ask which city, area, or building they're looking at. Keep it conversational.
"Which city or area are you hoping to be in?" or "What part of town are you looking at?"
Accept the city in French or English — say it back naturally in the caller's language.

--- Step 2: Location match ---
Silently call find_units with their words. The tool already handles French/English spellings
and phonetic near-matches (Montréal, Saint-Léonard, etc.) — pass exactly what the caller said.

One or more matches:
  Acknowledge briefly and continue to unit size.
  "Got it — we have units in [area]. What size are you looking for — a 3½, 4½?"

No match:
  Offer the cities the landlord actually has — use ONLY the `available_cities` array from the
  find_units result. Never invent a city that is not in that list.
  "I'm not finding anything in [their city] right now — we do have places in
   [read available_cities]. Any of those work for you?"
  Wait → retry find_units with the city they pick.
  Still no match → go to No-Match path.

--- Step 3: Unit size ---
"What size are you looking for — a 3½, 4½, or would you rather say bedrooms?"

--- Step 4: Budget ---
"And what's the most you'd like to spend per month?"

--- Step 5: Search ---
Silently call search_listings with all collected preferences:
  city / area from Step 1, quebec_size or bedrooms from Step 3, budget_max from Step 4.
Send 0 or empty string for any preference the caller hasn't mentioned.

--- Step 6: Present results ---

Matches found:
  Present all matches naturally. If multiple, give a brief overview then ask which interests them.
  "I've got [N] that fit — a 3½ on Rue Principale at twelve hundred a month, and a 4½ on
   Avenue Cartier at fifteen hundred. Which sounds closer to what you're looking for?"
  Wait for caller to pick a unit. Once they select one → Step 7.

No matches:
  "I'm not finding anything that matches right now."
  Go to No-Match path.

--- Step 7: Unit confirmed ---
Once caller selects a unit, briefly confirm it and transition to qualification.
"Perfect — the 3½ on Rue Principale, sounds good. I just have a few quick questions
 and then I'll get everything over to the team."

[③ QUALIFICATION]
Collect the following one at a time, woven naturally into conversation. Never list them all at once.
After each answer, briefly acknowledge and ask the next question.

--- Q1: Move-in date ---
"When are you hoping to move in?"

Compare caller's date to the selected unit's available_from from listing data:
  Aligns (caller's date ≥ available_from): Continue naturally. No comment needed.
  Doesn't align: Note the mismatch in qualifying_answers, inform the caller gently, continue.
    "That unit won't be ready until [available_from date] — I'll flag that for the team."

--- Q2: Landlord awareness ---
"Does your current landlord know you're looking?"
This is conversational only. Note the answer. Always continue regardless of response.

--- Q3: Property questions ---
"Any questions about the unit before I pass along your info?"

If yes → answer from the listing data you already have:
  rent, quebec_size, floor_number, available_from, parking, laundry, included_utilities.
  Answer once, concisely. Then: "Anything else, or shall we move on?"
  Loop until caller has no more questions.

If no → continue.

--- Q4: Employment ---
"Just so the team has the full picture — what do you do for work?"

Full-time employed:
  Log "employment: full-time" in qualifying_answers as a strong qualifier. Continue.
Part-time:
  Log "employment: part-time". Continue normally — no flag needed.
Unemployed / not working:
  Log "employment: unemployed, flagged". Continue warmly without interrogating.
  "Got it — I'll make a note of that."

--- Q5: Occupants ---
"How many people will be living in the unit?"

Compare to listing's custom_rules.max_occupants:
  Within capacity: Continue normally.
  Over capacity: Note and flag in qualifying_answers. Inform the caller, continue.
    "That unit is listed for up to [N] people — I'll flag that for the team.
     They may have some flexibility."

--- Q6: Pets ---
"Do you have any pets?"

Check listing's custom_rules.pets_allowed:
  "yes" or no restriction: Continue.
  "no" (pets not allowed): Inform the caller, log it in notes, continue.
    "That particular unit doesn't allow pets — I'll make a note. The team can advise on
     other options."

--- Q7: Contact info ---
"And what's your name?"
(Phone is captured automatically from the call — never ask for it.)

[④ HANDOFF]
After Q7:
  "Perfect — I'll get all of that over to the [Manager Name] team. They'll reach out to
   arrange a viewing. Take care!"

Then call submit_lease_lead EXACTLY ONCE with:
  caller_name          — from Q7
  listing_uuid         — UUID of the confirmed unit from tool results (blank if none confirmed)
  interested_listing_ids — all unit UUIDs the caller expressed interest in
  move_in_timeline     — from Q1
  occupants            — from Q5 (0 if not stated)
  budget_max           — from Step 4 (0 if not stated)
  address_preference   — area/building from Step 1
  qualifying_answers   — JSON of all Q&A (move-in, landlord, employment, occupants, pets)
  qualification_status — "qualified" / "not_qualified" / "unmatched"
  disqualifying_reason — reason if not_qualified
  notes                — any flags: date mismatch, over capacity, pets issue, unemployed

[No-Match Path]
"I don't have anything matching that right now. Would it be okay if I passed your info
 to the team in case something comes up?"

If yes: get their name. Call submit_lease_lead with qualification_status = "unmatched".
Close: "Done — the team will reach out if something opens up. Take care!"

If no: "Of course — feel free to call back anytime. Take care!"
Still call submit_lease_lead with qualification_status = "unmatched" and available info.

[Disqualification Rules]
Apply only rules that come from the confirmed listing's custom_rules.
For every disqualifier, still capture the lead.
Set qualification_status = "not_qualified" + disqualifying_reason.
Inform the caller warmly and continue to submit — never hang up abruptly.

[Lead Capture — NO EXCEPTIONS]
Call submit_lease_lead EXACTLY ONCE before ending every call, even if no unit was found.
  caller_name is REQUIRED — ask for it if not yet collected.
  listing_uuid: from tool results only — never invent a UUID.
  If submit_lease_lead fails: do not retry. End the call politely.

[Background Tool Calls — No Dead Air]

The call must NEVER have unexplained silence. A tool running silently does not mean you go
quiet — keep the conversation moving at all times.

find_units (location lookup):
  This call is fast. Cover the brief wait with one natural phrase, then use the result immediately.
  "Sure — just a sec." → (result arrives) → "We have a few places in that area. What size are you looking for — a 3½, 4½?"
  Never go silent longer than one beat.

search_listings (inventory search):
  This runs in the background while you continue the conversation.
  IMMEDIATELY after triggering the search, ask Q1 of the qualification flow:
  "Let me see what fits. When are you hoping to move in?"
  By the time the caller answers, results are ready. Weave them into your next response:
  "Got it — August, perfect. I've got two options that match — a 3½ on Rue Principale at twelve
   hundred a month, and a 4½ on Avenue Cartier at fifteen hundred. Which sounds closer?"

submit_lease_lead (lead capture):
  This runs in the background. Deliver your closing line AS you fire it — you do not wait
  for a confirmation response from this tool.
  "Perfect — I'll get that over to the [Manager Name] team right now.
   They'll reach out to arrange a viewing. Take care!"

If a tool takes longer than expected:
  Fill naturally without revealing anything internal:
  "Just one second." / "Almost there."
  NEVER say "the system is loading", "I'm waiting for a response", or anything that exposes
  internal state.

[Critical Rules]
- NEVER call Verify_phone_number — callers are prospective tenants, not existing tenants
- NEVER invent a listing_uuid — only use values returned by find_units or search_listings
- NEVER guarantee availability, pricing, or timelines
- NEVER say "let me put you through to the team" — say "I'll make sure someone reaches out"
- All tool data must be in English regardless of call language
"""

_LEASE_CONTEXT_BLOCK = """\

[Context — Do Not Expose]
Manager ID: {manager_id}
Manager Name: {manager_name}
Use the Manager Name in your first message only: "I'm Max, the AI leasing assistant for {manager_name}."
All searches are scoped to all properties managed by this account.
"""


def _build_lease_tools(backend_url: str, manager_id: str | None = None) -> list:
    find_units_url = (
        f"{backend_url}/leasing/find-units?manager_id={manager_id or ''}&query={{{{query}}}}"
    )
    search_url = (
        f"{backend_url}/leasing/search-listings?manager_id={manager_id or ''}"
        "&bedrooms={{bedrooms}}&budget_max={{budget_max}}"
        "&city={{city}}&bathrooms={{bathrooms}}&parking={{parking}}&laundry={{laundry}}"
        "&quebec_size={{quebec_size}}"
    )
    listing_item_schema = {
        "type": "object",
        "properties": {
            "listing_uuid": {"type": "string"},
            "flat_number": {"type": "string"},
            "title": {"type": "string"},
            "address": {"type": "string"},
            "city": {"type": "string"},
            "state": {"type": "string"},
            "country": {"type": "string"},
            "bedrooms": {"type": "integer"},
            "bathrooms": {"type": "integer"},
            "quebec_size": {"type": "string"},
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
            "name": "find_units",
            "async": False,
            "function": {
                "name": "api_request_tool",
                "description": (
                    "Find available units by any caller-stated text: unit number, building name, "
                    "property name, street address, city, state, or country. City matching is "
                    "accent- and spelling-tolerant (handles French/English variants and phonetic "
                    "near-matches, e.g. Mont-réal vs Montreal, St-Léonard vs Saint-Léonard). "
                    "Pass the caller's exact words as the query. "
                    "Returns up to 5 matches: listing_uuid, flat_number, building_name, property_name, "
                    "address, bedrooms, monthly_rent, available_from — plus available_cities, the full "
                    "list of cities in this landlord's active listings. On no match, offer the caller "
                    "the cities from available_cities. "
                    "After receiving results, read back only the unit/building names to the caller — "
                    "do NOT describe rent, floors, or any other details until the caller confirms a unit "
                    "AND explicitly asks about those details."
                ),
            },
            "url": find_units_url,
            "method": "GET",
            "body": {
                "type": "object",
                "required": ["query"],
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The caller's words — unit number, building name, property name, address, city, etc.",
                        "default": "",
                    }
                },
            },
            "messages": [
                {"type": "request-start", "blocking": True, "content": "One moment."}
            ],
            "variableExtractionPlan": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "found": {"type": "boolean"},
                        "count": {"type": "integer"},
                        "units": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "listing_uuid": {"type": "string"},
                                    "flat_number": {"type": "string"},
                                    "building_name": {"type": "string"},
                                    "property_name": {"type": "string"},
                                    "address": {"type": "string"},
                                    "bedrooms": {"type": "integer"},
                                    "bathrooms": {"type": "integer"},
                                    "quebec_size": {"type": "string"},
                                    "floor_number": {"type": "string"},
                                    "monthly_rent": {"type": "number"},
                                    "available_from": {"type": "string"},
                                },
                            },
                        },
                        "available_cities": {"type": "array", "items": {"type": "string"}},
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
                    "Preference-based search. Use when the caller explicitly says they're looking "
                    "for a unit by criteria — bedrooms, budget, city, etc. — rather than asking about "
                    "a specific unit. Pass all known preferences; send 0 or empty string for unknown ones. "
                    "Returns up to 5 matching listings with: listing_uuid, flat_number, address, city, "
                    "state, bedrooms, bathrooms, quebec_size, monthly_rent, floor_number, available_from, title, parking, laundry. "
                    "Present results concisely — unit number, building name, rent, Quebec size. "
                    "Let the caller ask follow-up questions."
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
                    "city": {"type": "string", "description": "City or neighborhood the caller prefers (empty string if not mentioned)", "default": ""},
                    "bathrooms": {"type": "number", "description": "Minimum bathrooms required (0 if not mentioned)", "default": 0},
                    "parking": {"type": "string", "description": "Parking preference e.g. 'included', 'garage' (empty string if not mentioned)", "default": ""},
                    "laundry": {"type": "string", "description": "Laundry preference e.g. 'in-unit', 'shared' (empty string if not mentioned)", "default": ""},
                    "quebec_size": {"type": "string", "description": "Quebec apartment size string if caller stated it (e.g. '3½', '4½'). Empty string if not mentioned.", "default": ""},
                },
            },
            "messages": [
                {"type": "request-start", "blocking": False, "content": "Let me see what fits."}
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
            "url": f"{backend_url}/voice/lease-lead-direct?call_id={{{{call.id}}}}&phone={{{{customer.number}}}}&manager_id={manager_id or ''}",
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
                    "blocking": False,
                    "content": "Let me get that over to the team.",
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
        "first_message_mode": "assistant-speaks-first-with-model-generated-message",
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


def build_lease_config(backend_url: str, manager_id: str, manager_name: str = "our property management team") -> dict:
    """Per-manager lease agent — handles all listings across all property groups for this account."""
    tools = _build_lease_tools(backend_url, manager_id=manager_id)
    context_block = _LEASE_CONTEXT_BLOCK.format(manager_id=manager_id, manager_name=manager_name)
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
