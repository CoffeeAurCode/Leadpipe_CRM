# Lease Agent (Max) — Call Diagnosis: "Pauses a lot / doesn't understand me"

> **Date:** 2026-06-22
> **Agent:** Max — lease voice agent (`build_lease_config`)
> **Source calls:** `Transcript1.md`, `Transcript2.md` (French partner, 2 test calls)
> **Portfolio under test:** `Lease_listing_shaun.csv` (manager `eb4b27dc-…3d084e9d`)
> **Partner's report:** "the agent was pausing a lot saying *one moment* a lot, and the agent was not understanding him."

## Verdict

**Both complaints are confirmed by the transcripts.** They are two different problems with two different root causes, and they **compound each other**:

| # | Complaint | Confirmed? | Root cause | Status |
|---|---|---|---|---|
| 1 | "Pausing a lot / *one moment* a lot" | ✅ Yes | The bilingual "system-check phrase" feature **shipped today** (2026-06-22) fires a stall phrase before **every** lookup, and the agent runs `find_units` on nearly every turn. Working as specified, but the **frequency** makes it feel like constant stalling — and the model over-applies the phrase even on turns with no lookup. | Behaving as designed; needs tuning |
| 2 | "Not understanding him" | ✅ Yes | Deepgram `language:"multi"` (`vapi_agent_config.py:289`) garbles Quebec-French speech — city names and short answers come back as English gibberish. | Known open issue (Task 2), fix planned not shipped |

**Good news:** Because Shaun's portfolio is actually populated (unlike the 3 earlier *confounded* test calls), the `available_cities` fallback **recovered** call 2 despite the garble — the architecture works end-to-end here. The cost is extra turns, which feeds straight back into complaint 1.

---

## Method & sources

- Read both transcripts turn-by-turn, including the `Find Units` tool events and their timestamps.
- Cross-checked the agent's quotes against `Lease_listing_shaun.csv` (the 3 listings the manager has live).
- Grounded the root causes in the live config:
  - Transcriber: `TRANSCRIBER_CONFIG` — Deepgram `nova-3`, `language:"multi"`, `confidenceThreshold:0.4` (`vapi_agent_config.py:286-301`).
  - System-check phrases: `[System-Check Phrases — Bilingual & Rotating]` (`vapi_agent_config.py:1204-1229`) and `[Background Tool Calls — No Dead Air]` (`:1231-1260`).
  - No-match fallback: `find_units` "No match → offer `available_cities`" (`vapi_agent_config.py:1069-1074`).
- Prior context (same system, same week):
  - `docs/sessions/voice_agent_bilingual_system_check_phrases_2026-06-22.md` — the stall-phrase feature was added **today**; static VAPI fillers were removed and the phrasing moved into the model. Its own follow-up #1 was literally *"Test on real calls."* These two calls are that test.
  - `docs/sessions/lease_agent_french_city_recognition_2026-06-22.md` + `docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md` — already diagnosed `multi` garbling French city names; the earlier 3 calls were *confounded* (managers had no listings). Task 2 (STT fix) still open.

---

## Complaint 1 — "Pausing a lot, saying *one moment* a lot" ✅ CONFIRMED

### What the caller actually heard

In **Transcript 2**, *every single* agent turn opens with a checking/stall phrase — 4 of them in ~85 seconds:

| Time | Agent opener | What it is |
|---|---|---|
| 02:11:14 | "Laissez-moi vérifier ça dans mon système. **Un instant s'il vous plaît.**" | The mandated FIRST-check phrase, **verbatim** (`vapi_agent_config.py:1215`) |
| 02:11:33 | "**Un instant, je vérifie ça pour vous**, parfait…" | Rotating phrase #1 (`:1226`) |
| 02:11:52 | "**Juste un moment**, nous avons un quatre et demi…" | Rotating phrase #3 (`:1228`) — **no `find_units` ran before this turn** |
| 02:12:16 | "**Je vérifie ça tout de suite**, parfait…" | Rotating phrase #4 (`:1229`) |

In **Transcript 1**: "**1 moment.**" (02:30:04) as a standalone turn after `find_units`.

### Root cause

This is the **direct, predictable side-effect of the feature shipped this morning** (`voice_agent_bilingual_system_check_phrases_2026-06-22.md`). The prompt now *mandates* a spoken checking phrase before every lookup, and removed the old static VAPI filler. Two things make it feel like constant stalling:

