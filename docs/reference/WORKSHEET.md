# Tenant Management MVP — Developer Worksheet
> Quick-reference for every session. Print or keep open alongside the learning modules.

---

## 1. Project Stack at a Glance

| Layer | Tech | Key File |
|---|---|---|
| Backend framework | FastAPI + Uvicorn | `backend/app/main.py` |
| Database SDK | Supabase Python SDK | `backend/app/db/session.py` |
| Auth | Supabase Auth (Google PKCE) + JWT | `backend/app/dependencies/auth.py` |
| Pydantic | V2 — `model_validator`, `field_validator` | `backend/app/schemas/` |
| AI chatbot | OpenAI `gpt-4o-mini` | `backend/app/ai/chatbot.py` |
| AI extraction | Groq `llama-3.3-70b-versatile` | `backend/app/ai/extractor.py` |
| Voice | VAPI.ai | `backend/app/routes/voice.py` |
| SMS | Twilio | `backend/app/integrations/twilio_client.py` |
| Email | SendGrid | `backend/app/integrations/email_client.py` |
| Payments | Stripe | `backend/app/routes/payments.py` |
| Frontend | React 18 + Vite + Tailwind + Framer Motion | `frontend/src/` |
| HTTP client (FE) | apiService.js (authFetch wrapper) | `frontend/src/services/apiService.js` |
| Charts | Recharts | `frontend/src/components/dashboard/` |
| Date parsing | date-fns `parseISO` / `format` | any component |

---

## 2. Data Hierarchy

```
PropertyGroup (properties_list)
  └── Building (buildings)
        └── Flat (flats)
              └── Tenant (tenants)
                    └── Complaint (complaints)
                          └── Appointment (appointments)
```

### Key FK relationships
- `flats.tenant_uuid` ↔ `tenants.flat_uuid` — **bidirectional**, must keep in sync
- `complaints.flat_uuid` → `flats.uuid`
- `appointments.complaint_uuid` → `complaints.uuid`
- `rents.flat_uuid` → `flats.uuid`
- `lease_listings.flat_uuid` → `flats.uuid`
- `manager_vapi_config.manager_id` → `auth.users` (one row per manager)
- `twilio_number_pool.assigned_manager_id` → `auth.users` (nullable)

---

## 3. Non-Negotiable Rules

```
Rule 1:  No /api prefix on ANY route
Rule 2:  All frontend HTTP calls go through apiService.js — never inline fetch
Rule 3:  Never use SQLAlchemy models — use Supabase SDK directly
Rule 4:  User routes → get_authenticated_db (RLS enforced)
         Webhooks/admin → get_service_db (bypasses RLS)
Rule 5:  VAPI endpoints always return HTTP 200 — never raise HTTP errors
Rule 6:  Pydantic V2 — model_validator / field_validator (not @validator)
Rule 7:  Groq model: llama-3.3-70b-versatile (3.1 is decommissioned)
Rule 8:  Date format: YYYY-MM-DDTHH:MM:SS (T separator) for parseISO
Rule 9:  Datetimes stored as IST (+05:30)
Rule 10: flats INSERT uses service-role client (svc), not db — RLS INSERT policy
```

---

## 4. Backend Auth Dependency Chain

```python
# Standard authenticated + gated route signature
async def my_route(
    db:   Client = Depends(get_authenticated_db),   # RLS-enforced Supabase client
    user: dict   = Depends(get_current_user),        # JWT payload {sub, email, role}
    _:    None   = Depends(require_active_subscription),  # Stripe gate (403 if not active)
):
```

```python
# Webhook / admin route (no user JWT available)
async def webhook_route(
    svc: Client = Depends(get_service_db),   # bypasses RLS
):
```

---

## 5. All Backend Routes (no /api prefix)

### Complaints — `routes/complaints.py`
```
POST   /complaints          Create complaint (auto-links flat/tenant, optional appointment)
GET    /complaints          List all + joined appointment data
GET    /complaints/{id}     Single complaint
PATCH  /complaints/{id}     Update fields
DELETE /complaints/{id}     Delete
```

