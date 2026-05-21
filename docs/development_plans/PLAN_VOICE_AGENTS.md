# Implementation Plan: Two Voice Agents (Complaint + Lease)

**Date:** 2026-05-20
**Author:** Pranav Raj
**Status:** Ready to implement
**Supersedes:** PLAN_DUAL_MODE_VOICE_AGENT.md
**Specs:** `docs/feature_specs/PRD_COMPLAINT_VOICE_AGENT.md`, `docs/feature_specs/PRD_LEASE_AGENT.md`

---

## 0. Architecture Overview

Two standalone VAPI voice agents. No Squad, no RouterAgent, no inter-agent transfers.

| Agent | Architecture | Phone Number | Scope |
|-------|-------------|--------------|-------|
| **Complaint Agent (Alex)** | Option B — Single Number + Caller Phone Lookup | One global number for ALL property groups | Existing + new property groups |
| **Lease Agent** | Hybrid (see §0.2) | Shared number for existing; dedicated number for new | Existing groups share; new groups auto-provisioned |

### 0.1 Complaint Agent — Option B

One VAPI assistant, one global phone number, handles complaints for all property groups. `Verify_phone_number` is extended to return `property_group_id` alongside the existing `status` and `datetime`. The agent reads this and passes it to all subsequent tools.

```
Tenant calls global complaint number (+91-XXXX-COMPLAINT)
        ↓
Alex greets the caller
        ↓
"What's your flat number?"
        ↓
Verify_phone_number(flat_number, caller_phone)
→ returns { status: "valid", property_group_id: "abc-123", datetime: "..." }
        ↓
Alex passes property_group_id to all subsequent tools:
submit_complaint, check_availability, view_active_appointments,
update_appointment, cancel_appointment
```

### 0.2 Lease Agent — Hybrid Architecture

**Existing property groups (test groups):**
- User provides one Twilio number → manually imported into VAPI
- One shared VAPI lease assistant, no `property_group_id` hardcoded
- Backend's `find_listing` and `search_available_listings` search across ALL property groups when no `property_group_id` is passed
- Lead's `property_group_id` is resolved from the matched `listing_uuid`; null if unmatched

**New property groups (from next signup onward):**
- Auto-provisioned on PropertyGroup creation (background task)
- One VAPI lease assistant created per group, `property_group_id` hardcoded in system prompt and tool URLs
- One dedicated +91 phone number purchased and linked to that assistant

```
Existing groups:
  Caller dials shared lease number
          ↓
  Shared VAPI lease assistant (no pg_id in URLs)
          ↓
  find_listing / search → backend searches ALL property groups
          ↓
  submit_lease_lead → pg_id derived from listing_uuid (or null)

New groups:
  Caller dials group's dedicated number
          ↓
  Per-group VAPI lease assistant (pg_id hardcoded)
          ↓
  find_listing / search → scoped to this group only
          ↓
  submit_lease_lead → pg_id from assistant lookup
```

---

## 1. Environment Variables

| Variable | Purpose | Setup |
|----------|---------|-------|
| `VAPI_COMPLAINT_ASSISTANT_ID` | Global complaint agent assistant ID | Create once in VAPI; store in .env |
| `VAPI_COMPLAINT_NUMBER_ID` | VAPI phone number ID for complaint agent | Assign in VAPI; store in .env |
| `VAPI_SHARED_LEASE_ASSISTANT_ID` | Shared lease assistant for existing property groups | Create once; store in .env |
| `VAPI_SHARED_LEASE_NUMBER_ID` | User-provided Twilio number imported into VAPI | User provides; import into VAPI; store in .env |
| `PRIVATE_VAPI_API` | VAPI API key for auto-provisioning new groups | Already exists |
| `BACKEND_URL` | Baked into tool URLs at build time | Already exists |

