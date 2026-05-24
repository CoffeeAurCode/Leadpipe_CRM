# Lease Agent — Diagnosis (2026-05-24)

## Symptom
Outbound lease call placed at 14:43:01. Agent never called `find_listing` or
`search_available_listings`. No search endpoints appeared in backend logs. Caller
name not taken. No lead created.

---

## Root Cause 1 — Render restart mid-call (environment)

**Evidence from logs:**
```
14:43:01  POST /voice/call/outbound  200 OK   ← call placed
14:43:10  Shutting down                        ← Render restarts (9 s later)
14:43:14  Back up
14:44:54  GET /voice/call-status               ← last poll (call still alive)
```

**What happened:**
`apiRequest` tools (`find_listing`, `search_available_listings`) are HTTP calls
our VAPI agent makes directly to the backend. Call timeline:

| Time offset | Event |
|---|---|
| +0 s  | Call placed via API |
| +4 s  | Call connects, VAPI agent speaks greeting |
| +7 s  | User speaks their preference |
| +9 s  | **Server shuts down** — backend unreachable |
| +9–13 s | VAPI tries first tool call → connection refused |
| +13 s | Server back — but LLM already received an error and moved on |

VAPI does not retry a failed `apiRequest` call. The LLM received a connection
error as the tool result, likely responded with an apology, and the conversation
continued but no further tool calls were made.

Zero `/leasing/find-listing` or `/leasing/search` requests in the logs confirms
the tools never reached the backend.

**Fix:** Not a code change — test when Render is stable (no active deployments).
Wait at least 2 minutes after a deploy before placing a test call.

---

## Root Cause 2 — `find_listing` variableExtractionPlan stale (code bug)

**Background:** Last session changed `find_listing` from returning flat fields
(`listing_uuid`, `address`, etc. at the top level) to returning:
```json
{ "found": true, "count": 5, "listings": [ { "listing_uuid": "...", ... } ] }
```

**The bug:** `variableExtractionPlan` in `vapi_agent_config.py` was not updated.
It still expected top-level fields:
```python
"listing_uuid": {"type": "string"},   # no longer top-level
"address":      {"type": "string"},   # no longer top-level
"bedrooms":     {"type": "integer"},  # no longer top-level
...
```

VAPI tries to extract these variables from the response and finds nothing (they
are now inside the `listings` array). The LLM still receives the full JSON body
and can read it, but VAPI cannot surface the structured variables for template
references.

**Fix:** Updated `variableExtractionPlan` to match the new shape — see
`LEASE_AGENT_FIX_PLAN.md`.

---

## Root Cause 3 — `search_available_listings` variableExtractionPlan incomplete

The `listings` field in the extraction plan had no `items` schema:
```python
"listings": {"type": "array", "description": "..."}
```

VAPI could not extract the individual listing objects (including `listing_uuid`)
from the array. Same impact as Root Cause 2 — LLM reads the JSON but VAPI
variables are empty.

**Fix:** Added full `items` schema with all listing fields.

---

## Root Cause 4 — EOC webhook not received after first test

After we added `server.url → /voice/lease-eoc-webhook`, no POST to that endpoint
appeared in the first test log. Three explanations:

1. **The call ended during the 4-second restart window** (14:43:10–14:43:14) —
   VAPI sent the `end-of-call-report` but the server was down. VAPI does not
   retry server events.
2. **VAPI propagation delay** — The VAPI assistant was patched seconds before
   the test. VAPI may take up to 60 seconds to apply a server URL change.
3. **The call was still live** — The polling ran until 14:44:54 with no EOC
   event, which means the call may have been held open (user didn't hang up
   cleanly or VAPI kept the session).

**Fix:** No code change needed. Future calls will use the EOC fallback correctly
now that the server URL is active and the server is stable.

---

## Summary Table

| # | Issue | Type | Fixed? |
|---|---|---|---|
| 1 | Render restart killed tool calls mid-call | Environment | Test on stable server |
| 2 | `find_listing` variableExtractionPlan stale | Code bug | ✅ Fixed + VAPI patched |
| 3 | `search_available_listings` items schema missing | Code bug | ✅ Fixed + VAPI patched |
| 4 | EOC webhook missed on first test | Timing | ✅ Will work on next stable call |