### Tenants — `routes/tenants.py`
```
GET    /tenants/by-flat/{flat_no}       VAPI: {exists, flat_no, tenant_name, phone, datetime}
GET    /tenants/by-flat-query?flat_no=  Query param alias for above
POST   /tenants                         Create tenant + flat assignment
GET    /tenants                         List (optional ?flat_uuid=)
GET    /tenants/{uuid}                  Single with computed lease fields
PATCH  /tenants/{uuid}                  Update
DELETE /tenants/{uuid}                  Delete
```

### Flats — `routes/flats.py`
```
POST   /flats/verify-phone              VAPI: {status: valid/invalid/vacant}
POST   /flats/identify-caller           VAPI: identify by phone
POST   /flats                           Create flat (uses svc for INSERT)
GET    /flats                           List (optional ?vacant=true)
GET    /flats/{uuid}/details            Single flat + tenant details
GET    /flats/{flat_number}             Flat by flat_number
PATCH  /flats/{flat_uuid}               Update flat + tenant action
DELETE /flats/{flat_uuid}               Delete (cascade tenant + rent)
PATCH  /flats/{flat_uuid}/assign-tenant    Bidirectional assign
PATCH  /flats/{flat_uuid}/unassign-tenant  Bidirectional unlink
```

### Appointments — `routes/appointments.py`
```
GET    /appointments/view?flat_number=           VAPI: active appointments
PATCH  /appointments/update?flat_number=&id=&new_appointment_date=  VAPI: reschedule
POST   /appointments/cancel?flat_number=&id=    VAPI: cancel
POST   /appointments                            Create
GET    /appointments                            List (with filters)
GET    /appointments/{id}                       Single
PATCH  /appointments/{id}                       Update
DELETE /appointments/{id}                       Soft-delete via status
```

### Buildings — `routes/buildings.py`
```
POST   /buildings           Create
GET    /buildings           List with unit counts
GET    /buildings/{id}      Single
PATCH  /buildings/{id}      Update
DELETE /buildings/{id}      Delete
```

### Property Groups — `routes/property_groups.py`
```
GET    /property-groups                             List
POST   /property-groups                             Create (triggers VAPI provisioning on first group)
GET    /property-groups/users/me/vapi-config        {vapi_provisioning_status, vapi_phone_number}
POST   /property-groups/users/me/provision-voice    Retry VAPI provisioning
GET    /property-groups/{id}/buildings              Buildings for group
DELETE /property-groups/{id}                        Cascade delete all children
```

### Rents — `routes/rents.py`
```
POST   /rents/set                   Set rent for flat (deactivates old, activates new)
GET    /rents/summary               All tenants with active rent + status counts
PATCH  /tenants/{uuid}/rent-status  Update tenant rent status
```

### Voice — `routes/voice.py`
```
POST   /voice/webhook               VAPI webhook (always 200, service DB)
GET    /voice/call-status           {last_call_ended_at} for polling
POST   /voice/lease-lead-webhook    Lease agent tool calls → lease_leads insert
POST   /voice/call/outbound         Trigger outbound call {customer_number, agent}
```

### Leasing — `routes/leasing.py`
```
# VAPI tool endpoints (no auth, always 200)
GET    /leasing/find-listing?query=&property_group_id=&manager_id=
GET    /leasing/search?bedrooms=&budget_max=&property_group_id=&manager_id=

# Manager CRUD (auth + subscription)
GET    /leasing/listings
POST   /leasing/listings
PATCH  /leasing/listings/{listing_uuid}
DELETE /leasing/listings/{listing_uuid}
GET    /leasing/leads?listing_uuid=&qualification_status=
PATCH  /leasing/leads/{lead_uuid}
DELETE /leasing/leads/{lead_uuid}
GET    /leasing/metrics?days=30
GET    /leasing/export
```

