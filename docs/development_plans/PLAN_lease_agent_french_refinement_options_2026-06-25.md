# Plan — Refining the Lease Agent's French Understanding (Options + Pros/Cons)

> **Date:** 2026-06-25
> **Agent:** Max — lease voice agent (`build_lease_config` in `backend/app/services/vapi_agent_config.py`)
> **Goal:** Improve French (Quebec-accent) comprehension **without degrading or breaking** the existing
> agent, the English call path, or the complaint agent.
> **Status:** Options for the owner to choose from. **R3 implemented + pushed to live agents on 2026-06-25**; R1/R2/R4/R5 still open.
> **Related:** `PLAN_lease_agent_french_accent_stt_city_recognition.md` (the source plan; A1/B1 below
> come from it and were never shipped), `docs/diagnoses/lease_agent_pausing_and_french_stt_2026-06-22.md`
> (the real-call evidence), `PLAN_lease_agent_fuzzy_band_entity_confirmation.md`.

---

## 1. Where French understanding stands today (so we don't redo solved work)

**Already shipped and strong — leave it alone:**

- **Backend matching is phonetic + fuzzy.** `services/city_matching.py` scores the spoken city with a
  hybrid `similarity()` = max(rapidfuzz, Metaphone-via-jellyfish, difflib), and `rank_candidates`
  produces banded `AUTO_ACCEPT / CONFIRM / NO_MATCH`. `normalize_place` strips diacritics and expands
  St/Ste → Saint/Sainte.
- **`find_units` already returns the safety nets** (`routes/leasing.py:235-313`): `available_cities`
  (real cities to offer on a no-match), a `disambiguation` block (the "did you mean X or Y?" turn), and
  the match gate is unified with the ranker so an AUTO_ACCEPT city is never silently dropped.
- **The prompt already has** the FR/EN language lock, the "et demi" unit-size pronunciation rule
  (`[Unit Size Pronunciation]`), and `now`-based date reasoning.

**The residual gap is UPSTREAM of the matcher (this is what these options target):**

The 06-22 call diagnosis proved the failures are at the **speech-to-text** step, not the matcher.
Deepgram `language:"multi"` mangles Quebec-French proper nouns so badly the matcher never gets a fair
chance (e.g. "Saint-Lazare" → *"thing on low"*, "quatre et demi" → *"Captain mi"*). Two fixes from the
source plan were **never implemented**:

- **No keyterm biasing** — `grep keyterm backend/` returns 0 hits. The lease agent shares the same static
  `TRANSCRIBER_CONFIG` (`vapi_agent_config.py:286-301`) as the complaint agent; STT gets no hint of the
  manager's real cities.
- **No proactive city list in the model's context** — `_LEASE_CONTEXT_BLOCK` (`vapi_agent_config.py:1327-1334`)
  carries only `manager_id` + `manager_name`. The model only learns the real cities *reactively* from a
  tool response *after* a no-match.

Plus the diagnosis flagged the agent's **own French** breaking and a **"pausing a lot"** complaint.

---

## 2. The non-breaking principle (applies to every option below)

Every option is **additive and scoped to the per-manager lease agent**. None of them:

- touches the English path (the same city data serves both languages),
- touches the complaint agent (`build_complaint_config` keeps its own static transcriber),
- changes the matcher's already-passing logic/tests.

Nothing goes live until pushed with `python backend/scripts/update_lease_agents.py` (run with the backend
venv `backend\.venv\Scripts\python.exe`; it needs `supabase` + `httpx`, **not** the `vapi` SDK). Always
`--dry-run` first.

---

## 3. The options

### R1 — Seed the model with the manager's real cities in the context block (source plan: B1)

**What:** Add the manager's distinct active-listing cities (with accents) into `_LEASE_CONTEXT_BLOCK`,
plus a Step-1/2 prompt rule: *resolve the spoken city to the nearest city on this list before calling
find_units; confirm briefly if unsure; only fall to `available_cities` when nothing is close.* Requires
one DB query (distinct `lease_listings.city` for the manager) in the deploy loop, right beside the
existing `manager_name` fetch at `update_lease_agents.py:130-132`, passed into `build_lease_config`.

**Pros:**
- Highest leverage for the lowest risk. gpt-5.2 is bilingual and knows Quebec geography — it bridges the
  phonetic gap *before* the tool round-trip, where `difflib` alone can't.
- Cuts `find_units` retries (each garbled-then-corrected city currently costs an extra lookup), so it
  also reduces the "pausing" feel — one change helps both complaints.
- Pure prompt + one query. Zero infra, zero latency, no model/transcriber change.
- Structurally cannot affect the English path (English callers benefit from the same list) or the
  complaint agent.

