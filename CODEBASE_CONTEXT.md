# Tenant Management MVP — Full Codebase Context

> **Purpose:** Single source of truth for every Claude Code session. Read this before touching any file. It covers product purpose, data model, every backend route, every frontend component, all integrations, and key architectural rules.

---

## 1. Product Overview

**Tenant Management MVP** is an AI-powered property and tenant management SaaS for landlords / property managers. Core capabilities:

- Manage a hierarchy: **PropertyGroup → Building → Flat → Tenant**
- Log and track maintenance **Complaints** with **Appointments**
- Accept **voice complaints** from tenants via a VAPI.ai phone agent
- AI **chatbot assistant** (OpenAI gpt-4o-mini) for natural-language management
- Send **SMS/email notifications** on appointment events
- **Rent tracking** per flat with payment schedules (currency: **Canadian dollars, CAD**)
- **Bulk CSV import** for properties and tenants
- **Stripe subscription** gate — managers must have an active subscription
- Per-building **feature flags** (rent management, voice, SMS reminders, etc.)
- **Onboarding tour** (react-joyride) with checklist tracked in Supabase
- **Lease agent auto-provisioning** — one Twilio number + one VAPI assistant provisioned per manager account on first property group creation; subsequent groups share the same number

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI (Python 3.13+), Uvicorn |
| Database | Supabase (PostgreSQL) via `supabase-py` SDK — **not** SQLAlchemy |
| Auth | Supabase Auth (Google OAuth PKCE flow) + JWT validation in FastAPI |
| Frontend | React 18 + Vite + TailwindCSS + Framer Motion + Lucide React |
| AI Chatbot | OpenAI `gpt-4o-mini` (tool calling) |
| AI Extraction | Groq `llama-3.3-70b-versatile` (complaint parsing from transcripts) |
| Voice | VAPI.ai (inbound/outbound phone agent) |
| SMS | Twilio |
| Email | SendGrid |
| Payments | Stripe (subscriptions + webhooks) |
| Charts | Recharts |
| Animations | Framer Motion |
| Date parsing | date-fns |

---

## 3. Repository Structure

```
Tenant_management_MVP/
├── backend/
│   ├── app/
│   │   ├── ai/                     # AI modules
│   │   │   ├── chatbot.py          # OpenAI tool-calling chatbot
│   │   │   ├── extractor.py        # Groq complaint extraction
│   │   │   └── validator.py        # Complaint completeness check
│   │   ├── core/
│   │   │   ├── constants.py        # ALLOWED_CATEGORIES, ComplaintStatus enum
│   │   │   └── features.py         # Feature flag registry
│   │   ├── db/
│   │   │   ├── session.py          # Supabase anon + service clients
│   │   │   └── models.py           # Legacy SQLAlchemy models (not used in routes)
│   │   ├── dependencies/
│   │   │   ├── auth.py             # get_current_user — JWT validation
│   │   │   ├── authenticated_db.py # get_authenticated_db — RLS-enforced client
│   │   │   ├── subscription.py     # require_active_subscription gate
│   │   │   └── features.py         # Feature flag dependency
│   │   ├── integrations/
│   │   │   ├── twilio_client.py    # SMS
│   │   │   └── email_client.py     # SendGrid email
│   │   ├── routes/                 # 18 route files (see Section 5)
│   │   ├── schemas/                # Pydantic V2 models
│   │   │   ├── complaint.py
│   │   │   ├── tenant.py
│   │   │   ├── flat.py
│   │   │   ├── appointment.py
│   │   │   └── workflow.py
│   │   ├── services/
│   │   │   ├── notifications.py    # SMS/email orchestration
│   │   │   ├── feature_service.py  # Feature flag logic
│   │   │   └── vapi_agent_config.py
│   │   ├── config.py               # Settings — all env vars
│   │   └── main.py                 # FastAPI app, CORS, router registration
│   ├── requirements.txt
│   ├── schema.sql                  # Supabase schema reference
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/             # ~67 JSX files (see Section 7)
│   │   ├── context/
│   │   │   ├── AuthContext.jsx     # Supabase session + ensureManagerProfile
│   │   │   ├── ThemeContext.jsx    # Dark/light mode
│   │   │   └── OnboardingContext.jsx
│   │   ├── services/
│   │   │   └── apiService.js       # ALL HTTP calls — authFetch wrapper
│   │   ├── lib/
│   │   │   ├── supabase.js         # Supabase client (PKCE)
│   │   │   └── cn.js               # tailwind-merge + clsx
│   │   ├── constants/
│   │   │   └── status.js           # Status enums + Tailwind color configs
│   │   ├── config/
│   │   │   └── onboardingTours.js  # react-joyride tour definitions
│   │   ├── App.jsx                 # Root — AuthGate, Dashboard, polling
│   │   └── main.jsx                # ReactDOM.render entry
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── package.json
│   └── .env.example
│
├── CLAUDE.md                       # Claude Code instructions (this file is referenced there)
└── CODEBASE_CONTEXT.md             # This file
```

---

## 4. Database Schema

### Data Hierarchy
```
PropertyGroup (properties_list)
  └── Building (buildings)
        └── Flat (flats)
              └── Tenant (tenants)
```

### Tables

#### `manager_profiles`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID | FK → auth.users |
| name | text | |
| phone | text | |
| tour_completed | boolean | Onboarding state |
| created_at | timestamptz | |

#### `properties_list` (PropertyGroups)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | |
| description, address, image_url | text | `address` is legacy; new code writes structured fields |
| street_address, city, state | text | Structured address (migration 022); required for new creates |
| country | text | Default 'Canada' |
| manager_id | UUID | FK → auth.users (RLS key) |
| vapi_lease_assistant_id | text | VAPI assistant ID provisioned for this group |
| vapi_phone_number_id | text | VAPI phone number ID |
| vapi_phone_number | text | E.164 phone number for this group's lease agent |
| vapi_provisioning_status | text | not_applicable / pending / active / failed |

#### `buildings`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name, description, address, image_url | text | `address` is legacy |
| street_address, address_line, city, state | text | Structured address (migration 022); city/state/country required for new creates |
| country | text | Default 'Canada'; auto-filled from parent property group on frontend |
| property_type_id | UUID | FK → property_types |
| property_id | UUID | FK → properties_list |
| manager_id | UUID | RLS key |

#### `property_types`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | text | Residential / Commercial / Mixed-use |
| icon_type | text | house / shop / apartment |

#### `flats`
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | New primary key |
| id | int | Legacy PK |
| flat_number | text UNIQUE | Normalized to UPPER |
| address, floor_number | text/int | `address` is legacy |
| street_address, address_line, city, state | text | Structured address (migration 022); auto-filled from parent building on frontend |
| country | text | Default 'Canada' |
| bedrooms, bathrooms | int | |
| living_rooms | int | Default 1 (migration 028) |
| kitchen | int | Default 1 (migration 028) |
| quebec_size | text | Computed server-side: `(bedrooms + living_rooms + kitchen + max(0, bathrooms-1))½` (migration 028) |
| occupied | boolean | Derived from tenant_uuid presence |
| is_listed | boolean | Default false; true when an active lease_listing exists for this flat (migration 026); prevents duplicate listings |
| image_url | text | Supabase Storage URL |
| building_id | UUID | FK → buildings |
| property_type_id | UUID | FK → property_types |
| tenant_uuid | UUID | FK → tenants (nullable) |
| manager_id | UUID | RLS key |

#### `tenants`
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| id | int | Legacy |
| name, phone, email | text | |
| flat_uuid | UUID | FK → flats |
| lease_start_date, lease_end_date | date | ISO strings |
| rent_status | text | On-time / Upcoming / Overdue / At Risk |
| payment_schedule | text | monthly / quarterly / custom |
| manager_notes | text | |
| document_urls | text[] | Array of file URLs |
| manager_id | UUID | RLS key |

#### `complaints`
| Column | Type | Notes |
|---|---|---|
| uuid | UUID PK | |
| id | int | Legacy |
| tenant_uuid | UUID | FK → tenants (nullable) |
| flat_uuid | UUID | FK → flats |
| flat_number | text | Denormalized for VAPI |
| category | text | CHECK: one of ALLOWED_CATEGORIES |
| priority | text | low / medium / high |
| description | text | |
| status | text | CHECK: pending / in-progress / resolved |
| source | text | AI_AGENT / voice / web |
| manager_id | UUID | RLS key |