### Others
```
POST   /chat                        {messages:[...]} → {reply, refresh_needed}
GET    /call-logs                   List call logs
GET    /call-logs/{id}              Single call log
POST   /payments/create-checkout-session
POST   /payments/webhook            Stripe (idempotent via stripe_events table)
GET    /payments/subscription-status
POST   /notifications/test-sms
POST   /notifications/test-email
GET    /notifications/preferences
GET    /settings                    Manager settings + notification prefs
PATCH  /settings
GET    /settings/features           Feature flags per building
POST   /settings/features           Enable/disable feature
POST   /import/analyze              AI column mapping check
POST   /import/properties           CSV/XLSX → PropertyGroup+Building+Flat
POST   /import/tenants              CSV/XLSX → Tenants
POST   /upload/image                Image → Supabase Storage, returns signed URL
POST   /workflow/sms-broadcast      Bulk SMS to filtered tenants
GET    /workflow/sms-templates
POST   /workflow/sms-templates
GET    /properties                  Flats mapped as property cards
GET    /property-types              Residential / Commercial / Mixed-use
```

---

## 6. Computed Fields on TenantResponse

Calculated by `TenantResponse` Pydantic model in `schemas/tenant.py`:

| Field | Type | Description |
|---|---|---|
| `tenancy_duration_months` | int | Months since lease_start_date |
| `lease_duration_months` | int | Total lease length in months |
| `remaining_time_on_lease_days` | int | Days until lease_end_date |
| `lease_status` | str | `active` / `expiring_soon` / `expired` |

Rule: `expiring_soon` = ≤ 30 days remaining. Computed server-side so frontend never re-derives.

---

## 7. VAPI Integration Patterns

### Always return HTTP 200
```python
# Never raise HTTPException from a VAPI endpoint
@router.post("/flats/verify-phone")
async def verify_phone(payload: PhonePayload):
    try:
        ...
        return {"status": "valid", "flat_number": flat_number}
    except Exception as e:
        return {"status": "error", "message": str(e)}   # still 200
```

### Normalize all inputs
```python
flat_number = payload.flat_number.strip().upper()
phone = payload.phone.strip()
```

### VAPI webhook — end-of-call-report only
```python
# In vapi_agent_config.py — lease agent server_messages setting
"serverMessages": ["end-of-call-report"]
# NEVER add "tool-calls" here — it silently breaks all tool calling
```

### VAPI tool endpoint quirk — empty string params
```python
# VAPI sends "" for int/float params the caller hasn't confirmed
# Use Optional[str] not int, then parse internally
async def search_listings(
    bedrooms: Optional[str] = None,    # not int!
    budget_max: Optional[str] = None,  # not float!
):
    b = _parse_int(bedrooms)    # "" or "0" → None
    bmax = _parse_float(budget_max)
```

---

## 8. Supabase Client Decision Matrix

| Situation | Client | Why |
|---|---|---|
| User-facing routes (CRUD) | `get_authenticated_db` | Enforces RLS — manager sees only their data |
| VAPI webhook, Stripe webhook | `get_service_db` | No user JWT on inbound webhook calls |
| `POST /flats` INSERT | `svc` (service-role) | RLS INSERT policy rejects anon client for some accounts |
| BackgroundTask (provisioning) | `svc` passed in, not request-scoped | Request-scoped client expires before background task finishes |
| Subscription check | service client | Needs to read subscriptions without RLS filter |

---

## 9. PostgreSQL Error Codes → User Messages

Mapped by `_clean_db_error()` helper in `routes/flats.py`:

| PG Code | Meaning | Message |
|---|---|---|
| `42501` | Permission denied | "You do not have permission to perform this action" |
| `23505` | Unique constraint violation | "This [entity] already exists" |
| `23503` | FK constraint violation | "Related record not found" |
| fallback | Any other error | Raw message (sanitized) |

---

## 10. Date/Time Rules

```python
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)

# Format for frontend (parseISO compatible — T separator, no +05:30 suffix)
formatted = now_ist.strftime("%Y-%m-%dT%H:%M:%S")
# → "2026-06-03T14:30:00"  ✓
# → "2026-06-03 14:30:00"  ✗  (space causes parseISO silent fail)
```