**Cons:**
- The city list is **baked at provision/update time** → goes stale when a manager adds/removes a city
  until the next `update_lease_agents.py` run (same staleness class as R2, but lower stakes — the
  `available_cities` tool fallback still covers a missing city at runtime).
- Adds tokens to the system prompt (negligible for a handful of cities; watch it for managers with very
  large portfolios).
- It's a *soft* fix — relies on the model following the instruction, not a hard guarantee.

**Risk:** Very low. **Effort:** Low. **Files:** `vapi_agent_config.py` (context block + Step 1/2 text,
`build_lease_config` signature), `update_lease_agents.py` (cities query), provisioning caller.

---

### R2 — Per-manager Deepgram keyterm prompting (source plan: A1)

**What:** Build a lease-only `LEASE_TRANSCRIBER_CONFIG` that adds `keyterm: [<manager's cities + accent /
St-Saint variants>]` while staying on nova-3 `language:"multi"`. Leaves the complaint agent's
`TRANSCRIBER_CONFIG` (`vapi_agent_config.py:286-301`) untouched.

**Pros:**
- Fixes the transcript **at the source**, so *every* downstream layer (matcher, model, disambiguation)
  benefits — this is the actual root-cause fix, not a recovery net.
- Stays on nova-3 + `language:"multi"` — no model downgrade, no loss of existing quality.
- Complementary to R1: R2 makes the transcript right more often; R1 recovers what R2 still misses.

**Cons:**
- **Needs a Vapi-acceptance gate.** The `keyterm` param must be validated with `--dry-run` first — if the
  param name/shape is wrong, Vapi could reject the assistant update. Must confirm before pushing to all
  managers.
- **Staleness is higher-stakes than R1** — keyterms are baked per-assistant; a manager adding a city
  silently stops biasing toward it until a re-push. Needs a refresh trigger (on listing create/delete, or
  a periodic `update_lease_agents.py`) — an open decision.
- Keyterm capacity is bounded (~500 tokens); huge portfolios may need a most-relevant subset.
- Biasing toward listed cities can, in rare cases, pull a genuinely different spoken city toward a listed
  one (low risk with proper-noun city names, but worth watching on the test corpus).

**Risk:** Low–Medium (mostly the deploy-acceptance + staleness wiring). **Effort:** Medium.
**Files:** `vapi_agent_config.py` (new transcriber builder + `_lease_assistant_shell` wiring),
`update_lease_agents.py` (cities query — shared with R1), staleness trigger TBD.

---

### R3 — Lock vous/tu register + fix the malformed French screening line (prompt-only) — ✅ IMPLEMENTED 2026-06-25

**What:** The transcripts show Max's *own* French breaking: *"Tu n'es pas bien compris"* (wrong grammar
**and** a tu/vous flip mid-call) and a garbled landlord-awareness question. The `[Language Policy]` locks
EN/FR but not register. Add a "use **vous** consistently, never **tu**" rule and clean the screening
phrasing in `_LEASE_SYSTEM_PROMPT_BASE`.

**Shipped:** Added a `[French Register — STRICT]` block to `_LEASE_SYSTEM_PROMPT_BASE` (`vapi_agent_config.py`)
mandating formal **vous** for the whole French call, banning **tu**/`t'`/tu-conjugations even if the caller
uses tu, and giving the correct "Je n'ai pas bien compris, pourriez-vous répéter?" recovery line (replacing
the broken "Tu n'es pas bien compris"). Also added an explicit **French (vous) template** to the Q2
landlord-awareness step — "Est-ce que votre propriétaire actuel sait que vous cherchez à déménager?" — so the
model stops translating it on the fly and producing the garbled version seen in the transcripts. Pushed to
all active per-manager lease assistants + the shared agent via `update_lease_agents.py`.

**Pros:**
- A bot that speaks broken/inconsistent French *feels* like it isn't understanding — this is "French
  understanding" from the caller's side. Direct UX win.
- Pure prompt; cannot affect English calls or any tool behavior.
- Trivial effort, deployable in the same push as R1.

**Cons:**
- Doesn't touch STT comprehension (the input side) — it polishes the *output* side only.
- Slightly more prompt text; the model must adhere (soft enforcement, like all prompt rules).

**Risk:** Very low. **Effort:** Very low. **Files:** `vapi_agent_config.py` (`_LEASE_SYSTEM_PROMPT_BASE`).

---

### R4 — Trim stall-phrase density + the dropped-token double re-prompt

