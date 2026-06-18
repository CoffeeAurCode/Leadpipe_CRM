# Plan — Lease Agent: French-Accent City Recognition (STT-Layer Root Cause)

> Date: 2026-06-18. Owner: lease agent (Max) — `vapi_agent_config.py` (transcriber + prompt),
> `routes/leasing.py` (`find_units` / `search_listings`), `services/city_matching.py`.
> **Supersedes the scope of** `PLAN_voice_agent_city_recognition.md` (which fixed the *backend matching*
> layer — already shipped and verified). This plan addresses why the bug **still persists** after that fix.

---

## 1. Problem

The lease voice agent still cannot reliably recognize Quebec city names spoken with a **French accent**
(e.g. *Trois-Rivières*, *Saint-Léonard*, *Longueuil*, *Montréal*), even when the landlord has active
listings in those cities. The caller names a city → Max says he can't find anything there.

## 2. Why the previous fix did not solve it

The earlier plan made the **backend matching** accent-/spelling-/fuzzy-tolerant:
`city_matching.py` (`normalize_place` strips diacritics + St/Ste, `city_matches` does substring + alias +
`difflib` ratio ≥ 0.82) and `find_units` returns `available_cities`. That logic is correct and live
(`leasing.py:152-249`, `vapi_agent_config.py:1060-1074`). Its unit tests pass.

But matching only ever sees the **transcript text**, never the audio. The failure is **upstream**:

```
Caller (FR accent)
  │  speaks "Trois-Rivières"
  ▼
[Telephony 8 kHz μ-law]  ──►  [Deepgram nova-3, language:"multi", confidenceThreshold 0.4]
                                        │  emits e.g. "twa reviewer" / "trois reviere" / "war riviera"
                                        ▼
                              transcript token  ──►  find_units → city_matching (difflib 0.82)
                                                                      │  "twa reviewer" vs "trois rivieres"
                                                                      ▼  ratio ≈ 0.5  →  NO MATCH
                                                                  LLM (gpt-5.2)  →  "I can't find that city"
```

**Root cause: the speech-to-text step mis-transcribes the accented proper noun so badly that no
downstream string match can recover it.** Garbage in, garbage out. `difflib` at 0.82 is *correctly*
rejecting "twa reviewer" — it genuinely isn't "trois rivieres" as a string. The fix has to either
(a) make the transcript correct, or (b) put a component smart enough to bridge the phonetic gap between
the matcher and the audio. Tuning the 0.82 threshold alone can't win: lower it and *Laval* starts
matching *Longueuil*.

### Diagnostic prerequisite (do this first — it decides everything)

We are currently guessing *how* cities get mangled. `call_logs.transcript` already stores every raw
call transcript. Before building anything, **mine the transcripts** of recent French calls where a city
was named:

- Pull `call_logs` rows, grep transcripts for turns around the location question.
- Tabulate: caller's real city (from the matched/expected listing) → what Deepgram actually emitted.
- This tells us whether failures are (i) total garbage (→ must fix STT) or (ii) near-misses just past
  0.82 (→ cheap backend/LLM fix), and gives us a **real regression corpus** for testing.

> One-off analysis script → `backend/scripts/` (e.g. `analyze_city_mistranscriptions.py`); findings →
> `docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md`.

---

## 3. Solution catalogue (all options, by pipeline layer)

### Layer A — Speech-to-Text (Deepgram) — fix the transcript at the source

| # | Solution | How |
|---|---|---|
| A1 | **Keyterm prompting with the manager's real cities** | nova-3 now supports **multilingual keyterm prompting** (Deepgram Nov-2025 update; up to ~500 tokens) and Vapi exposes a `keyterm` array on the Deepgram transcriber. Inject this manager's distinct active-listing cities **with proper accents + known variants** (`["Montréal","Trois-Rivières","Saint-Léonard","Québec",…]`) so Deepgram biases toward them. Works **without leaving `language:"multi"`**. |
| A2 | **Switch model to `nova-2-phonecall`** | Telephony-tuned on 8 kHz carrier audio (where accented proper nouns degrade most). Loses nova-3 quality + nova-3-only keyterm; nova-2 uses the older single-word `keywords:boost` param and multi is EN↔ES only. Weak fit for FR. |
| A3 | **Promote a multilingual-strong STT** | Make OpenAI `gpt-4o-transcribe` (Whisper-class, strong on accented French proper nouns) the **primary**, Deepgram the fallback — or add Gladia (multilingual focus). Buys accuracy, costs latency. |
| A4 | **Tune `confidenceThreshold`** | Currently 0.4. Lower → more noise tokens through; higher → accented words dropped entirely. Marginal, no upside for this bug. |

### Layer B — The LLM as a phonetic normalizer (cheapest leverage)

