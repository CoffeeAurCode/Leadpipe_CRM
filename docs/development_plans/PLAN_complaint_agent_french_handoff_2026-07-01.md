# Complaint Agent — French Handoff (parity with the lease agent)

**Date:** 2026-07-01
**Status:** Code landed; not yet provisioned/live.

## Goal
Give the complaint agent the same French support the lease agent already has, **without changing
the agent's functionality** — it still handles maintenance complaints, emergencies, and appointment
view/update/cancel exactly as before. The only change is the French machinery.

## Why a handoff (not just a bilingual prompt)
Deepgram's STT language is fixed at call start and cannot switch mid-call. A single `multi`
transcriber has materially higher French WER than the monolingual nova-3 `fr` model. The lease agent
solved this by routing French callers to a **dedicated French-only assistant** running `language:"fr"`.
We mirror that here. (Prompt-only French polish was the lighter alternative and was declined.)

## Architecture (identical to lease, adapted to a single global agent)
The complaint agent is ONE global assistant (`VAPI_COMPLAINT_ASSISTANT_ID` → `+14382314283`), not
per-manager — so there is exactly one entry + one French assistant, and **no DB migration** (the lease
per-manager rollout needed `manager_vapi_config.vapi_lease_french_assistant_id`; here the id is an env
var, like the shared lease French id).

- **Entry assistant** (`build_complaint_config(..., french_assistant_id=...)`): keeps the `multi`
  transcriber. When `french_assistant_id` is set it gains:
  - a `[French Routing — STRICT]` prompt block (English-first language gate),
  - a `type:"handoff"` tool → the French assistant (`contextEngineeringPlan:{type:"all"}` so the call
    continues, not restarts),
  - a **static bilingual gate** `first_message` on `assistant-speaks-first`.
  Routes on **anything-not-clearly-English → French** (French, French reply, or garbled/non-Latin
  transcription); a single re-ask only on true silence. English path is byte-identical when the arg is null.
- **French assistant** (`build_complaint_config_french(...)`): `FRENCH_TRANSCRIBER_CONFIG` (nova-3 `fr`),
  a static French opener (`_COMPLAINT_FRENCH_FIRST_MESSAGE`), and a `[French Call — Continuation]` note.
  Same tools, same `/voice/webhook`, no handoff tool (it is the target).
- **Shared French-speech rules** added to `COMPLAINT_SYSTEM_PROMPT` (inherited by both; no-op on English):
  `[French Register — STRICT]` (formal **vous**) and `[Date & Time Pronunciation — STRICT]` (speak
  dates/years/clock times as French words — the TTS reads bare digits with an English accent on French
  calls). Tool submissions stay ISO/English.

### Intentional deviation from the lease entry
The lease entry uses a **model-generated** bilingual gate; the complaint entry uses a **static** bilingual
gate `first_message`. Rationale: the complaint agent already opens with a static message, a fixed gate
question guarantees both languages are offered with no LLM latency on the routing turn, and it avoids a
stale-`firstMessage` merge issue on PATCH. Same routing outcome.

## Files changed
- `backend/app/services/vapi_agent_config.py` — French blocks in `COMPLAINT_SYSTEM_PROMPT`;
  `_COMPLAINT_GATE_FIRST_MESSAGE`, `_COMPLAINT_FRENCH_ROUTING_BLOCK`, `_COMPLAINT_FRENCH_FIRST_MESSAGE`,
  `_COMPLAINT_FRENCH_CONTINUATION_NOTE`, `_complaint_handoff_tool`, `_complaint_assistant_shell`;
  `build_complaint_config(french_assistant_id=…)` + new `build_complaint_config_french`.
- `backend/scripts/provision_complaint_french_handoff.py` — new (create/patch/rollback).
- `backend/scripts/update_shared_agents.py` — passes `VAPI_COMPLAINT_FRENCH_ASSISTANT_ID` so redeploys
  keep the handoff.
- `CODEBASE_CONTEXT.md` — updated.

## Deploy steps (run by the user — I can't reach the VAPI account)
1. `python backend/scripts/provision_complaint_french_handoff.py --dry-run`
2. `python backend/scripts/provision_complaint_french_handoff.py`
3. Add the printed `VAPI_COMPLAINT_FRENCH_ASSISTANT_ID=…` to `.env` and Render.
4. Test calls: one English (must behave exactly as today), one French (must hand off to the `fr`
   assistant and complete a complaint in French).
- Rollback: `python backend/scripts/provision_complaint_french_handoff.py --rollback`.