#### `appointments`
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| uuid | UUID | |
| complaint_uuid | UUID | FK → complaints |
| flat_number | text | Denormalized for VAPI |
| flat_uuid | UUID | FK → flats |
| appointment_date | timestamptz | Format: `YYYY-MM-DDTHH:MM:SS` |
| status | text | scheduled / attended / cancelled / completed |
| type | text | `callback` (manager calls tenant back) / `visit` (on-site visit); default `callback` |
| tenant_phone | text | E.164 phone to call back; set by complaint agent on callback appointments |
| notes | text | |
| manager_id | UUID | FK → auth.users; RLS key (migration 021) |

#### `call_logs`
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| call_id | text UNIQUE | Vapi call ID |
| phone_number | text | Caller E.164 |
| transcript | text | Raw call transcript |
| raw_event_type | text | Vapi event type |
| complaint_status | text | created / incomplete / failed |
| complaint_uuid | UUID | FK → complaints (nullable) |
| manager_id | UUID | RLS key |

#### `rents`
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| flat_uuid | UUID | FK → flats |
| monthly_rent | decimal | |
| effective_from | date | |
| is_active | boolean | Only one active per flat |
| manager_id | UUID | RLS key |

#### `lease_listings`
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| uuid | UUID UNIQUE | |
| property_group_id | UUID | FK → properties_list |
| flat_uuid | UUID | FK → flats |
| flat_number | text | Denormalized |
| title | text | |
| monthly_rent | numeric | |
| description | text | |
| available_from | date | |
| photo_urls | text[] | |
| is_active | boolean | |
| custom_rules | JSONB | `{max_occupants, income_required, pets_allowed, vegetarian_only, lease_term_months, custom_question}` |
| bedrooms | int | Denormalized from flat at listing creation (migration 028) |
| bathrooms | int | Denormalized from flat at listing creation (migration 028) |
| living_rooms | int | Denormalized from flat at listing creation (migration 028) |
| kitchen | int | Denormalized from flat at listing creation (migration 028) |
| quebec_size | text | Denormalized from flat at listing creation; used for direct filtering by lease agent (migration 028) |
| manager_id | UUID | |

#### `lease_leads`
| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| uuid | UUID UNIQUE | |
| property_group_id | UUID | FK → properties_list |
| listing_uuid | UUID | FK → lease_listings (nullable) — primary matched listing |
| interested_listing_ids | UUID[] | All listings caller expressed interest in (including primary) |
| caller_name | text | |
| phone | text | |
| email | text | |
| bedrooms, occupants | int | |
| budget_max | numeric | |
| move_in_timeline, floor_preference | text | |
| qualification_status | text | qualified / not_qualified / unmatched / contacted / toured / converted / lost |
| disqualifying_reason | text | |
| qualifying_answers | JSONB | Custom Q&A from agent |
| notes | text | Agent-generated summary |
| manager_notes | text | Manager editable |
| source | text | voice (default) |
| call_id | text | VAPI call ID |
| call_duration_seconds | int | |

#### `manager_vapi_config`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| manager_id | UUID UNIQUE | FK → auth.users |
| vapi_lease_assistant_id | text | Per-manager VAPI assistant ID |
| vapi_phone_number_id | text | VAPI's internal ID for the claimed number |
| vapi_phone_number | text | E.164 phone number for this manager's lease line |
| vapi_provisioning_status | text | pending / active / failed / not_set_up |
| pool_row_id | UUID | FK → twilio_number_pool |
| created_at | timestamptz | |
| updated_at | timestamptz | |

RLS: managers can read only their own row (`manager_id = auth.uid()`). All writes use service role.

#### `twilio_number_pool`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| phone_number | text UNIQUE | E.164 number bought in Twilio console |
| vapi_phone_number_id | text UNIQUE | VAPI's internal ID for this number |
| status | text | available / assigned |
| assigned_manager_id | UUID | FK → auth.users (nullable) — replaces `assigned_property_group_id` |
| assigned_at | timestamptz | When the number was claimed |
| notes | text | Optional label |

RLS: service-role only. Managers see their phone number via `manager_vapi_config.vapi_phone_number`.

Unique index: `twilio_number_pool_one_per_manager ON (assigned_manager_id) WHERE assigned_manager_id IS NOT NULL` — enforces one number per manager at the DB level.

Admin script to add numbers: `python backend/scripts/add_twilio_number_to_vapi.py <E.164>`

**Deploy/update scripts** (`backend/scripts/`):
- `update_shared_agents.py` — push latest config to complaint agent + shared lease agent
- `update_lease_agents.py` — push latest `vapi_agent_config.py` to **all active per-manager lease assistants** (iterates `manager_vapi_config` rows); fetches each manager's name from `manager_profiles` and passes to `build_lease_config`; uses direct **HTTP PATCH** to `api.vapi.ai/assistant/{id}` (not the VAPI SDK — SDK silently drops `firstMessageMode` and other camelCase fields); always uses hardcoded production URL
- `reprovision_existing_groups.py` — provision new per-manager agents for property groups that don't have one yet (status != active)

#### `subscriptions`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| manager_id | UUID | FK → auth.users |
| stripe_customer_id | text | |
| stripe_subscription_id | text | |
| status | text | trialing / active / past_due / cancelled / expired |
| current_period_start/end | date | |
| trial_ends_at | date | |

#### `stripe_events`
| Column | Type | Notes |
|---|---|---|
| event_id | text UNIQUE | Stripe event ID — idempotency key |
| event_type | text | |

#### `property_features`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| building_id | UUID | FK → buildings |
| feature_name | text | Feature enum value |
| is_enabled | boolean | |
| manager_id | UUID | RLS key |

#### `notifications` (in-app)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| manager_id | UUID | FK → auth.users |
| title | text | Short notification title |
| body | text | Full notification message |
| type | text | `callback` / `lead` / general |
| entity_id | text | UUID of related entity (appointment uuid or lead uuid) |
| is_read | boolean | Read status |
| created_at | timestamptz | |

Inserted by: voice webhook on new callback appointment; lease-lead webhooks on qualified lead. Read by `TopBar.jsx` / `NotificationPanel.jsx`.

#### `manager_notifications`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| manager_id | UUID | FK → auth.users |
| appointment_sms_enabled | boolean | |
| appointment_email_enabled | boolean | |

---

## 5. Backend — All Routes

**Global rule:** No `/api` prefix on any route. Every route is registered directly in `main.py`.

### Authentication Pattern
```python
# Standard authenticated route
db: Client = Depends(get_authenticated_db),      # RLS-enforced Supabase
user: dict = Depends(get_current_user),          # JWT payload
_: None = Depends(require_active_subscription),  # Stripe gate
```

---

### `/complaints` — `routes/complaints.py`
| Method | Path | Description |
|---|---|---|
| POST | `/complaints` | Create complaint; auto-links flat/tenant; optionally creates appointment |
| GET | `/complaints` | List all complaints with joined appointment data (newest first) |
| GET | `/complaints/{id}` | Single complaint |
| PATCH | `/complaints/{id}` | Update fields |
| DELETE | `/complaints/{id}` | Delete complaint |

---

### `/tenants` — `routes/tenants.py`
| Method | Path | Description |
|---|---|---|
| GET | `/tenants/by-flat/{flat_no}` | **VAPI endpoint** — returns `{exists, flat_no, tenant_name, tenant_phone, datetime}` |
| GET | `/tenants/by-flat-query?flat_no=` | Query param version of above |
| POST | `/tenants` | Create tenant with flat assignment |
| GET | `/tenants` | List all tenants (optional `?flat_uuid=`) |
| GET | `/tenants/{uuid}` | Single tenant with computed lease fields |
| PATCH | `/tenants/{uuid}` | Update tenant info — accepts `name`, `phone`, `email`, lease dates, rent_status, etc.; guards: name cannot be blank, phone uniqueness enforced application-side |
| DELETE | `/tenants/{uuid}` | Delete tenant |

Computed fields on GET (from `TenantResponse` schema):
- `tenancy_duration_months`
- `lease_duration_months`
- `remaining_time_on_lease_days`
- `lease_status` (active / expired / expiring_soon)

---