| # | Solution | How |
|---|---|---|
| B1 | **Give Max the portfolio city list up front, let him canonicalize before calling the tool** | gpt-5.2 is bilingual and knows Quebec geography — it can map a mangled "twa reviewer" to the real **Trois-Rivières** far better than `difflib`. Surface the manager's `available_cities` to the model (system-prompt context block at provision time, and/or a cheap `get_cities` tool / first `find_units` call) and instruct: *resolve the spoken city to the closest city on THIS list before searching; if none is close, ask.* |
| B2 | **Explicit "confirm the city" turn** | Max repeats the city he heard and asks the caller to confirm or spell it, then matches. +1 turn, big reliability gain, zero infra. |
| B3 | **Send candidate spellings to the tool** | Prompt Max to pass 2-3 alternative spellings; backend tries each through `city_matches`. Marginal over B1. |

### Layer C — Backend matching robustness (already strong; incremental)

| # | Solution | How |
|---|---|---|
| C1 | **Add phonetic matching** (Double-Metaphone / `jellyfish` / `rapidfuzz`) alongside `difflib` | Bridges phonetic near-misses ("longuil"→"Longueuil") more reliably than raw ratio. Small new dep; keep `difflib` fallback. |
| C2 | **Data-driven alias map** | Expand `_CITY_ALIASES` with real mistranscriptions harvested in §2 (`"twa reviewer"→"trois rivieres"`). Low effort, but reactive and needs upkeep. |
| C3 | **Lower / tune the 0.82 threshold** | Tuning only; raises false-positive risk between nearby cities. Do **only** with the §2 corpus as guardrail. |

### Layer D — Process / validation (supporting)

| # | Solution | How |
|---|---|---|
| D1 | **Transcript mining** (the §2 diagnostic) | Quantify real failure modes; produce the regression corpus. |
| D2 | **Regression test** | Extend `tests/test_city_matching.py` with the real mistranscriptions; add a live-call checklist in `docs/testing/`. |

---

## 4. Ranked recommendation

Ranking weighs **impact on the actual bug × low effort × low risk**, given the backend matcher is
already strong and the residual failures are STT-side.

