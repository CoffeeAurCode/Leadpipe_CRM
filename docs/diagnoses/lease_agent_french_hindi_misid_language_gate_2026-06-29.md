# Lease Agent (Max) — Call Diagnosis: French transcribed as Hindi at the language gate

> **Date:** 2026-06-29
> **Agent:** Max — bilingual ENTRY/gate assistant (`build_lease_config` + `_LEASE_FRENCH_ROUTING_BLOCK`)
> **Manager:** `eb4b27dc…` (Shaun/"Sean" Cery — same portfolio as the 2026-06-22 diagnosis)
> **Source call:** partner test call, transcript pasted in session 2026-06-29
> **Partner's report:** "the agent doesn't understand me" — his French was transcribed as **Hindi Devanagari**.

## Verdict

This is a **different and more severe** failure than the prior French-STT diagnoses. Those were *phonetic
garble* (French → English-ish nonsense like "thing on low", "Captain mi") while the language was still
identified as Latin-script. **This is a full language-identification (LID) failure:** Deepgram nova-3 in
`language:"multi"` classified the partner's accented French as **Hindi** and emitted Devanagari
(`आप कहां से?`). The gate LLM never sees the word "French/français", so it cannot route, and the call
**loops on the gate question** and never reaches the (working) French-only handoff agent.

| Fact | Evidence |
|---|---|
| Call is on the **bilingual gate** agent, transcriber = `TRANSCRIBER_CONFIG` (`multi`) | Greeting is verbatim the gate line in `_LEASE_FRENCH_ROUTING_BLOCK` (`vapi_agent_config.py:1371-1377`); transcriber `language:"multi"` (`:289`) |
| nova-3 `multi` includes **Hindi** in its candidate set and does **no** explicit LID/routing | Deepgram: original `multi` code-switches across **English, Spanish, French, German, Hindi, Russian, Portuguese, Japanese, Italian, Dutch** — "without relying on explicit routing or language-specific mechanisms" |
| Mis-ID is **deterministic & repeatable** | Both partner turns produced the *identical* string `आप कहां से?` — the same short French utterance maps to the same Hindi hypothesis every time |
| The gate then **dead-loops** | Agent re-asked "English or French?" twice (the "Unclear answer → ask once more" branch, `:1385`) because it received non-English, non-French tokens both times |

---

## Root cause

The bilingual gate's only job is one binary decision — **English or French** — but to make it, the call must
run a transcriber that accepts *either* language before routing. nova-3's **only** code-switching option is
`language:"multi"`, and `multi` is a **fixed 10-language model with no way to restrict the candidate set**.
So at the gate we are asking nova-3 to pick the right language for a **short, accented French utterance**
("en français" / "je préfère le français") against a 10-way field that **includes Hindi** — and for native
Quebec-French phonetics it loses the vote to Hindi and emits Devanagari.

Three design facts turn that single mis-ID into a hard failure instead of a recoverable hiccup:

1. **The gate routes on the literal language.** `_LEASE_FRENCH_ROUTING_BLOCK` keys off the caller saying/
   answering in French. A Hindi/Devanagari token is neither a clear English word nor recognizable French, so
   the router falls into "Unclear → ask once more" and re-asks — forever, because the next French answer
   mis-IDs to Hindi again. **The clean fix path (handoff to the `language:"fr"` agent) is never reached.**
2. **The fallback transcriber has the same disease.** `fallbackPlan` is OpenAI `gpt-4o-transcribe` with
   "no language lock — auto-detects" (`:295-298`). Whisper-family models also auto-detect across *all*
   languages and are notorious for **language hallucination on short/accented audio** — and the fallback only
   triggers on Deepgram *failure*, not on a confident-but-wrong Hindi result.
3. **`confidenceThreshold:0.4` won't save it** (`:291`). Deepgram emitted a clean, grammatical Hindi sentence
   ("आप कहां से?" = "Where are you from?"), i.e. a *confident* hypothesis — it sails past a 0.4 floor.

