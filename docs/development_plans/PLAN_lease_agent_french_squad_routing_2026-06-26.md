# Lease Agent — French-Only STT via Direct Handoff

**Date:** 2026-06-26
**Status:** LIVE on all 4 per-manager agents (2026-06-26) — in testing. Shared agent not wired. Rollback: `provision_lease_french_handoff.py --rollback --all --fleet-only`.
**Owner decision on file:** route French callers to a dedicated French-only assistant (chosen "language-router squad" — implemented via a **direct handoff tool, no squad object needed**, see §2).
**Related:** `PLAN_lease_agent_french_refinement_options_2026-06-25.md` (this completes R2 — dedicated FR transcriber), Session 12 (Québec city garble), Session 13 (French register lock).

---

## 1. Goal

French callers should be transcribed by a **dedicated French Deepgram model** (`language:"fr"`) instead of the shared `multi` model, while the **English path stays exactly as it is today**. The dedicated `fr` model unlocks French keyterm prompting (R2) — the part `multi` couldn't use — and is where Québec-French accuracy was hurting (Session 12).

The transcriber language is fixed at call-start and **cannot be switched mid-call**. So the switch happens at **routing time**, by handing the call off to a second assistant — not inside one assistant.

---

## 2. Architecture — entry = existing agent, French is the only branch (via direct handoff, no squad)

The current lease agent stays the entry assistant on the existing phone number. We add **one gated handoff tool**: if the caller's first utterance is French, the entry assistant hands the call off to a dedicated French assistant (targeted by `assistantId`); otherwise it continues exactly as today. English callers experience **zero change** — the handoff never fires.

```
Inbound call ──► Entry assistant = CURRENT lease agent (Deepgram multi)  [phone # UNCHANGED]
                 │  greets bilingually, reads caller's FIRST utterance
                 │
                 ├─ English detected ─► stay here. Nothing changes. (today's behavior)
                 │
                 └─ French detected ──► handoff tool (assistantId, contextEngineeringPlan:"all")
                                        ►  French-only assistant
                                           • Deepgram language:"fr", confidenceThreshold 0.4
                                           • French keyterms (unlocks R2)
                                           • [French Register], [Unit Size], Q2 template
                                           • French voicemail / endCall
                                           • eleven_flash_v2_5 (LEASE_VOICE_CONFIG)
```