1. **Lookup frequency is high.** `find_units` is wired to run at the location step **and again after every city clarification** (`vapi_agent_config.py:1062` + the "Wait → retry find_units" no-match loop at `:1074`). In T2 it fired 3× (02:11:10, 02:11:30, 02:12:12) — once per garbled-then-corrected city — and each fire earns its own stall phrase. Every STT miss = one more "un moment." (This is the compounding with complaint 2.)
2. **The model over-applies the phrase to non-lookup turns.** At T2 02:11:52 the agent opens "**Juste un moment**" and then immediately recites the rent — but there is **no `Find Units` event** between 02:11:30 and that turn. It already had the data; the stall phrase was gratuitous. The prompt says "any time you look something up" (`:1205`), but the model is reaching for it even when it isn't looking anything up.

The feature itself is *working to spec*: phrases are **French-locked**, **rotating**, and **never back-to-back repeats** (first → #1 → #3 → #4). The problem is **density and misapplication**, not correctness.

> Note: the pauses are also genuinely *long* — T2 caller says "Oui" at 02:12:09, no reply until 02:12:16 (~7s); T1 "Saint Lazole" 02:30:00 → "1 moment" 02:30:04 → answer 02:30:07. The stall phrase is papering over real tool-round-trip latency, so cutting the number of lookups helps the latency *and* the phrase count at once.

---

## Complaint 2 — "Not understanding him" ✅ CONFIRMED

### The speech-to-text is garbling Quebec French

The caller is a native French speaker. Deepgram `language:"multi"` mis-transcribes his speech into English-ish gibberish:

| Caller almost certainly said | Transcribed as | Where |
|---|---|---|
| Saint-Lazare (city) | **"thing on low"** | T1 02:29:39 |
| Saint-Lazare | **"Saint Lazole"** | T1 02:30:00 |
| (oui / short answer) | **"Uh, we"** then **"we Wheat"** | T1 02:31:00 / 02:31:06 |
| Saint-Lazare | **"Saint-L'Asor"** | T2 02:11:01 |
| Saint-Lazare | **"Saint-Lavaure"** | T2 02:11:27 |
| quatre et demi (4½) | **"Captain mi"** | T2 02:11:44 |

The garbled token then flows into the tool: the agent searched and *spoke back* "**Saint-LaSort**" / "**Saint-Laçore**" (T2 02:11:14) — i.e. it's matching against noise, not the real city.

### Root cause

Confirmed in config: `TRANSCRIBER_CONFIG` uses `language:"multi"` (`vapi_agent_config.py:289`). This is the **exact failure mode already diagnosed** in `lease_agent_french_city_stt_2026-06-18.md`: in `multi`, French-accented Quebec proper nouns are mangled so badly that no downstream string-matcher can recover them (garbage in → garbage out). The planned fixes — Deepgram **keyterm prompting** (A1) and **LLM canonicalization of the city against the manager's portfolio** (B1) — are **not yet shipped**. Task 2 in the city-recognition session is still open.

`confidenceThreshold:0.4` (`:291`) also silently *drops* the worst tokens, which is why T1 has the agent re-asking into apparent silence (see secondary finding 3).

### …but this time the fallback rescued the call

Unlike the earlier *confounded* calls (test managers had **no** listings, so `available_cities` was empty), Shaun's portfolio is populated, so the recovery path actually engaged:

- T2 02:11:14 — `find_units` on the garbled "Saint-L'Asor" returned no match, and the agent correctly executed the **no-match → offer `available_cities`** branch (`vapi_agent_config.py:1069-1073`): *"nous avons des logements à **Château Gué** et à **Saint-Laçore**"* — i.e. the real cities **Châteauguay** and **Saint-Lazare** from the CSV.
- The caller picked Saint-Lazare, the second `find_units` matched, and the unit was quoted **correctly** against the data: 4½, Saint-Lazare, **$1400/mo** (CSV row 84).

So the matcher + `available_cities` fallback is the safety net that makes the agent *eventually* understand the caller. It works — but it costs the caller 2–3 repeats of the city, which is exactly what "not understanding him" feels like, and each repeat triggers another stall phrase.

---

## How the two complaints compound

```
STT garbles the city  →  find_units no-match / wrong match  →  agent re-asks + re-runs find_units
        ▲                                                                   │
        │                                                                   ▼
   caller repeats  ◄───────────  another mandated "un moment" stall phrase ─┘
```

Every STT miss forces an extra `find_units`, and every `find_units` earns another stall phrase. **Fixing the STT (complaint 2) directly reduces the number of lookups, which directly reduces the stall-phrase density (complaint 1).** They are not independent annoyances — #2 is a multiplier on #1.

---

## Secondary findings

1. **Company name renders blank in the T1 greeting.** T1 line 2: *"I'm Max, the AI leasing assistant **for.** Are you looking…"* — the business-name variable was empty. T2 rendered it fine ("Chantellery"). This is the same intermittent first-message/name bug flagged as open item #3 in `lease_agent_french_city_recognition_2026-06-22.md`. Make the greeting fall back gracefully so it never says "…for." with a blank.

2. **The agent's own French is sometimes broken (model output, not STT).**
   - T1 02:30:50: *"…juillet ça fonctionne avec la disponibilité, **bref c'est ce que votre propriétaire actuel sait que vous regardez pour déménager.**"* — the screening question ("does your current landlord know you're looking to move?") came out malformed.
   - T1 02:31:04: *"**Tu n'es pas bien compris**…"* — grammatically wrong (should be *"Je n'ai pas bien compris"*) **and** it switches from *vous* to *tu* mid-call. The `[Language Policy]` locks EN/FR but does **not** enforce *vous*/*tu* register consistency. This makes the agent itself feel like it isn't understanding.

3. **Back-to-back re-prompt into silence (T1).** 02:29:42 and 02:29:53 are two agent turns with no caller turn between them, both re-asking for the city. The caller's prior word ("thing on low") was low-confidence and dropped by `confidenceThreshold:0.4`, leaving the agent with nothing → it re-asked twice within 11s. Tune endpointing so a dropped token doesn't trigger an immediate double re-prompt; ask once, then wait.

4. **Data hygiene in the CSV (not call-breaking yet, but verify):**
   - The agent quoted *"au **carré Saint-Laurent** à Saint-Lazare"* but CSV row 84's `street_address` is **"2803 Rue Du Comtois"**. "carré Saint-Laurent" is likely a property-group/building name — confirm the source so the agent doesn't quote a building that contradicts the address a tenant shows up to.
   - `state` is inconsistent: row 84 = **"QC"**, row 85 = **"Quebec"**. Normalize.
   - Row 83 (flat 21, $1300, 3 bed/2 bath) has **no city, no street_address, and no `available_from`** — it can't surface sensibly in `find_units` and would read oddly if it did. Backfill or deactivate.

---

## Recommendations (ranked)

Tie-ins to already-written plans are noted so this doesn't reopen settled decisions.

| Pri | Fix | Why / where |
|---|---|---|
| **P0** | **Ship the STT city fix.** Enable Deepgram **keyterm prompting** (A1) seeded with the manager's real cities (here: *Saint-Lazare, Châteauguay*) **and/or** add the **LLM city-canonicalization** turn (B1) before `find_units`. | Root cause of complaint 2 **and** the multiplier on complaint 1. Plan already exists: `PLAN_lease_agent_french_accent_stt_city_recognition.md`. Seed `tests/test_city_matching.py` with the garble corpus in the table above. |
| **P0** | **Cut stall-phrase density.** (a) Only speak a checking phrase on turns where a tool **actually runs** — stop the over-application seen at T2 02:11:52. (b) Don't re-call `find_units` for a city the call already resolved; cache the result/`available_cities` within the call so a clarification doesn't always re-hit the tool. | Directly addresses complaint 1 without removing the (correctly-working) bilingual feature. Touches `[System-Check Phrases]` / `[Background Tool Calls]` (`vapi_agent_config.py:1204-1260`) and the find_units retry loop (`:1062,:1074`). |
| **P1** | **Fix the blank company name** in the first message so it can never render "…for." with an empty variable. | Secondary finding 1; recurring (also noted in the city-recognition session). |
| **P1** | **Add a *vous*/*tu* consistency rule** and fix the screening-question phrasing in `_LEASE_SYSTEM_PROMPT_BASE`; correct "Je n'ai pas bien compris". | Secondary finding 2 — the agent's own French. |
| **P2** | **Tune endpointing** so a low-confidence dropped token doesn't trigger an immediate double re-prompt. | Secondary finding 3; adds to the "pausing" feel. |
| **P2** | **CSV data hygiene** — confirm "carré Saint-Laurent" vs "Rue Du Comtois", normalize `state` (QC/Quebec), backfill or deactivate row 83. | Secondary finding 4. |

> **Deploy gotcha (from the prior sessions):** none of the prompt/transcriber changes go live until the per-manager assistants are re-pushed — `python backend/scripts/update_lease_agents.py` (run with the backend venv: `backend\.venv\Scripts\python.exe`; that script needs `supabase`+`httpx`, **not** the `vapi` SDK).

---

## Appendix — annotated call timelines

### Transcript 1 (~2 min, ends mid-sentence)

| Time | Who | Content | Note |
|---|---|---|---|
| 02:29:12 | Max | "…the AI leasing assistant **for.** Are you looking…" | ⚠️ blank company name |
| 02:29:21 | Caller | "Oui salut… j'ai vu que vous aviez des unités à louer, je serais intéressé." | clean FR |
| 02:29:31 | Max | "Dans quel quartier ou quelle ville se trouvait l'immeuble…" | asks city |
| 02:29:39 | Caller | **"Uh, thing on low."** | ⚠️ STT garble (Saint-Lazare) |
| 02:29:42 | Max | "…vous pouvez me redire le nom de la rue ou de la ville…" | re-ask #1 |
| 02:29:53 | Max | "Je veux juste être sûr de bien comprendre… quelle ville…" | ⚠️ re-ask #2, no caller turn between |
| 02:30:00 | Caller | **"Saint Lazole."** | ⚠️ STT garble |
| 02:30:02 | 🔧 | **Find Units** ✓ | |
| 02:30:04 | Max | **"1 moment."** | ⚠️ stall phrase (standalone) |
| 02:30:07 | Max | "Parfait. Nous avons des logements à Saint-Lazare. Quelle grandeur…" | match recovered |
| 02:30:15 | Caller | "…c'était des quatre et demi… il est à combien par mois?" | clean FR |
| 02:30:30 | Max | "…un quatre et demi au carré Saint-Laurent à Saint-Lazare à **quatorze cents** par mois, dispo du 22 juin 2026…" | ✓ matches CSV row 84 (but "carré Saint-Laurent" ≠ "Rue Du Comtois") |
| 02:30:45 | Caller | "C'est pour juillet, le mois prochain." | clean FR |
| 02:30:50 | Max | "…juillet ça fonctionne… **bref c'est ce que votre propriétaire actuel sait que vous regardez pour déménager.**" | ⚠️ malformed FR (screening Q) |
| 02:31:00 | Caller | **"Uh, we"** | ⚠️ STT garble |
| 02:31:04 | Max | "**Tu n'es pas bien compris**, est-ce que… votre propriétaire actuel est au courant…" | ⚠️ wrong grammar + vous→tu |
| 02:31:06 | Caller | **"we Wheat."** | ⚠️ STT garble |
| 02:31:13 | Max | "Désolé, je veux juste confirmer…" | call cuts off |

### Transcript 2 (~85s, ends cleanly mid-flow)

| Time | Who | Content | Note |
|---|---|---|---|
| 02:10:52 | Max | "I'm Max the AI leasing assistant for **Chantellery**…" | ✓ name renders |
| 02:11:01 | Caller | "…je suis à **Saint-L'Asor** présentement… des unités à louer…" | ⚠️ STT garble (Saint-Lazare) |
| 02:11:10 | 🔧 | **Find Units** ✓ (on garbled token) | |
| 02:11:14 | Max | "**Laissez-moi vérifier ça dans mon système. Un instant s'il vous plaît.** Je ne trouve rien à Saint-LaSort… mais nous avons **Château Gué** et **Saint-Laçore**…" | mandated 1st-check phrase + ✓ `available_cities` fallback (Châteauguay + Saint-Lazare) |
| 02:11:27 | Caller | "Oui, **Saint-Lavaure**." | picks Saint-Lazare (still garbled) |
| 02:11:30 | 🔧 | **Find Units** ✓ | |
| 02:11:33 | Max | "**Un instant, je vérifie ça pour vous**, parfait. Nous avons un logement à Saint-Lazare. Quel format — 3½ ou 4½?" | rotating phrase #1 |
| 02:11:44 | Caller | "**Captain mi** s'il vous plaît… c'est quoi le montant par mois pour les quatre et demi?" | ⚠️ STT garble (quatre et demi) |
| 02:11:52 | Max | "**Juste un moment**, nous avons un quatre et demi à Saint-Lazare à **quatorze cent** par mois. Ce budget vous convient?" | ⚠️ stall phrase with **no preceding lookup**; price ✓ (CSV row 84) |
| 02:12:09 | Caller | "Oui," | clean |
| 02:12:12 | 🔧 | **Find Units** ✓ | |
| 02:12:16 | Max | "**Je vérifie ça tout de suite**, parfait. Le quatre et demi au carré Saint-Laurent à quatorze cent par mois." | rotating phrase #4 |

**Stall-phrase count: 4 in ~85s.** Rotation correct (1st verbatim → #1 → #3 → #4, no repeats, all French). STT garble: 3 caller turns. Recovery: ✓ via `available_cities`.