### `/flats` — `routes/flats.py`
| Method | Path | Description |
|---|---|---|
| POST | `/flats/verify-phone` | **VAPI endpoint** — verifies caller phone matches tenant; returns `{status: valid/invalid/vacant}` |
| POST | `/flats/identify-caller` | VAPI — identify caller by phone number |
| POST | `/flats` | Create flat |
| GET | `/flats` | List flats (optional `?vacant=true`, `?not_listed=true`); when `vacant=true` uses PostgREST nested join to include `building_name` (from `buildings.name`) and `property_name` (from `properties_list.name`) in each row; `not_listed=true` (requires `vacant=true`) further filters to `is_listed=false` flats only — used by AddListingModal dropdown; non-vacant path returns raw flat rows |
| GET | `/flats/{uuid}/details` | Single flat with tenant details |
| GET | `/flats/{flat_number}` | Flat by flat number |
| PATCH | `/flats/{flat_uuid}` | Update flat + tenant action (ADD_TENANT / REMOVE_TENANT / UPDATE_TENANT); ADD_TENANT nullifies leads that referenced the listing, **deletes** the `lease_listings` row, sets `is_listed=false`, and auto-sets rent from listing's `monthly_rent` |
| DELETE | `/flats/bulk` | Bulk delete flats by UUID list; body `{uuids: [...]}`; returns `{deleted, errors}` |
| DELETE | `/flats/{flat_uuid}` | Delete flat (cascade: lease_listings → rents → tenant → flat) |
| PATCH | `/flats/{flat_uuid}/assign-tenant` | Assign existing tenant to flat (bidirectional link); fetches active listing's `monthly_rent` first, nullifies any leads that referenced it, **deletes** the `lease_listings` row, sets `is_listed=false` on flat, then if listing had a rent value auto-inserts an active rent record for the flat — no-op if no listing exists |
| PATCH | `/flats/{flat_uuid}/unassign-tenant` | Remove tenant from flat (bidirectional unlink); does NOT reactivate listings — manager must manually re-enable |

**VAPI rules:** Always returns HTTP 200. Inputs normalized with `.strip().upper()`.

**RLS / flat creation:** `POST /flats` uses `svc` (service-role client) for the actual `flats` INSERT — the Supabase RLS INSERT policy rejects the anon client for some manager accounts. All ownership/subscription checks run first with the authenticated `db` client.

**Error messages:** `clean_db_error(e)` in `app/core/db_errors.py` maps PostgreSQL error codes to plain English — `23514` → invalid field value, `23505` → already exists, `23503` → FK violation (with lease_listing hint), `23502` → missing required field, `42501` → permission denied. Used by all DELETE routes and `import_routes.py`. Raw Supabase exception dicts never reach the frontend.

---

### `/appointments` — `routes/appointments.py`
| Method | Path | Description |
|---|---|---|
| GET | `/appointments/view?flat_number=` | **VAPI tool** — returns all appointments for flat (no date/status filter) |
| PATCH | `/appointments/update?flat_number=&id=&new_appointment_date=` | **VAPI tool** — reschedule |
| PATCH | `/appointments/cancel?flat_number=&id=` | **VAPI tool** — cancel (idempotent) |
| GET | `/appointments/availability?appointment_date=` | **VAPI tool** — checks manager availability using 1-hour slot model; always HTTP 200; returns `{status: available\|unavailable}`; uses service DB; fails safe to `unavailable` on any error |
| POST | `/appointments` | Create appointment |
| GET | `/appointments` | List all (optional filters: `start_date`, `end_date`, `flat_number`) |
| GET | `/appointments/{id}` | Single appointment |
| PATCH | `/appointments/{id}` | Update |
| DELETE | `/appointments/{id}` | Soft-delete via status change |

**Availability slot model:** An appointment occupies exactly 1 hour. A requested slot T is `unavailable` if any existing `scheduled` appointment A satisfies `A - 1hr < T < A + 1hr`. Back-to-back slots (e.g. 10:00 and 11:00) are both available.

---

### `/buildings` — `routes/buildings.py`
| Method | Path | Description |
|---|---|---|
| POST | `/buildings` | Create building |
| GET | `/buildings` | List all with unit counts aggregated from flats |
| GET | `/buildings/{id}` | Single building; unit list response includes `building_street_address` field on each flat (joined from parent building) for frontend auto-fill |
| PATCH | `/buildings/{id}` | Update |
| DELETE | `/buildings/bulk` | Bulk delete buildings; body `{ids: [...]}`; cascade: lease_listings → rents → tenants → flats → buildings |
| DELETE | `/buildings/{id}` | Delete building (cascade: lease_listings → rents → tenants → flats → building) |

---

### `/property-groups` — `routes/property_groups.py`
| Method | Path | Description |
|---|---|---|
| GET | `/property-groups` | List all property groups |
| POST | `/property-groups` | Create property group; on first group, inserts `manager_vapi_config` row with `pending` status and triggers `provision_vapi_for_manager` as BackgroundTask; subsequent groups skip provisioning |
| GET | `/property-groups/users/me/vapi-config` | Returns `{vapi_provisioning_status, vapi_phone_number}` from `manager_vapi_config` for the current manager |
| POST | `/property-groups/users/me/provision-voice` | Retry VAPI lease provisioning for the manager account (upserts `pending` status, re-runs background task) |
| PATCH | `/property-groups/{id}` | Update property group fields (name, description, street_address, city, state, country, image_url, property_type_id) |
| GET | `/property-groups/{id}/buildings` | Buildings with unit counts for a property group |
| DELETE | `/property-groups/bulk` | Bulk delete property groups; body `{ids: [...]}`; `?force=true` required to proceed when tenants exist (otherwise 409 `tenant_block`); full cascade: lease_leads nullify → lease_listings → rents → complaints → appointments → call_logs → tenants → flats → buildings → property group; each step logs `[CASCADE]` to stdout |
| DELETE | `/property-groups/{id}` | Cascade-delete all buildings, flats, rents, tenants, lease_listings within the group; `?force=true` required when tenants exist (otherwise 409 `{detail: "tenant_block", tenant_count: N}`); same cascade order as bulk; each step logs `[CASCADE]` to stdout |

---

### `/properties` — `routes/properties.py`
| Method | Path | Description |
|---|---|---|
| GET | `/properties` | Returns flats mapped as properties (name, address, bedrooms, bathrooms, image_url, occupied) |

`PropertyResponse.floor_number` is `Optional[int] = None` — some flats have NULL floor_number in the DB; using `int` causes a `ResponseValidationError` 500. The dict builder passes `flat.get("floor_number")` (no fallback) so null flows through cleanly.

---

### `/property-types` — `routes/property_types.py`
| Method | Path | Description |
|---|---|---|
| GET | `/property-types` | List property types (Residential, Commercial, Mixed-use) |

---

### `/rents` — `routes/rents.py`
| Method | Path | Description |
|---|---|---|
| POST | `/rents/set` | Set rent for flat (deactivates previous, activates new) |
| GET | `/rents/summary` | All tenants with active rent, flat info, status counts |
| PATCH | `/tenants/{uuid}/rent-status` | Update tenant rent status |

---

### `/call_logs` — `routes/call_logs.py`
| Method | Path | Description |
|---|---|---|
| GET | `/call_logs` | List call logs (optional filters: phone, flat_number, complaint_status) |
| GET | `/call_logs/{id}` | Single call log |

---

### `/chat` — `routes/chat.py`
| Method | Path | Description |
|---|---|---|
| POST | `/chat` | Accept conversation history `{messages: [...]}`, return `{reply, refresh_needed}` |

---

### `/voice` — `routes/voice.py`
| Method | Path | Description |
|---|---|---|
| POST | `/voice/webhook` | Vapi webhook — processes call events, creates CallLog, optionally creates Complaint + Appointment + Notification |
| POST | `/voice/lease-lead-webhook` | *Deprecated* — function-tool webhook for `submit_lease_lead` |
| POST | `/voice/lease-lead-direct` | **Primary** apiRequest endpoint for `submit_lease_lead` (query params: `call_id`, `phone`) |
| POST | `/voice/lease-eoc-webhook` | Lease EOC fallback — creates partial unmatched lead if no lead was submitted during call |
| GET | `/voice/call-status` | Returns `{last_call_ended_at}` for frontend polling |
| GET | `/voice/agent-info` | Returns `{complaint_phone_number}` — authenticated + subscription gate |
| POST | `/voice/call/outbound` | Initiate outbound call — body `{customer_number, agent, first_message?}` |