**Verified against Vapi docs (2026-06-26):**
- Handoff destinations can target a **saved `assistantId` with NO squad** — the inbound number keeps pointing at the single entry assistant. (`docs.vapi.ai/squads/handoff`)
- Handoff tool shape (attached to the entry assistant's `model.tools`):
  ```json
  { "type": "handoff",
    "destinations": [
      { "type": "assistant",
        "assistantId": "<french assistant id>",
        "description": "Transfer when the caller is speaking French.",
        "contextEngineeringPlan": { "type": "all" } } ] }
  ```
  `contextEngineeringPlan:{type:"all"}` carries the conversation so the French assistant **continues, not restarts**.

### What it buys vs. the unavoidable cost
- **Win:** the entire French *conversation* runs on the dedicated `fr` model with keyterms.
- **Unavoidable cost:** the caller's **first French utterance is still transcribed on `multi`** (you must hear them before routing). Keep the entry turn trivial — greet, hear one turn, hand off.

### Gotchas to design for
1. **Smooth handoff, no double-greeting.** The French assistant must *continue* (context carried), e.g. open with "Parfait, je continue en français — qu'est-ce que vous cherchez?" — validate the exact first-message behavior on a test call.
2. **Detection rule must be explicit + the handoff `description` must scope to French only**, so it never mis-fires for an English caller. Entry prompt: "On the caller's first utterance, if it is French → call the handoff tool immediately, do not answer in French yourself. If unclear → ask 'English or French? / Anglais ou français?' then route."
3. **Per-manager fan-out.** 4 per-manager + 1 shared. Each needs its own French sibling assistant + the handoff id wired into its entry assistant.
4. **Keyterms are per-manager.** French assistant's Deepgram keyterms seed from that manager's real city/street values (R2 corpus).

---

## 3. Implementation scope (small — no squad, no repoint)

`vapi_agent_config.py`:
- `FRENCH_TRANSCRIBER_CONFIG` — `nova-3`, `language:"fr"`, `confidenceThreshold 0.4`, keyterms, OpenAI fallback.
- `build_lease_config_french()` / `_shared()` — French-only assistant (French transcriber, French-continuation first message, the four French blocks).
- `_lease_handoff_tool(french_assistant_id)` — the gated handoff tool.
- `build_lease_config()` / `_shared()` gain an optional `french_assistant_id=None` param: when set, append a `[French Routing]` block to the prompt and add the handoff tool; when `None`, byte-for-byte today's config (backward-compatible for every existing caller).

`backend/scripts/provision_lease_french_handoff.py` (new): create the French assistant → store its id → re-PATCH the entry assistant so it carries the handoff tool. `--dry-run` + `--shared-only` (pilot).

`update_lease_agents.py`: read each entry's French assistant id (env for shared, DB column per-manager) and pass it to `build_lease_config`, so redeploys don't drop the handoff tool.

**Persistence:** pilot stores the shared French id in env `VAPI_SHARED_LEASE_FRENCH_ASSISTANT_ID` — **no schema change for the pilot**. Per-manager rollout later adds `manager_vapi_config.vapi_lease_french_assistant_id`.

---

## 4. Honest risk assessment (materially lower than the squad version)

| Part | Risk | Why |
|---|---|---|
| Inbound phone routing | **None** | Number stays on the entry assistant. No squad, no repoint. |
| English prompt/behavior | **None** | Handoff is gated "if French"; for English it never fires. `french_assistant_id=None` path is unchanged. |
| French assistant content | Low | Additive; reuses the four already-shipped French blocks. Creating it has no effect until handed to. |
| Handoff **mis-fire** on an English caller | Low–Med | Model could wrongly trigger handoff. Mitigation: tight handoff `description` + routing block scoped to French; validated by an English test call. |
| French handoff UX (double-greet / latency / lost context) | Med | First time exercised here. Validated by a native-French test call before fleet rollout. |
| First French utterance on `multi` | Accepted | Inherent to in-call detection; mitigated by handing off after one turn. |

**Bottom line:** with the no-squad handoff, the live blast radius is one additive, French-gated tool on the entry assistant — close to Session 13's profile. The two things that genuinely can misbehave (handoff mis-fire on English; the French handoff UX) are exactly what the shared-agent pilot test call exists to catch. Still pilot first; do not big-bang all five.

---

## 5. Rollback

Trivial: re-run `update_lease_agents.py` with no French id → the entry assistant is rebuilt without the handoff tool, instantly back to today. The French assistant can be deleted afterward. No phone change, no DB migration, no backend deploy.

---

## 6. Staged rollout (pilot-gated)

1. **Build** `build_lease_config_french()`, the gated handoff in `build_lease_config()`, and `provision_lease_french_handoff.py` (`--dry-run`). No live impact.
2. **Dry-run** the provisioning to confirm payloads.
3. **Pilot on the SHARED agent only:** create its French assistant, store the id in env, PATCH the shared entry assistant to carry the handoff tool.
4. **Validate:** English test call (no handoff, identical to today); native-French test call (handoff fires, French assistant continues without re-greeting, runs on `fr`, lead saved). Read the agent's own French lines in the transcript (Session 13 lesson).
5. **Only then** roll to the 4 per-manager agents + add the DB column + auto-wire new-manager provisioning ("all future lease agents").
6. **Paper trail:** update `CODEBASE_CONTEXT.md`, mark this plan done, write the session learning-material file.

---

## 7. Open decisions before fleet rollout

- Per-manager persistence column `manager_vapi_config.vapi_lease_french_assistant_id` + migration (pilot uses env, so deferred).
- Keyterm source per manager (reuse R2 corpus / `generate_stt_garble_corpus.py`).
- Entry assistant stays on `multi` (required for detection) — confirm not switching it to `en`.
- Exact French-assistant first-message behavior on handoff (continue vs. re-greet) — settle from the pilot transcript.