> `VAPI_ASSISTANT_ID` and `VAPI_NUMBER_ID` are the legacy single-assistant env vars. Rename to `VAPI_COMPLAINT_ASSISTANT_ID` and `VAPI_COMPLAINT_NUMBER_ID` during the agent config refactor.

---

## 2. Database Changes

**File:** `backend/migrations/0XX_voice_agents.sql`

### 2.1 `properties_list` — Lease Agent Columns (new property groups only)

```sql
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS vapi_lease_assistant_id    TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number_id       TEXT,
  ADD COLUMN IF NOT EXISTS vapi_phone_number          TEXT,
  ADD COLUMN IF NOT EXISTS vapi_provisioning_status   TEXT DEFAULT 'not_applicable'
    CHECK (vapi_provisioning_status IN (
      'not_applicable', 'pending', 'active', 'failed'
    ));
```

`not_applicable` = existing (test) property groups using the shared lease number. Set for all rows that exist at migration time.
`pending` / `active` / `failed` = lifecycle for new property groups being auto-provisioned.

No Squad columns. No per-group complaint assistant columns.

### 2.2 `lease_listings` table (new)

```sql
CREATE TABLE IF NOT EXISTS lease_listings (
  id                SERIAL PRIMARY KEY,
  uuid              UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id UUID NOT NULL REFERENCES properties_list(id),
  flat_uuid         UUID NOT NULL REFERENCES flats(uuid),
  flat_number       TEXT NOT NULL,
  title             TEXT,
  monthly_rent      NUMERIC NOT NULL,
  description       TEXT,
  available_from    DATE,
  photo_urls        TEXT[]  DEFAULT '{}',
  is_active         BOOLEAN DEFAULT true,
  custom_rules      JSONB   DEFAULT '{}',
  manager_id        UUID,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_ll_active ON lease_listings(is_active) WHERE is_active = true;
CREATE INDEX idx_ll_flat   ON lease_listings(flat_uuid);
CREATE INDEX idx_ll_pg     ON lease_listings(property_group_id);
```

`custom_rules` JSONB shape:
```json
{
  "max_occupants": null,
  "income_required": true,
  "pets_allowed": "yes",
  "vegetarian_only": false,
  "lease_term_months": 11,
  "custom_question": ""
}
```

### 2.3 `lease_leads` table (new)

```sql
CREATE TABLE IF NOT EXISTS lease_leads (
  id                    SERIAL PRIMARY KEY,
  uuid                  UUID DEFAULT gen_random_uuid() UNIQUE NOT NULL,
  property_group_id     UUID REFERENCES properties_list(id),
  listing_uuid          UUID REFERENCES lease_listings(uuid),
  interested_listing_ids UUID[] DEFAULT '{}',
  caller_name           TEXT NOT NULL,
  phone                 TEXT NOT NULL,
  email                 TEXT,
  bedrooms              INTEGER,
  budget_max            NUMERIC,
  move_in_timeline      TEXT,
  occupants             INTEGER,
  floor_preference      TEXT,
  qualification_status  TEXT NOT NULL DEFAULT 'unmatched'
    CHECK (qualification_status IN (
      'qualified','not_qualified','unmatched','contacted','toured','converted','lost'
    )),
  disqualifying_reason  TEXT,
  qualifying_answers    JSONB    DEFAULT '{}',
  notes                 TEXT,
  source                TEXT NOT NULL DEFAULT 'voice',
  call_id               TEXT,
  call_duration_seconds INTEGER,
  manager_notes         TEXT,
  created_at            TIMESTAMPTZ DEFAULT now(),
  updated_at            TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_leads_status  ON lease_leads(qualification_status);
CREATE INDEX idx_leads_listing ON lease_leads(listing_uuid);
CREATE INDEX idx_leads_pg      ON lease_leads(property_group_id);
CREATE INDEX idx_leads_created ON lease_leads(created_at DESC);
```

`property_group_id` is nullable here — unmatched calls from the shared lease assistant that found no listing will have null.