**Complaint webhook behavior (`POST /voice/webhook`):**
- Always returns HTTP 200 (keeps Vapi session alive)
- Filters on final event types: `tool-calls`, `end-of-call-report`
- Creates CallLog always; creates Complaint only if user confirmed via `submit_complaint` tool call
- **Callback scheduling (post-migration 020):** on complaint creation, inserts an `appointments` row with `type="callback"` and `tenant_phone=caller_phone` — agent books a manager callback slot, not an on-site visit
- Inserts a `notifications` row (`type="callback"`) for the manager when a callback appointment is created
- Resolves `manager_id` from caller phone → tenant → flat → building → properties_list chain
- Uses `get_service_db` (bypasses RLS — call arrives without user JWT)

**Lease lead webhooks:**

`POST /voice/lease-lead-direct` (**primary path** — apiRequest version)
- VAPI posts lead fields as flat JSON body; `call_id`, `phone`, and `manager_id` come as query params via VAPI template variables
- Resolves `listing_uuid` → `lease_listings` to get `property_group_id` + `manager_id`; UUID validated with regex
- **Fallback:** if `listing_uuid` is absent or unmatched (unmatched calls), `manager_id` query param is used directly — ensures unmatched leads are always stored with a non-NULL `manager_id` and remain visible in `GET /leasing/leads`
- Inserts into `lease_leads`; creates `notifications` row for qualified leads; updates `_last_call_ended_at`
- Always returns HTTP 200

`POST /voice/lease-lead-webhook` (**deprecated** — function-tool webhook version; logs deprecation warning)
- Original webhook-style endpoint; still processes `submit_lease_lead` function tool calls
- Same resolution logic (3-path fallback: listing_uuid → assistant_id → phone_number_id)
- Validates `listing_uuid` against UUID regex; validates each entry in `interested_listing_ids`

`POST /voice/lease-eoc-webhook`
- Fallback for the lease agent's end-of-call-report
- If `submit_lease_lead` was never called, creates a partial `unmatched` lead with transcript excerpt
- For tool-call events routed here, returns neutral tool result to prevent VAPI from marking call as failed
- Updates `_last_call_ended_at`

Common to all lease webhooks:
- `interested_listing_ids` (UUID array) validated against UUID regex before insert; agent captures all listing UUIDs the caller showed interest in
- `property_group_id` resolution path logged as `[pg resolution] path=<path> property_group_id=<uuid>`
- Always return HTTP 200

**Outbound call:** `POST /voice/call/outbound`
- Body: `{customer_number, agent, first_message?}` — `agent` is `"complaint"` (default) or `"lease"`
- `complaint` → uses `VAPI_COMPLAINT_ASSISTANT_ID` + `VAPI_COMPLAINT_NUMBER_ID` (complaint agent Alex on `+14382314283`)
- `lease` → looks up `manager_vapi_config` for this manager's `vapi_lease_assistant_id` + `vapi_phone_number_id`; raises HTTP 500 if no active config found
- Outbound phone number default in frontend: `+1` (Canadian); accepts any E.164 number
- Wrapped in `asyncio.to_thread` to avoid blocking the event loop
- Returns `{call_id, status, agent}`; raises HTTP 504 on `httpx.ReadTimeout`

---

### `/notifications` — `routes/notifications.py`
| Method | Path | Description |
|---|---|---|
| POST | `/notifications/test-sms` | Send test SMS |
| POST | `/notifications/test-email` | Send test email |
| GET | `/notifications/preferences` | Notification settings per building |

---

### `/leasing` — `routes/leasing.py`

#### VAPI Tool Endpoints (no auth, service DB, always HTTP 200)
| Method | Path | Description |
|---|---|---|
| GET | `/leasing/find-units?query=&manager_id=` | **New** — query-first unit lookup; searches flat_number, title, address, building name, and property group name; returns `{found, count, units: [{listing_uuid, flat_number, building_name, property_name, address, bedrooms, bathrooms, floor_number, monthly_rent, available_from}]}` — up to 5 matches; used by the new lease agent flow. **Search algorithm:** token-based — query is split on whitespace, tokens ≤ 2 chars ignored; a listing matches if ANY token appears in its haystack (resilient to partial queries and minor spelling divergence) |
| GET | `/leasing/find-listing?query=&property_group_id=&manager_id=` | Search listing by flat number or title; `manager_id` filters across all groups owned by that manager; returns `{found, listing_uuid, address, bedrooms, monthly_rent, floor_number, available_from, custom_rules}` |
| GET | `/leasing/search?bedrooms=&budget_max=&property_group_id=&manager_id=` | Return up to 5 matching listings; `manager_id` filters across all groups owned by that manager; returns `{count, listings: [{listing_uuid, flat_number, bedrooms, monthly_rent, floor_number, available_from, title}]}` |

**`/leasing/search` filter behaviour:** `bedrooms` and `budget_max` are accepted as `Optional[str]` (not int/float) because VAPI sends `""` when the caller hasn't confirmed a preference — FastAPI would 422 on empty-string int. Internal `_parse_int` / `_parse_float` helpers treat `""` and `0` as **no filter**. `budget_max` is applied as a DB-level `lte` filter; `bedrooms` is applied as a Python post-fetch filter (PostgREST embedded-resource `eq` on joined tables is unreliable with `!inner`). Fetches up to 20 rows before Python filtering, returns top 5.

#### Manager CRUD (authenticated + subscription gate)
| Method | Path | Description |
|---|---|---|
| GET | `/leasing/listings` | List manager's **active** listings only (`is_active=true`); newest first |
| POST | `/leasing/listings` | Create listing — looks up flat, rejects with 400 if flat is occupied (`tenant_uuid` IS NOT NULL or `occupied=true`) or already listed (`is_listed=true`); resolves property_group_id; sets `is_listed=true` on flat after insert |
| PATCH | `/leasing/listings/{listing_uuid}` | Update listing fields; if `is_active=false` is set, also sets `is_listed=false` on the flat |
| DELETE | `/leasing/listings/{listing_uuid}` | Hard delete; sets `is_listed=false` on the flat before deleting |
| GET | `/leasing/leads?listing_uuid=&qualification_status=` | List leads scoped to manager's property groups; `listing_uuid` filter matches both `listing_uuid` and `interested_listing_ids` contains |
| PATCH | `/leasing/leads/{lead_uuid}` | Update lead status (contacted/toured/converted/lost only for manager) |
| DELETE | `/leasing/leads/{lead_uuid}` | Hard delete |
| GET | `/leasing/metrics?days=30` | Aggregated call metrics: total, qualified, not_qualified, unmatched, rate, avg_duration |
| GET | `/leasing/export` | CSV download of filtered leads |

---

### `/workflow` — `routes/workflow.py`
| Method | Path | Description |
|---|---|---|
| POST | `/workflow/sms-broadcast` | Bulk SMS to filtered tenants |
| GET | `/workflow/sms-templates` | List SMS templates |
| POST | `/workflow/sms-templates` | Create template |

---

### `/settings` — `routes/settings.py`
| Method | Path | Description |
|---|---|---|
| GET | `/settings` | Manager settings (name, email, phone, notification preferences) |
| PATCH | `/settings` | Update manager settings |
| GET | `/settings/features` | Feature flags per building |
| POST | `/settings/features` | Enable/disable feature per building |

---

### `/import` — `routes/import_routes.py`
| Method | Path | Description |
|---|---|---|
| POST | `/import/analyze` | Detect if uploaded file columns match schema; call `gpt-4o-mini` to semantically map non-matching columns; return `{needs_mapping, mapping, unmapped_required, row_count}` |
| POST | `/import/properties` | CSV or XLSX → PropertyGroup + Building + Flat hierarchy; optional `column_mapping` form field (JSON) |
| POST | `/import/tenants` | CSV or XLSX → Tenants linked to existing flats; optional `column_mapping` form field (JSON); when a CSV row assigns a tenant to a flat, that flat's `lease_listings` row is **deleted** (leads nullified first) |

