# VAPI Replacement Requirements

> Derived from full codebase audit — covers every VAPI feature this system currently depends on.
> Date: 2026-06-07

---

## 1. Phone Infrastructure

| Requirement | How it is used today |
|---|---|
| **Inbound call handling** | Callers dial a Twilio E.164 number; call is routed to the assigned agent |
| **Outbound call initiation** | `POST /voice/call/outbound` triggers `client.calls.create(assistant_id, phone_number_id, customer.number)` |
| **Phone number ↔ agent linking** | `PATCH /phone-number/{id}` with `{"assistantId": ...}` links a number to a specific agent at provision time |
| **Per-manager dedicated numbers** | One Twilio number per manager account; stored in `twilio_number_pool`, claimed on first property group creation |
| **Bring-your-own numbers** | Numbers are Twilio-owned; added to a pool and registered with the provider via `add_twilio_number_to_vapi.py` |
| **Number identity in webhooks** | `phoneNumberId` and `assistantId` arrive in every webhook — used as fallback to resolve `manager_id` when no listing was matched |

---

## 2. Agent Configuration API

| Requirement | How it is used today |
|---|---|
| **Create agent via API** | `client.assistants.create(**config)` — called during manager provisioning |
| **Update agent via API** | `PATCH api.vapi.ai/assistant/{id}` directly (SDK's phone-number update is broken — raw HTTP is used for that step) |
| **Multiple named agents** | 1 global complaint agent + 1 per-manager lease agent + 1 shared lease agent = N+2 agents |
| **Per-agent config** | Each agent has its own: system prompt, LLM model, tools list, voice, transcriber, speaking behavior |
| **Dynamic config at create time** | `manager_id` is baked into tool URLs when the agent is created — different tool URLs per manager |
| **Bulk config push** | `update_lease_agents.py` iterates all active managers and PATCHes their assistants — replacement must support programmatic PATCH by agent ID |
| **First message modes** | `assistant-speaks-first` (complaint) and `assistant-speaks-first-with-model-generated-message` (lease — model generates a fresh bilingual greeting each call) |

---

## 3. LLM Configuration

| Requirement | Detail |
|---|---|
| **Provider + model selection** | OpenAI `gpt-5.2-chat-latest`; provider field must be configurable per agent |
| **System prompt injection** | Long multi-section prompts (1,000+ chars) set at agent-creation time |
| **Temperature and maxTokens** | temperature=0.7, maxTokens=300 configurable per agent |
| **Tool definitions (JSON Schema)** | Full tool schemas with enums, required fields, and descriptions passed to the LLM |

---

## 4. Voice / TTS

| Requirement | Detail |
|---|---|
| **ElevenLabs integration** | `eleven_turbo_v2_5`, voice ID `E4GQ42zEV1kwul03Bl16` (bilingual Wilkins voice) |
| **Voice tuning params** | stability=0.6, similarityBoost=0.75, useSpeakerBoost=true, inputMinCharacters=15, optimizeStreamingLatency=1 |
| **Speed control** | speed=1 |

> If a replacement does not support ElevenLabs or this specific voice ID, the bilingual English/French quality must be re-tested with whatever voice is substituted.

---

## 5. Transcription / STT

| Requirement | Detail |
|---|---|
| **Deepgram nova-3** | Primary transcriber |
| **Multilingual in one call** | `language: "multi"` — auto-detects English and French within the same call without switching modes |
| **Confidence threshold** | 0.4 (lease inbound), 0.6 (complaint outbound — more carrier noise at connection) |
| **Numerals mode** | `numerals: true` — transcribes "two" as "2" for cleaner tool parsing |
| **Fallback transcriber** | OpenAI `gpt-4o-transcribe` as secondary if Deepgram confidence falls below threshold |

> Bilingual `language: "multi"` on Deepgram is a hard requirement. It is what enables French callers without a separate French-language agent.

---

## 6. Tool System

You use two distinct tool types with several platform-specific behaviors.

### 6a. `apiRequest` Tools (direct HTTP — no webhook roundtrip)

| Requirement | Example |
|---|---|
| **Agent calls your backend URL directly** | `GET /leasing/find-units?manager_id=...&query={{query}}` |
| **URL template variables** | `{{customer.number}}`, `{{call.id}}`, `{{query}}`, `{{datetime}}`, `{{flat_number}}`, `{{bedrooms}}`, `{{budget_max}}` injected from call state or prior tool responses |
| **`variableExtractionPlan`** | Platform parses the HTTP response JSON and makes named fields available as `{{variable_name}}` in subsequent tool URLs. Example: `Verify_phone_number` returns `{datetime, status}` → `{{datetime}}` is used in `check_availability`'s URL |
| **Sync mode** (`async: false`) | Agent waits for the HTTP response before continuing — used for verification and search |
| **Async mode** (`async: true`) | Agent fires and continues without waiting — used for `search_listings` and `submit_lease_lead` |
| **Per-tool TTS messages** | `request-start`: "One moment while I verify that." — spoken while the tool runs |
| **Delayed response message** | `request-response-delayed`: "Still working on it, just another moment." — spoken if tool takes >3 s |

> `variableExtractionPlan` is the single hardest VAPI-specific feature to replicate. It maintains a per-call variable store that flows between tools without any code on your side.

### 6b. `function` (Webhook) Tools

| Requirement | Example |
|---|---|
| **Agent POSTs tool call data to your webhook** | `submit_complaint` → `POST /voice/webhook` |
| **Tool result returned in HTTP response body** | `{"results": [{"toolCallId": "...", "result": "Complaint #42 created."}]}` — fed back to the LLM as the tool output |
| **Async function tools** | `submit_lease_lead` — platform fires webhook, does not wait for result |
| **Per-tool server URL + timeout** | Each function tool has its own `server.url` and `timeoutSeconds` |

---

## 7. Webhook Events

| Requirement | Detail |
|---|---|
| **`tool-calls` event** | Fired when agent calls a `function` tool; payload contains tool name, arguments, call metadata |
| **`end-of-call-report` event** | Fired at call end; contains full transcript, call ID, duration, customer number |
| **Multiple webhook URLs per agent** | Complaint agent: all events → `/voice/webhook`; Lease agent EOC → `/voice/lease-eoc-webhook`; individual function tools → their own per-tool URLs |
| **Event filtering** | Platform sends many event types per call (status-update, transcript chunks, etc.); only `tool-calls` and `end-of-call-report` are processed |
| **Transcript formats in EOC** | `artifact.transcript` (plain text) and `artifact.messagesOpenAIFormatted` (OpenAI message array) — both consumed |
| **Call metadata in every event** | `call.id`, `call.customer.number`, `call.assistantId`, `call.phoneNumberId` — all four used for manager resolution |
| **Always HTTP 200 from your webhook** | Any non-200 marks the call as failed in the platform — hard constraint throughout the codebase |
| **Idempotency via `call.id`** | Duplicate events for the same call are deduplicated via the `call_logs` table |

---

## 8. Conversational / Call Behavior Controls

| Requirement | Detail |
|---|---|
| **`waitSeconds`** | 0.1 s — how long agent waits before speaking after caller finishes |
| **`transcriptionEndpointingPlan.onNumberSeconds`** | 0.1 s — endpoint detection sensitivity |
| **`stop_speaking_plan.numWords`** | 2 words from caller interrupts the agent (lease) / 5 words (complaint) |
| **Background denoising** | `smartDenoisingPlan.enabled: true` |
| **Background sound** | `office` ambient on both agents |
| **`voicemail_message`** | Bilingual voicemail prompt if call goes to voicemail |
| **`end_call_message`** | Final phrase spoken before hangup |
| **`end_call_phrases`** | `["goodbye", "au revoir", "talk to you soon"]` — agent self-terminates when these are detected |

---

## 9. Multi-Tenant Provisioning Flow

| Requirement | Detail |
|---|---|
| **Per-manager agent creation** | On manager's first property group creation, a new agent is created just for them |
| **Phone number claiming** | Pick an available number from pool, mark assigned, link it to the new agent |
| **Status tracking** | `pending → active → failed` states stored in `manager_vapi_config` |
| **Race condition guard** | DB unique index prevents two concurrent provisioning tasks claiming two numbers for the same manager |
| **Retry endpoint** | `POST /property-groups/users/me/provision-voice` re-triggers provisioning; guard prevents re-running if already active |
| **Pool-empty behavior** | Mark `failed` immediately — no silent fallback |

---

## 10. Python SDK Surface Used

```python
from vapi import Vapi, CreateCustomerDto, AssistantOverrides
from vapi.core.api_error import ApiError

client = Vapi(token=PRIVATE_VAPI_API)

# Create agent
client.assistants.create(**config_dict)

# Update agent
client.assistants.update(id=assistant_id, **config_dict)

# Initiate outbound call
client.calls.create(
    assistant_id=...,
    phone_number_id=...,
    customer=CreateCustomerDto(number="+1..."),
    assistant_overrides=AssistantOverrides(first_message="...")
)

# Link phone number to agent
# NOTE: SDK's phone_numbers.update() + UpdatePhoneNumberDto are broken in the
# installed version — a raw httpx PATCH is used instead:
httpx.patch(
    f"https://api.vapi.ai/phone-number/{vapi_phone_number_id}",
    headers={"Authorization": f"Bearer {PRIVATE_VAPI_API}"},
    json={"assistantId": assistant_id},
)
```

---

## 11. Summary: Hard Requirements vs Nice-to-Have

### Hard Requirements (no workaround without code changes)

1. **`apiRequest` tool type** — agent calls your backend directly with URL template variables; no webhook roundtrip per tool call.
2. **`variableExtractionPlan`** — parses API response fields into named variables reusable across tools within the same call (e.g., `{{datetime}}` from verify-phone flows into check-availability URL).
3. **Bilingual Deepgram `language: "multi"`** — English and French in one call without a separate agent per language.
4. **`tool-calls` webhook + result injection** — platform POSTs to your webhook and feeds the HTTP response body back to the LLM as the tool result.
5. **Per-agent webhook routing** — different tools and event types route to different backend endpoints.
6. **Phone number ↔ agent linking API** — programmatic assignment of a specific phone number to a specific agent.
7. **`assistant-speaks-first-with-model-generated-message`** — model generates its own opening line; not a static `first_message` string.
8. **Async vs sync tool modes** — some tools the agent waits for (search, verification), others it fires and continues (lead submission).
9. **`end_call_phrases`** — agent self-terminates on detected phrases without explicit end-call logic.
10. **Python SDK** — used in provisioning (`vapi_provisioning.py`) and outbound call route (`voice.py`).

### Nice-to-Have (can adapt with moderate refactoring)

- ElevenLabs voice ID passthrough (could switch to a different voice with re-testing)
- `request-start` / `request-response-delayed` tool messages (UX polish only)
- `background_sound: "office"` (cosmetic)
- Specific `stop_speaking_plan` / `start_speaking_plan` millisecond tuning

---

## 12. What a Replacement Must Expose (Minimum API Contract)

```
POST   /assistants            → create agent, returns {id}
PATCH  /assistants/{id}       → update agent config in place
POST   /calls                 → initiate outbound call
PATCH  /phone-numbers/{id}    → assign assistantId to a number
GET    /phone-numbers         → list available numbers

Webhook events (POST to your URL):
  - tool-calls          (with toolCalls array + call metadata)
  - end-of-call-report  (with artifact.transcript + call metadata)

Tool types:
  - apiRequest  (direct HTTP with URL template vars + variableExtractionPlan)
  - function    (webhook with sync/async modes + result injection)
```

If a platform cannot provide `apiRequest` tools with `variableExtractionPlan`, the entire
`verify-phone → check-availability → submit_complaint` chain must be rewritten as a
single webhook-based tool or the variable threading must be managed inside your backend.