---

## 3. Backend Implementation

### Phase 1 — Extend `Verify_phone_number` Response

**File:** `backend/app/routes/flats.py`

Add `property_group_id` to the `POST /flats/verify-phone` response.

```python
# Existing verify-phone endpoint — add property_group_id to all returns

# After flat lookup:
property_group_id = str(flat["buildings"]["property_id"])

# Valid return:
return {
    "status": "valid",
    "result": "Tenant verified",
    "datetime": _now_ist(),
    "property_group_id": property_group_id,
}

# Vacant / invalid returns:
return {
    "status": "vacant",   # or "invalid"
    "result": "...",
    "datetime": _now_ist(),
    "property_group_id": None,
}
```

The complaint agent's system prompt instructs it to extract `property_group_id` from this response and pass it to all subsequent tools.

### Phase 2 — Refactor `vapi_agent_config.py`

**File:** `backend/app/services/vapi_agent_config.py`

Keep the existing `build_assistant_config()` and `build_tools()` as a legacy path (test group uses it). Add these new functions:

```
build_complaint_config(backend_url)
  → Standalone complaint agent (all property groups via Option B)
  → 6 tools: Verify_phone_number (extended), submit_complaint, check_availability,
             view_active_appointments, update_appointment, cancel_appointment
  → System prompt: instructs agent to extract + forward property_group_id

build_lease_config_shared(backend_url)
  → Shared lease agent for existing property groups
  → 3 tools: find_listing (no pg_id in URL), search_available_listings (no pg_id),
             submit_lease_lead
  → System prompt: no [Context] block; backend handles cross-group search

build_lease_config(backend_url, property_group_id, pg_name)
  → Per-group lease agent for new property groups
  → 3 tools: same tools but pg_id hardcoded in URLs
  → System prompt: includes [Context — Do Not Expose] block with property_group_id
```

#### 3.2.1 Complaint System Prompt (key additions)

```
[IMPORTANT — property_group_id]
The Verify_phone_number tool returns a property_group_id field.
After successful verification (status = "valid"), extract this value.
You MUST pass it as property_group_id in ALL subsequent tool calls:
  submit_complaint, check_availability, view_active_appointments,
  update_appointment, cancel_appointment.
Never reveal this value to the caller.
```

#### 3.2.2 Tool URL Differences

| Tool | Shared Lease Assistant | Per-Group Lease Assistant |
|------|----------------------|--------------------------|
| `find_listing` | `.../leasing/find-listing?query={{query}}` | `.../leasing/find-listing?property_group_id={PG_ID}&query={{query}}` |
| `search_available_listings` | `.../leasing/search?bedrooms={{bedrooms}}&budget_max={{budget_max}}` | `.../leasing/search?property_group_id={PG_ID}&bedrooms={{bedrooms}}&budget_max={{budget_max}}` |
| `submit_lease_lead` | `.../voice/lease-lead-webhook` | `.../voice/lease-lead-webhook` |

### Phase 3 — Leasing VAPI Endpoints

**New file:** `backend/app/routes/leasing.py`

`property_group_id` is optional on both VAPI tool endpoints. When absent, search spans all groups.

#### `GET /leasing/find-listing`

```python
@router.get("/find-listing")
async def find_listing(
    query: str = Query(...),
    property_group_id: Optional[str] = Query(None),
    db: Client = Depends(get_db),
):
    try:
        q = (
            db.table("lease_listings")
            .select("uuid, flat_number, title, monthly_rent, available_from, "
                    "custom_rules, flats!inner(bedrooms, floor_number, address)")
            .eq("is_active", True)
        )
        if property_group_id:
            q = q.eq("property_group_id", property_group_id)
        results = q.ilike("flats.address", f"%{query}%").limit(1).execute()
        if not results.data:
            results = q.ilike("flat_number", f"%{query}%").limit(1).execute()
        if not results.data:
            return {"found": False}
        listing = results.data[0]
        flat = listing.get("flats") or {}
        return {
            "found":          True,
            "listing_uuid":   listing["uuid"],
            "address":        flat.get("address"),
            "bedrooms":       flat.get("bedrooms"),
            "monthly_rent":   listing["monthly_rent"],
            "floor_number":   flat.get("floor_number"),
            "available_from": str(listing.get("available_from") or ""),
            "custom_rules":   json.dumps(listing.get("custom_rules") or {}),
        }
    except Exception:
        return {"found": False}
```

