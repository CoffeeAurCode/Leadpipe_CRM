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
- **Rent tracking** per flat with payment schedules
- **Bulk CSV import** for properties and tenants
- **Stripe subscription** gate — managers must have an active subscription
- Per-building **feature flags** (rent management, voice, SMS reminders, etc.)
- **Onboarding tour** (react-joyride) with checklist tracked in Supabase

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
| description, address, image_url | text | |
| manager_id | UUID | FK → auth.users (RLS key) |

#### `buildings`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name, description, address, image_url | text | |
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
| address, floor_number | text/int | |
| bedrooms, bathrooms | int | |
| occupied | boolean | Derived from tenant_uuid presence |
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
| notes | text | |
| manager_id | UUID | RLS key |

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
| PATCH | `/tenants/{uuid}` | Update tenant info |
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
| GET | `/flats` | List flats (optional `?building_id=`) |
| GET | `/flats/{uuid}` | Single flat with tenant details |
| PATCH | `/flats/{uuid}` | Update flat |
| DELETE | `/flats/{uuid}` | Delete flat |
| POST | `/flats/{uuid}/upload-image` | Upload cover image → Supabase Storage |
| POST | `/flats/{uuid}/assign-tenant` | Assign existing tenant to flat |
| POST | `/flats/{uuid}/unassign-tenant` | Remove tenant from flat |

**VAPI rules:** Always returns HTTP 200. Inputs normalized with `.strip().upper()`.

---

### `/appointments` — `routes/appointments.py`
| Method | Path | Description |
|---|---|---|
| GET | `/appointments/view?flat_number=` | **VAPI tool** — returns active appointments for flat |
| PATCH | `/appointments/update?flat_number=&id=&new_appointment_date=` | **VAPI tool** — reschedule |
| POST | `/appointments/cancel?flat_number=&id=` | **VAPI tool** — cancel |
| POST | `/appointments` | Create appointment |
| GET | `/appointments` | List all (optional filters) |
| GET | `/appointments/{id}` | Single appointment |
| PATCH | `/appointments/{id}` | Update |
| DELETE | `/appointments/{id}` | Soft-delete via status change |

---

### `/buildings` — `routes/buildings.py`
| Method | Path | Description |
|---|---|---|
| POST | `/buildings` | Create building |
| GET | `/buildings` | List all with unit counts aggregated from flats |
| GET | `/buildings/{id}` | Single building |
| PATCH | `/buildings/{id}` | Update |
| DELETE | `/buildings/{id}` | Delete |

---

### `/properties-list` — `routes/property_groups.py`
| Method | Path | Description |
|---|---|---|
| POST | `/properties-list` | Create property group |
| GET | `/properties-list` | List all |
| GET | `/properties-list/{id}` | Single |
| PATCH | `/properties-list/{id}` | Update |
| DELETE | `/properties-list/{id}` | Delete |

---

### `/properties` — `routes/properties.py`
| Method | Path | Description |
|---|---|---|
| GET | `/properties` | Returns flats mapped as properties (name, address, bedrooms, bathrooms, image_url, occupied) |

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

### `/call-logs` — `routes/call_logs.py`
| Method | Path | Description |
|---|---|---|
| GET | `/call-logs` | List call logs (optional filters: phone, flat_number, complaint_status) |
| GET | `/call-logs/{id}` | Single call log |

---

### `/chat` — `routes/chat.py`
| Method | Path | Description |
|---|---|---|
| POST | `/chat` | Accept conversation history `{messages: [...]}`, return `{reply, refresh_needed}` |

---

### `/voice` — `routes/voice.py`
| Method | Path | Description |
|---|---|---|
| POST | `/voice/webhook` | Vapi webhook — processes call events, creates CallLog, optionally creates Complaint |
| GET | `/voice/call-status` | Returns `{last_call_ended_at}` for frontend polling |

