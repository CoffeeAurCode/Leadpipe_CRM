# Lease Agent — Latency Config Snapshot & Rollback (2026-06-23)

Records the before/after of the latency changes shipped 2026-06-23 so the lease agents can be
rolled back. Two surfaces change independently:

- **VAPI assistant config** (model + voice) — lives in `vapi_agent_config.py`, pushed to VAPI by
  `backend/scripts/update_lease_agents.py`. Takes effect the moment the script runs.
- **Backend route** (`find_units`) — lives in `backend/app/routes/leasing.py`, runs on Render. Takes
  effect only after the backend is redeployed (git push to the Render-tracked branch). The script does
  **not** deploy backend code.

Each change is reversible on its own — you can roll back just the voice (if French TTS regresses),
just the model, or just `find_units`, without touching the others.

---

## Change 1 — LLM model (#1)  ·  VAPI config

`vapi_agent_config.py` → `_lease_assistant_shell()` → `model.model`

| | Value |
|---|---|
| **BEFORE** | `gpt-5.2-chat-latest` |
| **AFTER**  | `gpt-4o` |

`provider: openai`, `maxTokens: 300`, `temperature: 0.7`, `tools` — all unchanged.

**Why:** LLM time-to-first-token dominated the 2–4s per-turn pause (paid on every turn, tool or not).
**Watch:** Quebec-French fluency, register (vous/tu) consistency, qualification-flow adherence,
tool-call reliability. These are the quality axes a smaller model can regress.

---

## Change 2 — TTS model (#5)  ·  VAPI config

`vapi_agent_config.py` → new `LEASE_VOICE_CONFIG` (lease-only; shared `VOICE_CONFIG` left untouched so
the complaint/tenant agents are unaffected).

| | Value |
|---|---|
| **BEFORE** | lease used `VOICE_CONFIG` directly, `model: eleven_turbo_v2_5` |
| **AFTER**  | lease uses `LEASE_VOICE_CONFIG = {**VOICE_CONFIG, "model": "eleven_flash_v2_5"}` |

Same `voiceId` (`E4GQ42zEV1kwul03Bl16`), `speed 1`, `stability 0.6`, `similarityBoost 0.75`,
`useSpeakerBoost true`, `inputMinCharacters 15`, `optimizeStreamingLatency 1` — only the TTS model changed.

**Why:** Flash v2.5 lowers TTS first-byte. **Watch:** French pronunciation/naturalness — this is the
change most likely to need rolling back. Same voice library, so timbre should be unchanged.

---

## Change 3 — `find_units` single nested query (#3)  ·  backend route

`backend/app/routes/leasing.py` → `find_units()`

**BEFORE:** 3 sequential Supabase queries — `lease_listings` (with `flats!inner(... building_id)`),
then `buildings`, then `properties_list` — joined in Python via `building_rows` / `property_rows` dicts.

**AFTER:** 1 query with a nested embed; building/property names read from the embed:
```
flats!inner(bedrooms, bathrooms, floor_number, buildings(name, properties_list(name)))
```
```python
building = flat.get("buildings") or {}
prop_group = building.get("properties_list") or {}
if not isinstance(prop_group, dict):
    prop_group = {}
```

**Why:** removes 2 network round trips per lookup. Validated against the live schema (returns
building/property names; null building handled; `properties_list` is to-one → dict). Return shape
unchanged.

---

## Deploy commands

- **VAPI config (Changes 1 & 2):**
  `backend\.venv\Scripts\python.exe backend/scripts/update_lease_agents.py`
  (dry-run first with `--dry-run`). Pushes to all active per-manager lease agents + the shared agent.
- **Backend (Change 3):** commit `leasing.py` and push to the Render-tracked branch; Render redeploys.

## Rollback

1. **Model and/or voice:** in `vapi_agent_config.py`, restore the BEFORE value(s) above
   (`gpt-5.2-chat-latest` and/or `LEASE_VOICE_CONFIG` model → `eleven_turbo_v2_5`, or point the lease
   `voice` back at `VOICE_CONFIG`), then re-run `update_lease_agents.py`.
2. **`find_units`:** revert the `leasing.py` edit to the 3-query BEFORE version and redeploy the backend.
   Until the backend is redeployed, the live behaviour is whatever is currently deployed on Render.
