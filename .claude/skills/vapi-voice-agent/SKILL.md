---
name: vapi-voice-agent
description: >
  Build, configure, and deploy Vapi voice agents using the Python server SDK (vapi_server_sdk).
  Use this skill any time the user wants to create a voice AI agent on Vapi, configure an assistant,
  set up phone calls (inbound or outbound), add tools/functions, handle webhooks, or wire up
  integrations using the Vapi Python SDK. Triggers include: "build a voice agent", "create a Vapi
  assistant", "set up a phone bot", "make a Vapi agent that...", or any request to implement
  voice AI with specs/config/requirements. Always use this skill before writing any Vapi Python code.
---

# Vapi Voice Agent Skill

Use this skill to implement Vapi voice agents using Python. Follow every section carefully — it contains all patterns needed to translate a spec into working code.

## Table of Contents
1. [Core Concepts](#1-core-concepts)
2. [Installation & Setup](#2-installation--setup)
3. [Creating an Assistant](#3-creating-an-assistant)
4. [Model Configuration](#4-model-configuration)
5. [Voice Configuration](#5-voice-configuration)
6. [Transcriber Configuration](#6-transcriber-configuration)
7. [Phone Numbers & Calls](#7-phone-numbers--calls)
8. [Tools / Function Calling](#8-tools--function-calling)
9. [Webhooks / Server URL](#9-webhooks--server-url)
10. [Squads (Multi-Agent)](#10-squads-multi-agent)
11. [Full Working Example](#11-full-working-example)
12. [Common Patterns Reference](#12-common-patterns-reference)

---

## 1. Core Concepts

A Vapi voice agent has three core components:
- **Transcriber** (STT): Converts user speech → text (Deepgram, AssemblyAI, etc.)
- **Model** (LLM): Processes conversation and generates responses (OpenAI, Anthropic, etc.)
- **Voice** (TTS): Converts assistant text → speech (ElevenLabs, Azure, OpenAI, etc.)

Two main primitives:
- **Assistant** — single-agent, system prompt + tools. Best for most use cases.
- **Squad** — orchestrates multiple assistants with context-preserving transfers.

SDK to use: **`vapi_server_sdk`** (server-side management). Do NOT use `vapi_python` (browser client SDK).

---

## 2. Installation & Setup

```bash
pip install vapi_server_sdk
```

```python
from vapi import Vapi

client = Vapi(token="YOUR_VAPI_API_KEY")

# Async variant
from vapi import AsyncVapi
import asyncio
client = AsyncVapi(token="YOUR_VAPI_API_KEY")
```

Always load the API key from an environment variable:
```python
import os
from vapi import Vapi

client = Vapi(token=os.environ["VAPI_API_KEY"])
```

---

## 3. Creating an Assistant

### Minimal assistant
```python
assistant = client.assistants.create(
    name="Support Agent",
    first_message="Hello! How can I help you today?",
    model={
        "provider": "openai",
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a helpful support agent."}],
    },
    voice={
        "provider": "openai",
        "voice_id": "alloy",
    },
)
print(assistant.id)
```

### Key assistant parameters
| Parameter | Type | Description |
|---|---|---|
| `name` | str | Required if transferring between assistants. Max 40 chars. |
| `first_message` | str | What assistant says first. If omitted, waits for user. |
| `first_message_mode` | str | `"assistant-speaks-first"` (default), `"assistant-waits-for-user"`, `"assistant-speaks-first-with-model-generated-message"` |
| `model` | dict | LLM config (see §4) |
| `voice` | dict | TTS config (see §5) |
| `transcriber` | dict | STT config (see §6) |
| `end_call_message` | str | What assistant says before hanging up |
| `end_call_phrases` | list[str] | Phrases that trigger hang-up |
| `voicemail_message` | str | Message left on voicemail |
| `max_duration_seconds` | int | Max call length, default 600 (10 min), max 43200 |
| `background_sound` | str | `"office"` (default phone), `"off"` (default web) |
| `server` | dict | Webhook URL config `{"url": "https://..."}` |
| `metadata` | dict | Any custom key/value data |

### Update an assistant
```python
client.assistants.update(
    id=assistant.id,
    first_message="Updated greeting!",
)
```

### Delete an assistant
```python
client.assistants.delete(id=assistant.id)
```

---

## 4. Model Configuration

### OpenAI
```python
model={
    "provider": "openai",
    "model": "gpt-4o",          # gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo
    "messages": [
        {"role": "system", "content": "System prompt here."},
    ],
    "temperature": 0.7,          # 0.0–2.0
    "max_tokens": 500,
    "tools": [...],              # inline tool definitions (see §8)
    "tool_ids": ["tool-uuid"],   # reference pre-created tools by ID
    "emotion_recognition_enabled": True,
}
```

### Anthropic
```python
model={
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514",  # or claude-opus-4-20250514
    "messages": [{"role": "system", "content": "..."}],
}
```

### Google
```python
model={
    "provider": "google",
    "model": "gemini-1.5-pro",
    "messages": [{"role": "system", "content": "..."}],
}
```

### Groq
```python
model={
    "provider": "groq",
    "model": "llama-3.1-70b-versatile",
    "messages": [{"role": "system", "content": "..."}],
}
```

---

## 5. Voice Configuration

### ElevenLabs (highest quality)
```python
voice={
    "provider": "11labs",
    "voice_id": "21m00Tcm4TlvDq8ikWAM",   # ElevenLabs voice ID
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}
```

### OpenAI TTS
```python
voice={
    "provider": "openai",
    "voice_id": "alloy",   # alloy, echo, fable, onyx, nova, shimmer
}
```

### Azure
```python
voice={
    "provider": "azure",
    "voice_id": "en-US-JennyNeural",  # or other Azure voice names
    "speed": 1.0,
}
```

### PlayHT
```python
voice={
    "provider": "playht",
    "voice_id": "jennifer",
    "speed": 1.0,
    "quality": "premium",
}
```

### Deepgram Aura
```python
voice={
    "provider": "deepgram",
    "voice_id": "aura-asteria-en",
}
```

### Common voice options
```python
voice={
    "provider": "openai",
    "voice_id": "nova",
    "caching_enabled": True,    # cache TTS for repeated phrases (reduces latency)
    "speed": 1.0,               # playback speed multiplier
    "chunk_plan": {
        "enabled": True,
        "min_characters": 30,   # min chars before TTS chunk is sent
    },
}
```

---

## 6. Transcriber Configuration

### Deepgram (recommended, lowest latency)
```python
transcriber={
    "provider": "deepgram",
    "model": "nova-3",          # nova-3, nova-2, enhanced, base
    "language": "en",           # BCP-47 language code
    "smart_format": True,
    "punctuate": True,
    "diarize": False,
}
```

### AssemblyAI
```python
transcriber={
    "provider": "assembly-ai",
    "language": "en",
    "confidence_threshold": 0.4,
    "end_of_turn_confidence_threshold": 0.7,
}
```

### OpenAI Whisper
```python
transcriber={
    "provider": "openai",
    "model": "whisper-1",
    "language": "en",
}
```

---

## 7. Phone Numbers & Calls

### Buy/provision a Vapi phone number
```python
phone_number = client.phone_numbers.create(
    fallback_destination={
        "type": "number",
        "number": "+1234567890",  # where to forward if agent fails
    }
)
```

### Assign assistant to phone number
```python
client.phone_numbers.update(
    id=phone_number.id,
    assistant_id=assistant.id,
)
```

### Make an outbound call
```python
call = client.calls.create(
    assistant_id=assistant.id,
    customer={"number": "+1234567890"},  # E.164 format
    # Optional: phone_number_id to use a specific caller ID
    phone_number_id=phone_number.id,
)
print(call.id, call.status)
```

### Make outbound call with transient (inline) assistant
```python
call = client.calls.create(
    assistant={   # inline assistant config — not saved permanently
        "first_message": "Hi, this is a reminder call.",
        "model": {"provider": "openai", "model": "gpt-4o-mini",
                  "messages": [{"role": "system", "content": "..."}]},
        "voice": {"provider": "openai", "voice_id": "alloy"},
    },
    customer={"number": "+1234567890"},
    phone_number_id=phone_number.id,
)
```

### List and retrieve calls
```python
calls = client.calls.list(limit=10)
call = client.calls.get(id="call-uuid")
print(call.transcript)       # full transcript
print(call.summary)          # AI-generated summary
print(call.ended_reason)     # why the call ended
```

### Call with dynamic variables (assistant overrides)
Pass runtime data by overriding parts of the assistant config per-call:
```python
call = client.calls.create(
    assistant_id=assistant.id,
    assistant_overrides={
        "variable_values": {"customer_name": "Alice", "account_id": "acc_123"},
        "first_message": "Hello Alice, calling about your account.",
    },
    customer={"number": "+1234567890"},
    phone_number_id=phone_number.id,
)
```
In the system prompt, reference variables as `{{customer_name}}`.

---

## 8. Tools / Function Calling

Tools let the assistant take real-world actions during a call.

### Method A: Inline tool (defined directly in the assistant)
```python
assistant = client.assistants.create(
    model={
        "provider": "openai",
        "model": "gpt-4o",
        "messages": [{"role": "system", "content": "You are a booking assistant."}],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "check_availability",
                    "description": "Check available appointment slots for a given date",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                            "service_type": {"type": "string", "enum": ["consultation", "follow-up"]},
                        },
                        "required": ["date"],
                    },
                },
                "server": {"url": "https://your-server.com/tools/check-availability"},
            }
        ],
    },
    ...
)
```

### Method B: Pre-created tool (reusable across assistants)
```python
# Create the tool once
tool = client.tools.create(
    type="function",
    function={
        "name": "get_order_status",
        "description": "Get the current status of a customer order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID"},
            },
            "required": ["order_id"],
        },
    },
    server={"url": "https://your-server.com/tools/order-status"},
    messages=[
        {"type": "request-start", "content": "Let me check your order status..."},
        {"type": "request-complete", "content": "Got it."},
        {"type": "request-failed", "content": "I couldn't retrieve that order right now."},
    ],
)

# Reference by ID in model
assistant = client.assistants.create(
    model={
        "provider": "openai",
        "model": "gpt-4o",
        "messages": [...],
        "tool_ids": [tool.id],
    },
    ...
)
```

### Built-in tools
```python
# Transfer to human / another number
{"type": "transferCall", "destinations": [{"type": "number", "number": "+1555..."}]}

# End call programmatically
{"type": "endCall"}

# DTMF (keypad tones)
{"type": "dtmf"}

# Voicemail detection
{"type": "voicemail"}
```

### Webhook handler for tool calls (FastAPI example)
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/tools/check-availability")
async def check_availability(request: Request):
    body = await request.json()
    message = body["message"]
    tool_calls = message["toolCallList"]

    results = []
    for tool_call in tool_calls:
        call_id = tool_call["id"]
        args = tool_call["arguments"]
        date = args.get("date")

        # Your business logic here
        slots = get_available_slots(date)

        results.append({
            "toolCallId": call_id,
            "result": f"Available slots on {date}: {', '.join(slots)}"
        })

    return JSONResponse({"results": results})
```

---

## 9. Webhooks / Server URL

Vapi sends events to your server URL in real time.

### Set server URL on assistant
```python
assistant = client.assistants.create(
    server={"url": "https://your-server.com/vapi/webhook"},
    server_messages=[
        "conversation-update",
        "end-of-call-report",
        "function-call",
        "tool-calls",
        "status-update",
        "hang",
    ],
    ...
)
```

### Key webhook event types
| Event type | When it fires |
|---|---|
| `status-update` | Call status changes (ringing, in-progress, ended) |
| `transcript` | Partial/final transcripts |
| `conversation-update` | New message added to conversation |
| `tool-calls` | Assistant wants to call a function |
| `end-of-call-report` | Call ended; includes summary, transcript, recording URL |
| `hang` | Assistant has gone silent (may need intervention) |
| `assistant-request` | Vapi needs dynamic assistant config for this specific call |

### FastAPI webhook server
```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    msg_type = body.get("message", {}).get("type")

    if msg_type == "end-of-call-report":
        report = body["message"]
        print("Call ended:", report.get("endedReason"))
        print("Summary:", report.get("summary"))
        print("Transcript:", report.get("transcript"))

    elif msg_type == "tool-calls":
        # Handle tool calls — return results
        tool_calls = body["message"]["toolCallList"]
        results = []
        for tc in tool_calls:
            results.append({"toolCallId": tc["id"], "result": "done"})
        return JSONResponse({"results": results})

    elif msg_type == "assistant-request":
        # Dynamically return assistant config
        return JSONResponse({
            "assistant": {
                "firstMessage": "Hello, how can I help?",
                "model": {"provider": "openai", "model": "gpt-4o",
                          "messages": [{"role": "system", "content": "..."}]},
                "voice": {"provider": "openai", "voiceId": "alloy"},
            }
        })

    return JSONResponse({"status": "ok"})
```

---

## 10. Squads (Multi-Agent)

Use squads when you need specialized assistants with context-preserving transfers.

```python
# Create specialized assistants first
triage = client.assistants.create(name="Triage", ...)
billing = client.assistants.create(name="Billing", ...)
support = client.assistants.create(name="Support", ...)

# Create squad
squad = client.squads.create(
    name="Customer Service Squad",
    members=[
        {
            "assistantId": triage.id,
            "assistant_overrides": {},
        },
        {
            "assistantId": billing.id,
        },
        {
            "assistantId": support.id,
        },
    ],
    # First assistant to handle the call
)

# Use squad in a call
call = client.calls.create(
    squad_id=squad.id,
    customer={"number": "+1234567890"},
    phone_number_id=phone_number.id,
)
```

Transfer between squad members using the `transferCall` tool in each assistant's tools.

---

## 11. Full Working Example

This is a complete, runnable customer support voice agent:

```python
import os
from vapi import Vapi
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# --- Vapi Setup ---
client = Vapi(token=os.environ["VAPI_API_KEY"])

# --- Create the assistant ---
assistant = client.assistants.create(
    name="Customer Support Agent",
    first_message="Thank you for calling Acme support! How can I help you today?",
    first_message_mode="assistant-speaks-first",
    transcriber={
        "provider": "deepgram",
        "model": "nova-3",
        "language": "en",
        "smart_format": True,
    },
    model={
        "provider": "openai",
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a friendly customer support agent for Acme Corp. "
                    "Help customers with order status, returns, and general questions. "
                    "Keep responses concise — under 40 words when possible. "
                    "If the customer wants to speak to a human, use the transferCall tool."
                ),
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_order_status",
                    "description": "Look up the status of a customer order by order number",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "order_number": {
                                "type": "string",
                                "description": "The order number, e.g. ORD-12345",
                            }
                        },
                        "required": ["order_number"],
                    },
                },
                "server": {"url": os.environ.get("WEBHOOK_URL", "https://your-server.com") + "/tools/order-status"},
                "messages": [
                    {"type": "request-start", "content": "Let me look up that order for you..."},
                    {"type": "request-complete", "content": "Got the order details."},
                    {"type": "request-failed", "content": "I couldn't retrieve that order right now."},
                ],
            },
            {
                "type": "transferCall",
                "destinations": [
                    {
                        "type": "number",
                        "number": os.environ.get("HUMAN_AGENT_NUMBER", "+15550001234"),
                        "message": "Please hold while I transfer you to a human agent.",
                    }
                ],
            },
        ],
    },
    voice={
        "provider": "11labs",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "stability": 0.5,
        "similarity_boost": 0.75,
        "caching_enabled": True,
    },
    end_call_message="Thank you for contacting Acme support. Have a great day!",
    end_call_phrases=["goodbye", "thank you bye", "that's all"],
    max_duration_seconds=1800,
    background_sound="office",
    server={
        "url": os.environ.get("WEBHOOK_URL", "https://your-server.com") + "/vapi/webhook"
    },
    server_messages=["end-of-call-report", "tool-calls", "status-update"],
    analysis_plan={
        "summary_plan": {"enabled": True},
        "success_evaluation_plan": {
            "rubric": "NumericScale",
            "enabled": True,
        },
    },
)

print(f"Assistant created: {assistant.id}")

# --- Webhook server ---
app = FastAPI()

@app.post("/vapi/webhook")
async def vapi_webhook(request: Request):
    body = await request.json()
    msg = body.get("message", {})
    msg_type = msg.get("type")

    if msg_type == "tool-calls":
        results = []
        for tc in msg.get("toolCallList", []):
            name = tc.get("name")
            args = tc.get("arguments", {})
            if name == "get_order_status":
                order_num = args.get("order_number", "")
                # Replace with real lookup
                result = f"Order {order_num} is shipped and will arrive in 2 business days."
            else:
                result = "Action completed."
            results.append({"toolCallId": tc["id"], "result": result})
        return JSONResponse({"results": results})

    if msg_type == "end-of-call-report":
        print("=== CALL ENDED ===")
        print("Reason:", msg.get("endedReason"))
        print("Duration:", msg.get("durationSeconds"), "seconds")
        print("Summary:", msg.get("summary"))

    return JSONResponse({"status": "ok"})

@app.post("/tools/order-status")
async def order_status_tool(request: Request):
    body = await request.json()
    tool_calls = body["message"]["toolCallList"]
    results = []
    for tc in tool_calls:
        order_num = tc["arguments"].get("order_number", "")
        results.append({
            "toolCallId": tc["id"],
            "result": f"Order {order_num}: Shipped, arriving in 2 business days."
        })
    return JSONResponse({"results": results})

# --- Make an outbound test call ---
def make_outbound_call(to_number: str):
    call = client.calls.create(
        assistant_id=assistant.id,
        customer={"number": to_number},
    )
    print(f"Call started: {call.id}")
    return call

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 12. Common Patterns Reference

### Error handling
```python
from vapi.core.api_error import ApiError

try:
    assistant = client.assistants.create(...)
except ApiError as e:
    print(f"API Error {e.status_code}: {e.body}")
```

### Async usage
```python
import asyncio
from vapi import AsyncVapi

async def main():
    client = AsyncVapi(token=os.environ["VAPI_API_KEY"])
    assistant = await client.assistants.create(...)
    call = await client.calls.create(assistant_id=assistant.id, customer={"number": "+1..."})

asyncio.run(main())
```

### Analysis plan (post-call insights)
```python
analysis_plan={
    "summary_plan": {
        "enabled": True,
        "messages": [{"role": "system", "content": "Summarize the key outcomes."}],
    },
    "structured_data_plan": {
        "enabled": True,
        "schema": {
            "type": "object",
            "properties": {
                "issue_type": {"type": "string"},
                "resolved": {"type": "boolean"},
                "order_number": {"type": "string"},
            },
        },
    },
    "success_evaluation_plan": {
        "rubric": "NumericScale",  # or "DescriptiveScale", "Checklist", "Matrix"
        "enabled": True,
        "messages": [{"role": "system", "content": "Rate how well the issue was resolved 1-10."}],
    },
}
```

### Recording calls
```python
artifact_plan={
    "recording_enabled": True,
    "recording_format": "mp3",   # or "wav;l16"
    "transcript_plan": {
        "enabled": True,
        "assistant_name": "Agent",
        "user_name": "Customer",
    },
    "video_recording_enabled": False,
}
```

### Conversation behavior tuning
```python
# Fine-tune when assistant starts speaking after user stops
start_speaking_plan={
    "wait_seconds": 0.4,       # delay after user stops talking
    "smart_endpointing_plan": {"provider": "vapi"},
    "transcription_endpointing_plan": {
        "on_punctuation_seconds": 0.1,
        "on_no_punctuation_seconds": 1.5,
        "on_number_seconds": 0.5,
    },
}

# Fine-tune when assistant stops talking on interruption
stop_speaking_plan={
    "num_words": 0,         # words spoken before checking for interruption
    "voice_seconds": 0.2,   # voice activity required to trigger interruption
    "backoff_seconds": 1,   # wait before resuming after interruption
}
```

### Background noise denoising
```python
background_speech_denoising_plan={
    "smart_denoising_plan": {"enabled": True},   # Krisp AI denoising
}
```

### Provider-specific credentials (per-assistant)
```python
credentials=[
    {"provider": "openai", "api_key": os.environ["OPENAI_KEY"]},
    {"provider": "11labs", "api_key": os.environ["ELEVEN_KEY"]},
]
```

---

## Quick Decision Guide

| Requirement | Solution |
|---|---|
| Single-purpose agent | Use `assistants.create()` |
| Multi-specialist routing | Use `squads.create()` |
| Reusable tools across agents | `tools.create()` + `tool_ids` |
| One-off tool for single agent | Inline `tools` array in model |
| Dynamic agent config per-call | `assistant_overrides` or `assistant-request` webhook |
| Outbound campaign | Use `calls.create()` in a loop with rate limiting |
| Real-time data during calls | Webhook server URL + tool calls |
| Post-call data extraction | `analysis_plan.structured_data_plan` |

## Important Notes
- All phone numbers must be in **E.164 format** (e.g., `+12125551234`)
- The `vapi_server_sdk` package name is `vapi` in Python imports: `from vapi import Vapi`
- Tool call webhook must return `{"results": [{"toolCallId": "...", "result": "..."}]}`
- For `assistant-request` webhook, return `{"assistant": {...}}` with full config
- `max_duration_seconds` defaults to 600 (10 min); set higher for long calls
- Variable substitution in prompts uses double curly braces: `{{variable_name}}`
- See `references/providers.md` for full list of supported model/voice/transcriber providers