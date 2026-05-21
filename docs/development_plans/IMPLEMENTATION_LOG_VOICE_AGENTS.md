# Implementation Log — Voice Agents (Complaint + Lease)

**Date:** 2026-05-20  
**Plan:** `docs/development_plans/PLAN_VOICE_AGENTS.md`  
**Status:** Ready for manual VAPI setup (stop at §5)

---

## What Was Built

All code from the plan has been implemented through Phase 16 (Sidebar + App.jsx routing). The system is code-complete and awaiting the one-time manual VAPI dashboard setup described in §5 of the plan.

---

## Files Created

| File | Purpose |
|------|---------|
| `backend/migrations/010_voice_agents.sql` | Adds lease agent columns to `properties_list`; creates `lease_listings` and `lease_leads` tables |
| `backend/app/schemas/leasing.py` | Pydantic V2 schemas: `ListingCreate`, `ListingUpdate`, `ListingResponse`, `LeadUpdate`, `LeadResponse`, `CustomRules` |
| `backend/app/routes/leasing.py` | VAPI tool endpoints (`GET /leasing/find-listing`, `GET /leasing/search`) + Manager CRUD (listings, leads, metrics, CSV export) |
| `backend/app/services/vapi_provisioning.py` | `provision_vapi_for_property_group()` — provisions lease assistant + phone number for new property groups |
| `frontend/src/components/LeasingTab.jsx` | Leasing dashboard: metrics cards, listings grid, leads table with filters |
| `frontend/src/components/AddListingModal.jsx` | Create/edit listing modal with collapsible qualifying rules section |
| `frontend/src/components/LeadDetailModal.jsx` | Lead detail view: contact, preferences, qualifying answers, pipeline status, manager notes |

---

## Files Modified

| File | What Changed |
|------|-------------|
| `backend/app/schemas/flat.py` | Added `property_group_id: Optional[str]` to `FlatVerifyPhoneResponse` |
| `backend/app/routes/flats.py` | `verify_phone`: fetches `building_id` from flat, resolves `property_group_id` via `buildings → properties_list`, returns it on valid responses |
| `backend/app/services/vapi_agent_config.py` | Added `build_complaint_config()`, `build_complaint_tools()`, `_build_lease_tools()`, `build_lease_config_shared()`, `build_lease_config()` + system prompts. Legacy `build_assistant_config()` / `build_tools()` untouched. |
| `backend/app/routes/voice.py` | Added `POST /voice/lease-lead-webhook` (creates `lease_leads` record from VAPI function call); imported `get_service_db` |
| `backend/app/routes/property_groups.py` | `create_property_group` now sets `vapi_provisioning_status = "pending"` and fires `provision_vapi_for_property_group` as a `BackgroundTask`; added `POST /property-groups/{id}/provision-voice` retry endpoint; `PropertyGroupResponse` now includes `vapi_provisioning_status` and `vapi_phone_number` |
| `backend/app/config.py` | Added `VAPI_COMPLAINT_ASSISTANT_ID`, `VAPI_COMPLAINT_NUMBER_ID`, `VAPI_SHARED_LEASE_ASSISTANT_ID`, `VAPI_SHARED_LEASE_NUMBER_ID` |
| `backend/app/main.py` | Registered `leasing.router` |
| `frontend/src/services/apiService.js` | Added `getListings`, `createListing`, `updateListing`, `deleteListing`, `getLeaseLeads`, `updateLead`, `deleteLead`, `getLeasingMetrics`, `exportLeads` |
| `frontend/src/components/Sidebar.jsx` | Added `{ id: 'leasing', icon: KeyRound, label: 'Leasing' }` after `voice-stats` |
| `frontend/src/App.jsx` | Added `LeasingTab` lazy import; added `{currentView === 'leasing' && <LeasingTab />}` |

---

## Architecture Implemented

### Complaint Agent (Option B)
- One global VAPI assistant, one phone number → handles complaints for ALL property groups
- `verify_phone` now returns `property_group_id` (resolved: flat → building → properties_list)
- `build_complaint_config()` generates the assistant payload with:
  - Extended `Verify_phone_number` variableExtractionPlan (includes `property_group_id`)
  - `submit_complaint` function tool now requires `property_group_id` parameter
  - System prompt instructs agent to extract and forward `property_group_id` to `submit_complaint`