**Smart import flow:**
1. Frontend calls `/import/analyze` with the file + `import_type`
2. If `needs_mapping: false` → import directly (existing column names matched)
3. If `needs_mapping: true` → frontend shows `ColumnMappingStep` UI with AI-suggested column mapping
4. User confirms/edits mapping → frontend calls import endpoint with `column_mapping` JSON form field
5. Backend applies `_apply_mapping(rows, mapping)` before the existing column-check and row-processing logic

**File format support:** `.csv` (UTF-8 or UTF-8 with BOM) and `.xlsx` (Excel). Format detected by filename extension via `_detect_and_parse`. New dependency: `openpyxl>=3.1.0`.

**Key helpers:**
- `_parse_csv(content)` → `(rows, fieldnames)` — lowercases + strips all headers/values, handles BOM
- `_parse_xlsx(content)` → `(rows, fieldnames)` — reads first sheet, skips empty rows
- `_apply_mapping(rows, mapping)` — renames row keys per `{original: target}` dict; drops null-mapped columns
- `_map_columns_with_ai(headers, sample_rows, import_type)` — async; calls `AsyncOpenAI` with headers + 3 sample rows + schema descriptions; sanitizes response to only allow valid target columns; falls back to `{header: None}` on any exception

---

### `/upload` — `routes/upload.py`
| Method | Path | Description |
|---|---|---|
| POST | `/upload/image` | Upload building photo → Supabase Storage, returns signed URL |

---

### `/payments` — `routes/payments.py`
| Method | Path | Description |
|---|---|---|
| POST | `/payments/create-checkout-session` | Stripe Checkout (14-day trial + $1 card verify) |
| POST | `/payments/webhook` | Idempotent Stripe event handler; updates `subscriptions` table |
| GET | `/payments/subscription-status` | Current subscription status |

---

## 6. Backend — Key Modules

### `app/config.py` — Settings
Single `Settings` class loading all env vars via `os.getenv`. Imported as `settings` singleton.

Key vars:
- `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`
- `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`
- `PRIVATE_VAPI_API` — server-side VAPI SDK key
- `VAPI_NUMBER_ID`, `VAPI_ASSISTANT_ID` — **legacy**, kept for backward compat only; not used by any current live path
- `VAPI_COMPLAINT_ASSISTANT_ID`, `VAPI_COMPLAINT_NUMBER_ID`, `VAPI_COMPLAINT_PHONE_NUMBER` — complaint agent (`+14382314283`)
- `VAPI_SHARED_LEASE_ASSISTANT_ID`, `VAPI_SHARED_LEASE_NUMBER_ID`, `VAPI_SHARED_LEASE_PHONE_NUMBER` — shared lease agent (`+14313415768`)
- `OPEN_AI_API`, `GROQ_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`
- `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`
- `FRONTEND_URL`, `LANDING_PAGE_URL`, `BACKEND_URL`, `ALLOWED_ORIGINS`

---

### `app/db/session.py` — Supabase Clients
```python
get_db()          # anon client (respects RLS) — for user-facing routes
get_service_db()  # service-role client (bypasses RLS) — for webhooks, admin
```

---

### `app/dependencies/auth.py` — JWT Validation
- `get_current_user()` — validates Bearer JWT
- Supports ES256 (JWKS from Supabase) and HS256 (fallback with `SUPABASE_JWT_SECRET`)
- Returns dict: `{sub: user_uuid, email, role, ...}`

---

### `app/dependencies/authenticated_db.py`
- `get_authenticated_db()` — wraps anon client, calls `db.postgrest.auth(token)` so RLS resolves `auth.uid()` correctly

---

### `app/dependencies/subscription.py`
- `require_active_subscription()` — checks `subscriptions` table for `status IN (active, trialing)`
- Uses service client (bypasses RLS)
- Raises HTTP 403 if not subscribed

---

### `app/schemas/flat.py` — `FlatResponse`
Extends `FlatBase` with: `id`, `uuid`, `created_at`, `image_url`, `tenant_uuid`, `tenant`, `building_id`, `property_type_id`, `street_address`, `address_line`, `city`, `state`, `country`, and enrichment fields:
- `building_name: Optional[str] = None` — populated by `GET /flats?vacant=true`
- `property_name: Optional[str] = None` — populated by `GET /flats?vacant=true`
- `is_listed: Optional[bool] = None` — mirrors `flats.is_listed`; used by `UnitListPanel` for listing status badge

Non-vacant/non-enriched responses leave building_name/property_name as `null`.

### `app/schemas/tenant.py`
Includes a Pydantic `field_validator` on `phone` enforcing E.164 format (`^\+[1-9]\d{9,14}$`). Raises `ValueError` on invalid input, surfaced as HTTP 422.

### `app/schemas/leasing.py`
- `CustomRules` — JSONB config: `max_occupants`, `income_required`, `pets_allowed`, `vegetarian_only`, `lease_term_months`, `custom_question`
- `ListingCreate / ListingUpdate / ListingResponse`
- `LeadUpdate / LeadResponse`
- `LeadResponse.updated_at` is `Optional[datetime] = None` — the insert never sets this field and the DB column has no DEFAULT; making it optional prevents a Pydantic 500 on fresh rows

---

### `app/services/vapi_provisioning.py`
- `provision_vapi_for_manager(manager_id, db)` — run as a FastAPI `BackgroundTask` when a manager creates their FIRST property group
- **Per-manager provisioning** (one number + one assistant per manager account, not per group):
  1. Guard: exits immediately if `manager_vapi_config` already has `status = active` for this manager
  2. Race guard: checks `twilio_number_pool` for an existing row with `assigned_manager_id = manager_id` — reuses it instead of claiming a new one (prevents double-claim on rapid retries)
  3. Else: picks the oldest `available` row from `twilio_number_pool` (service DB, bypasses RLS)
  4. Marks the row `assigned` with `assigned_manager_id` (optimistic lock)
  5. Creates a per-manager lease assistant via `build_lease_config(backend_url, manager_id)`
  6. Links the assistant to the Twilio number via **`httpx.patch("https://api.vapi.ai/phone-number/{id}", json={"assistantId": ...})`** — the VAPI SDK `phone_numbers.update()` and `UpdatePhoneNumberDto` are broken in the installed version; direct HTTP patch is the only working path
  7. Upserts `manager_vapi_config` with `vapi_lease_assistant_id`, `vapi_phone_number_id`, `vapi_phone_number`, `vapi_provisioning_status = "active"`
- On failure: upserts `manager_vapi_config` with `vapi_provisioning_status = "failed"` and re-raises
- **Pool-empty behaviour:** if `twilio_number_pool` has no available rows, upserts `failed` status immediately — no silent fallback
- **Background task DB:** the task must receive `svc_db` (service-role client), NOT the request-scoped `get_authenticated_db` client — the authenticated client expires when the HTTP response is sent, before the background task completes

---

### `app/services/vapi_agent_config.py`
Four builder functions:
- `build_assistant_config()` — legacy complaint agent (existing test group)
- `build_complaint_config(backend_url)` — global complaint agent (Option B, multi-group); complaint agent books **manager callbacks** (appointment `type="callback"`, `tenant_phone` set) — agent checks `check_availability` before scheduling, then calls `submit_complaint` with `appointment_date`
- `build_lease_config(backend_url, manager_id, manager_name="our property management team")` — per-manager lease agent; injects `manager_id` into tool URLs so the agent searches listings across ALL property groups owned by this manager; `submit_lease_lead` posts to `/voice/lease-lead-direct?call_id=...&phone=...&manager_id={manager_id}` (apiRequest) — `manager_id` baked into the URL so unmatched leads always have a non-NULL `manager_id`; greeting says "I'm Max, the AI leasing assistant for {manager_name}"
- `build_lease_config_shared(backend_url)` — shared lease agent with no manager scope (used by `update_shared_agents.py` and `setup_vapi_agents.py`)
- `submit_lease_lead` tool includes `interested_listing_ids` (array of UUIDs) — agent captures all listing UUIDs the caller showed interest in, not just the primary one

