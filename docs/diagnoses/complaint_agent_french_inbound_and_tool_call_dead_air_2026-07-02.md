# Complaint Agent — French inbound failures (2026-07-02)

Two separate failures reported by the French test partner, diagnosed from VAPI live config,
call artifacts, and per-request LLM logs (`artifact.logUrl`).

## Failure 1 — inbound never connected (fixed 2026-07-02, morning)

**Symptom:** outbound complaint calls from the website worked; inbound calls to the complaint
number rang but never reached the agent.

**Root cause:** the complaint number `+14382567782` (VAPI phone-number id `c3b8394e…`) had
`assistantId: null` in VAPI. Outbound passes the assistant id per-call
(`POST /voice/call/outbound`), so it works without the binding; inbound routes to the number's
attached assistant — with none attached the call dies. Signature in the call list: inbound call
with **empty assistantId** and `endedReason: call.in-progress.twilio-completed-call`.

**Fix:** `PATCH /phone-number/c3b8394e…` with
`assistantId: 9e507761-7bf7-451a-9413-8ae62ec0176f` (entry complaint assistant, which carries
the French gate + handoff). Not caused by the French handoff work — that only patches assistants.

## Failure 2 — after handoff, FR assistant never calls tools (fixed 2026-07-02, evening)

**Symptom (2 test calls):**
1. Caller gives flat "26" → FR agent says "Laissez-moi vérifier ça dans mon système. Un instant,
   s'il vous plaît." → dead air → `silence-timed-out`.
2. FR agent loops demanding "le numéro complet avec la lettre au début" → caller hangs up.

**Ruled out:** missing tools (live FR config has the identical 6 tools as the entry; per-request
LLM logs show all 6 passed on every FR request), model choice (working lease FR uses the same
`gpt-5.2-chat-latest`), backend (English calls exercise the same endpoints end-to-end fine), and
stored-config mojibake (was a local cp1252 read artifact, not real corruption).

**Root cause (call 1):** `COMPLAINT_SYSTEM_PROMPT` `[System-Check Phrases]` said to speak a
checking phrase *"OUT LOUD before the tool runs"*. On French post-handoff turns the model took
the sequencing literally: it emitted ONLY the scripted filler (21 tokens, no tool call — visible
in `assistant.model.responseSucceeded`) and ended its turn. VAPI only starts a new model turn on
user speech or a tool result, the caller waits silently, and the 30s silence timeout kills the
call. The lease prompt never hits this because it frames narration as *"say the phrase AS you
fire it"* — tool call and phrase in the same turn.

**Root cause (call 2):** the tool-data rule "Never drop the letter" (flat prefixes like "S201")
had no bound, so the FR model refused digits-only "26" and re-asked in a loop while French
endpointing fragmented the caller's replies.

**Fix (both in `backend/app/services/vapi_agent_config.py` → `COMPLAINT_SYSTEM_PROMPT`, shared
by entry + FR):**
- `[System-Check Phrases]` rewritten: phrase and tool call MUST go out in the SAME turn/response;
  ending a turn after announcing a check without the tool call is a hard failure.
- Flat-number rule bounded: digits-only flat numbers are valid; ask about a letter prefix at most
  once, then accept and verify.

**Deploy:** `python backend/scripts/provision_complaint_french_handoff.py` (patches the FR
assistant in place and re-patches the entry with the handoff preserved). Verified live via GET on
both assistants.

**Retest checklist:** English call (unchanged behavior), French call: gate → handoff → give a
digits-only flat number → FR agent must say the checking phrase AND `Verify_phone_number` must
fire in the same turn (no dead air), then complete a complaint through `submit_complaint`.