### Lease Agent (Hybrid)
- **Existing groups** → shared assistant (no pg_id in tool URLs) → backend searches all groups
- **New groups** → auto-provisioned on `PropertyGroup` creation → dedicated assistant + phone, pg_id hardcoded in tool URLs
- `lease-lead-webhook` resolves `property_group_id` via listing UUID → DB, then assistant_id → DB, then null

### VAPI Tool Endpoints
- `GET /leasing/find-listing?query=...&property_group_id=` — optional pg_id; searches all groups when absent
- `GET /leasing/search?bedrooms=...&budget_max=...&property_group_id=` — same pattern
- Both use `get_service_db` (service role, bypasses RLS for cross-group search)

### Manager CRUD
- All `/leasing/*` CRUD endpoints use `get_authenticated_db` + `require_active_subscription`
- Listing creation resolves `property_group_id` from flat → building → properties_list
- Lead status: voice sets `qualified` / `not_qualified` / `unmatched`; managers can advance to `contacted` / `toured` / `converted` / `lost`

---

## Database Migration — Run This Next

**File:** `backend/migrations/010_voice_agents.sql`

Run in the Supabase SQL editor:

```
1. ALTER TABLE properties_list — adds vapi_lease_assistant_id, vapi_phone_number_id,
   vapi_phone_number, vapi_provisioning_status (default: 'not_applicable' for all existing rows)

2. CREATE TABLE lease_listings — per-group listings with flat FK, qualifying rules JSONB

3. CREATE TABLE lease_leads — voice-captured leads with qualification pipeline
```

---

## Environment Variables — Add to `.env`

```env
# Complaint Agent (set after manual VAPI setup — see §5.1 of plan)
VAPI_COMPLAINT_ASSISTANT_ID=
VAPI_COMPLAINT_NUMBER_ID=

# Shared Lease Agent (set after manual VAPI setup — see §5.2 of plan)
VAPI_SHARED_LEASE_ASSISTANT_ID=
VAPI_SHARED_LEASE_NUMBER_ID=
```

The existing `VAPI_ASSISTANT_ID` and `VAPI_NUMBER_ID` are kept (used by the outbound call endpoint).

---

## What To Do Next (§5 — Manual VAPI Setup)

### 5.1 Complaint Agent
```python
# Run this in a Python shell to generate the assistant payload:
from app.services.vapi_agent_config import build_complaint_config
import json
print(json.dumps(build_complaint_config(), indent=2))
```
1. Paste the payload into the VAPI dashboard → Create assistant
2. Copy the assistant ID → set `VAPI_COMPLAINT_ASSISTANT_ID=<id>` in `.env`
3. Assign or purchase a phone number in VAPI → link to this assistant
4. Set `VAPI_COMPLAINT_NUMBER_ID=<id>` in `.env`

### 5.2 Shared Lease Agent
```python
from app.services.vapi_agent_config import build_lease_config_shared
import json
print(json.dumps(build_lease_config_shared(), indent=2))
```
1. Have a Twilio number ready; import it into VAPI (requires Twilio credentials in VAPI settings)
2. Paste the payload → Create assistant in VAPI dashboard
3. Copy assistant ID → set `VAPI_SHARED_LEASE_ASSISTANT_ID=<id>` in `.env`
4. Set `VAPI_SHARED_LEASE_NUMBER_ID=<id>` in `.env`
5. Link the Twilio number to the shared lease assistant in VAPI

### After Setup
- The Leasing tab is live in the sidebar — add listings before testing
- Run the DB migration (`010_voice_agents.sql`) in Supabase SQL editor
- Restart the backend so new env vars are picked up
- Call the complaint number and verify `property_group_id` is returned in verify-phone responses
- Create a test listing, call the lease number, confirm a lead appears in the Leasing tab

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `get_service_db` on VAPI endpoints | VAPI calls have no auth token; anon client would be blocked by RLS on new tables |
| `property_group_id` resolved at webhook time (not passed by agent for lease) | Lease agent callers are strangers — no verification step to extract pg_id from |
| Manager-editable statuses: `contacted, toured, converted, lost` | Voice sets `qualified / not_qualified / unmatched`; managers drive the pipeline forward |
| Provisioning runs as BackgroundTask | Keeps `POST /property-groups` fast; VAPI API calls can take 2–5s |
| Legacy `build_assistant_config()` kept untouched | Existing test group assistant not re-deployed; only new assistant IDs use new config |
