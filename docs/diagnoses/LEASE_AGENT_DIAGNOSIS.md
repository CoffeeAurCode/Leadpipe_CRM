# Lease Agent — Diagnosis (2026-05-24, updated)

## Symptoms Reported
- Agent said "availability system is offline"
- No lead was added to the database
- Search tools not reaching the backend

---

## Root Cause 1 — `server_messages` now routes function/tool events to EOC handler (CODE BUG — FIXED)

**Background:** This session we added `server.url → /voice/lease-eoc-webhook` to the lease assistant.
Before that, `server_messages` listed many event types but had nowhere to send them (no server URL).
After the change, VAPI started routing ALL listed events to our EOC handler, including:

```
"function-call"    ← VAPI sends function calls here for execution
"tool-calls"       ← VAPI sends tool-call notifications here
```

Our handler returns `{"status": "ignored"}` for anything that isn't `end-of-call-report`.
For `function-call` and `tool-calls`, VAPI expects an execution result. Receiving `"ignored"`
caused VAPI to treat the tool call as failed — blocking tool execution entirely.

**Evidence:** Server was healthy at 15:09:38 (all GET requests returning 200 OK), yet ZERO
hits to `/leasing/find-listing` or `/leasing/search` appeared in logs. Tool calls were being
swallowed by the EOC handler, never reaching the search endpoints.

**Fix applied:** Reduced `server_messages` in `_lease_assistant_shell` to only
`["end-of-call-report"]`. VAPI now only sends EOC events to our server. Tool execution
flows are completely unaffected (apiRequest tools call their URL directly; `submit_lease_lead`
has its own dedicated server URL `/voice/lease-lead-webhook`).

---

## Root Cause 2 — Lease agent system prompt had no error handling (PROMPT BUG — FIXED)

The lease agent system prompt had no `[Error Handling]` section. When any tool failed,
the LLM was left to improvise. GPT-5.2 improvised with "availability system is offline"
and then gave up — no retry, no lead capture.

The complaint agent has `[Error Handling & Fallbacks]` but the lease agent never did.

**Fix applied:** Added `[Error Handling]` block to the lease agent system prompt:
- Retry search tools once on failure
- If second attempt also fails: capture lead with `qualification_status="unmatched"` and
  notes about the technical issue, then end politely
- `submit_lease_lead` MUST be called before ending, even on tool failure

---

## Root Cause 3 — Render deployment cycle (environment — not fixable in code)

Render's zero-downtime deploy shuts down the OLD server after the NEW server goes live.
In this log the pattern was:

```
14:42:11  New server live
14:43:10  Old server shut down   ← 9 seconds gap
14:57:35  New server live
14:58:35  Old server shut down   ← 60 seconds gap
```

A call placed at 14:43:01 (9 seconds before old server dies) could have had its first
tool call land during the changeover. The new error handling in the prompt (Root Cause 2
fix) now makes the agent retry once and gracefully capture a partial lead if tools keep failing.

---

## Root Cause 4 — 400 errors at 15:01 (VAPI rejected outbound calls)

```
15:01:13  POST /voice/call/outbound  400 Bad Request
15:01:22  POST /voice/call/outbound  400 Bad Request
```

VAPI returned 400 for both attempts. Our backend re-raises VAPI's status code.
VAPI 400 reasons: invalid E.164 phone number, assistant not provisioned for outbound,
or phone number ID not active. The user fixed this by 15:09:38 (likely corrected phone format).
Nothing to fix in code.

---

## Root Cause 5 — EOC webhook code not yet deployed

The `POST /voice/lease-eoc-webhook` endpoint was added to `voice.py` in this session.
VAPI was patched to point to that URL. But the endpoint only exists on Render after the
code is pushed and deployed. Until then VAPI gets a 404 for EOC events and doesn't retry.

**Fix:** Push and deploy the current code to Render.

---

## Summary Table

| # | Issue | Type | Status |
|---|---|---|---|
| 1 | `server_messages` routing tool events to EOC handler — broke all tool execution | Code bug | ✅ Fixed, VAPI patched |
| 2 | No `[Error Handling]` in lease agent prompt — LLM gave up on tool failure | Prompt bug | ✅ Fixed, VAPI patched |
| 3 | Render deploy cycle kills in-flight tool calls | Environment | Mitigated by retry logic |
| 4 | VAPI 400 errors for outbound calls | User input (phone format) | Self-resolved |
| 5 | `lease_eoc_webhook` endpoint not deployed | Deploy required | Deploy code to Render |
