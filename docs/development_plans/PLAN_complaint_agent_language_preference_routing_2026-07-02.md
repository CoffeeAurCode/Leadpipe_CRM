# Complaint Agent — Per-Tenant Language Preference Routing

**Date:** 2026-07-02
**Status:** ✅ FULLY LIVE (2026-07-02). Migration 032 applied, backend deployed, number repointed to
`/voice/inbound-router`. Verified end-to-end on production with a test tenant: fr lock on first
valid verify → router returns FR assistant + French opener; lock survives a later `language=en`
verify; `en` pref → EN assistant; NULL → entry gate. Awaiting real-call test by the French partner.

## Goal
First call from any tenant: bilingual gate ("English or French?"). The chosen language is stored
per tenant, and every future call — inbound AND outbound — starts directly on the assistant for
that language. English tenants never hear French again and vice versa.

## Design

### Three complaint assistants
| Assistant | Env var | Role |
|---|---|---|
| Entry `9e507761…` | `VAPI_COMPLAINT_ASSISTANT_ID` | Bilingual gate + handoff → FR (unknown callers only) |
| English-locked `43d28cbd…` | `VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID` | Returning `en` tenants; no gate, `[English Call — Locked]` note |
| French `71105e4a…` | `VAPI_COMPLAINT_FRENCH_ASSISTANT_ID` | Handoff target AND direct route for returning `fr` tenants |

### Preference capture (deterministic, no LLM)
Each assistant's `Verify_phone_number` tool URL carries `&language=en|fr` (entry/EN → `en`,
FR → `fr`). `POST /flats/verify-phone` writes `tenants.preferred_language` on a **valid** match,
only when currently NULL — the first verified call locks the choice; later calls never overwrite.

### Inbound routing (assistant-request)
The complaint number drops its static `assistantId`; its `server.url` points at
`POST /voice/inbound-router`. Per inbound call VAPI sends an `assistant-request`; the endpoint
looks up the caller's phone in `tenants` (exact match, then digits-suffix `_phones_match`
fallback) and returns:
- `fr` → `{assistantId: FR, assistantOverrides.firstMessage: COMPLAINT_FRENCH_DIRECT_FIRST_MESSAGE}`
  (the saved FR firstMessage "Parfait, je continue en français…" only fits the mid-call handoff)
- `en` → `{assistantId: EN}`
- unknown / no preference / any error → entry assistant (bilingual gate). Always HTTP 200.

### Outbound routing
`POST /voice/call/outbound` (complaint branch) uses the same `_complaint_assistant_for_phone`
helper; FR gets the direct French opener unless `first_message` was passed explicitly.

## Files changed
- `backend/migrations/032_tenant_preferred_language.sql` — new column + CHECK
- `backend/app/config.py` — `VAPI_COMPLAINT_FRENCH_ASSISTANT_ID`, `VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID`
- `backend/app/services/vapi_agent_config.py` — `build_complaint_tools(language=)`,
  `build_complaint_config_english`, `COMPLAINT_FRENCH_DIRECT_FIRST_MESSAGE`,
  `_COMPLAINT_ENGLISH_LOCKED_NOTE`, continuation note covers direct FR calls
- `backend/app/routes/flats.py` — `verify_phone` records preference (migration-tolerant select)
- `backend/app/routes/voice.py` — `_complaint_assistant_for_phone`, `POST /voice/inbound-router`,
  outbound complaint branch routes by preference
- `backend/scripts/provision_complaint_language_routing.py` — new (EN assistant, `--route-number`,
  `--rollback` restores the static entry binding)

## Deploy order (CRITICAL — inbound breaks if reordered)
1. ✅ Entry + FR assistants re-patched (verify URLs now carry `&language=`; harmless pre-deploy —
   FastAPI ignores the extra param until the new code ships)
2. ✅ English assistant created: `VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID=43d28cbd-d01f-406f-bc70-646f45852a8a`
   (added to local `.env`)
3. ✅ Migration 032 run in the Supabase SQL editor (project `nfgnxndktecqeleabbip`)
4. ✅ Render env: `VAPI_COMPLAINT_ENGLISH_ASSISTANT_ID`, `VAPI_COMPLAINT_FRENCH_ASSISTANT_ID`
5. ✅ Backend deployed (commit `deef01c0` on `test`)
6. ✅ Number repointed: `--route-number` run; VAPI confirms `assistantId=null`,
   `server.url=/voice/inbound-router`
7. ✅ API-level test matrix passed on production (test tenant `9dee048d`, reset to NULL after):
   fr verify locks pref; en verify cannot overwrite; router returns FR+opener / EN / entry per pref.
   ⬜ Real-call test by the French partner pending.

Rollback any time: `python backend/scripts/provision_complaint_language_routing.py --rollback`
(number goes back to the static entry binding; everything else is additive).

## Notes / limitations
- Preference is locked on first verified call by design; to change a tenant's language, update
  `tenants.preferred_language` manually (or clear to NULL to re-gate them).
- `/voice/inbound-router` must answer within VAPI's assistant-request timeout (~7.5 s) — if the
  Render service can cold-start, inbound calls during a cold start will fail; keep the service warm.
- Tenants sharing one phone number resolve to the first matching row's preference.