**Lease agent conversation behaviour (updated 2026-06-07 — query-first flow):**
- `first_message_mode` = `assistant-speaks-first-with-model-generated-message` — AI generates a fresh bilingual greeting each call; no hardcoded `first_message`
- Step 1: bilingual greeting ends with "Which unit are you calling about?"
- Step 2: caller says any identifying info → agent calls `find_units` tool immediately (no preference collection first)
- `find_units` searches flat_number, title, address, building name, and property group name; returns up to 5 compact matches (identifiers only, not full details)
- Agent reads back only unit/building names to caller; waits for confirmation; NEVER volunteers rent, floor, or other details until caller asks
- Step 3: after unit confirmed, agent answers ONLY what the caller specifically asks — one fact per response
- Preference-based browsing (`search_listings`) is a **secondary flow** — only used when caller explicitly says "I'm looking for a 2-bedroom" etc.
- `load_listings` tool has been **removed** — background preloading is replaced by the query-first `find_units` approach

**Model (all agents):** OpenAI `gpt-5.2-chat-latest` (provider `"openai"`). Applies to `build_assistant_config`, `build_complaint_config`, and `_lease_assistant_shell` in `vapi_agent_config.py`.

**Voice & language config (all agents):**
- Voice: ElevenLabs `eleven_turbo_v2_5`, voiceId `E4GQ42zEV1kwul03Bl16` (Wilkins bilingual voice), stability 0.6, useSpeakerBoost, optimizeStreamingLatency 1
- Transcriber: Deepgram nova-3, `language: "multi"`, confidenceThreshold 0.4, numerals False, OpenAI gpt-4o-transcribe fallback (unchanged)
- Speaking: waitSeconds 0.1, transcriptionEndpointingPlan onNumberSeconds 0.1, stopSpeakingPlan numWords 2, backgroundDenoisingEnabled
- Language policy: **all agents respond in the caller's detected language** (English or Quebec French). Tool submissions are always English — French is silently translated before any tool call.
- First messages are bilingual (English / French) so callers know both are supported
- **Currency:** lease agent quotes all rent amounts in **Canadian dollars** — "two thousand dollars per month", never "rupees" or bare digits

---

### `app/ai/chatbot.py` — AI Chatbot
- Entry: `run_chat(messages: list, db: Client) -> (reply: str, refresh_needed: bool)`
- Model: `gpt-4o-mini` with tool calling
- Tools: `add_new_unit`, `add_new_building`, `add_new_property`, `retrieve_building`, `retrieve_unit`, `retrieve_tenant`, `retrieve_appointment`, `retrieve_complaint`, `add_appointment`, `reschedule_appointment`, `cancel_appointment`, `mark_attended`
- Asks for confirmation before write/delete
- `refresh_needed = True` triggers frontend data reload
- Uses `{today}` placeholder in system prompt for date awareness
- Truncates to last 10 messages before sending to OpenAI

---

### `app/ai/extractor.py` — Complaint Extraction
- `extract_complaint_from_transcript(transcript)` — Groq Llama extraction
- Returns: `{flat_number, category, priority, description}` — never fabricates missing fields
- Validates category against `ALLOWED_CATEGORIES`

---

### `app/core/constants.py`
```python
ALLOWED_CATEGORIES = ["water", "electricity", "cleaning", "noise", "maintenance", "security", "other"]

class ComplaintStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in-progress"
    RESOLVED = "resolved"
```

---

### `app/core/features.py` — Feature Flags
```python
class Feature(str, Enum):
    RENT_MANAGEMENT = "rent_management"
    RENT_DUE_DATE = "rent_due_date"
    FLAT_DETAILS = "flat_details"
    VOICE_CALLS = "voice_calls"
    SMS_REMINDERS = "sms_reminders"
    EMAIL_REMINDERS = "email_reminders"
    TENANT_DETAILS = "tenant_details"
    TENANT_DOCUMENTS = "tenant_documents"
```

---

### `app/services/notifications.py`
- `notify_tenant_appointment(flat_uuid, event, flat_number, db, new_date)` — SMS to tenant on: created / rescheduled / cancelled / attended / reactivated
- `notify_manager_appointment_scheduled(appointment)` — SMS + email to manager
- All notifications are non-blocking background tasks; errors are logged, never raised

---

## 7. Frontend — All Components

### Pages / Top-Level Views
| File | Purpose |
|---|---|
| `App.jsx` | Root — AuthGate, Dashboard shell, 3s call-status polling, lazy page loading |
| `components/Dashboard.jsx` | Main dashboard — KPI cards, charts, appointment list |
| `components/BentoDashboard.jsx` | Bento-grid layout overview |
| `components/ComplaintsPage.jsx` | Full complaints view with category/status filters |
| `components/PropertiesPage.jsx` | Property + building listing; `handleDeleteGroup` intercepts 409 `tenant_block` response and shows a confirmation dialog with tenant count; on confirm re-calls `deletePropertyGroup(id, true)` with `?force=true` |
| `components/TenantManagement.jsx` | Tenant CRUD, lease info, rent status |
| `components/CalendarView.jsx` | Month calendar + day panel for appointments |
| `components/SettingsPage.jsx` | Manager settings + per-building feature flags |
| `components/RentTab.jsx` | Set/view monthly rents per flat |
| `components/VoiceStatsTab.jsx` | Voice call analytics |
| `components/SmsWorkflow.jsx` | Bulk SMS broadcast to tenants |
| `components/OnboardingChecklist.jsx` | Interactive onboarding checklist |
| `components/LeasingTab.jsx` | Leasing management page — listings CRUD, lead pipeline, metrics KPIs, CSV export, Refresh button; on load calls `GET /property-groups/users/me/vapi-config` and shows one account-level lease line banner (active phone number / provisioning spinner / retry button); `pending` state shows "Stuck? Trigger setup" link alongside the spinner; `handleRetryProvisioning` debounced with `retrying` guard; auto-polls once after 8 s on retry click; leads table shows primary matched listing flat_number column; passes `listings` to `LeadDetailModal` |

### Modals
| File | Purpose |
|---|---|
| `ComplaintModal.jsx` | Create/edit complaint |
| `ComplaintDetailModal.jsx` | View complaint + linked appointments |
| `AppointmentModal.jsx` | Create appointment |
| `AppointmentDetailModal.jsx` | View/edit appointment + linked complaints |
| `FlatDetailModal.jsx` | Flat details |
| `FlatEditModal.jsx` | Edit flat; when `flat.street_address` is empty, pre-fills it from `flat.building_street_address` (injected by `GET /buildings/{id}/units`); phone field has E.164 inline validation |
| `TenantProfile.jsx` | Tenant detail modal; edit form includes `name`, `phone` (E.164 inline validation, regex `^\+[1-9]\d{9,14}$`), `email`, lease dates, rent_status, notes |
| `AddPropertyModal.jsx` | Create PropertyGroup |
| `AddBuildingModal.jsx` | Create/edit Building — dual-mode: when `initialData` prop is provided it calls `updateBuilding()` instead of `createBuilding()`; title changes to "Edit Building"; on create mode auto-fills `street_address`, `city`, `state`, `country` from parent property group; `street_address` is required (validated before submit) |
| `AddPropertyGroupModal.jsx` | Create/edit property group — dual-mode: when `initialData` prop is provided it calls `updatePropertyGroup()` instead of `createPropertyGroup()`; title changes to "Edit Property Group" |
| `AddTenantModal.jsx` | Create Tenant; phone field has E.164 inline validation (regex `^\+[1-9]\d{9,14}$`); vacant-flat dropdown shows `flat_number — building_name, property_name` (falls back to `street_address`); dispatches `refresh-listings` event after successful flat assignment |
| `AssignTenantModal.jsx` | Assign existing tenant to flat |
| `AddListingModal.jsx` | Create / edit a lease listing (flat selector, rent, availability, custom rules); vacant-flat dropdown uses `fetchNotListedVacantFlats` (filters `vacant=true&not_listed=true`) so only un-listed vacant flats appear; shows `flat_number — building_name, property_name` (falls back to `street_address` or "No address") |
| `LeadDetailModal.jsx` | View lead details + update qualification status; accepts `listings` prop to resolve flat_number for primary listing and interested_listing_ids chips; when `findListing()` returns undefined (listing deleted), renders a `"Unit delisted"` pill (muted/grey) instead of the raw UUID — applies to both primary listing and each also-interested chip |
| `BuildingInfoModal.jsx` | Building detail |
| `CsvImportModal.jsx` | Smart bulk import — accepts `.csv` and `.xlsx`; calls `/import/analyze` first; shows `ColumnMappingStep` (editable AI-suggested mapping table) when columns don't match; passes confirmed mapping to import endpoint |
| `DateComplaintsModal.jsx` | Complaints for a selected calendar date |
| `DailyTasksModal.jsx` | Today's appointment list |
| `DashboardListModal.jsx` | Generic list-view modal |

