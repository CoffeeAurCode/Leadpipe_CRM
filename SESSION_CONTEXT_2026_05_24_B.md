# Session Context — 2026-05-24 (Session B)

## Issues Diagnosed & Fixed

---

### 1. Outbound Lease Call — Agent Not Taking Name / Adding Lead

**Symptom:** Outbound call placed via lease agent. Agent never asked for caller's name and no lead was created.

**Diagnosis:**
- The call was placed with the correct lease agent
- `POST /voice/lease-lead-webhook` never appeared in Render logs → `submit_lease_lead` was never called by the LLM
- Most likely: conversation ended before step 7 (Capture Lead), OR the LLM skipped the step

**Root cause:** No safety net existed if `submit_lease_lead` was skipped. The call ended with no record.

---

### 2. EOC Fallback Webhook (New Feature)

**What was built:**
- New endpoint: `POST /voice/lease-eoc-webhook` in `backend/app/routes/voice.py`
- Fires when VAPI sends `end-of-call-report` for any lease agent call
- Checks if a `lease_leads` row already exists for the `call_id`
- If YES → ignored (submit_lease_lead already fired normally)
- If NO → saves a partial lead: `caller_name="Unknown"`, `qualification_status="unmatched"`, full transcript in `notes` field
- Also stamps `_last_call_ended_at` so frontend dashboard refreshes on lease calls (previously only refreshed on complaint calls)

**`vapi_agent_config.py` change:**
- Added `"server": {"url": f"{backend_url}/voice/lease-eoc-webhook", "timeoutSeconds": 20}` to `_lease_assistant_shell`
- Added `backend_url` parameter to `_lease_assistant_shell` (default = `BACKEND_URL`)
- Both `build_lease_config` and `build_lease_config_shared` pass `backend_url` through

**`update_lease_assistants.py` change:**
- `patch_assistant` now includes `"server"` in the PATCH payload when present in config

---

### 3. variableExtractionPlan Mismatch (Bug Fix)

**Background:** Previous session changed `find_listing` response from flat top-level fields to `{found, count, listings:[...]}`. The `variableExtractionPlan` was never updated.

**Fix — `find_listing`:**
- Old plan expected top-level `listing_uuid`, `address`, `bedrooms`, etc.
- New plan extracts `found`, `count`, and a full `listings` array with `items` schema

**Fix — `search_available_listings`:**
- Old plan had `listings` as a bare `type: array` with no `items` schema
- New plan adds full `items` schema so VAPI can extract individual listing objects including `listing_uuid`

---

### 4. Agent Saying "Availability System is Offline" + No Lead Created (Critical Bug)

**Symptom:** After deploying code and placing a lease call on a healthy server, agent said "availability system is offline." No search endpoints hit in Render logs. No lead saved.

**Root cause:** Adding `server.url` to the lease assistant activated the `server_messages` list, which included `"function-call"` and `"tool-calls"`. VAPI started routing these events to `/voice/lease-eoc-webhook`. That handler returned `{"status": "ignored"}` for non-EOC events. VAPI treated this as a function execution failure and **blocked all tool calls** — explaining why no search requests ever reached the backend even on a healthy server.

**Fix — `vapi_agent_config.py`:**
- Changed `server_messages` in `_lease_assistant_shell` from a long list to only `["end-of-call-report"]`
- VAPI now only sends EOC events to our server; `apiRequest` tools call their URLs directly (unaffected); `submit_lease_lead` still routes to its own `/voice/lease-lead-webhook`

---

### 5. Lease Agent System Prompt — Missing Error Handling (Prompt Bug)

**Symptom:** When tools failed, the LLM said "availability system is offline" and ended the call — no retry, no lead capture.

**Root cause:** The lease agent system prompt had no `[Error Handling]` section. The complaint agent has one; the lease agent never did.

**Fix — added `[Error Handling]` block to `_LEASE_SYSTEM_PROMPT_BASE`:**
```
If find_listing or search_available_listings returns an error or fails to respond:
- Say: "Give me just one moment, I'm having a brief connection issue."
- Retry the same tool call once with identical parameters.
- If it fails a second time: say "I'm sorry, I'm unable to search our listings right now. Our team will follow up with you directly."
- Then IMMEDIATELY call submit_lease_lead with qualification_status="unmatched",
  notes="Search tool unavailable during call", and whatever preferences were collected.
- Do NOT end the call without calling submit_lease_lead.

If submit_lease_lead fails or times out: do not retry — end the call politely.
```

---

## VAPI Assistants Updated (All Three Patched)

Script: `python scripts/update_lease_assistants.py`

| Label | Manager ID | VAPI Assistant ID |
|---|---|---|
| Per-manager | `28c43c77` | `c76a69ea-103d-4a24-b542-adda79957294` |
| Per-manager | `7fb0c018` | `70a03059-1595-47d9-b94b-b41deaa49030` |
| Shared | — | `2dba3a50-6862-400c-861a-bfc0a45d4a95` |

All patches applied in this session included:
- `server.url` (EOC fallback)
- `server_messages: ["end-of-call-report"]` only
- Fixed `variableExtractionPlan` for both search tools
- Updated `[Error Handling]` in system prompt

---

## Files Changed

| File | Changes |
|---|---|
| `backend/app/routes/voice.py` | New `POST /voice/lease-eoc-webhook` endpoint |
| `backend/app/services/vapi_agent_config.py` | EOC server URL, server_messages fix, extraction plan fixes, error handling prompt |
| `backend/scripts/update_lease_assistants.py` | `patch_assistant` now includes `server` in PATCH payload |

---

## Still Needs Deploy (Render)

| File | Change |
|---|---|
| `backend/app/routes/voice.py` | `POST /voice/lease-eoc-webhook` endpoint |
| `backend/app/services/vapi_agent_config.py` | All changes above (used by update script, not runtime) |
| `backend/scripts/update_lease_assistants.py` | Script-only, not runtime |

**VAPI config changes are already live.** Only `voice.py` needs the deploy for the EOC endpoint to exist on Render.

---

## Render Restart Pattern (Observed, Not a Bug)

Render's zero-downtime deploy works by:
1. Starting new server process
2. When new server is healthy, shutting down the old one

This causes apparent "restarts" in logs (shutdown ~60s after a new deploy goes live). It is **not a crash**. However a call placed in the 5–10s window during the swap can have its first tool call land on a dying server.

The new error handling in the system prompt mitigates this: the agent retries once and captures a partial lead if tools keep failing.

**Recommended test protocol:** Wait **3 full minutes** after "Your service is live 🎉" before placing a test call.

---

## Diagnosis & Plan Files

- `LEASE_AGENT_DIAGNOSIS.md` — Full root cause analysis for both test failures
- `LEASE_AGENT_FIX_PLAN.md` — What was changed, deploy checklist, test scenarios with expected Render log patterns