```js
// Frontend — always use parseISO from date-fns
import { parseISO, format } from 'date-fns';
const date = parseISO(appointment.appointment_date);
const display = format(date, 'MMM d, yyyy h:mm a');
```

---

## 11. Frontend HTTP Pattern

```js
// frontend/src/services/apiService.js
const authFetch = async (path, options = {}) => {
  const token = await getToken();                // from Supabase session
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (res.status === 401) { signOut(); return; }
  if (res.status === 403) { redirect('/pricing'); return; }
  return res.json();
};

// Component uses apiService, never raw fetch
import { fetchComplaints } from '../services/apiService';
const data = await fetchComplaints();
```

---

## 12. Cross-Component Refresh Pattern

```js
// After a mutation that other components need to know about:
window.dispatchEvent(new Event('refresh-appointments'));

// In the component that should respond:
useEffect(() => {
  const handler = () => fetchData();
  window.addEventListener('refresh-appointments', handler);
  return () => window.removeEventListener('refresh-appointments', handler);
}, []);
```

Used by: chatbot mutations, voice webhook detection, appointment CRUD.

---

## 13. AI Chatbot — Key Facts

- **Model:** `gpt-4o-mini` (OpenAI)
- **Entry:** `run_chat(messages, db)` → `(reply: str, refresh_needed: bool)`
- **Context window:** last 10 messages sent to OpenAI (truncation)
- **Date injection:** `_SYSTEM_PROMPT_BASE` has `{today}` placeholder → filled at call time
- **Tool result format:** always string (not dict) — LLM reads string to form reply
- **`refresh_needed = True`:** returned when any write tool fires; frontend uses this to reload data
- **Hallucination guard:** catch `BadRequestError` where `"tool_use_failed" in str(e)`, retry without tools

---

## 14. Groq Complaint Extraction — Key Facts

