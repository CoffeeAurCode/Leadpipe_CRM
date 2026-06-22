# Session — Voice Agent Bilingual & Rotating "System-Check" Phrases

**Date:** 2026-06-22
**Scope:** Task 1 of `leadpipe_phrases_brief.md` (June 20, 2026 brief). Task 2 (French city speech recognition) NOT done — still open.
**Status:** ✅ Implemented + deployed to all live VAPI agents.

---

## Problem

Both voice agents said the same hardcoded English filler every time they hit a tool
(e.g. lease agent's `find_units` → `"One moment."`), regardless of call language or how
many times it had already checked. A static VAPI `request-start` `content` string cannot be
language-aware, cannot rotate, and cannot tell a first check from a later one.

## Requirement (from brief)

- Detect caller language (FR/EN); say the checking phrase in that language the whole call; adapt if caller switches mid-call.
- **First** system check — exact phrasing:
  - EN: "Let me check that in my system. One moment please."
  - FR: "Laissez-moi vérifier ça dans mon système. Un instant, s'il vous plaît."
- **Subsequent** checks — rotate randomly, never back-to-back repeat, language-matched:
  - EN: "Just a second while I pull that up." / "Let me take a quick look at that for you." / "Give me just a moment." / "I'll check on that right now."
  - FR: "Un instant, je vérifie ça pour vous." / "Laissez-moi regarder ça rapidement." / "Juste un moment." / "Je vérifie ça tout de suite."
- Never mix EN/FR in the same call.

## Approach (the key decision)

Static VAPI filler strings can't satisfy any of the above, so **the phrasing was moved
entirely into the model via the system prompt**, and the static `content` strings were
**removed** (emptied to `"messages": []`). Reason for removal (not just addition): if both
existed, the caller would hear the model's bilingual phrase *and* the static English string —
double-speak, and the English string violates the language lock on French calls.

Trade-off: there's no longer a hard VAPI filler guarantee — the model must speak before each
tool call. The prompts mandate this and gpt-5.2 is reliable; the prior design already leaned on
model-spoken fillers anyway. **Verify on real calls.**

---

## Changes — `backend/app/services/vapi_agent_config.py`

### Lease agent (Max)
- Added `[System-Check Phrases — Bilingual & Rotating]` block to `_LEASE_SYSTEM_PROMPT_BASE`.
- Rewrote `[Background Tool Calls — No Dead Air]` to reference the new block (kept the "ask Q1 while `search_listings` runs" behavior).
- Emptied static `content` on `find_units`, `search_listings`, `submit_lease_lead` in `_build_lease_tools`.

### Complaint agent (Alex)
- Added the same `[System-Check Phrases — Bilingual & Rotating]` block to `COMPLAINT_SYSTEM_PROMPT` (after `[Style]`).
- Emptied static `content`/`request-response-delayed` on all 6 tools in `build_complaint_tools`: `Verify_phone_number`, `check_availability`, `view_active_appointments`, `update_appointment`, `cancel_appointment`, `submit_complaint`.

### Left untouched (intentionally)
- Legacy `build_tools()` / `build_assistant_config()` — old test-group agent, NOT pushed by either deploy script; its `request-start` entries have no `content` anyway.

### Docs
- `CODEBASE_CONTEXT.md` updated for both the lease-agent and complaint-agent behaviour sections.

---

## Deploy (run from `backend/`, all succeeded)

Live VAPI assistants don't change until the deploy scripts run.

- `python backend/scripts/update_shared_agents.py` → Complaint agent `+14382314283`, Shared lease agent `+14313415768`.
- `python backend/scripts/update_lease_agents.py` → 4 per-manager lease assistants + 1 shared. Uses direct HTTP PATCH (not the VAPI SDK).

**Interpreter gotcha:** `update_shared_agents.py` needs the `vapi` SDK (present in system Python `C:\Python314`).
`update_lease_agents.py` needs `supabase`+`httpx` (NOT `vapi`) — run it with the backend venv:
`C:\Users\BIT\Coding\Leadpipe_CRM\backend\.venv\Scripts\python.exe`. Neither interpreter has both sets of deps.

Result: 2 shared + 5 lease (4 per-manager + 1 shared) updated, 0 failed. Tools/firstMessageMode/serverMessages verified intact.

---

## Follow-ups / open

1. **Test on real calls** — 1 EN + 1 FR per agent, each with 3+ lookups. Confirm: exact first phrase, varied non-repeating follow-ups, correct language, no dead air. First check is `Verify_phone_number` (complaint) / `find_units` (lease).
2. **Task 2 still open** — improve French speech recognition for city names (Deepgram/transcriber config in `vapi_agent_config.py`).

## Which agent is which
- **Max** = lease agent (`build_lease_config` / `build_lease_config_shared`).
- **Alex** = complaint agent (`build_complaint_config`).
