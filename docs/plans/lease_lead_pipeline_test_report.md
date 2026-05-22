# Lease Lead Pipeline — Test Execution Report

**Date:** 2026-05-22
**Branch:** main
**Auditor:** Claude Code (static analysis — no live server)

> This report executes every verifiable section of `lease_lead_pipeline_test_plan.md`
> against the current source code. Sections that require a running server or a live
> VAPI call are marked accordingly.

---

## Verdict: READY TO DEPLOY (pending Section 7 live-call sign-off)

All code paths are correct. Three pre-deploy manual gates remain.

---

## Section-by-Section Results

### Section 0 — Pre-flight

| Check | Status | Notes |
|---|---|---|
| `VAPI_SHARED_LEASE_ASSISTANT_ID` env var | MANUAL | `config.py:31` reads it from env, defaults to `""` |
| `VAPI_SHARED_LEASE_NUMBER_ID` env var | MANUAL | `config.py:32` reads it from env, defaults to `""` |
| At least one property group exists | MANUAL | Required for Path 4 resolution |
| At least one active listing exists | MANUAL | Required for Path 1 test |
| Backend + frontend servers running | MANUAL | — |

---

### Section 1 — DB Baseline Check

| Check | Status | Notes |
|---|---|---|
| `lease_leads` table columns | MANUAL | Can't verify DB schema from code |
| `updated_at` allows NULL | PASS | `LeadResponse.updated_at: Optional[datetime] = None` (`schemas/leasing.py:85`) |
| Insert never sets `updated_at` | PASS | `lead_payload` in `voice.py:587–604` has no `updated_at` key |

---

### Section 2 — Webhook Endpoint

#### 2a. Path 4 — Shared agent fallback

| Check | Status | Notes |
|---|---|---|
| Endpoint exists at `POST /voice/lease-lead-webhook` | PASS | `voice.py:464`, registered in `main.py:33` |
| Returns `{"status": "processed"}` | PASS | `voice.py:613` — always returns this regardless of path |
| Extracts `assistantId` / `phoneNumberId` from `message.call` | PASS | `voice.py:517–518` |
| Path 4 triggers on matching `assistantId` OR `phoneNumberId` | PASS | `voice.py:566–567` — OR condition covers either field |
| Falls back to first `properties_list` row | PASS | `voice.py:569–576` |
| Log emits `path=shared_agent_fallback property_group_id=<uuid>` | PASS | `voice.py:578` |
| Log emits `[SAVED] phone=... status=... property_group_id=...` | PASS | `voice.py:607` |

#### 2b. Path 1 — listing_uuid resolution

| Check | Status | Notes |
|---|---|---|
| UUID regex rejects non-UUID values | PASS | `voice.py:526` — `UUID_RE.match()` gates the lookup |
| Valid UUID triggers `lease_listings` lookup | PASS | `voice.py:528–531` |
| Resolution path logged as `listing_uuid` | PASS | `voice.py:531` |

#### 2c. No tool call — ignored

| Check | Status | Notes |
|---|---|---|
| Empty `toolCalls` returns `{"status": "ignored"}` | PASS | `voice.py:494–497` — breaks early when `lead_tool is None` |
| No DB insert on ignored event | PASS | Insert at `voice.py:606` is unreachable without a `lead_tool` |

---

### Section 3 — GET /leasing/leads

| Check | Status | Notes |
|---|---|---|
| Route exists | PASS | `leasing.py:230`, registered via `leasing.router` prefix `/leasing` |
| Returns 200 (not 500) on NULL `updated_at` | PASS | `LeadResponse.updated_at: Optional[datetime] = None` — no validation error |
| All non-nullable `LeadResponse` fields are always set by webhook | PASS | `caller_name` → `or "Unknown"`, `phone` → `""` fallback, `qualification_status` → `or "unmatched"`, `source` → hardcoded `"voice"` |
| Filters by manager's `property_group_id` | PASS | `leasing.py:238–245` — looks up manager's PG IDs first |
| `interested_listing_ids` missing from DB | SAFE | `Field(default_factory=list)` — Pydantic uses `[]` for missing key |

---

### Section 4 — GET /leasing/metrics

| Check | Status | Notes |
|---|---|---|
| Route exists | PASS | `leasing.py:288` |
| `total_calls` = row count | PASS | `leasing.py:303` |
| `qualified` count correct | PASS | `leasing.py:304` |
| `qualification_rate` safe when total = 0 | PASS | `round(qualified / total * 100, 1) if total else 0` — `leasing.py:317` |
| Filters by manager's property groups | PASS | `leasing.py:295–300` |

---

### Section 5 — Frontend UI