> The irony: the dedicated **French-only** handoff agent uses `FRENCH_TRANSCRIBER_CONFIG` →
> `language:"fr"` (monolingual French, `:315-318`). It would transcribe the partner **perfectly**. The bug
> is entirely in the **`multi` gate that stands between the caller and that agent** — the caller can't get
> through the door to the room that works.

### Why you get understood but your partner doesn't

The decisive variable is **native-French-accented short utterances at the gate**.

- You almost certainly answer the gate **in English** (or test in English) — nova-3 `multi` handles English
  natively and never mis-IDs it. You sail through.
- Even if you speak French, a non-native accent tends to land closer to the model's English/French acoustic
  space; the partner is a **native** speaker whose phonetics + a 1–3 word answer give the LID its weakest
  possible signal, and Hindi wins.
- It only has to misfire **once, on the gate turn**, to brick the whole call.

---

## Fixes (ranked)

| Pri | Fix | Where / why |
|---|---|---|
| **P0 — deploy today, prompt only** | **Treat "not clearly English" as French at the gate.** French is the *only* non-English route, so any gate answer that is **not a clear English word** — non-Latin script (Devanagari/CJK), unintelligible garble, or actual French — should route to the **French handoff**, not loop. A Hindi transcription is itself proof the caller is *not* answering in English. Rewrite the routing rules in `_LEASE_FRENCH_ROUTING_BLOCK` (`vapi_agent_config.py:1380-1388`): *ENGLISH only on an explicit, clearly-English answer; everything else (including unreadable/non-Latin output) → hand off to French.* Converts the fatal loop into a correct route. Re-push with `update_lease_agents.py`. | Breaks the loop with zero infra change; the French agent (`language:"fr"`) then transcribes him cleanly. |
| **P1 — reduce LID exposure** | nova-3 `multi`'s candidate set **cannot** be narrowed, so lower the surface area instead: (a) add Deepgram **keyterm prompting** to the gate transcriber seeded with the gate's expected tokens (`français, French, anglais, English, oui, non, yes, no`) to bias recognition toward the real choices; (b) evaluate a transcriber that lets you **restrict languages to en+fr** for the gate (AssemblyAI / Gladia multilingual) — if either supports a 2-language constraint, the Hindi hypothesis disappears at the source. | Treats the cause, not the symptom; needs a test call to validate WER/latency before swapping. |
| **P2 — make the gate shorter-lived** | Consider routing on **first French sound** rather than requiring a parse: any non-English reply → immediately offer the French handoff once, then default to French. Minimizes how long the caller is exposed to the `multi` gate. | Defense-in-depth on top of P0. |

> **Do NOT** rely on raising `confidenceThreshold` — the mis-ID is high-confidence and won't be dropped.
> **Do NOT** expect the OpenAI fallback to help — it auto-detects the same 100+ languages and only fires on
> Deepgram failure, not on a confident wrong answer.

> **Deploy gotcha (unchanged from prior sessions):** none of this goes live until the per-manager assistants
> are re-pushed — `backend\.venv\Scripts\python.exe backend\scripts\update_lease_agents.py` (needs
> `supabase`+`httpx`, **not** the `vapi` SDK).

---

## Relationship to prior diagnoses

- `docs/diagnoses/lease_agent_french_city_stt_2026-06-18.md` and
  `docs/diagnoses/lease_agent_pausing_and_french_stt_2026-06-22.md` cover **`multi` phonetic garble of
  French city names** (English-ish nonsense) and the `available_cities` recovery path. Those are about
  *word accuracy within French*.
- **This diagnosis is about `multi` choosing the wrong *language* entirely (Hindi), at the *gate* turn** —
  a failure that the `available_cities` matcher cannot rescue because the call never gets past routing.
  Same offending config line (`:289`), different and more fatal symptom.

## Sources

- Deepgram — "Deepgram Expands Nova-3 with 10 New Languages and Multilingual Keyterm Prompting": https://deepgram.com/learn/deepgram-expands-nova-3-with-10-new-languages-and-multilingual-keyterm-prompting
- Deepgram Docs — "Multilingual Codeswitching": https://developers.deepgram.com/docs/multilingual-code-switching
- Deepgram Docs — "Models & Languages Overview": https://developers.deepgram.com/docs/models-languages-overview