**What:** Two tweaks to the "pausing a lot" complaint: (a) instruct the model to speak the "one moment"
checking phrase **only on turns where a tool actually fires** (it currently over-applies it — see T2
02:11:52, a stall phrase with no preceding lookup); (b) tune endpointing so one low-confidence dropped
token doesn't trigger two back-to-back re-asks (`confidenceThreshold` / `transcriptionEndpointingPlan`).

**Pros:**
- Attacks the "pauses a lot" half directly; that perception compounds "doesn't understand me."
- Mostly prompt; the endpointing piece is a small, reversible config tweak scoped to the lease agent.

**Cons:**
- The endpointing tuning is empirical — needs a couple of test calls to confirm it doesn't *under*-prompt
  (drop a real answer). Slightly more validation than R1/R3.
- Indirect: improves *flow/latency feel*, not raw recognition accuracy.

**Risk:** Low (endpointing change needs a test call). **Effort:** Low.
**Files:** `vapi_agent_config.py` (`[System-Check Phrases]` / `[Background Tool Calls]` text;
`start_speaking_plan` / transcriber threshold for the lease shell).

---

### R5 — Corpus-driven alias expansion (optional, lowest priority)

**What:** Harvest real mistranscriptions from `call_logs.transcript` and seed `_CITY_ALIASES` in
`city_matching.py` (e.g. `"twa reviewer" → "trois rivieres"`). Optionally add a one-off mining script in
`backend/scripts/`.

**Pros:**
- Cheap, data-grounded wins for the exact garbles your callers actually produce.
- Gives a real regression corpus to lock into `tests/test_city_matching.py`.

**Cons:**
- Reactive and needs ongoing upkeep — every new accent/garble is a new alias.
- Lower marginal value now that `similarity()` is already phonetic; mostly mops up tail cases.
- **Do NOT** globally lower the difflib 0.82 threshold to chase these — it regresses distinct-city
  separation (Laval ≠ Longueuil). Keep that as a guard test.

**Risk:** Low. **Effort:** Low–Medium (mining + tuning). **Files:** `city_matching.py`,
`tests/test_city_matching.py`, optional `backend/scripts/analyze_city_mistranscriptions.py`.

---

## 4. Summary table

| ID | Refinement | Layer | Impact | Effort | Risk | Breaks English/complaint agent? |
|----|------------|-------|--------|--------|------|---------------------------------|
| R1 | Seed model with manager's real cities (B1) | Prompt + deploy query | High | Low | Very low | No |
| R2 | Per-manager Deepgram keyterm (A1) | Transcriber (STT) | High | Medium | Low–Med | No (lease-only transcriber) |
| R3 | vous/tu lock + fix malformed FR ✅ done | Prompt | Medium | Very low | Very low | No |
| R4 | Trim stall phrases + endpointing | Prompt + config | Medium | Low | Low | No (lease-only) |
| R5 | Corpus-driven alias expansion | Backend matcher | Low–Med | Low–Med | Low | No |

---

## 5. Recommended sequencing (not a decision — a suggestion)

1. **R1 + R3 first** — both pure prompt (R1 adds one query), deployable together in one
   `update_lease_agents.py` push, structurally incapable of affecting English or the complaint agent.
2. **R2 next**, behind a `--dry-run` to confirm Vapi accepts `keyterm`, once R1's gain is measured — it's
   the bigger STT lever but carries the deploy-acceptance + staleness wiring.
3. **R4** alongside, since it shares the same prompt file and addresses the compounding "pausing" complaint.
4. **R5** last, corpus-driven, only if tail garbles persist after R1/R2.

R1 and R2 share the same "manager's distinct cities" query, so doing R1 first makes R2 cheaper.

---

## 6. Deploy + verify (applies to whichever options are chosen)

- Push: `backend\.venv\Scripts\python.exe backend/scripts/update_lease_agents.py --dry-run` then without
  `--dry-run`.
- Live FR-accent test calls naming each portfolio city + one not-in-portfolio city; confirm Max matches,
  confirms the city back, speaks consistent *vous*, and offers only real `available_cities` on a true
  no-match.
- On completion, update `CODEBASE_CONTEXT.md`: the `/leasing/find-units` row (LLM pre-canonicalization),
  the transcriber section (per-manager keyterm + refresh trigger), and the lease-agent behavior section.

## 7. Open decisions for the owner

1. Which options to implement (R1–R5 / subset).
2. **R2 staleness trigger** — re-push keyterms on listing create/delete (precise, more wiring) vs periodic
   `update_lease_agents.py` (simple, lag).
3. Whether to add the cities query to the **provisioning path** too (not just the bulk update script), so
   newly provisioned managers get R1/R2 immediately.