| Check | Status | Notes |
|---|---|---|
| Page loads with loading state | PASS | `LeasingTab.jsx:115–121` |
| Metrics cards render | PASS | `LeasingTab.jsx:165–173` |
| Listings grid renders | PASS | `LeasingTab.jsx:192–222` |
| Leads table columns: Name, Phone, Budget, Beds, Move-in, Status, Actions | PASS | `LeasingTab.jsx:258` — all 7 headers present |
| Status badge colours (green/red/yellow/blue/purple/emerald/muted) | PASS | `LeasingTab.jsx:12–20` — all 7 statuses in `STATUS_BADGE` |
| Refresh button visible top-right | PASS | `LeasingTab.jsx:130–135` |
| Refresh button re-fetches without full reload | PASS | Calls `load()` which does `Promise.all([...])` — `LeasingTab.jsx:60–78` |

---

### Section 6 — Lead Detail Modal

| Check | Status | Notes |
|---|---|---|
| "View" button opens modal | PASS | `LeasingTab.jsx:284–285` — `setSelectedLead(lead)` |
| Modal shows all lead fields | PASS | `LeadDetailModal.jsx` — phone, email, bedrooms, budget, move-in, floor, occupants, qualifying answers, disqualifying reason, call ID, duration |
| Changing status and Save calls PATCH | PASS | `LeadDetailModal.jsx:37` — `updateLead(lead.uuid, payload)` |
| Lead row in table updates after save | PASS | `LeasingTab.jsx:104–107` — `handleLeadUpdated` replaces the row |
| Cannot set status back to a voice-set status (qualified, not_qualified, unmatched) | PASS | Backend: `leasing.py:261–268` — `_MANAGER_EDITABLE_STATUSES` rejects them with 400. Frontend: once moved to a manager status, `isVoiceSet = false` and dropdown only shows manager statuses — `LeadDetailModal.jsx:25, 168–178` |

---

### Section 7 — Live VAPI Call Test

**Status: MANUAL — cannot be executed via static analysis.**

Required before deploy sign-off:
1. Call the shared lease phone number from a test device
2. Complete the full conversation
3. Confirm backend log shows `path=shared_agent_fallback` and non-null `property_group_id`
4. Confirm lead appears in UI after clicking Refresh
5. Confirm `qualification_status` matches agent's determination

---

### Section 8 — Edge Cases

#### 8a. Hallucinated listing_uuid (e.g. "S-106")

| Check | Status | Notes |
|---|---|---|
| UUID regex rejects non-UUID string | PASS | `voice.py:526` — `UUID_RE.match("S-106")` returns None, so `listing_uuid = None` |
| Falls through to Path 4 | PASS | All three resolution paths are tried before Path 4 |
| Lead still saved | PASS | `voice.py:606` always runs if a `lead_tool` was found |

#### 8b. No property_group resolution

| Check | Status | Notes |
|---|---|---|
| `property_group_id` stays None | PASS | Default `None` if no path resolves — `voice.py:522` |
| Log shows `path=None property_group_id=None` | PASS | `voice.py:578` prints both |
| Lead inserted with `property_group_id = NULL` | PASS | `voice.py:588` — `str(property_group_id) if property_group_id else None` evaluates to `None` |
| Lead invisible to managers | PASS | `get_leads` at `leasing.py:243` uses `.in_("property_group_id", pg_ids)` — NULL won't match any real UUID |

---

## Known Issues / Non-Blockers

| Issue | Severity | Detail |
|---|---|---|
| `update_lead` has no ownership check | Low (MVP) | `leasing.py:272` — any authenticated manager can PATCH any lead UUID. Fine for single-tenant MVP, worth fixing before multi-tenant rollout. |
| `get_listings` uses service DB | Low | `leasing.py:144` — bypasses RLS but applies explicit `eq("manager_id", ...)` filter. Functionally safe. |
| Path 4 picks the **first** property group | Informational | `voice.py:569–576` — single-tenant assumption. Works correctly for current MVP setup. |

---

## Pre-Deploy Checklist

- [ ] **Section 0:** Confirm `VAPI_SHARED_LEASE_ASSISTANT_ID` and `VAPI_SHARED_LEASE_NUMBER_ID` are set in `.env` / Render env vars
- [ ] **Section 1:** Confirm `lease_leads` table exists in Supabase with all required columns
- [ ] **Section 7:** Execute live VAPI call test and confirm lead appears in UI

---

## Sign-off

| Check | Result |
|---|---|
| Webhook processes shared agent call correctly | PASS (code) |
| `property_group_id` resolved via correct path | PASS (code) |
| Leads visible in UI after Refresh | PASS (code) |
| Metrics match actual lead count | PASS (code) |
| Lead detail + status update works | PASS (code) |
| Cannot regress status to voice-set value | PASS (code — both backend + frontend) |
| Live call end-to-end | PENDING (Section 7 manual gate) |
