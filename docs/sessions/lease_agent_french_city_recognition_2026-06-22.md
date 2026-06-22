# Session Context — Lease Agent French-Accent City Recognition

> Date: 2026-06-22. Topic: why Max (lease voice agent) still can't recognize Quebec city names spoken
> with a French accent, and what to do about it. Output of this session: a ranked solution plan + a
> completed Phase-0 diagnosis grounded in 3 real call transcripts.

## Task

User report: "the voice lease agent is still not able to recognise city names in French accent." Asked for
(1) a plan ranking all possible solutions, then (2) to complete the diagnosis from 3 supplied transcripts —
explicitly "don't hallucinate or do something for the sake of it."

## What was already in place (prior work, before this session)

- `backend/app/services/city_matching.py` — `normalize_place` (strip diacritics, hyphens, St/Ste→Saint/Sainte)
  + `city_matches` (substring + FR/EN alias map + `difflib` ratio ≥ 0.82). Unit tests in
  `tests/test_city_matching.py` pass.
- `find_units` (`backend/app/routes/leasing.py:152-249`) uses that matcher and returns `available_cities`
  (the manager's distinct active-listing cities) on every call.
- Lease agent prompt + tool wiring in `backend/app/services/vapi_agent_config.py` already instruct the no-match
  branch to offer `available_cities`.
- Prior plan `docs/development_plans/PLAN_voice_agent_city_recognition.md` — covered the **backend matching**
  layer only; shipped. The bug persisted anyway → motivated this session.

## Key insight this session

The persisting failure is **not** the backend matcher (already accent/fuzzy-tolerant). It is **upstream at the
Deepgram STT layer**: in `language:"multi"`, French-accented city names are mis-transcribed so badly that no
string match can recover them (garbage in → garbage out). Lowering the `difflib` 0.82 threshold can't win —
it would start matching distinct nearby cities (Laval≈Longueuil).

Verified fact (web-checked): **Deepgram nova-3 keyterm prompting now works in `language:"multi"`** (Nov-2025
update, ~500 tokens) and Vapi exposes a `keyterm` array on the Deepgram transcriber. This unblocks biasing the
STT toward a manager's real city names without leaving bilingual mode.

## Deliverable 1 — Ranked plan

`docs/development_plans/PLAN_lease_agent_french_accent_stt_city_recognition.md`. Solutions grouped by pipeline
layer (A: STT, B: LLM, C: backend, D: process) and ranked by impact × low effort × low risk. Top of the ranking:

1. **B1 — LLM canonicalizes the spoken city against the manager's portfolio list** before calling the tool
   (gpt-5.2 is bilingual; bridges phonetic gaps difflib can't; no infra/latency).
2. **A1 — Deepgram multilingual keyterm prompting** seeded with the manager's real cities (fixes the transcript
   at source; caveat: keyterms bake into the assistant → need a refresh hook when a manager's cities change).
3. **D1 — diagnose from transcripts/`call_logs`** first (cheap, de-risks everything).
   Then B2 (confirm-the-city turn), C1 (phonetic/`rapidfuzz`), C2 (data-driven alias map); A3 (Whisper-class
   STT primary) held as escalation. Recommended path: **D1 → B1 + A1 → B2 → (C1/C2 as needed)**.

Deploy gotcha captured: none of these go live until `python backend/scripts/update_lease_agents.py` is run
against the per-manager assistants.

## Deliverable 2 — Completed Phase-0 diagnosis

`docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md`, from 3 transcripts
(`docs/development_plans/transcript1..3.md`).

**Finding 1 (confirmed):** Deepgram `multi` garbles Quebec French. Corpus:
| Caller meant | Transcribed | Source |
|---|---|---|
| Vaudreuil-Dorion | "Nathan Vaudreuil d'Orient" | T2 |
| Saint-Lazare | "Astin Lagar" (1st), "Saint-Lazare" clean (2nd) | T3 |
| Saint-* (unresolved) | "Saint-Azal" | T2 |
| unrecoverable | "je suis en allant du carré, cinq heures" | T1 |

**Finding 2 (the important one — these calls are CONFOUNDED):** In all 3 calls Max never offered
`available_cities`, and in T3 a **cleanly** transcribed "Saint-Lazare" still returned no match. Code is wired
correctly — `manager_id` in the find_units URL (`vapi_agent_config.py:1253`), `available_cities` in the tool
schema (`:1347`), prompt reads it on no-match (`:1069`); and `available_cities` is empty **only** when the
manager has zero active listings (`leasing.py:173-179`). So the most parsimonious cause of these specific
failures is that the **test managers ("Sean Serre", "Chantery") have no active listings** — not French accent.
Schema, scoping, and matcher are all ruled out as the proximate cause here.

**Honest conclusion:** the STT garble is real and will bite once portfolios are populated, but these three
recordings do **not** prove the accent bug. Don't ship STT changes on their strength alone.

## Open items / next steps

1. **Confirm the portfolio** for the two managers under test:
   `select city, count(*) from lease_listings where is_active and manager_id = <id> group by city;`
   - Empty → recordings are confounded; re-test against a manager with listings in the named cities.
   - Populated and a clean French city still misses → STT confirmed; proceed to A1/B1, seed
     `tests/test_city_matching.py` with the corpus above.
2. (Offered, not yet written) `backend/scripts/analyze_city_mistranscriptions.py` to scale transcript mining
   over all `call_logs`; and `backend/scripts/` portfolio-check query.
3. Incidental bug (not the city issue): T1 first greeting renders the manager name blank ("…leasing assistant
   **for.** Are you looking…", `transcript1.md:2`) before re-greeting as "Sean Seri" — first-message/name bug,
   worth a separate follow-up.

## Files created/changed this session

| File | What |
|---|---|
| `docs/development_plans/PLAN_lease_agent_french_accent_stt_city_recognition.md` | **New** — ranked solution plan (Phase 0 since marked DONE) |
| `docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md` | **New** — completed Phase-0 diagnosis from transcripts |
| `docs/sessions/lease_agent_french_city_recognition_2026-06-22.md` | **New** — this handoff |

No application code changed this session (planning + diagnosis only).