#### `GET /leasing/search`

Same pattern — `property_group_id` optional; if absent, all groups searched.

### Phase 4 — Lease Lead Webhook

**File:** `backend/app/routes/voice.py` — add `POST /voice/lease-lead-webhook`

`property_group_id` is resolved in priority order:

```python
# 1. If a specific listing was matched, pg_id comes from that listing
if listing_uuid := lead_data.get("listing_uuid"):
    row = db.table("lease_listings").select("property_group_id").eq("uuid", listing_uuid).maybe_single().execute()
    property_group_id = (row.data or {}).get("property_group_id")
else:
    # 2. For per-group assistants: look up by assistant_id saved in DB
    assistant_id = call.get("assistantId")
    pg_row = db.table("properties_list").select("id").eq("vapi_lease_assistant_id", assistant_id).maybe_single().execute()
    property_group_id = (pg_row.data or {}).get("id")
    # 3. If still None: shared assistant + unmatched call → pg_id stays null (acceptable)
```

### Phase 5 — Manager CRUD

**File:** `backend/app/routes/leasing.py` (continued)
**New file:** `backend/app/schemas/leasing.py`

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET`    | `/leasing/listings`         | Manager (RLS) | List listings for this PropertyGroup |
| `POST`   | `/leasing/listings`         | Manager (RLS) | Create new listing |
| `PATCH`  | `/leasing/listings/{uuid}`  | Manager (RLS) | Update listing |
| `DELETE` | `/leasing/listings/{uuid}`  | Manager (RLS) | Remove listing |
| `GET`    | `/leasing/leads`            | Manager (RLS) | List leads with filters |
| `PATCH`  | `/leasing/leads/{uuid}`     | Manager (RLS) | Update lead status / notes |
| `DELETE` | `/leasing/leads/{uuid}`     | Manager (RLS) | Delete lead |
| `GET`    | `/leasing/metrics`          | Manager (RLS) | Aggregate stats |
| `GET`    | `/leasing/export`           | Manager (RLS) | CSV download |

### Phase 6 — Provisioning Service (New Property Groups Only)

**New file:** `backend/app/services/vapi_provisioning.py`

Creates ONE lease assistant + ONE phone number. No Squad, no complaint assistant (that is global/shared).

```python
async def provision_vapi_for_property_group(
    property_group_id: str,
    pg_name: str,
    db: Client,
):
    """
    BackgroundTask triggered on new PropertyGroup creation.
    Provisions a dedicated lease VAPI assistant + phone number.
    Complaint calls are handled by the global shared complaint assistant.
    """
    client = AsyncVapi(token=settings.PRIVATE_VAPI_API)
    try:
        # 1. Create per-group lease assistant (pg_id hardcoded)
        lease_cfg = build_lease_config(BACKEND_URL, property_group_id, pg_name)
        lease = await client.assistants.create(**lease_cfg)

        # 2. Buy +91 phone number
        phone = await client.phone_numbers.create(fallback_destination=None)

        # 3. Link phone → lease assistant
        await client.phone_numbers.update(id=phone.id, assistant_id=lease.id)

        # 4. Save to DB
        db.table("properties_list").update({
            "vapi_lease_assistant_id":  lease.id,
            "vapi_phone_number_id":     phone.id,
            "vapi_phone_number":        phone.number,
            "vapi_provisioning_status": "active",
        }).eq("id", property_group_id).execute()

    except Exception:
        db.table("properties_list").update({
            "vapi_provisioning_status": "failed",
        }).eq("id", property_group_id).execute()
        raise