- **Model:** `llama-3.3-70b-versatile` (NOT 3.1 — it's decommissioned)
- **Entry:** `extract_complaint_from_transcript(transcript)` in `ai/extractor.py`
- **Returns:** `{flat_number, category, priority, description}`
- **Validation:** `category` must be in `ALLOWED_CATEGORIES` — hallucinated values rejected
- **Never fabricates:** missing fields returned as `null`, never guessed

```python
ALLOWED_CATEGORIES = [
    "water", "electricity", "cleaning",
    "noise", "maintenance", "security", "other"
]
```

---

## 15. Stripe Subscription Flow

```
1. User hits 403 → frontend redirects to /pricing
2. Frontend → POST /payments/create-checkout-session
3. Backend creates Checkout session (14-day trial + $1 card verify)
4. User completes checkout on Stripe-hosted page
5. Stripe fires webhook events to POST /payments/webhook
6. Backend deduplicates via stripe_events table (event_id UNIQUE)
7. Updates subscriptions table: status = trialing → active
8. Frontend polls GET /payments/subscription-status → unlocks app
```

```python
# Subscription states
trialing → active → past_due → cancelled → expired
```

---

## 16. VAPI Provisioning Flow (Per-Manager)

```
Manager creates FIRST property group
  ↓
POST /property-groups fires BackgroundTask: provision_vapi_for_manager(manager_id, svc_db)
  ↓
1. Guard: exit if manager_vapi_config already active
2. Race guard: check if this manager already claimed a pool number (prevents double-claim)
3. Claim oldest 'available' row from twilio_number_pool → mark 'assigned'
4. Create VAPI assistant via build_lease_config(backend_url, manager_id)
5. Link assistant to Twilio number via httpx.patch (SDK broken — use direct HTTP)
6. Upsert manager_vapi_config: status = 'active', phone, assistant_id
  ↓ on failure
Upsert manager_vapi_config: status = 'failed'
```

```
Subsequent property groups → provisioning is SKIPPED (one number per manager, not per group)
```

---

## 17. Feature Flags

Stored in `property_features` table. Per-building toggle.

| Feature Key | Default |
|---|---|
| `rent_management` | enabled |
| `rent_due_date` | enabled |
| `flat_details` | enabled |
| `voice_calls` | enabled |
| `sms_reminders` | **disabled** |
| `email_reminders` | **disabled** |
| `tenant_details` | enabled |
| `tenant_documents` | **disabled** |

```python
# Check in a route
async def route(
    _: None = Depends(require_feature(Feature.SMS_REMINDERS, building_id))
):
```

---

## 18. Status Enums

```python
# Complaints
ComplaintStatus: pending | in-progress | resolved

# Appointments
AppointmentStatus: scheduled | attended | cancelled | completed

# Subscription
SubscriptionStatus: trialing | active | past_due | cancelled | expired

# VAPI provisioning (manager_vapi_config)
ProvisioningStatus: pending | active | failed | not_set_up

# Lease lead qualification
LeadStatus: qualified | not_qualified | unmatched | contacted | toured | converted | lost

# Rent status (on tenants table)
RentStatus: On-time | Upcoming | Overdue | At Risk
```

---

## 19. Environment Variables Reference

### Backend `.env`
```
SUPABASE_URL=
SUPABASE_KEY=                    # anon key
SUPABASE_SERVICE_KEY=            # service role key
SUPABASE_JWT_SECRET=             # for HS256 JWT fallback

STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_ID=

PRIVATE_VAPI_API=                # server-side VAPI SDK key
VAPI_COMPLAINT_ASSISTANT_ID=
VAPI_COMPLAINT_NUMBER_ID=
VAPI_COMPLAINT_PHONE_NUMBER=     # +14382314283
VAPI_SHARED_LEASE_ASSISTANT_ID=
VAPI_SHARED_LEASE_NUMBER_ID=
VAPI_SHARED_LEASE_PHONE_NUMBER=  # +14313415768

OPEN_AI_API=
GROQ_API_KEY=

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=

SENDGRID_API_KEY=
SENDGRID_FROM_EMAIL=

FRONTEND_URL=
BACKEND_URL=
LANDING_PAGE_URL=
ALLOWED_ORIGINS=
```

### Frontend `.env`
```
VITE_SUPABASE_URL=
VITE_SUPABASE_ANON_KEY=
VITE_API_BASE_URL=               # http://localhost:8000 in dev
```

---

## 20. Common Bugs & Fixes

| Bug | Root Cause | Fix |
|---|---|---|
| `parseISO` returns Invalid Date | Space separator in datetime string | Use `strftime("%Y-%m-%dT%H:%M:%S")` — T not space |
| Flat INSERT → 42501 permission denied | RLS INSERT policy blocks anon client | Use `svc` (service-role) for flat INSERT |
| VAPI 422 on int param | VAPI sends `""` for unset int fields | Accept `Optional[str]`, parse with `_parse_int()` |
| Groq calls `brave_search` tool | LLM hallucinating tool names | Catch `BadRequestError` where `"tool_use_failed" in str(e)`, retry without tools |
| BackgroundTask DB expires | Request-scoped client dies when response is sent | Pass `svc_db` (service-role) to background tasks, not `db` |
| Duplicate VAPI number claim | Race condition in provisioning | UNIQUE INDEX on `twilio_number_pool (assigned_manager_id)` guards at DB level |
| VAPI tool calls break silently | `"tool-calls"` in `serverMessages` | Lease agent must use only `["end-of-call-report"]` |
| Stripe duplicate processing | Webhook replays | Deduplicate via `stripe_events` table (`event_id` UNIQUE) |
| `floor_number` causes 500 | DB has NULL, Pydantic field typed `int` | Type as `Optional[int] = None` |
| Chatbot can't see today's date | System prompt has no date | Inject `{today}` → `datetime.now().strftime("%A, %B %d, %Y")` |
| VAPI SDK `phone_numbers.update()` broken | SDK bug in installed version | Use `httpx.patch("https://api.vapi.ai/phone-number/{id}", ...)` directly |

---

## 21. Learning Material Index

All files in `docs/learning_material/`:

| File | Module | Topic |
|---|---|---|
| `index.html` | — | Dashboard — module grid, quick start, architecture |
| `module_00_setup.html` | 00 | Project setup, env vars, Supabase project |
| `module_01_fastapi_entry.html` | 01 | main.py, config.py, CORS, router registration |
| `module_02_database_layer.html` | 02 | Supabase SDK, anon vs service client, RLS |
| `module_03_auth_jwt.html` | 03 | JWT validation, get_authenticated_db, Depends() |
| `module_04_subscription_stripe.html` | 04 | Stripe Checkout, webhooks, subscription gate |
| `module_05_property_groups_buildings.html` | 05 | Group→Building CRUD, cascade delete |
| `module_06_flats_assignment.html` | 06 | Flat CRUD, bidirectional FK, service-role INSERT |
| `module_07_tenants_computed.html` | 07 | Tenant CRUD, computed lease fields, Pydantic V2 |
| `module_08_complaints_appointments.html` | 08 | Complaints + appointments, VAPI-safe endpoints |
| `module_09_groq_extraction.html` | 09 | Groq LLM, structured extraction, hallucination guard |
| `module_10_openai_chatbot.html` | 10 | OpenAI tool calling, chatbot, refresh_needed |
| `module_11_vapi_webhook.html` | 11 | VAPI webhook, always-200, call log, service DB |
| `module_12_vapi_provisioning.html` | 12 | Agent config, Twilio pool, BackgroundTask, race guard |
| `module_13_notifications.html` | 13 | Twilio SMS, SendGrid email, notification service |
| `module_14_feature_flags.html` | 14 | Feature enum, DB-backed flags, FastAPI dependency |
| `module_15_bulk_import.html` | 15 | CSV/XLSX import, AI column mapping, two-step flow |
| `module_16_leasing.html` | 16 | Listings CRUD, lead pipeline, VAPI search endpoints |
| `module_17_frontend_setup.html` | 17 | Vite, Tailwind, React 18, main.jsx, proxy config |
| `module_18_auth_context.html` | 18 | Supabase PKCE, Google OAuth, AuthContext |
| `module_19_api_service.html` | 19 | apiService.js, authFetch, global error handling |
| `module_20_dashboard_charts.html` | 20 | Dashboard, Recharts, KPI cards, bento grid |
| `module_21_properties_buildings.html` | 21 | PropertiesPage, modals, image upload, UnitListPanel |
| `module_22_tenant_management.html` | 22 | TenantManagement, lease display, assign/unassign |
| `module_23_complaints_calendar.html` | 23 | ComplaintsPage, CalendarView, cross-linked modals |
| `module_24_voice_leasing_ui.html` | 24 | VoiceStatsTab, LeasingTab, provisioning status UI |
| `module_25_chatbot_outbound.html` | 25 | Chatbot FAB, markdown, OutboundCallButton |
| `module_26_settings_onboarding.html` | 26 | SettingsPage, SmsWorkflow, react-joyride onboarding |

---

## 22. Dev Server Commands

```bash
# Backend
cd backend
python -m uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm run dev          # starts on http://localhost:5173

# Run both at once (separate terminals)
# Backend: http://localhost:8000
# Frontend: http://localhost:5173 (proxies /api → :8000 via vite.config.js)
```

---

## 23. Useful Admin Scripts

```bash
# Add a Twilio number to the VAPI number pool
python backend/scripts/add_twilio_number_to_vapi.py +1XXXXXXXXXX

# Push latest agent config to all active per-manager lease assistants
python backend/scripts/update_lease_agents.py

# Push latest config to complaint agent + shared lease agent
python backend/scripts/update_shared_agents.py

# Provision VAPI for existing property groups that don't have one yet
python backend/scripts/reprovision_existing_groups.py
```

---

*Part of the Tenant Management MVP learning material. Companion to `docs/learning_material/index.html`.*
