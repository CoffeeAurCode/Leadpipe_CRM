# PLAN — Lease Agent: Fuzzy-Band Entity Confirmation ("did you mean X or Y?")

> **Date:** 2026-06-22 · **Agent:** Max (lease) · **Status:** Phase 1 (City) implemented 2026-06-22 —
> `rank_candidates` + hybrid phonetic/string `similarity` in `city_matching.py`, `disambiguation` block
> in `find_units`, Step 2 prompt + tool schema, garble-corpus script, unit tests. Phases 2 (building) /
> 3 (street) and Phase-0 threshold fitting still open.
> **Slots into:** `PLAN_lease_agent_french_accent_stt_city_recognition.md` — this is the detailed
> design for **B2 (confirm-the-entity turn)**, generalized from *city only* to *any identifying field*,
> with the explicit ambiguity-gating rule. Depends on **C1 (phonetic scoring)** from that plan.

## The idea (restated)

When a caller says something to pick out which unit they mean — a **city**, **building/property name**,
or **street** — don't blindly accept the top fuzzy match, and don't reflexively confirm everything either.
Score what they said against the manager's **real listing values**, and:

- **One clear winner** → don't ask; just proceed (say it back as you continue — *implicit* confirm).
- **Two or more values are close enough to be genuinely confusable** → ask the caller to choose
  **between only those** ("Did you mean **Saint-Lazare** or **Saint-Lazaire**?").
- **Nothing close** → fall through to the existing `available_cities` offer (the no-match path).

Caller says "Saint-Lazar"; portfolio has *Saint-Lazare* and *Saint-Lazaire* → confirm between those two.
Never drag *Châteauguay* into the question — it sounds nothing alike, so it's not in the confusable band.

This is a **confidence-banded, ambiguity-triggered, inventory-scoped** disambiguation. It is the missing
middle tier between "auto-accept the top match" and "dump the whole city list."

## Why this is worth doing (and where it sits)

Today there are only two outcomes (`leasing.py:152-249` + prompt Step 2 at `~1061-1075`):
1. `find_units` returns matches → agent proceeds on whatever matched.
2. No match → agent reads **all** `available_cities`.

There's no notion of "I matched, but two candidates are about equally likely." That gap is exactly where
STT garble causes silent **false accepts** (proceeds on the wrong city) or unhelpful **full-list dumps**.
This plan adds the third outcome — *bounded disambiguation* — without changing the safety net.

