# Lease Agent Diagnosis — 2026-05-24 (Test C)

## Symptom

Outbound lease call placed at 15:33:53. Agent spoke greeting, caller stated their requirement, agent cut the call. No leads created.

**Render log evidence:**
- `POST /voice/call/outbound 200 OK` at 15:33:53 ✅ call placed
- Zero hits to `/leasing/search`, `/leasing/find-listing`, `/voice/lease-lead-webhook`, or `/voice/lease-eoc-webhook` in the log window
- Only `/voice/call-status` poll traffic after the call

This is the same symptom as Session B bug #4 — tools blocked, agent can't search.

---

## Why It Looks Like Session B Bug #4 Was Already Fixed

Session B added `server_messages: ["end-of-call-report"]` to `_lease_assistant_shell` in `vapi_agent_config.py` (correct) and ran `update_lease_assistants.py` to patch VAPI (claimed ✅).

The Session B fix was incomplete — see root cause below.

---

## Root Cause

**`patch_assistant` in `update_lease_assistants.py` never includes `server_messages` in the VAPI PATCH payload.**

The function at lines 41–65 of `backend/scripts/update_lease_assistants.py` builds this payload:

```python
payload = {
    "model": {
        "provider": ...,
        "model": ...,
        "messages": ...,   # system prompt ✅
        "tools": ...,      # variableExtractionPlan ✅
    }
}
if "server" in new_config:
    payload["server"] = new_config["server"]   # EOC webhook URL ✅
# server_messages is never added ❌
```

`server_messages` lives at the top level of the assistant config — the same level as `server`, `model`, etc. — but is never included in the PATCH. VAPI therefore preserved the original `server_messages` value on all three assistants, which includes `function-call` and `tool-calls`.

---

## How This Kills All Tool Calls

1. Caller states preference; LLM decides to call `find_listing` or `search_available_listings`
2. VAPI sees `tool-calls` in `server_messages` → sends a `tool-calls` event to `server.url` (the EOC webhook)
3. `lease_eoc_webhook` at line 660 of `voice.py` checks: `if message.get("type") != "end-of-call-report": return {"status": "ignored"}`
4. VAPI receives `{"status": "ignored"}` — interprets this as a tool execution failure
5. VAPI blocks the tool call; the HTTP request to `/leasing/find-listing` or `/leasing/search` is **never sent**
6. LLM hits the `[Error Handling]` path, retries once (same failure), then tries to call `submit_lease_lead`
7. `submit_lease_lead` is a `function` type tool — ALSO routed through server → same "ignored" response → also fails
8. Error handling for `submit_lease_lead` says "do not retry — end the call politely" → call ends, no lead saved

---

## Evidence Checklist

| Signal | Expected if root cause is correct | Observed |
|---|---|---|
| No `/leasing/search` or `/leasing/find-listing` in logs | ✅ tools blocked | ✅ confirmed |
| No `/voice/lease-lead-webhook` in logs | ✅ blocked | ✅ confirmed |
| No `/voice/lease-eoc-webhook` in logs | EOC event may fire after log cutoff or VAPI may suppress | Inconclusive (log ends 42s after call) |
| Call cuts quickly without searching | ✅ error handling path → both retries fail → polite end | ✅ confirmed |

---

## What Session B Actually Fixed vs What It Didn't

| Change | Code | VAPI (live) |
|---|---|---|
| `server.url` (EOC webhook URL) | ✅ | ✅ (patch script includes `server`) |
| `server_messages: ["end-of-call-report"]` | ✅ | ❌ (patch script NEVER sends `server_messages`) |
| System prompt `[Error Handling]` block | ✅ | ✅ (included in `model.messages`) |
| `variableExtractionPlan` fixes | ✅ | ✅ (included in `model.tools`) |

---

## Secondary Bug (Non-Blocking for This Failure)

`find_listing` in `backend/app/routes/leasing.py` uses `.limit(1)` on the first two query paths (flat_number match and title match). Even after the tool-blocking bug is fixed, a caller asking about a specific building by name will get at most 1 result from those paths (unless the third fallback triggers). The system prompt promises to present ALL matching units. This is a separate fix needed after the main bug is resolved.

---

## What to Fix

See `LEASE_AGENT_FIX_2026_05_24_C.md`.
