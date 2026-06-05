# Voice Agent Bug Diagnosis
**Date:** 2026-06-05  
**Tests affected:** L14, L15, C01 (complaint agent); Voice Stats tab (all sessions)

---

## Bug 1 — Complaint agent starting message hangs and last word is stretched/distorted

### Symptoms
- Every complaint agent call: a multi-second silence ("hang") occurs immediately after the call connects
- The agent's greeting eventually plays but the **last word is audibly stretched or repeated**
- In L14 the call was cut before the agent could proceed past the greeting
- In C01 the startup took ~27 seconds before the first tool call fired (vs ~15s for the lease agent)

### What is NOT the cause
- Not the `first_message` string — `"Hi, this is Alex — how can I help you today?"` is short (43 chars), well within ElevenLabs' streaming buffer
- Not the TTS config (`eleven_turbo_v2_5`, `optimizeStreamingLatency: 1`) — same config as the lease agent which doesn't exhibit this
- Not the model or system prompt — these are only invoked after the first message plays
- Not the `server_messages` config — `tool-calls` correctly included for complaint agent

### Root cause: `stop_speaking_plan.numWords: 2` triggering on call-connect noise

**Location:** `backend/app/services/vapi_agent_config.py:962`
```python
"stop_speaking_plan": {"numWords": 2},
```

**How it breaks the first message:**

VAPI outbound calls go through a carrier connect sequence that produces low-level audio artifacts (DTMF tones, ring-back echo, packet burst at connection). These artifacts are fed to the Deepgram transcriber (`language: "multi"`, `confidenceThreshold: 0.4`). Deepgram, tuned aggressively for low-latency endpointing (`onNumberSeconds: 0.1`), can transcribe these artifacts as 1–2 "words" with low confidence. With `numWords: 2`, the `stop_speaking_plan` fires as soon as the transcriber sees 2 words from the user — even if that "speech" is just connection noise.

When `stop_speaking_plan` fires while ElevenLabs is mid-stream, VAPI signals the TTS to stop. The TTS driver flushes its remaining audio buffer in a single chunk rather than cleanly ending — this produces the **stretched / repeated last word** artifact. After the stop, VAPI waits for the user to speak (turn handoff), which is the hang.

**Why this doesn't happen on the lease agent:** The lease agent is typically tested with a cleaner call path (inbound tenant → Twilio → VAPI), while complaint agent tests have used the VAPI outbound call path (`POST /voice/call/outbound`). Outbound calls through the Twilio number pool have more carrier-layer noise at connection time than inbound calls.