**Webhook behavior:**
- Always returns HTTP 200 (keeps Vapi session alive)
- Filters on final event types: `tool-calls`, `end-of-call-report`
- Creates CallLog always
- Creates Complaint only if user confirmed via VAPI tool call

---

### `/notifications` — `routes/notifications.py`
| Method | Path | Description |
|---|---|---|
| POST | `/notifications/test-sms` | Send test SMS |
| POST | `/notifications/test-email` | Send test email |
| GET | `/notifications/preferences` | Notification settings per building |

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
| POST | `/import/properties` | CSV → PropertyGroup + Building + Flat hierarchy |
| POST | `/import/tenants` | CSV → Tenants linked to existing flats |

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
Single `Settings` class loading all env vars via pydantic-settings. Imported as `settings` singleton.

Key vars: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`, `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `VAPI_API_KEY`, `VAPI_NUMBER_ID`, `VAPI_ASSISTANT_ID`, `OPENAI_API_KEY`, `GROQ_API_KEY`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER`, `SENDGRID_API_KEY`, `SENDGRID_FROM_EMAIL`, `FRONTEND_URL`, `LANDING_PAGE_URL`, `ALLOWED_ORIGINS`.

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
| `components/PropertiesPage.jsx` | Property + building listing |
| `components/TenantManagement.jsx` | Tenant CRUD, lease info, rent status |
| `components/CalendarView.jsx` | Month calendar + day panel for appointments |
| `components/SettingsPage.jsx` | Manager settings + per-building feature flags |
| `components/RentTab.jsx` | Set/view monthly rents per flat |
| `components/VoiceStatsTab.jsx` | Voice call analytics |
| `components/SmsWorkflow.jsx` | Bulk SMS broadcast to tenants |
| `components/OnboardingChecklist.jsx` | Interactive onboarding checklist |

### Modals
| File | Purpose |
|---|---|
| `ComplaintModal.jsx` | Create/edit complaint |
| `ComplaintDetailModal.jsx` | View complaint + linked appointments |
| `AppointmentModal.jsx` | Create appointment |
| `AppointmentDetailModal.jsx` | View/edit appointment + linked complaints |
| `FlatDetailModal.jsx` | Flat details |
| `FlatEditModal.jsx` | Edit flat |
| `TenantProfile.jsx` | Tenant detail modal |
| `AddPropertyModal.jsx` | Create PropertyGroup |
| `AddBuildingModal.jsx` | Create Building |
| `AddPropertyGroupModal.jsx` | Alias for property group creation |
| `AddTenantModal.jsx` | Create Tenant |
| `AssignTenantModal.jsx` | Assign existing tenant to flat |
| `BuildingInfoModal.jsx` | Building detail |
| `CsvImportModal.jsx` | CSV bulk import UI |
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
| `UnitListPanel.jsx` | Flat list panel within a building |

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
| `Sidebar.jsx` | Main nav sidebar with route switching |
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
| `OutboundCallButton.jsx` | Trigger outbound VAPI call |
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
window.dispatchEvent(new Event('refresh-appointments'))
```
Used after voice/chatbot actions that modify data.

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
| Vapi.ai | Voice phone agent | `VAPI_API_KEY`, `VAPI_NUMBER_ID`, `VAPI_ASSISTANT_ID` |
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

1. Tenant calls the VAPI number
2. VAPI agent (`VAPI_ASSISTANT_ID`) handles conversation
3. For caller ID: VAPI calls `POST /flats/verify-phone` with phone number
4. For tenant lookup: VAPI calls `GET /tenants/by-flat/{flat_no}`
5. For appointments: VAPI calls `/appointments/view`, `/appointments/update`, `/appointments/cancel`
6. At call end: VAPI fires `POST /voice/webhook` with transcript + event data
7. Backend: creates `CallLog` always; creates `Complaint` only if user confirmed via tool
8. Frontend polls `GET /voice/call-status` every 3 seconds to detect new calls