### Cards & Tables
| File | Purpose |
|---|---|
| `ComplaintTable.jsx` | Table view of complaints |
| `ComplaintCard.jsx` | Card view of complaint |
| `CompactComplaintCard.jsx` | Compact card variant |
| `ComplaintsOverview.jsx` | Summary statistics block |
| `PropertyCard.jsx` | Single property card |
| `PropertyGroupCard.jsx` | Property group card |
| `BuildingCard.jsx` | Building card |
| `UnitListPanel.jsx` | Flat list panel within a building; each unit card shows a 3-state listing badge: **Listed** (blue, `is_listed=true`), **Not Listed** (amber, `is_listed=false`), **Cannot be listed** (grey, occupied) alongside the existing Occupied/Vacant badge |

### Charts (in `components/dashboard/`)
| File | Purpose |
|---|---|
| `TrendsChart.jsx` | Complaint trends line chart |
| `StatusDonut.jsx` | Complaint status donut chart |
| `CategoriesPie.jsx` | Category breakdown pie chart |
| `AppointmentsBar.jsx` | Appointments-per-day bar chart |
| `KPICard.jsx` | Individual KPI metric card |

| `CompactStatsGrid.jsx` | Compact stats grid |
| `CompactCalendar.jsx` | Mini month calendar widget |

### Navigation & UI Primitives
| File | Purpose |
|---|---|
| `Sidebar.jsx` | Main nav sidebar with route switching; nav list is `overflow-y-auto` so it scrolls when items exceed the viewport height |
| `TopBar.jsx` | Header — user menu, theme toggle |
| `ViewSwitcher.jsx` | Toggle list/card/calendar views |
| `QuickFilters.jsx` | Filter bar |
| `PriorityBadge.jsx` | Priority display badge |
| `StatusDropdown.jsx` | Status filter/selector |
| `ThemeToggle.jsx` | Dark/light mode toggle |
| `global/AnimationContainer.jsx` | Framer Motion wrapper |
| `global/Wrapper.jsx` | Layout wrapper |

### AI & Communication
| File | Purpose |
|---|---|
| `Chatbot.jsx` | Floating FAB chatbot — renders responses as markdown |
| `OutboundCallButton.jsx` | Trigger outbound VAPI call — agent selector (complaint / lease); phone number field defaults to `+1` (Canadian); accepts any E.164 international number |
| `NotificationPanel.jsx` | Toast notification display |
| `RecentUpdates.jsx` | Recent activity feed |

### Onboarding
| File | Purpose |
|---|---|
| `OnboardingTour.jsx` | Guided tour via react-joyride |
| `OnboardingTooltip.jsx` | Custom tooltip for tour |
| `AuthPage.jsx` | Login/signup (Google OAuth PKCE) |

### Misc
| File | Purpose |
|---|---|
| `ImageUploadField.jsx` | Image upload with preview |
| `PropertySettings.jsx` | Per-building feature flag toggles |
| `PriorityQueue.jsx` | Priority-ordered complaint list |

---

## 8. Frontend — Key Services & Utilities

### `services/apiService.js`
- **All HTTP calls go here.** Never inline `fetch` in components.
- `authFetch(path, options)` — adds `Authorization: Bearer <token>`, handles 401 (sign out) and 403 (redirect to pricing)
- Exports: `fetchComplaints`, `createComplaint`, `updateComplaint`, `fetchAppointments`, `updateAppointment`, `deleteAppointment`, `fetchFlats`, `fetchTenants`, `fetchBuildings`, `sendChatMessage`, `createCheckoutSession`, `getCallStatus`, etc.
- **Leasing exports:** `getListings`, `createListing`, `updateListing`, `deleteListing`, `getLeaseLeads`, `updateLead`, `deleteLead`, `getLeasingMetrics`, `exportLeads`
- **Flat helpers:** `fetchVacantFlats()` → `GET /flats?vacant=true` (all vacant); `fetchNotListedVacantFlats()` → `GET /flats?vacant=true&not_listed=true` (vacant + not yet listed — used by AddListingModal)
- **Property groups:** `fetchPropertyGroups()`, `createPropertyGroup(payload)`, `updatePropertyGroup(groupId, data)` → `PATCH /property-groups/{id}`, `deletePropertyGroup(groupId, force=false)` → `DELETE /property-groups/{id}?force=true` (force param skips tenant-block 409), `getUserVapiConfig()` → `GET /property-groups/users/me/vapi-config`, `retryUserProvisioning()` → `POST /property-groups/users/me/provision-voice`
- **Buildings:** `updateBuilding(buildingId, data)` → `PATCH /buildings/{id}`
- **Image upload:** `uploadImage(file, entityType)` → `POST /upload/image`, returns `{url, path}`
- **Outbound call:** `makeOutboundCall(customerNumber, agentType='complaint', firstMessage=null)` — `agentType` forwarded as `agent` field in request body
- **Smart import:** `analyzeImportFile(file, importType)` → `POST /import/analyze`; `importPropertiesCsv(file, columnMapping?)` and `importTenantsCsv(file, columnMapping?)` accept optional mapping object

### `lib/supabase.js`
- Supabase client configured with PKCE auth flow
- Detects OAuth redirect from URL hash
- Used directly only in `AuthContext.jsx` and `lib/supabase.js`

### `context/AuthContext.jsx`
- `AuthProvider` — wraps app, listens to `supabase.auth.onAuthStateChange`
- `ensureManagerProfile()` — creates `manager_profiles` row on first Google OAuth sign-in
- `useAuth()` — returns `{session, user, loading}`

### `context/OnboardingContext.jsx`
- Tracks tour completion per manager in localStorage + Supabase DB (DB is authority)
- `triggerTour(section)` — starts tour for section: `dashboard | properties | tenants | complaints | calendar | workflow`
- Sections defined in `config/onboardingTours.js`

### `constants/status.js`
```js
STATUS = { PENDING: "pending", IN_PROGRESS: "in-progress", RESOLVED: "resolved" }
APPOINTMENT_STATUS = { SCHEDULED: "scheduled", CANCELLED: "cancelled", ATTENDED: "attended", COMPLETED: "completed" }
```

---

## 9. Key Architectural Rules

### Routing
- **No `/api` prefix** on any backend route
- Route file registers its own prefix via `router = APIRouter(prefix="/complaints", ...)`
- `main.py` calls `app.include_router(complaints_router)` — no extra prefix added

### Database Access
- Always use `db: Client = Depends(get_authenticated_db)` for user routes (enforces RLS)
- Use `get_service_db()` only for webhooks, Stripe events, admin operations
- Never use SQLAlchemy models in new code — use Supabase SDK directly

### VAPI Endpoints
- Always return HTTP 200 (even on error) to keep the voice session alive
- Use `exists: bool` or `status: str` fields for logic branching
- Normalize all inputs: `.strip().upper()` on flat numbers, phone numbers to E.164

### Date/Time
- Store as IST: `timezone(timedelta(hours=5, minutes=30))`
- Format for frontend: `YYYY-MM-DDTHH:MM:SS` (T separator, NOT space — for `parseISO` compatibility)

### Cross-Component Refresh
```js
window.dispatchEvent(new Event('refresh-appointments'))  // voice/chatbot actions that create/update appointments
window.dispatchEvent(new Event('refresh-listings'))      // after tenant assignment (AddTenantModal, AssignTenantModal)
```
`LeasingTab` listens for `refresh-listings` and re-fetches its listings list.

### Flat Creation
- Flat number uniqueness is enforced at DB level (UNIQUE constraint)
- Before inserting a tenant during flat creation, the route checks `tenants.phone` for uniqueness
- If the phone already exists and is assigned to another flat, returns HTTP 400: `"This phone number belongs to a tenant already in Unit {flat_number}."` (fetches the flat_number from DB; falls back to "another unit" if lookup fails). If phone exists but unassigned, returns "A tenant with this phone number already exists. Use 'Assign Existing Tenant'…"
- Image uploaded to Storage is cleaned up if any subsequent check fails (no orphaned files)
- **The `flats` INSERT uses `svc` (service-role client), not `db`** — some manager accounts have RLS INSERT policies that reject the anon client. Ownership is validated first via `require_active_subscription` and duplicate checks. Do not revert this to `db.table("flats").insert()`.

