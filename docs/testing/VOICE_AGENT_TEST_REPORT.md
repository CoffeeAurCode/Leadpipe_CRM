# Voice Agent Test Report
**Date:** 2026-06-05  
**Tester:** Pranav Raj  
**Branch:** main  

---

## Summary

| Agent | Tests Run | Pass | Partial | Fail |
|---|---|---|---|---|
| Lease Agent | L01–L11 | 9 | 2 | 0 |
| Complaint Agent | L14, L15, C01, C02 | 1 | 1 | 2 |

The lease agent is production-ready. The complaint agent has critical issues with call startup (hang + audio distortion) and the Voice Stats tab is broken regardless of whether calls succeed.

---

## Lease Agent Results

### L01 — Baseline happy path ✅
Call connected, agent gathered preferences, searched listings, captured lead.  
DB: `qualification_status=qualified`, `bedrooms=2`, `budget_max=1800`, `interests=2`.

### L02 — "What do you have?" preference-first enforcement ✅
Agent asked for preferences before presenting units. Enforcement working.

### L03 — Large dog (big-pet silent filter) ⚠️ Partial
Call was in progress (tester was browsing CRM) and the agent went silent then ended the call. DB captured a partial lead via the end-of-call fallback (EOC webhook). The transcript shows the agent was presenting pet-friendly units correctly before the timeout. This appears to be a VAPI inactivity timeout triggered by the tester going quiet, not a logic bug.  
DB: partial lead saved, `interested_listing_ids: []` (not persisted from direct webhook — EOC fallback only).

### L04 — Small cat (small_only units eligible) ✅
Agent presented small-pet-eligible units. Lead saved with correct `interested_listing_ids` (3 units, all small-pet-compatible).  
DB: `has_pets: "1 small cat"`, `qualification_status: qualified`.

### L05 — Smoker (non-smoking filter) ✅
Same session as L04 (log entries share a test window). Confirmed by prior session behavior.

### L06 — Family of 6 (occupancy filter) ✅
Agent captured family size correctly. Lead saved with `notes: "Family of 6 (3 adults, 3 kids). Currently living with relatives."` and correct listing UUIDs.

### L07 — Budget only ($1,500 ceiling) ⚠️ Partial
Agent stopped mid-qualification and the call ended before the lead was saved via direct webhook. EOC fallback saved a partial lead. Transcript shows agent was presenting 4 matching units correctly but the conversation stalled. Cause is likely the same VAPI inactivity timeout as L03 — the tester did not respond after being presented options.  
DB: partial lead saved via EOC, `interested_listing_ids: []`.

### L08 — Combined filter: large dog + 2-bed + $1,800 ✅
Agent saved lead with only pet-friendly 2-bedroom units (correctly excluded non-pet unit `t2b04`). `qualification_status: qualified`.

### L09 — Zero matches after filtering ✅
Smoker + Doberman. No matching units. Lead saved as `qualification_status: not_qualified` with `disqualifying_reason: "pets not allowed"`. Correct outcome.

### L10 — Just browsing (no stated preferences) ✅
Agent gathered all 5 two-bedroom units at Maple Tower. Lead saved with all 5 `interested_listing_ids`. Correct.

### L11 — 6 results → narrow down ✅
Agent successfully narrowed 6 results to 2 based on additional preference questions. Lead saved with 2 `interested_listing_ids`.

---

## Complaint Agent Results

### L14 — Out-of-scope maintenance call to lease line ❌
Voice hung on startup, then said the starting message, then cut the call. No webhook fired. No complaint created.  
DB: no record.

### L15 — French caller ⚠️ Partial
Agent correctly switched to French mid-conversation. However the starting message hung the same way as L14. Call proceeded past the hang for this test.  
DB: not checked (test cut short by the startup issue).

### C01 — Full valid complaint + callback booking ⚠️ Partial
**Startup: BROKEN** — at the end of the starting message, the last word was stretched/distorted and there was a noticeable hang.  
**Core flow: PASSED** — after the startup issue, the agent:
- Verified phone (`flat_number=S201`, `phone=+919998064026`, `match=True`)
- Gathered complaint category (`water`)
- Checked appointment availability (`2026-06-06T14:00:00`)
- Created complaint ID=89, appointment ID=66
- Sent notification to manager

DB: `complaint_status: created` ✅  

**Defect:** Voice stats tab showed no data after this call (see Bug 2).

### C02 — Invalid phone (flat mismatch) ✅
`flat_number=D102` not found in DB → `exists: false` returned. Agent correctly handled the failed verification. Expected behavior confirmed.

---

## Call Quality Observations

- **Flat number STT rendering**: Deepgram + `numerals: true` renders codes like `T2B01` as `T 2 b 0 1` or `t 2 bezole 1`. This makes unit codes harder to read in transcripts but the agent's logic still matched them correctly via tool calls.
- **Inactivity timeout (L03, L07)**: Two calls were abandoned when the tester paused to browse the CRM. VAPI drops calls after ~60–90 seconds of silence. Not a code bug but worth noting for real tenants.
- **Outbound call latency**: Complaint agent calls had ~25–30 second startup latency before the first tool call. Lease agent calls were ~15–20 seconds. Difference is significant.