| Rank | Solution | Impact | Effort | Risk | Why this rank |
|---|---|---|---|---|---|
| **1** | **B1 — LLM canonicalizes against the portfolio city list** | High | Low | Low | Highest leverage. The bilingual model bridges the phonetic gap `difflib` can't, with no infra, no latency, no model change. Directly attacks "garbage→can't recover." |
| **2** | **A1 — Deepgram multilingual keyterm prompting (manager's cities)** | High | Med | Low–Med | Fixes the transcript at the source so *every* downstream layer benefits. Now unblocked (multi-mode keyterm). Main cost: keyterms are baked per-assistant and go **stale** when a manager adds a city → needs a refresh hook. |
| **3** | **D1 — Transcript mining / diagnosis** | (enabler) | Low | None | Cheap, do **first**; grounds the threshold/alias choices and yields the test corpus. Not a fix itself but de-risks all others. |
| **4** | **B2 — Confirm-the-city turn** | Med | Low | Low | Reliability backstop for the genuinely ambiguous cases; pairs naturally with B1. |
| **5** | **C1 — Phonetic matching in backend** | Med | Med | Low | Solid incremental robustness; helps near-misses that survive B1/A1. Small dependency. |
| **6** | **C2 — Data-driven alias expansion** | Med | Low | Low | Quick wins from the §2 corpus; ongoing maintenance. |
| **7** | **A3 — Whisper-class STT primary** | Med–High | Med | Med | Real accuracy gain on FR proper nouns but adds latency/cost; hold as escalation if A1+B1 underperform. |
| **8** | **C3 — Threshold tuning** | Low | Low | Med | Only alongside the corpus; easy to regress nearby-city matches. |
| **9** | **A2 — nova-2-phonecall** | Low | Med | Med | Loses nova-3 + multilingual keyterm; nova-2 multi is EN↔ES. Poor fit. |
| **10** | **A4 — confidenceThreshold tweak** | Low | Low | Med | No real upside for this bug. |

**Recommended path = D1 → B1 + A1 → B2 → (C1/C2 as needed).** B1 and A1 are complementary, not
either/or: A1 makes the transcript right more often; B1 recovers the cases A1 still misses. Doing both
covers the pipeline end-to-end.

---

## 5. Implementation outline (recommended path)

### Phase 0 — Diagnose (D1) — DONE (`docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md`)
- ✅ Mined 3 real transcripts → confirmed Deepgram `multi` garbles Quebec French (corpus:
  `Vaudreuil-Dorion`→"Vaudreuil d'Orient", `Saint-Lazare`→"Astin Lagar").
- ⚠️ **Confounder found:** the agent never offered `available_cities` and a *clean* "Saint-Lazare" still
  returned no match → the test managers most likely have **no active listings**, so those calls don't prove
  the accent bug. **Add a portfolio check before any STT work:**
  `select city, count(*) from lease_listings where is_active and manager_id = ... group by city` for the
  managers under test; re-test against a manager who actually has listings in the named cities.
- (Optional) `backend/scripts/analyze_city_mistranscriptions.py` to scale this over all `call_logs` later.

### Phase 1 — LLM canonicalization (B1) + confirm turn (B2)
- `vapi_agent_config.py`: in `build_lease_config`, add the manager's distinct active-listing cities to the
  system-prompt **context block** at provision time, and rewrite **Step 1/Step 2** (`~1055-1074`) so Max:
  resolves the spoken city to the nearest city on that list *before* calling `find_units`; briefly confirms
  it back to the caller; only falls to the `available_cities` offer when nothing is close.
- Keep `find_units` unchanged as the safety net.

### Phase 2 — Deepgram keyterm biasing (A1)
- `vapi_agent_config.py`: parameterize `TRANSCRIBER_CONFIG` so `build_lease_config(backend_url, manager_id, …)`
  builds a per-manager transcriber with `"keyterm": [<this manager's cities + accented variants>]`
  (nova-3, `language:"multi"` retained). Add a small variant expander (canonical + diacritic + St/Saint forms).
- **Staleness hook:** keyterms are baked into the assistant at provision/update time. Re-push the transcriber
  when a manager's listing cities change — either call the push on listing create/delete, or rely on a periodic
  `update_lease_agents.py` run. Document the chosen trigger.

### Phase 3 — Backend hardening (C1/C2, optional, corpus-driven)
- Add `rapidfuzz`/phonetic scoring in `city_matching.py` behind the existing `city_matches` signature;
  seed `_CITY_ALIASES` from the Phase 0 corpus.

### Phase 4 — Deploy + verify
- **Prompt/tool/transcriber edits do not go live until pushed:** `python backend/scripts/update_lease_agents.py`
  (per-manager assistants) and `update_shared_agents.py` if the shared lease agent is still used.
- Live FR-accent test calls per §6.

---

## 6. Test plan

- **Unit** — extend `tests/test_city_matching.py` with the Phase-0 real mistranscriptions (must-match) and
  preserve the distinct-city non-matches (Laval≠Longueuil) as regression guards.
- **Live** — French-accent calls naming each portfolio city (and a not-in-portfolio city); confirm Max
  matches and continues to size, confirms the city back, and on true no-match offers only real
  `available_cities`. Log results in `docs/testing/`.

---

## 7. Files touched

| File | Change |
|---|---|
| `backend/scripts/analyze_city_mistranscriptions.py` | **New** — Phase 0 transcript-mining diagnostic |
| `docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md` | **New** — findings + real mistranscription corpus |
| `backend/app/services/vapi_agent_config.py` | Per-manager `keyterm` transcriber (A1); Step 1/2 prompt for LLM canonicalization + confirm (B1/B2); city context block |
| `backend/app/services/city_matching.py` | (Optional C1/C2) phonetic scoring + corpus-seeded aliases |
| `tests/test_city_matching.py` | Add real-mistranscription regression cases |
| `backend/scripts/update_lease_agents.py` | (run, + add transcriber re-push on city change) push config to live assistants |

## 8. Out of scope
- No hardcoded city list as the matching *authority* — the per-manager `available_cities`/listing cities
  remain the source of truth (keyterms and prompt context derive from them).
- No DB schema change — cities already live on `lease_listings.city`.

## 9. Open decisions
1. **A1 staleness trigger** — re-push keyterms on listing create/delete (precise, more wiring) vs periodic
   `update_lease_agents.py` (simple, lag). Pick after Phase 0 shows how often cities change.
2. **Do B1 alone first, or B1+A1 together?** If Phase 0 shows mostly near-misses, B1 may suffice and A1 can
   wait; if it shows total garbage, A1 is mandatory.
3. **C1 dependency** — accept `rapidfuzz`/`jellyfish`, or stay stdlib-only with `difflib` + alias map.

## 10. CODEBASE_CONTEXT.md updates on completion
- `/leasing/find-units` row: note LLM pre-canonicalization against portfolio cities.
- Transcriber section: note per-manager Deepgram `keyterm` biasing on the lease agent and its refresh trigger.
- Lease agent behaviour section: note Step 1/2 city-confirm turn.

## Sources (keyterm capability verification)
- [Deepgram — Nova-3 multilingual keyterm prompting](https://deepgram.com/learn/deepgram-expands-nova-3-with-10-new-languages-and-multilingual-keyterm-prompting)
- [Deepgram Docs — Keyterm Prompting](https://developers.deepgram.com/docs/keyterm)
- [Vapi — Deepgram Keywords and Keyterm Prompting](https://docs.vapi.ai/customization/custom-keywords)
- [Vapi — Multilingual support](https://docs.vapi.ai/customization/multilingual)
