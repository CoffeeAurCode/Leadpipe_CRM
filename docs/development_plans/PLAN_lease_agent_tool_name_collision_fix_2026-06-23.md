# Plan — Fix VAPI Tool-Name Collision (lease + complaint agents)

**Date:** 2026-06-23
**Owner:** voice agents
**Status:** Ready to implement
**Trigger:** English lease test call (`Transcript4.md` / `Render_logs.md`, call ~17:09–17:13 UTC, manager `28c43c77`).

---

## 1. Symptoms observed

- Agent "kept searching the unit" — fired `find_units` ~10× in a loop.
- Agent kept repeating a bilingual "one moment" line ("Let me check that in my system, one moment. Un instant, je vérifie ça.").
- The lead was **not** logged through the live path (`/voice/lease-lead-direct` never hit).
- Frontend shows the lead as **"Unknown"**.

## 2. Root cause (confirmed)

In `backend/app/services/vapi_agent_config.py`, every `apiRequest` tool declares the **same** inner identifier `function.name = "api_request_tool"`:

- Lease (`_build_lease_tools`): `find_units`, `search_listings`, `submit_lease_lead` — all `api_request_tool`.
- Complaint (`build_complaint_tools`): `Verify_phone_number`, `check_availability`, `view_active_appointments`, `update_appointment`, `cancel_appointment` — all `api_request_tool`.
- Legacy (`build_tools`): same five — all `api_request_tool`.

VAPI/OpenAI deduplicate tools by function name, so only the **first** tool with a duplicated name is reachable by the model. For the lease agent that is `find_units`; `search_listings` and `submit_lease_lead` are invisible. The model, having no lead-capture tool, loops on `find_units` and the call ends with no lead. The end-of-call safety-net (`/voice/lease-eoc-webhook`) then writes a bare `caller_name="Unknown"` row.

Evidence: render logs contain many `GET /leasing/find-units`, **zero** `GET /leasing/search-listings`, **zero** `POST /voice/lease-lead-direct`. One `find_units` call has `query=` (empty) right at handoff time — a `submit_lease_lead` invocation mis-dispatched to `find_units`, dropping all its args.

VAPI guidance: multiple apiRequest tools each need a distinct function name, else the assistant only ever calls the first one.

Secondary: the bilingual "one moment" string is a **static** `request-start` message, so it ignores the per-call language lock (speaks EN+FR even on an English-locked call).

## 3. Fix

### 3a. Unique tool names (the core fix)

Add one helper in `vapi_agent_config.py` and wrap each builder's returned list:

```python
def _alias_apirequest_tool_names(tools: list) -> list:
    """VAPI/OpenAI require each tool's function.name to be unique; duplicates collapse
    so the model can only ever reach the first tool. apiRequest tools historically all
    used 'api_request_tool' — alias each to its (already-unique) top-level name. Pure
    function tools (submit_complaint) have no top-level name and are left untouched."""
    for t in tools:
        top_name = t.get("name")
        fn = t.get("function")
        if top_name and isinstance(fn, dict):
            fn["name"] = top_name
    return tools
```

Wrap the returns of `build_tools`, `build_complaint_tools`, `_build_lease_tools`.

Result — function names become:
- Lease: `find_units`, `search_listings`, `submit_lease_lead`
- Complaint/legacy: `Verify_phone_number`, `check_availability`, `view_active_appointments`, `update_appointment`, `cancel_appointment`
- Unchanged: `submit_complaint` (pure `function` tool, name already unique)

**Why this is safe:** backend handlers never match on `api_request_tool`. apiRequest tools are routed by **URL**; `/voice/webhook` matches `"submit_complaint"` (voice.py:163) and the deprecated lease webhook matches `"submit_lease_lead"` (voice.py:533) — both already unique. The live `submit_lease_lead` posts to `/voice/lease-lead-direct`, which reads the JSON body and ignores the tool name entirely. All function names satisfy VAPI's `^[A-Za-z0-9_-]{1,64}$`.