### VAPI Voice Webhook DB Client
- `POST /voice/webhook` uses `get_service_db` (not `get_authenticated_db`) — inbound calls carry no user JWT
- `GET /appointments/availability` uses `get_service_db` — called by VAPI before complaint submission, no user session

### VAPI Agent Types
- Two agent roles: **complaint** (maintenance intake) and **lease** (lead capture)
- Both agents can be triggered via outbound call; `agent` field in `POST /voice/call/outbound` selects which
- Complaint agent is global (one assistant for all groups): `VAPI_COMPLAINT_ASSISTANT_ID` on `+14382314283` (`VAPI_COMPLAINT_NUMBER_ID`)
- Lease agent is **per-manager account** (one number + one assistant per manager, not per property group). Stored in `manager_vapi_config` table.
- `vapi_provisioning_status` in `manager_vapi_config` tracks state: `pending` | `active` | `failed` | `not_set_up` (not_set_up = no row exists yet)
- **Provisioning trigger:** fires only when a manager creates their FIRST property group. Second, third, ... groups do NOT re-trigger provisioning.
- **LeasingTab** calls `GET /property-groups/users/me/vapi-config` on load and displays one account-level banner (phone number, spinner, or retry button).
- **Phone number source**: Twilio-owned numbers from `twilio_number_pool` (`assigned_manager_id` column). When pool is empty, provisioning marks `failed` — no silent fallback. Add pool numbers: `python backend/scripts/add_twilio_number_to_vapi.py <E.164>`
- **DB-level race guard**: `CREATE UNIQUE INDEX twilio_number_pool_one_per_manager ON twilio_number_pool (assigned_manager_id) WHERE assigned_manager_id IS NOT NULL` — migration `016_fix_vapi_provisioning_cleanup.sql`. Prevents two concurrent provisioning tasks from claiming two different numbers for the same manager.
- **Retry endpoint guard**: `POST /property-groups/users/me/provision-voice` checks `manager_vapi_config.vapi_provisioning_status` first; returns early without spawning a background task if already `active`.
- **Live phone numbers** (do not reassign):
  - `+14382314283` → complaint agent (`VAPI_COMPLAINT_NUMBER_ID`)
  - `+14313404212` → leadpipecrm manager `28c43c77` (active)
  - `+14313415768` → available in pool (unassigned)
- Outbound complaint call uses `VAPI_COMPLAINT_ASSISTANT_ID`/`VAPI_COMPLAINT_NUMBER_ID` (fixed 2026-05-23).
- **Pending cleanup**: `+12494028641` assigned to orphaned manager `02672346-...` during race condition incident — run `backend/migrations/017_unassign_12494028641.sql` in Supabase SQL editor.

### Idempotency
- Stripe webhooks: deduplicated via `stripe_events` table (`event_id` UNIQUE)
- VAPI webhooks: `call_id` UNIQUE on `call_logs` prevents duplicate processing

### Subscription Gate
- `require_active_subscription` dependency blocks routes for non-subscribers
- Checks `subscriptions` table for `status IN ('active', 'trialing')`
- HTTP 403 triggers frontend redirect to pricing page

### Groq Tool Calling Quirk
- `llama-3.3-70b-versatile` can hallucinate tool names not in schema (e.g., `brave_search`)
- Fix: catch `BadRequestError` where `"tool_use_failed" in str(e)`, retry as plain completion
- Tool results must be strings (not dicts) — LLM reads them for human response

### LLM Models
- Chatbot: `gpt-4o-mini` (OpenAI, tool calling)
- Complaint extraction: `llama-3.3-70b-versatile` (Groq — `llama-3.1-70b-versatile` is decommissioned)

### Frontend HTTP
- **Never** `fetch()` directly in a component — always go through `apiService.js`
- `authFetch` auto-attaches token, handles auth errors globally

### Comments / Code Style
- Pydantic V2 (not V1) — use `model_validator`, `field_validator`, not `@validator`
- Backend: FastAPI dependency injection pattern throughout
- Frontend: functional components only, hooks for state/effects

---

## 10. External Services — Integration Summary

| Service | Purpose | Key Config Vars |
|---|---|---|
| Supabase | DB, Auth, Storage | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY` |
| Stripe | Subscription billing | `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID` |
| Vapi.ai | Voice phone agent | `VAPI_API_KEY`, `VAPI_NUMBER_ID`, `VAPI_ASSISTANT_ID`, `PRIVATE_VAPI_API` (private SDK key), `VAPI_SHARED_LEASE_ASSISTANT_ID`, `VAPI_SHARED_LEASE_NUMBER_ID` |
| OpenAI | Chatbot (gpt-4o-mini) | `OPENAI_API_KEY` |
| Groq | Complaint extraction | `GROQ_API_KEY` |
| Twilio | SMS notifications | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` |
| SendGrid | Email notifications | `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL` |

---

## 11. Feature Flags

Per-building feature control stored in `property_features` table.

| Feature Key | Default | Description |
|---|---|---|
| `rent_management` | enabled | Rent tracking + summary |
| `rent_due_date` | enabled | Due date calculations |
| `flat_details` | enabled | Flat detail view |
| `voice_calls` | enabled | VAPI voice intake |
| `sms_reminders` | disabled | Tenant SMS notifications |
| `email_reminders` | disabled | Tenant email notifications |
| `tenant_details` | enabled | Tenant profile view |
| `tenant_documents` | disabled | Document upload/view |

---

## 12. Onboarding System

- Tour sections: `dashboard`, `properties`, `tenants`, `complaints`, `calendar`, `workflow`
- State persisted: `localStorage` (fast) + `manager_profiles.tour_completed` in Supabase (authoritative)
- `OnboardingContext` exposes `triggerTour(section)` to launch tours from any component
- Tour steps defined in `frontend/src/config/onboardingTours.js`
- `OnboardingChecklist` component shows checklist sidebar panel

---

## 13. Payments / Subscription Flow

1. User hits subscription gate → redirected to pricing
2. Frontend calls `POST /payments/create-checkout-session`
3. Backend creates Stripe Checkout session (14-day trial + $1 card verification)
4. User completes checkout → Stripe fires webhook events
5. `POST /payments/webhook` processes `customer.subscription.*` events idempotently
6. Updates `subscriptions` table → unlocks the app
7. Frontend checks status via `GET /payments/subscription-status`

---

## 14. Voice Call Flow (VAPI)

### Complaint Agent Flow
1. Tenant calls the VAPI complaint number (`+14382314283`)
2. Agent asks for flat number → calls `POST /flats/verify-phone` (caller ID gate)
3. Tenant describes issue → agent silently identifies category
4. Agent asks for preferred callback time → calls `GET /appointments/availability` to check slot
5. If unavailable: agent asks for another time; loops back
6. If available: agent confirms details → calls `submit_complaint` tool
7. Backend (`POST /voice/webhook`): creates Complaint + Appointment (`type="callback"`, `tenant_phone=caller`) + Notification for manager
8. Frontend polls `GET /voice/call-status` every 3 seconds; refreshes on new timestamp

### Existing Tenant Appointment Management
- View: VAPI calls `GET /appointments/view?flat_number=`
- Reschedule: checks availability → calls `PATCH /appointments/update`
- Cancel: calls `PATCH /appointments/cancel`

### Lease Agent Flow (updated 2026-06-07 — query-first)
1. Prospect calls the manager's lease line (per-manager Twilio number)
2. Agent generates a bilingual greeting (model-generated, not hardcoded); asks "Which unit are you calling about?"
3. Caller states any identifying info (unit number, building, address, city, etc.) → agent calls `GET /leasing/find-units` silently
4. Agent reads back only unit/building names from results; waits for caller to confirm the unit
5. Agent answers ONLY what the caller specifically asks — one fact per response (never volunteers rent, floor, etc. unprompted)
6. Agent collects caller name; calls `submit_lease_lead` → `POST /voice/lease-lead-direct`
7. EOC fallback: `POST /voice/lease-eoc-webhook` creates partial unmatched lead if no submit occurred
8. Preference-based browsing (secondary): if caller explicitly says "I'm looking for a 2-bedroom", agent uses `search_listings` instead
9. Manager sees lead in `LeasingTab` → Leads table