Pipeline layering (so this doesn't collide with the other fixes):
```
A1 Deepgram keyterm  →  [transcript]  →  THIS banded disambiguation (deterministic, backend)
                                              │ inconclusive (below band floor)
                                              ▼
                                       B1 LLM canonicalization (context-aware fallback)
                                              │ still nothing close
                                              ▼
                                       available_cities offer (existing no-match path)
```

---

## Core algorithm

Extend `city_matching.py` with a candidate-ranking function (field-agnostic), used by `find_units`.

```
rank_candidates(spoken_token, candidate_values) -> RankResult
  # candidate_values = the manager's DISTINCT, NORMALIZED values for ONE field
  # (e.g. all distinct active-listing cities)

  for c in candidate_values:
      score[c] = similarity(spoken_token, c)        # see "Similarity" below — NOT plain difflib
  sort desc by score
  top, second = score[0], score[1] (if any)

  decision:
    AUTO_ACCEPT   if top >= T_HIGH and (top - second) >= MARGIN      # clear winner
    CONFIRM       if top >= T_CONFIRM and (no clear winner)          # ambiguous band
                     → candidates = all c with score >= (top - BAND), capped at N_MAX
    NO_MATCH      if top < T_FLOOR                                   # nothing close → existing offer
```

Three zones, two gaps that matter:
- **`MARGIN`** (gap between #1 and #2) is what distinguishes "confident" from "ambiguous." A high top score
  with a *close* runner-up is the confirm case; a high top score with a *distant* runner-up is auto-accept.
- **`BAND`** defines who joins the confirmation question — only values within `BAND` of the top. This is the
  rule that keeps *Châteauguay* out: it's not within `BAND` of "Saint-Lazar," so it's excluded.

Starting thresholds (tune against the corpus, see Validation): `T_HIGH 0.86`, `MARGIN 0.08`,
`T_CONFIRM 0.66`, `BAND 0.06`, `T_FLOOR 0.55`, `N_MAX 3`.

---

## The make-or-break decision: similarity must be PHONETIC, not string

This is the single most important detail and the easiest way to build the wrong thing.

The caller's complaint is "**similar sounding**." But `difflib.SequenceMatcher` (current matcher,
`city_matching.py:38`) is a **character** ratio. It works for "Saint-Lazar"↔"Saint-Lazare" (string-close),
but the real STT garble is *phonetically* close while *string*-far:

| Spoken / garbled | Real city | difflib ratio | Phonetically close? |
|---|---|---|---|
| "Saint-L'Asor" | Saint-Lazare | ~0.55 (apostrophe + transposition) | **yes** |
| "Saint-Lavaure" | Saint-Lazare | ~0.67 | **yes** |
| "Saint Lazole" | Saint-Lazare | ~0.78 | yes |
| "thing on low" | Saint-Lazare | ~0.10 | **no** (unrecoverable) |

A pure-difflib version **misses exactly the cases you care about**.

**Reframe that drives the encoder choice:** the input is **not clean French** — it's Deepgram's *English-ish
rendering of French-accented audio* ("Saint-L'Asor", "Captain mi" for *quatre et demi*). So this is a
**cross-orthography** match (pseudo-English garble ↔ canonical French name), not a French-spelling match. A
French-*only* encoder applied to an English-spelled token can underperform. Don't bet the design on one encoder.

**Resolved default (ship this) — a hybrid score with a pluggable phonetic backend:**
```
similarity(spoken, candidate) = max(
    rapidfuzz_ratio(norm_spoken, norm_candidate),   # edit-distance garble: "Saint Lazole"→"Saint Lazare"
    phonetic_match(spoken, candidate),              # sound-alike/spelled-different: "Saint-L'Asor"
    difflib_ratio(norm_spoken, norm_candidate),     # existing cheap baseline, kept
)
```
Phonetic backend ranking (decided, revisit only on the corpus):
1. **Double Metaphone (`jellyfish`)** — ship this. English-rule but operates on *sound* (the right axis vs
   pseudo-English garble), fast, gives two codes. Almost certainly enough at a handful of candidates.
2. **Beider-Morse, French ruleset (`abydos`)** — most French-aware, but heavier/slower. Reach for it **only** if
   large-manager precision (many near-homophones) shows Double Metaphone false-accepting. Don't pay up front.
3. **French Soundex variant** (Brouard "Phonex"-style) — built for *clean* French, so it's the contender for the
   **post-A1 regime** (when transcripts are actually French-spelled), not the garble regime.

This feature *requires* the existing plan's **C1** (phonetic scoring in `city_matching.py`) — do C1 first or together.
Keep `normalize_place` (`city_matching.py:12`) as the pre-step (strips diacritics/hyphens, St→Saint); all three
scorers run on its output (correct, since the garble carries no accents anyway).

**The encoder barely matters at small scale** — with ~5 candidates almost anything separates them. It only earns
its keep at scale, so don't block Phase 1 on the perfect encoder; ship the hybrid and let the corpus (below)
decide whether Beider-Morse is worth its weight, by **false-accept rate at fixed recall** (the guarded metric).

**Boundary to state honestly:** banded confirmation only rescues **mild** garble (still phonetically near a
real value). Severe garble ("thing on low") correctly scores below `T_FLOOR` and falls to the
`available_cities` offer. This is a complement to A1/B1, not a replacement.

---

## Where it runs: backend-deterministic, model just speaks it

Two options; recommend the first.

- **(Recommended) Backend computes the band; the model only voices it.** `find_units` returns a new
  `disambiguation` block alongside `units`/`available_cities`:
  ```json
  { "needs_confirmation": true, "field": "city", "spoken": "Saint-Lazar",
    "candidates": [
      { "value": "Saint-Lazare",  "rent_low": 1400, "rent_high": 1400 },
      { "value": "Saint-Lazaire", "rent_low": 1600, "rent_high": 1600 }
    ] }
  ```
  Each candidate carries its **rent** (range, if the city spans multiple listings) so the prompt can build the
  homophone disambiguator by rent; ordinal ("first/second") is free from array position.
  The prompt's Step 2 reads it and asks. **Pros:** deterministic, unit-testable, tunable thresholds, reused by
  both agents; matches the existing "tool returns `available_cities`, prompt reads it" pattern.
  **Cons:** model still phrases the question + routes the answer back (retry `find_units` with the pick).
- **(Fallback only) LLM decides ambiguity (= B1).** Give the model the candidate list and let it judge.
  **Pro:** no threshold tuning, uses context. **Con:** non-deterministic, can't *guarantee* it confirms when
  it should, hard to test. Use as the layer **below** the deterministic band, not instead of it.

Because the cost of errors is **asymmetric** — a false *accept* (proceed on the wrong city) burns the whole
call and captures a junk lead, while a false *confirm* costs one turn — lean the thresholds toward confirming
in the gray zone, balanced against turn-count fatigue (below).

---

## Two confirmation shapes (and the homophone trap)

The candidate set is usually small. Handle both sizes:

1. **Single candidate in band** (the common case — garble-vs-one-real-city): *implicit* or yes/no confirm.
   - Prefer **implicit**: say it back while moving on — "Got it, **Saint-Lazare** — what size?" If wrong, the
     caller corrects naturally ("no, Saint-Lazaire"). Lower friction than asking. (See "different
     perspectives.")
   - Use explicit yes/no only when the single match is weak (`T_CONFIRM ≤ score < T_HIGH`).
2. **≥2 candidates in band** (your example — two real near-homophones): explicit choice between them.

**The homophone trap (important):** if two candidates are so alike that the caller can't tell them apart when
the agent *speaks* them — and the STT will garble the caller's spoken answer the same way — then confirming
**by name resolves nothing**.

**Resolved principle:** the disambiguator must be answerable in a modality the STT handles **well** — a
**number, a yes/no, or an ordinal** — and **never another proper noun.** Street and neighborhood *names*
re-trigger the exact failure (the caller who can't say "Saint-Lazare" can't say "Rue du Comtois" either, and
Deepgram garbles it identically), so the textbook "disambiguate by street/neighborhood" is **wrong for this
system**. Ranked by reliability × data-on-hand × caller salience:

1. **Rent (primary).** Numeric, and `numerals:True` is already set (`vapi_agent_config.py:290`) so digits
   transcribe cleanly; highest salience to a tenant; present in every listing. Only works if the candidates'
   rents differ — else fall through.
   > "One's around **fourteen hundred**, the other's **sixteen** — which sounds right?"
2. **Ordinal pick (universal fallback mechanism).** Sidesteps proper nouns *and* content-numbers — the caller
   picks a position. Pair with the agent enumerating the two options slowly.
   > "The **first** one I mentioned, or the **second**?"
3. **Size (3½/4½) — weak.** OK as an agent-offered binary, but the caller's own "quatre et demi" garbled to
   "Captain mi" in the transcript, so don't rely on the caller producing it.

**Reject** street name, neighborhood, building name as disambiguators (all proper nouns; neighborhood data
isn't even in the CSV). The backend surfaces each candidate's **rent** in the `disambiguation` block; the
**ordinal** is free from list position.

---

## Field-awareness & scope (don't fuzzy-confirm "everything" at once)

The fields differ sharply in cardinality and collision risk — phase them:

| Field | Cardinality | Collision risk | Phase |
|---|---|---|---|
| **City** | low (handful/manager) | clean, high value | **1** (data already in `available_cities`) |
| **Building / property name** | medium | distinctive but can *contain* a city token (e.g. "carré Saint-**Laurent**") → cross-field collision | **2** |
| **Street address** | high; has civic numbers ("2803"), Rue/Bd/Av; callers rarely say it fully | noisiest | **3 (optional)** |

Rules that follow:
- Score against **field-scoped** candidate sets (cities vs buildings vs streets), and make the confirmation
  **field-aware** ("which **city**" vs "which **building**"). `find_units` already separates these fields
  (`leasing.py:208-217`), so the candidate sets are available.
- **Cap the spoken list at `N_MAX` (2–3).** If more than `N_MAX` land in the band (more likely for big
  portfolios), **don't** read a long list — ask a *narrowing* question instead (size / budget / neighborhood).
- **Data-quality prerequisite:** scoring is only as good as the candidate values. The CSV already shows
  `state` "QC" vs "Quebec," a row with no `city`, and building-vs-street mismatch ("carré Saint-Laurent" vs
  "Rue Du Comtois"). Normalize the distinct candidate set before scoring (ties to the data-hygiene items in
  `docs/diagnoses/lease_agent_pausing_and_french_stt_2026-06-22.md`).

---

## Different perspectives (the user explicitly asked — pressure-testing the idea)

1. **Implicit > explicit confirmation (UX).** The lowest-friction version often isn't a question at all —
   state the resolved value while proceeding and let the caller correct. Reserve the explicit "X or Y?" turn
   for true ≥2-candidate ambiguity. This directly fights the *"agent pauses / asks too much / one moment"*
   problem from the call diagnosis: every avoidable confirm turn = another `find_units` = another stall phrase.
2. **Error asymmetry.** False-accept ≫ false-confirm in cost. Tune toward confirming in the gray zone — but
   bound it so the *confirm rate per call* stays low (target: most calls auto-accept).
3. **Collisions are usually garble-vs-real, not real-vs-real.** A manager rarely has two genuinely
   near-homophone cities, so the dominant path is single-candidate (implicit) confirm; the "pick between two"
   path is the rarer (but real) case in your example. Design for both; expect the single-candidate path to
   dominate.
4. **This is record-linkage / "did-you-mean," not novel.** Borrow the standard recipe: normalize (blocking) →
   hybrid phonetic+string score → threshold **with a margin** → human-in-the-loop for the gray zone. That
   framing justifies the deterministic-backend approach and the precision/recall eval.
5. **Scale cuts both ways.** For a 200-unit manager banding is *more* valuable (more near-collisions) but the
   list can't be read aloud → the `N_MAX` cap + narrow-by-attribute fallback is what makes it scale (consistent
   with the large-manager analysis).
6. **Do we even need it if A1 lands?** If keyterm prompting fixes the transcript at source, fewer tokens reach
   the band. But A1 *increases* confident wrong outputs among similar keyterms (it boosts *all* of them), so a
   confirm-on-ambiguity backstop is the natural complement to A1, not a redundancy.

---

## Implementation sketch

| File | Change |
|---|---|
| `backend/app/services/city_matching.py` | Add `rank_candidates(spoken, candidates, field) -> RankResult` with the three-zone decision; add hybrid `similarity() = max(rapidfuzz, Double-Metaphone (`jellyfish`), difflib)` with a **swappable** phonetic backend (this is **C1**). Keep `normalize_place`/`city_matches` intact. New deps: `rapidfuzz`, `jellyfish` (and `abydos` only if Beider-Morse wins the bake-off). |
| `backend/app/routes/leasing.py` (`find_units`) | After computing matches, run `rank_candidates` over the distinct candidate sets; return a `disambiguation` block (`needs_confirmation`, `field`, `spoken`, `candidates[]` with `value` + `rent_low`/`rent_high`). Safety net unchanged. |
| `backend/scripts/generate_stt_garble_corpus.py` | **New** — French-accent TTS → Deepgram round-trip over each manager's real city/building values to manufacture labeled `garble→truth` pairs at volume; feeds threshold fitting + the encoder bake-off. |
| `backend/app/services/vapi_agent_config.py` (Step 1/2, `~1055-1075`) | Teach Max: on `needs_confirmation`, ask the bounded question (implicit for 1 weak candidate, explicit choice for ≥2; narrow-by-attribute on homophones); on the caller's pick, retry `find_units`; only offer `available_cities` when `needs_confirmation` is false **and** no match. Keep language-locked phrasing. |
| `tests/test_city_matching.py` | Add the garble corpus as labeled cases: must-AUTO_ACCEPT, must-CONFIRM (with expected candidate set), must-NO_MATCH; regression guard that distinct cities (Laval≠Longueuil, Saint-Lazare vs Châteauguay) never co-occur in a band. |
| `CODEBASE_CONTEXT.md` | `find_units` row: note `disambiguation` block. Lease behaviour: note banded confirm turn. |

Deploy: prompt/tool changes go live only after `python backend/scripts/update_lease_agents.py`
(backend venv: `backend\.venv\Scripts\python.exe`).

---

## Phased rollout

- **Phase 0 — corpus, encoder bake-off & thresholds.** Seed the labeled garble set from the transcripts (this diagnosis + `lease_agent_french_city_stt_2026-06-18.md`), then **expand it cheaply** via `generate_stt_garble_corpus.py` (French-accent TTS → Deepgram round-trip on real city/building names — dozens of realistic pairs per value). Bake off the phonetic backends (Double Metaphone → ship; Beider-Morse FR → only if it beats it) by **false-accept rate at fixed recall**. Then fit `T_HIGH/MARGIN/T_CONFIRM/BAND/T_FLOOR` to maximize correct AUTO_ACCEPT and correct CONFIRM while keeping false-accepts ~0.
- **Phase 1 — City** (highest value, data already present). Backend band + Step 2 prompt (implicit-first). Ship behind the existing no-match safety net.
- **Phase 2 — Building / property name.** Field-scoped candidates; handle city-token cross-collision.
- **Phase 3 (optional) — Street.** Only if Phase 1–2 prove out; expect noise from civic numbers.

## Validation

- **Unit:** the labeled corpus above; precision/recall on the three decisions; false-accept rate is the
  guarded metric (must stay ~0). Distinct-city non-collision regression.
- **Live:** French-accent calls naming (a) a clean portfolio city, (b) a near-homophone pair if the manager
  has one, (c) a not-in-portfolio city. Confirm: clear case auto-accepts (no extra turn), ambiguous case asks
  **only** the close candidates, junk falls to `available_cities`. Track **confirm-rate per call** (UX guard).
  Log in `docs/testing/`.

## Resolved decisions

1. **Phonetic encoder — DECIDED.** Ship a hybrid `max(rapidfuzz, Double Metaphone, difflib)` with a swappable
   phonetic backend. Default phonetic = **Double Metaphone (`jellyfish`)** — sound-based, which is the right axis
   against pseudo-English garble, and plenty at small candidate counts. Promote to **Beider-Morse French
   (`abydos`)** only if the Phase-0 bake-off shows Double Metaphone false-accepting at scale; hold a **French
   Soundex** variant for the post-A1 (clean-French) regime. The encoder barely matters at ~5 candidates, so it
   doesn't gate Phase 1; the **TTS→Deepgram corpus** + false-accept-at-fixed-recall picks the winner empirically.
2. **Homophone disambiguator — DECIDED.** Disambiguate by **rent first** (numeric, `numerals:True` already on,
   high salience, in every listing), with **ordinal pick ("first or second?")** as the universal fallback
   mechanism. **Never** use street/neighborhood/building *names* — they re-trigger the same proper-noun STT
   failure. Backend surfaces each candidate's rent in the `disambiguation` block.

## Open questions

1. Should thresholds be **per-field** (city vs street likely need different bands) or global? Lean per-field;
   confirm in Phase 0.