### 3b. Remove the bilingual static filler (respect language lock)

Mirror the already-working complaint agent: set `messages: []` on `find_units` and `search_listings`, and have the model speak a short **locked-language** checking phrase. Update the lease prompt:
- Replace `[System-Check Phrases — handled automatically]` with a "locked-language only" instruction (single language, no slash, no appended translation, vary phrasing, none for `submit_lease_lead`).
- Update `[Background Tool Calls — No Dead Air]` so the model (not "the system") speaks the brief phrase before each lookup, then keeps the flow moving.

`submit_lease_lead` already has `messages: []` and the model delivers the closing line as it fires — unchanged.

## 4. Deploy (push to live assistants)

Code edits do nothing until pushed to VAPI.

1. Per-manager lease agents (incl. failing `28c43c77`) — HTTP PATCH, reliable:
   `backend/.venv/Scripts/python.exe backend/scripts/update_lease_agents.py --dry-run` then without `--dry-run`.
2. Shared complaint + shared lease agents (VAPI SDK):
   install `vapi` into `backend/.venv`, then `update_shared_agents.py`.

Verify each PATCH echoes the expected `serverMessages` and the new `tools` names.

## 5. Regression guarantees

- **Complaint submit still works:** `submit_complaint` untouched; its 4 sibling apiRequest tools (view/update/cancel/availability) become reachable for the first time — net improvement, no regression to the verify→submit path.
- **Lead logging works end-to-end:** `submit_lease_lead` reachable → `/voice/lease-lead-direct` captures the full lead (name, budget, move-in, occupants); EOC webhook dedups and skips → no more "Unknown" rows.
- **No backend/API/schema changes** — VAPI assistant config only.

## 6. Validation after deploy

- New English lease test call → render logs show `search_listings` + one `POST /voice/lease-lead-direct`; lead appears with the real caller name (not "Unknown").
- Filler spoken in one language only, no repetition.
- Complaint test call → complaint still submits; appointment view/cancel now function.

## 7. Files touched

- `backend/app/services/vapi_agent_config.py` (helper + 3 wraps + 2 `messages` + prompt edits)
- `CODEBASE_CONTEXT.md` (VAPI tool-config note)
- This plan.

---

## 8. Follow-up (2026-06-23) — complaint agent didn't file the complaint

After the lease fix shipped and was verified working, a complaint test call failed to file: the
agent said "your complaint has been logged" but **`submit_complaint` never fired** (no `POST /voice/webhook`).

**Diagnosis (from the live VAPI call `019ef5a4`):** the model emitted `Verify_phone_number` and
`check_availability` (both succeeded — verify returned a real `property_group_id=17232efd…`, slot was
`available`), then produced a pure-text turn claiming success with **no `submit_complaint` tool call**.
So it wasn't a config/schema/data problem — the model had everything and chose to narrate instead of call.

**Root cause:** prompt strength. The lease prompt hammers tool-calling 3× and *excludes*
`submit_lease_lead` from the "say a checking phrase first" list; the complaint prompt mentioned
`submit_complaint` once (buried in a numbered list) *and* listed it among tools to "say a phrase
before" — so the model spoke the checking phrase + the success line as one fluent narration and
skipped the call.

**Fix (prompt only — no tool/webhook/schema change):** in `COMPLAINT_SYSTEM_PROMPT` —
1. Removed `submit_complaint` from `[System-Check Phrases — Bilingual & Rotating]` (do not pre-narrate it).
2. `[CALLBACK SCHEDULING FLOW]` step 4/5: "you MUST emit the submit_complaint call; never say
   'logged' without calling it."
3. Added `[Complaint Submission — NO EXCEPTIONS]` ("the ONLY way to file; a call without it has FAILED";
   retry once on error).

Pushed live via `update_shared_agents.py`; confirmed the new prompt is on assistant `9e507761`.

**Validate:** complaint test call → `POST /voice/webhook` with the `submit_complaint` tool call →
complaint + callback appointment created.