```

### Phase 7 — Wire Provisioning to PropertyGroup Creation

**File:** `backend/app/routes/property_groups.py`

On new PropertyGroup creation:
1. Set `vapi_provisioning_status = "pending"` in the insert
2. Add background task: `provision_vapi_for_property_group(pg_id, pg_name, db)`

SQL migration sets `vapi_provisioning_status = 'not_applicable'` for all existing rows.

Add retry endpoint:

```python
@router.post("/{property_id}/provision-voice", status_code=202)
async def retry_voice_provisioning(
    property_id: str,
    background_tasks: BackgroundTasks,
    db: Client = Depends(get_authenticated_db),
):
    pg = db.table("properties_list").select("id, name").eq("id", property_id).single().execute()
    db.table("properties_list").update({"vapi_provisioning_status": "pending"}).eq("id", property_id).execute()
    background_tasks.add_task(provision_vapi_for_property_group, pg.data["id"], pg.data["name"], db)
    return {"status": "provisioning_started"}
```

### Phase 8 — Register Leasing Router

**File:** `backend/app/main.py`

```python
from app.routes import leasing
app.include_router(leasing.router)
```

---

## 4. Frontend Implementation

### Phase 9 — `apiService.js` Additions

```js
getListings:       ()           => apiFetch('/leasing/listings'),
createListing:     (data)       => apiFetch('/leasing/listings', { method: 'POST', body: data }),
updateListing:     (uuid, data) => apiFetch(`/leasing/listings/${uuid}`, { method: 'PATCH', body: data }),
deleteListing:     (uuid)       => apiFetch(`/leasing/listings/${uuid}`, { method: 'DELETE' }),
getLeaseLeads:     (params)     => apiFetch(`/leasing/leads?${new URLSearchParams(params)}`),
updateLead:        (uuid, data) => apiFetch(`/leasing/leads/${uuid}`, { method: 'PATCH', body: data }),
deleteLead:        (uuid)       => apiFetch(`/leasing/leads/${uuid}`, { method: 'DELETE' }),
getLeasingMetrics: (params)     => apiFetch(`/leasing/metrics?${new URLSearchParams(params)}`),
exportLeads:       (params)     => apiFetch(`/leasing/export?${new URLSearchParams(params)}`),
```

### Phase 10 — `LeasingTab.jsx`

New file: `frontend/src/components/LeasingTab.jsx`

Layout:
```
┌─────────────────────────────────────────────────────────────────┐
│ Leasing                                    [Last 7 days ▼]      │
├─────────────┬─────────────┬──────────────┬──────────┬──────────┤
│ Total Calls │  Qualified  │ Not Qualified│ Qual Rate│Avg Duration│
│    142      │     98      │     30       │  69%     │  3m 12s   │
├─────────────────────────────────────────────────────────────────┤
│ Available Listings                              [+ Add Listing]  │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│ │  [photo] │  │  A-101   │  │  B-204   │                       │
│ │  2 BHK   │  │  3 BHK   │  │  1 BHK   │                       │
│ │ ₹15,000  │  │ ₹22,000  │  │ ₹10,000  │                       │
│ │  Active  │  │  Active  │  │ Inactive  │                       │
│ │ [Edit][×]│  │ [Edit][×]│  │ [Edit][×] │                       │
│ └──────────┘  └──────────┘  └──────────┘                       │
├─────────────────────────────────────────────────────────────────┤
│ Leads    [All Listings ▼] [All Status ▼]        [Export CSV]    │
│ Name  │ Phone      │ Budget  │ Beds │ Move-in │ Status │ Actions│
└─────────────────────────────────────────────────────────────────┘
```

### Phase 11 — `AddListingModal.jsx`

New file: `frontend/src/components/AddListingModal.jsx`

Fields: Unit (vacant flats dropdown), Monthly Rent, Available From, Description, Status toggle.
Collapsible qualifying rules section: Max occupants, Income required, Pets allowed, Vegetarian-only, Lease term, Custom question.

### Phase 12 — `LeadDetailModal.jsx`

New file: `frontend/src/components/LeadDetailModal.jsx`

Panels: Contact info, Preferences, Qualifying answers (JSONB), Qualification status, Call info, Manager notes (editable), Status pipeline dropdown.

Status rule: `qualified` / `not_qualified` / `unmatched` are read-only (set by voice); dropdown shows `contacted` → `toured` → `converted` / `lost`.

### Phase 13 — Sidebar + App.jsx Routing

`Sidebar.jsx`: Add `{ id: 'leasing', icon: KeyRound, label: 'Leasing' }` after `voice-stats`.
`App.jsx`: Add `case 'leasing': return <LeasingTab />;`

---

## 5. One-Time Manual Setup (Before Voice Testing)

These steps are done once by the developer. Not part of the automated provisioning flow.

### 5.1 Complaint Agent

1. Run `build_complaint_config(BACKEND_URL)` to generate the assistant payload
2. Create assistant in VAPI dashboard → copy assistant ID
3. Set `VAPI_COMPLAINT_ASSISTANT_ID=<id>` in `.env`
4. In VAPI, assign or purchase a phone number, link it to the complaint assistant
5. Set `VAPI_COMPLAINT_NUMBER_ID=<id>` in `.env`

### 5.2 Shared Lease Agent

1. User provides their Twilio number
2. Import the Twilio number into VAPI (Twilio credentials required in VAPI)
3. Run `build_lease_config_shared(BACKEND_URL)` to generate the assistant payload
4. Create assistant in VAPI dashboard → copy assistant ID
5. Set `VAPI_SHARED_LEASE_ASSISTANT_ID=<id>` and `VAPI_SHARED_LEASE_NUMBER_ID=<id>` in `.env`
6. Link the imported Twilio number to the shared lease assistant in VAPI

---

## 6. Test Plan

### Curl Test Scripts (Backend)

- `backend/scripts/test_complaint_endpoints.sh` — verify-phone (valid/invalid/vacant), availability, appointments, voice webhook
- `backend/scripts/test_leasing_endpoints.sh` — find-listing (with/without pg_id), search (with/without pg_id), lease lead webhook (qualified/not_qualified/unmatched)

### Manual Voice Tests — Complaint Agent

| # | Scenario | Expected |
|---|----------|----------|
| C1 | Valid tenant calls → files complaint | Complaint + appointment created; property_group_id in complaint record |
| C2 | Wrong phone for flat | "Doesn't match our records" → call ends immediately |
| C3 | Vacant flat | "No registered tenant" → call ends |
| C4 | Emergency situation | Appointment created; no troubleshooting advice given |
| C5 | View / reschedule / cancel appointment | Correct flat data; DB updated |
| C6 | Two different tenants from different property groups call | Each complaint has the correct property_group_id |

### Manual Voice Tests — Shared Lease Agent (Existing Groups)

| # | Scenario | Expected |
|---|----------|----------|
| L1 | Caller knows specific address | find_listing searches all groups; finds listing |
| L2 | Caller browsing | search returns listings from all groups |
| L3 | Qualified lead | Lead created; property_group_id from listing |
| L4 | Unmatched (no listings match) | Lead created; property_group_id = null |
| L5 | Disqualified → alternatives offered | Cross-group search across all groups |
| L6 | Verify_phone_number is never called | VAPI call log shows no verify-phone request |

### Manual Voice Tests — Per-Group Lease Agent (New Property Group)

| # | Scenario | Expected |
|---|----------|----------|
| L7 | Call dedicated number | find_listing/search scoped to this group only |
| L8 | Qualified lead | property_group_id = the group's ID |
| L9 | No cross-group leakage | Listings from other groups not returned |

### Regression Tests

| # | Scenario | Expected |
|---|----------|----------|
| R1 | Calling complaint number → no leasing flow | No leasing tools called |
| R2 | Calling lease number → no complaint flow | Verify_phone_number never called |
| R3 | New PropertyGroup created | vapi_provisioning_status = active; phone number saved to DB |
| R4 | Existing PropertyGroups | vapi_provisioning_status = not_applicable; no auto-provisioning attempted |

---

## 7. Files Summary

### New Files (9)

| File | Purpose |
|------|---------|
| `backend/migrations/0XX_voice_agents.sql` | DB: lease columns on property_groups, lease_listings, lease_leads |
| `backend/app/services/vapi_provisioning.py` | Provision lease assistant + number for new property groups |
| `backend/app/routes/leasing.py` | VAPI leasing tool endpoints + manager CRUD |
| `backend/app/schemas/leasing.py` | Pydantic V2 models for listings, leads, metrics |
| `backend/scripts/test_complaint_endpoints.sh` | Curl tests for complaint/voice endpoints |
| `backend/scripts/test_leasing_endpoints.sh` | Curl tests for leasing endpoints |
| `frontend/src/components/LeasingTab.jsx` | Leasing dashboard: metrics + listings + leads |
| `frontend/src/components/AddListingModal.jsx` | Create/edit listing modal with qualifying rules |
| `frontend/src/components/LeadDetailModal.jsx` | Lead detail view, status pipeline, manager notes |

### Modified Files (8)

| File | Change |
|------|--------|
| `backend/app/services/vapi_agent_config.py` | Add complaint, shared-lease, per-group-lease configs; keep legacy |
| `backend/app/routes/flats.py` | `Verify_phone_number` returns `property_group_id` |
| `backend/app/routes/voice.py` | Add `POST /voice/lease-lead-webhook`; complaint webhook uses pg_id |
| `backend/app/routes/property_groups.py` | BackgroundTask provisioning on creation; retry endpoint |
| `backend/app/main.py` | Register leasing router |
| `frontend/src/services/apiService.js` | Add leasing API methods |
| `frontend/src/components/Sidebar.jsx` | Add Leasing nav item (KeyRound icon) |
| `frontend/src/App.jsx` | Add `case 'leasing': return <LeasingTab />` |

---

## 8. Implementation Order

| Phase | Task | Effort |
|-------|------|--------|
| 1 | DB migration | Low |
| 2 | Extend `Verify_phone_number` to return `property_group_id` | Low |
| 3 | Refactor `vapi_agent_config.py` (complaint + shared-lease + per-group-lease) | Medium |
| 4 | Update complaint webhook to store/use `property_group_id` | Low |
| 5 | Leasing VAPI endpoints (`find-listing`, `search`) with optional `property_group_id` | Low |
| 6 | Lease lead webhook (`property_group_id` from listing) | Medium |
| 7 | Manager CRUD (`/leasing/listings`, `/leasing/leads`, metrics, export) + schemas | Medium |
| 8 | Register leasing router in `main.py` | Trivial |
| 9 | Provisioning service (new groups only) | Medium |
| 10 | Wire provisioning to PropertyGroup creation + retry endpoint | Low |
| 11 | One-time manual agent setup (complaint + shared lease) | Low |
| 12 | `apiService.js` leasing methods | Low |
| 13 | `LeasingTab.jsx` | Medium |
| 14 | `AddListingModal.jsx` | Medium |
| 15 | `LeadDetailModal.jsx` | Medium |
| 16 | Sidebar + App.jsx routing | Trivial |
| 17 | Manual voice testing (all scenarios above) | High |

**Estimated total: 7–9 days**