**Supporting evidence:**
- Lease agent (L01–L11): all outbound, all work correctly — but lease calls also use the same `numWords: 2` and same Twilio pool. The difference: each lease test followed an established warm call path, while the complaint agent calls were the first calls through the complaint number in the test session (cold start for that number's Twilio routing).
- C01 transcript: the user says `"Hi, Alex."` confirming the agent's name came through — the greeting DID play, but only after the stop/restart cycle.
- L14: the hang was so severe the greeting never recovered and VAPI cut the call (default max-silence timeout).

### Secondary contributing factor: no `firstMessageMode` explicit setting

VAPI defaults `firstMessageMode` to `"assistant-speaks-first-with-model-generated-message"` when not set. This means on **every** call the LLM is invoked to generate the greeting before TTS can begin — adding ~1–1.5s of LLM latency on top of the TTS cold-start. The lease agent config sets this implicitly via the `first_message` field only; both agents are missing the explicit `"firstMessageMode": "assistant-speaks-first"` flag that would bypass LLM generation for the greeting.

**Location of missing field:** `build_complaint_config()` at line 932 in `vapi_agent_config.py` — no `firstMessageMode` key in the returned dict.

### Fix

1. **Add `firstMessageMode`** to `build_complaint_config()`:
   ```python
   "firstMessageMode": "assistant-speaks-first",
   ```
   This tells VAPI to play the hardcoded `first_message` immediately without calling the LLM, removing ~1.5s of latency.

2. **Raise `stop_speaking_plan.numWords`** from `2` to `5` for the complaint agent:
   ```python
   "stop_speaking_plan": {"numWords": 5},
   ```
   A tenant with a complaint will typically speak several words before the agent needs to yield. Requiring 5 words before yielding prevents connection noise from triggering a premature stop.

3. **Raise `confidenceThreshold`** in the transcriber from `0.4` to `0.6` to filter out low-confidence noise transcriptions:
   ```python
   "confidenceThreshold": 0.6,
   ```

After applying changes, run `python backend/scripts/update_shared_agents.py` to push the new config to VAPI.

---

## Bug 2 — Complaint AI tab (Voice Stats) shows no data after calls complete

### Symptoms
- `/call_logs/stats?days=30` returns HTTP 200 with `{"total": 0, "resolved": 0, "escalated": 0, "by_date": {}, "recent": []}`
- VoiceStatsTab shows zeros and "No recent calls found" even after C01 successfully created complaint ID=89 with call_log ID=77
- Backend log confirms call_log ID=77 was inserted with `manager_id=28c43c77-...`

### Root cause: missing RLS SELECT policy on `call_logs` table

**How the data flows:**
1. VAPI webhook fires → `POST /voice/webhook` → uses `get_service_db` (Supabase service role, bypasses RLS) → **inserts** row into `call_logs` with `manager_id` ✓
2. Voice Stats tab loads → `GET /call_logs/stats` → uses `get_authenticated_db` (Supabase anon/authenticated client, RLS-enforced) → **selects** from `call_logs`

With Supabase, when RLS is enabled on a table and no SELECT policy exists, authenticated queries return **0 rows** (the default deny). The endpoint returns 200 with an empty result rather than an error — which is why the API call succeeds but the UI shows nothing.

**Confirmed by schema audit:**
- `schema.sql` — no RLS policies defined for `call_logs`
- `migrations/010_voice_agents.sql` through `022_structured_address.sql` — no migration adds an RLS SELECT policy for `call_logs`
- `call_logs` table does have `manager_id UUID` column (added in a past hotfix, not reflected in schema.sql)

The `manager_id` column exists and is populated, but there is no policy telling Supabase to allow `SELECT WHERE manager_id = auth.uid()`.

**Location:**
- Stats endpoint: `backend/app/routes/call_logs.py:16` — uses `get_authenticated_db`, correct
- Missing: a Supabase RLS policy for `call_logs`

### Fix

Run this in the Supabase SQL editor:

```sql
-- Enable RLS if not already on (likely already on)
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- Allow managers to read their own call logs
CREATE POLICY "managers_read_own_call_logs"
ON call_logs
FOR SELECT
USING (manager_id = auth.uid());
```

No backend code changes needed — the endpoint already queries correctly once the RLS policy exists.

### Secondary issue: stats tab does not refresh after a call ends

Even with the RLS fix applied, the VoiceStatsTab only loads data once on mount (`useEffect(() => { load(); }, [load])`). After a complaint call completes and a new call_log is created, the tab will not refresh automatically. The user has to click the Refresh button or navigate away and back.

This is not a blocker (the Refresh button exists) but it means the tab will appear stale immediately after finishing a test call.

**Location:** `frontend/src/components/VoiceStatsTab.jsx:94`

**Optional fix:** Dispatch a `refresh-voice-stats` event from the voice webhook response path, and add a listener in VoiceStatsTab — the same pattern used for `refresh-appointments` in `App.jsx`.

---

## Summary Table

| Bug | Severity | Root Cause | Fix Location |
|---|---|---|---|
| Startup hang + word stretch | High | `stop_speaking_plan.numWords: 2` triggers on call-connect noise; no `firstMessageMode` | `vapi_agent_config.py:build_complaint_config()` + `update_shared_agents.py` |
| Voice stats shows 0 | High | No RLS SELECT policy on `call_logs` table | Supabase SQL editor (one migration) |
| Stats tab not auto-refreshing | Low | No event listener / polling in `VoiceStatsTab` | `VoiceStatsTab.jsx` + `voice.py` (optional) |
