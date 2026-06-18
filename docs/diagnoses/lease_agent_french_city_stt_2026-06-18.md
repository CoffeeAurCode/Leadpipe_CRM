# Diagnosis — Lease Agent French-Accent City Recognition (Phase 0)

> Date: 2026-06-18. Inputs: 3 real call transcripts (`docs/development_plans/transcript1..3.md`).
> Completes Phase 0 of `PLAN_lease_agent_french_accent_stt_city_recognition.md`.
> Method: read the raw transcripts (Deepgram output), recover the city the caller intended, then
> cross-check against the live code (`find_units` wiring, `city_matching`, prompt).

## TL;DR — honest read

Two separate things are true, and they are **not** the same as each other:

1. **Deepgram `multi` does garble Quebec French** — proven by the transcripts (corpus below). This is real
   and will hurt once portfolios are populated. It validates the plan's STT focus.
2. **But these three specific calls do NOT prove the city-recognition bug.** The dominant signal is that the
   agent **never once offered `available_cities`**, and in T3 a **cleanly-transcribed real city ("Saint-Lazare")
   still returned no match.** Given the code is wired correctly (verified below), the most parsimonious
   explanation is that **these test managers have no active listings** — so `find_units` returns empty and
   `available_cities` is empty regardless of how good or bad the transcription is.

So: the recordings are **confounded**. We cannot attribute these failures to French accent until we test
against a manager who actually has listings in the cities being named.

## What the transcripts show (Deepgram `multi` output)

| # | Manager | Caller intended (inferred) | Deepgram transcribed | Confidence |
|---|---|---|---|---|
| T2 | Sean Serre | **Vaudreuil-Dorion** | "Nathan **Vaudreuil d'Orient**" | High — near-perfect phonetic |
| T3 | Chantery | **Saint-Lazare** (1st attempt) | "je suis **Astin Lagar**" (agent echoed "Louis-P") | High — caller restates it cleanly next turn |
| T3 | Chantery | **Saint-Lazare** (2nd attempt) | "je suis à **Saint-Lazare**" (clean) | Certain — clean transcription |
| T2 | Sean Serre | Saint-* (unresolved) | "je suis de **Saint-Azal**" | Low — not a real municipality; candidate Saint-Lazare |
| T1 | (name blank→Sean Seri) | **unrecoverable** | "je suis en allant du **carré, cinq heures**" | None — clause is garbage, no city extractable |

Whole-clause garble (French → English-ish nonsense) also appears: T1 "Oh, sale as well?", "Hey, guys." The
city is frequently **buried inside a garbled run-on sentence**, not delivered as an isolated token.

## The decisive observation

`find_units` returns `available_cities` on **every** call, and it is empty **only** when the manager has zero
active listings (`leasing.py:173-179` builds it from the manager's active listings; `:245` returns it
populated even on a no-match). The tool is fully wired to the agent:

- `manager_id` is injected into the tool URL — `vapi_agent_config.py:1252-1253`.
- `available_cities` is in the tool's `variableExtractionPlan` schema — `:1347` — and named in the tool
  description — `:1298-1300`.
- The prompt tells Max to read `available_cities` on no-match — `:1069-1072`.

Across **all three** calls Max never named a single portfolio city; he only asked "which other city?"
(T1 `:31,39,47`; T2 `:23,40`; T3 `:19,32`). With the wiring correct, the cleanest explanation is that
`available_cities` was **empty** → the managers have **no active listings**. T3 corroborates: a *certain*,
clean "Saint-Lazare" produced no match — if any listing existed there, `city_matches("saint lazare",
"saint lazare")` is a trivial substring hit and would have matched.

## What the code rules OUT (checked, not assumed)

- ❌ "Tool schema doesn't expose `available_cities`" — it does (`:1347`). Already fixed in the prior plan.
- ❌ "`manager_id` not passed → wrong scope" — it is in the URL (`:1253`).
- ❌ "Matcher too weak for these cases" — for the recoverable cases the matcher would have **succeeded** if a
  listing existed: `"vaudreuil"` substring-hits `"Vaudreuil-Dorion"`; `"saint lazare"` exact-matches a stored
  `"Saint-Lazare"`. So matching is not the proximate failure here.

## What is CONFIRMED vs what is STILL OPEN

**Confirmed**
- Deepgram `multi` mis-transcribes Quebec French badly (corpus above) — the STT root cause in the plan is real.
- The no-match → `available_cities` path is wired correctly end-to-end; earlier-plan items are in place.

**Open (cannot be answered from transcripts alone)**
- Do managers **"Sean Serre"** and **"Chantery"** have any active listings, and in which cities? This single
  fact decides whether these three calls are STT failures or just empty-portfolio no-matches.
- Incidental: T1's first greeting renders the manager name as blank ("…leasing assistant **for.** Are you
  looking…", `transcript1.md:2`) before re-greeting as "Sean Seri". Separate first-message/name bug; not the
  city issue, but worth a follow-up.

## How to close the diagnosis (next concrete step)

1. **Query the two managers' active-listing cities** (service DB):
   `select manager_id, city, count(*) from lease_listings where is_active group by 1,2` for their `manager_id`s
   (resolve via `manager_profiles.name`). If empty → these calls are confounded and prove nothing about accent.
2. **Re-test** with French-accent calls against a manager who **has** listings in the named cities. Only those
   calls can isolate STT failures from empty-portfolio no-matches.
3. If, with a populated portfolio, a clean French city still misses → escalate to the STT fixes (A1 keyterm /
   B1 LLM canonicalization). The corpus above (`Vaudreuil-Dorion`→"Vaudreuil d'Orient", `Saint-Lazare`→"Astin
   Lagar") is the seed regression set for `tests/test_city_matching.py` once that path is confirmed.

## Impact on the plan

- **Phase 0 must add a portfolio check**, not just transcript mining — the transcripts proved that a portfolio
  check is the actual blocker to interpreting them.
- The STT fixes (A1/B1) remain correctly prioritized **for when portfolios are populated**, but they are **not
  validated as the cause of these three recordings**. Do not ship STT changes on the strength of these calls
  alone; confirm with step 1–2 first.
