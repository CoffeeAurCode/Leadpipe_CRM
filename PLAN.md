# Tenant Management MVP — Learning Material Plan

> Phase 1 of 2. Review this plan and reply **"approved"** when ready to build.

---

## MODULE BREAKDOWN

The project is split into **27 modules (00–26)** organized into 6 build sessions.
Each module produces one self-contained HTML file in `learning_material/`.

---

### PART A — Backend Foundation (Build Session 1)

#### Module 00 — Project Setup & Environment
**Source files:** `backend/.env.example`, `backend/requirements.txt`, `backend/schema.sql`
**Learner outcome:** Can scaffold the project from nothing — install dependencies, connect to Supabase, read the DB schema.
**Concepts:** Python virtual environments, pip/requirements.txt, environment variables, Supabase project creation, PostgreSQL schema reading, `.env` safety.

---

#### Module 01 — FastAPI Application Entry Point
**Source files:** `backend/app/main.py`, `backend/app/config.py`
**Learner outcome:** Can create a multi-router FastAPI app with CORS, import a Settings singleton from env vars, and understand how the entire backend is wired together in one place.
**Concepts:** FastAPI app factory, `APIRouter`, `include_router`, `CORSMiddleware`, Pydantic Settings, `os.getenv`, startup events, Uvicorn.

---

#### Module 02 — Database Layer (Supabase SDK)
**Source files:** `backend/app/db/session.py`, `backend/app/db/models.py`
**Learner outcome:** Understands the two-client pattern (anon vs service-role), can make Supabase queries, and knows why SQLAlchemy is avoided here.
**Concepts:** Supabase Python SDK, anon vs service-role clients, Row Level Security (RLS), PostgREST query builder, `select/insert/update/delete/eq/ilike`, why not to use SQLAlchemy with Supabase.

---

#### Module 03 — Authentication & JWT Validation
**Source files:** `backend/app/dependencies/auth.py`, `backend/app/dependencies/authenticated_db.py`
**Learner outcome:** Can write a FastAPI dependency that validates a Supabase JWT and injects an RLS-enforced DB client.
**Concepts:** FastAPI `Depends()`, JWT (ES256 / HS256), JWKS, Bearer tokens, `python-jose`, how Supabase RLS resolves `auth.uid()` from the token, `postgrest.auth()`.

---

#### Module 04 — Subscription Gate (Stripe Basics)
**Source files:** `backend/app/dependencies/subscription.py`, `backend/app/routes/payments.py`
**Learner outcome:** Can add a subscription check dependency to any route, implement Stripe Checkout with a trial, and handle Stripe webhooks idempotently.
**Concepts:** FastAPI dependency chaining, Stripe Checkout Sessions, trial periods, `stripe.Webhook.construct_event`, webhook idempotency (unique event ID), `subscriptions` table state machine (`trialing → active → past_due → cancelled`).

---

### PART B — Core Data Layer (Build Session 2)

#### Module 05 — Property Groups & Buildings
**Source files:** `backend/app/routes/property_groups.py`, `backend/app/routes/buildings.py`, `backend/app/schemas/` (relevant parts)
**Learner outcome:** Can build full CRUD routes for a two-level hierarchy (Group → Building), including cascade-delete logic.
**Concepts:** FastAPI CRUD pattern, Pydantic V2 `BaseModel`, nested data hierarchies, cascade delete strategies, UUID primary keys, `manager_id` RLS pattern, background tasks, `BackgroundTasks`.

---

#### Module 06 — Flats & Tenant Assignment
**Source files:** `backend/app/routes/flats.py`, `backend/app/schemas/flat.py`
**Learner outcome:** Can handle bidirectional FK links, normalize user input, use a service-role client for specific inserts, and map PostgreSQL error codes to user-friendly messages.
**Concepts:** Bidirectional FK pattern (`flats.tenant_uuid` ↔ `tenants.flat_uuid`), input normalization (`.strip().upper()`), service-role bypass for INSERT policies, PostgreSQL error codes (`42501`, `23505`, `23503`), `_clean_db_error` helper pattern, UNIQUE constraints.

---

#### Module 07 — Tenants & Computed Lease Fields
**Source files:** `backend/app/routes/tenants.py`, `backend/app/schemas/tenant.py`
**Learner outcome:** Can write Pydantic models that compute derived fields from raw DB data, and understand the three-layer status rule (DB truth → computed field → frontend display).
**Concepts:** Pydantic V2 `model_validator(mode='after')`, computed properties (`tenancy_duration_months`, `lease_status`), `Optional` fields, date arithmetic with `datetime`, IST timezone handling.

---

#### Module 08 — Complaints & Appointments
**Source files:** `backend/app/routes/complaints.py`, `backend/app/routes/appointments.py`, `backend/app/schemas/complaint.py`, `backend/app/schemas/appointment.py`, `backend/app/core/constants.py`
**Learner outcome:** Can link two tables (complaint → appointment), enforce category constraints, implement VAPI-safe endpoints (always HTTP 200), and handle soft-delete via status changes.
**Concepts:** FK joins via Supabase SDK, `CHECK` constraints in queries, denormalized fields (flat_number stored on appointment for VAPI speed), soft delete vs hard delete, IST datetime formatting (`YYYY-MM-DDTHH:MM:SS`).

---

### PART C — AI & Voice Integration (Build Session 3)

#### Module 09 — AI Complaint Extraction (Groq)
**Source files:** `backend/app/ai/extractor.py`, `backend/app/ai/validator.py`, `backend/app/core/constants.py`
**Learner outcome:** Can call the Groq LLM API to extract structured data from free-text, validate the output, and handle LLM unreliability.
**Concepts:** Groq Python SDK, structured extraction with JSON prompts, output validation against enum lists, hallucination guards, why `llama-3.3-70b-versatile` (not 3.1), prompt engineering for extraction vs chat.

---

#### Module 10 — AI Chatbot with Tool Calling (OpenAI)
**Source files:** `backend/app/ai/chatbot.py`, `backend/app/routes/chat.py`
**Learner outcome:** Can build a multi-turn chatbot with tool calling, inject dynamic context (today's date), truncate history to manage costs, and detect when tools mutate data so the frontend can refresh.
**Concepts:** OpenAI `gpt-4o-mini`, tool calling schema (`function`, `parameters`, `required`), multi-turn message history format, `{today}` placeholder injection, context truncation (last 10 messages), `refresh_needed` signal, `BadRequestError` hallucination fallback, Groq tool quirk workaround.

---

#### Module 11 — VAPI Voice Webhook & Call Flow
**Source files:** `backend/app/routes/voice.py`, `backend/app/services/notifications.py` (partial)
**Learner outcome:** Can implement a webhook handler for a voice AI platform, create records from transcript data, and understand why webhooks must always return 200.
**Concepts:** VAPI webhook architecture, `end-of-call-report` vs `tool-calls` events, always-200 pattern, `call_id` UNIQUE idempotency, service-role DB (no JWT on webhook calls), transcript → complaint extraction pipeline, `GET /voice/call-status` polling pattern.

---

#### Module 12 — VAPI Agent Configuration & Provisioning
**Source files:** `backend/app/services/vapi_agent_config.py`, `backend/app/services/vapi_provisioning.py`, `backend/scripts/update_lease_agents.py`
**Learner outcome:** Can configure a VAPI assistant programmatically, provision per-manager phone numbers from a pool, and handle race conditions in background tasks.
**Concepts:** VAPI Python SDK, ElevenLabs voice config, Deepgram transcriber, tool definitions for voice agents, per-manager provisioning pattern, Twilio number pool, `BackgroundTask` lifetime (must use service DB), optimistic lock pattern, race condition guards (UNIQUE index on `assigned_manager_id`), httpx direct HTTP (SDK bug workaround), bilingual agent config.

---

### PART D — Integrations & Advanced Features (Build Session 4)

#### Module 13 — SMS & Email Notifications
**Source files:** `backend/app/integrations/twilio_client.py`, `backend/app/integrations/email_client.py`, `backend/app/services/notifications.py`
**Learner outcome:** Can integrate Twilio SMS and SendGrid email, orchestrate multiple notification channels from a single service function, and make notifications non-blocking.
**Concepts:** Twilio Python SDK, SendGrid Python SDK, notification orchestration pattern, non-blocking background notifications (errors logged, not raised), feature-flag-gated notifications, appointment lifecycle event types.

---

#### Module 14 — Feature Flags
**Source files:** `backend/app/core/features.py`, `backend/app/dependencies/features.py`, `backend/app/services/feature_service.py`, `backend/app/routes/settings.py` (features section)
**Learner outcome:** Can implement a per-building feature flag system with database storage and a FastAPI dependency.
**Concepts:** `Enum` for feature keys, per-entity feature storage pattern, FastAPI dependency for feature checking, `property_features` table lookup, default-on vs default-off features.

---

#### Module 15 — Bulk Import (CSV/XLSX + AI Column Mapping)
**Source files:** `backend/app/routes/import_routes.py`
**Learner outcome:** Can build a smart file import endpoint that handles both CSV and Excel, uses AI to map non-standard column names, and applies the mapping before processing.
**Concepts:** `pandas`-free CSV parsing (stdlib `csv` module), `openpyxl` for Excel, async `AsyncOpenAI` for column mapping, `_apply_mapping` pattern, BOM handling (`utf-8-sig`), two-step import flow (analyze → import), multi-part form data (`UploadFile`).

---

#### Module 16 — Leasing Module (Listings + Lead Pipeline)
**Source files:** `backend/app/routes/leasing.py`, `backend/app/schemas/leasing.py`
**Learner outcome:** Can build a dual-audience route file (VAPI tool endpoints + manager CRUD), handle VAPI's quirky empty-string parameters, and implement lead pipeline state management.
**Concepts:** Dual-audience route design (no-auth VAPI vs auth manager), `Optional[str]` for VAPI int params (empty-string problem), `_parse_int`/`_parse_float` helpers, JSONB `custom_rules`, UUID array `interested_listing_ids`, CSV export (`io.StringIO`, `csv.DictWriter`), lead qualification state machine.

---

### PART E — Frontend Foundation (Build Session 5)

#### Module 17 — Frontend Setup (Vite + Tailwind + React 18)
**Source files:** `frontend/vite.config.js`, `frontend/tailwind.config.js`, `frontend/package.json`, `frontend/src/main.jsx`
**Learner outcome:** Can scaffold a Vite + React 18 + Tailwind project, understand the build pipeline, and configure a dev proxy for the backend.
**Concepts:** Vite project structure, HMR, Tailwind JIT, PostCSS, `ReactDOM.createRoot`, `StrictMode`, Vite proxy config (avoids CORS in dev), dependency overview (Framer Motion, Lucide React, Recharts, date-fns, react-joyride).

---

#### Module 18 — Auth Context & Google OAuth (Supabase PKCE)
**Source files:** `frontend/src/lib/supabase.js`, `frontend/src/context/AuthContext.jsx`, `frontend/src/components/AuthPage.jsx`
**Learner outcome:** Can implement Google OAuth with Supabase's PKCE flow in React, manage session state via context, and auto-create a manager profile on first sign-in.
**Concepts:** Supabase PKCE flow (vs implicit), `onAuthStateChange`, React Context + Provider pattern, `ensureManagerProfile` upsert-on-login, JWT token extraction from session, OAuth redirect handling.

---

#### Module 19 — API Service Layer
**Source files:** `frontend/src/services/apiService.js`
**Learner outcome:** Can centralize all HTTP calls in one service module, implement an `authFetch` wrapper that auto-attaches tokens and handles auth errors globally.
**Concepts:** Service module pattern (vs inline fetch), `authFetch` wrapper, `Authorization: Bearer` header injection, global 401/403 handling (sign out / redirect), `FormData` for file uploads, query-string construction.

---

#### Module 20 — Dashboard & Charts
**Source files:** `frontend/src/components/Dashboard.jsx`, `frontend/src/components/BentoDashboard.jsx`, `frontend/src/components/dashboard/` (all chart files), `frontend/src/components/dashboard/KPICard.jsx`
**Learner outcome:** Can build a data dashboard with Recharts, design KPI cards, and implement a bento-grid layout.
**Concepts:** Recharts (`LineChart`, `PieChart`, `BarChart`, `ResponsiveContainer`), bento-grid CSS (CSS Grid), KPI card patterns, `useMemo` for chart data transforms, Framer Motion `AnimatePresence`, loading skeleton states.

---

#### Module 21 — Properties & Buildings Management
**Source files:** `frontend/src/components/PropertiesPage.jsx`, `frontend/src/components/PropertyGroupCard.jsx`, `frontend/src/components/BuildingCard.jsx`, `frontend/src/components/AddPropertyModal.jsx`, `frontend/src/components/AddBuildingModal.jsx`, `frontend/src/components/UnitListPanel.jsx`, `frontend/src/components/ImageUploadField.jsx`
**Learner outcome:** Can build a multi-level entity manager (group → building → flat) with modals for CRUD, image upload to Supabase Storage, and cascading data fetches.
**Concepts:** Modal pattern in React, controlled form state, Supabase Storage upload via API endpoint, optimistic UI updates, cascading fetch (select group → fetch buildings → fetch flats), Lucide React icons.

---

### PART F — Frontend Advanced (Build Session 6)

#### Module 22 — Tenant Management
**Source files:** `frontend/src/components/TenantManagement.jsx`, `frontend/src/components/TenantProfile.jsx`, `frontend/src/components/AddTenantModal.jsx`, `frontend/src/components/AssignTenantModal.jsx`
**Learner outcome:** Can display computed lease fields from the API, implement tenant CRUD with bidirectional flat assignment, and show lease status badges.
**Concepts:** Consuming computed API fields (lease_status, remaining_time_on_lease_days), bidirectional assign/unassign pattern, `PATCH /flats/{uuid}/assign-tenant` vs tenant CRUD, document URL arrays, date-fns `parseISO` / `format`.

---

#### Module 23 — Complaints & Appointments UI
**Source files:** `frontend/src/components/ComplaintsPage.jsx`, `frontend/src/components/ComplaintModal.jsx`, `frontend/src/components/ComplaintDetailModal.jsx`, `frontend/src/components/AppointmentModal.jsx`, `frontend/src/components/AppointmentDetailModal.jsx`, `frontend/src/components/CalendarView.jsx`, `frontend/src/constants/status.js`
**Learner outcome:** Can build a multi-view list (table/card/calendar) with filters, cross-linked detail modals, and a calendar that shows data by day.
**Concepts:** View switcher pattern, category/status filter composition, detail modal with linked records, `react-calendar` (or custom grid), `cross-component event dispatch` (`window.dispatchEvent`), status color config pattern.

---

#### Module 24 — Voice Stats & Leasing UI
**Source files:** `frontend/src/components/VoiceStatsTab.jsx`, `frontend/src/components/LeasingTab.jsx`, `frontend/src/components/AddListingModal.jsx`, `frontend/src/components/LeadDetailModal.jsx`
**Learner outcome:** Can build analytics dashboards that aggregate call data, implement a full lead pipeline UI, and display provisioning state (pending/active/failed) with retry logic.
**Concepts:** Metrics aggregation from API, lead pipeline status workflow, VAPI provisioning status polling (8s auto-poll after retry), debounced retry guard, `interested_listing_ids` chip display, CSV export download trigger.

---

#### Module 25 — Chatbot UI & Outbound Calls
**Source files:** `frontend/src/components/Chatbot.jsx`, `frontend/src/components/OutboundCallButton.jsx`
**Learner outcome:** Can build a floating FAB chatbot with markdown rendering, conversation history, and scroll-to-bottom behavior; can trigger outbound VAPI calls from the UI.
**Concepts:** Floating Action Button (FAB) pattern, `useRef` for scroll-to-bottom, markdown rendering (without external library or with `marked.js` embedded), conversation history management, `refresh_needed` → data reload event, E.164 phone number input, agent type selector.

---

#### Module 26 — Settings, Notifications, Onboarding & SMS Broadcast
**Source files:** `frontend/src/components/SettingsPage.jsx`, `frontend/src/components/SmsWorkflow.jsx`, `frontend/src/components/OnboardingChecklist.jsx`, `frontend/src/components/OnboardingTour.jsx`, `frontend/src/context/OnboardingContext.jsx`, `frontend/src/config/onboardingTours.js`, `frontend/src/components/PropertySettings.jsx`
**Learner outcome:** Can implement per-building feature flag toggles, an SMS broadcast system with templates, and a react-joyride guided tour tracked in both localStorage and the database.
**Concepts:** Feature flag toggle UI (per-building), SMS template CRUD, react-joyride tour definitions, dual-persistence (localStorage + DB), `triggerTour(section)` context API, `manager_notifications` preferences.

---

## FINAL FILE STRUCTURE

```
learning_material/
├── index.html                        # Dashboard — module grid, progress, architecture diagram, quick start
├── module_00_setup.html              # Project setup, env vars, Supabase project creation
├── module_01_fastapi_entry.html      # main.py, config.py, CORS, router registration
├── module_02_database_layer.html     # Supabase SDK, anon vs service client, RLS
├── module_03_auth_jwt.html           # JWT validation, authenticated_db, Depends()
├── module_04_subscription_stripe.html # Stripe Checkout, webhooks, subscription gate
├── module_05_property_groups_buildings.html # Group→Building CRUD, cascade delete
├── module_06_flats_assignment.html   # Flat CRUD, bidirectional FK, service-role INSERT
├── module_07_tenants_computed.html   # Tenant CRUD, computed lease fields, Pydantic V2
├── module_08_complaints_appointments.html # Complaints + appointments, VAPI-safe endpoints
├── module_09_groq_extraction.html    # Groq LLM, structured extraction, hallucination guard
├── module_10_openai_chatbot.html     # OpenAI tool calling, chatbot, refresh_needed
├── module_11_vapi_webhook.html       # VAPI webhook, always-200, call log, service DB
├── module_12_vapi_provisioning.html  # Agent config, Twilio pool, BackgroundTask, race guard
├── module_13_notifications.html      # Twilio SMS, SendGrid email, notification service
├── module_14_feature_flags.html      # Feature enum, DB-backed flags, FastAPI dependency
├── module_15_bulk_import.html        # CSV/XLSX import, AI column mapping, two-step flow
├── module_16_leasing.html            # Listings CRUD, lead pipeline, VAPI search endpoints
├── module_17_frontend_setup.html     # Vite, Tailwind, React 18, main.jsx, proxy config
├── module_18_auth_context.html       # Supabase PKCE, Google OAuth, AuthContext, profile creation
├── module_19_api_service.html        # apiService.js, authFetch, global error handling
├── module_20_dashboard_charts.html   # Dashboard, Recharts, KPI cards, bento grid
├── module_21_properties_buildings.html # PropertiesPage, modals, image upload, UnitListPanel
├── module_22_tenant_management.html  # TenantManagement, lease display, assign/unassign
├── module_23_complaints_calendar.html # ComplaintsPage, CalendarView, cross-linked modals
├── module_24_voice_leasing_ui.html   # VoiceStatsTab, LeasingTab, provisioning status UI
├── module_25_chatbot_outbound.html   # Chatbot FAB, markdown, OutboundCallButton
└── module_26_settings_onboarding.html # SettingsPage, SmsWorkflow, react-joyride onboarding

WORKSHEET.md                          # Quick-reference text file (project root)
```

Total: 27 module HTML files + 1 index + 1 WORKSHEET = **29 files**

---

## BUILD SESSION PLAN

Because each HTML file is large (500–1000+ lines with inline CSS, JS, full content, and syntax-highlighted code), the build is split into **6 sessions**:

| Session | Modules | Files |
|---|---|---|
| **Session 1** | 00–04 | module_00 → module_04 (5 files) |
| **Session 2** | 05–08 | module_05 → module_08 (4 files) |
| **Session 3** | 09–12 | module_09 → module_12 (4 files) |
| **Session 4** | 13–16 | module_13 → module_16 (4 files) |
| **Session 5** | 17–21 | module_17 → module_21 (5 files) |
| **Session 6** | 22–26 + index + WORKSHEET | module_22 → module_26, index.html, WORKSHEET.md (7 files) |

After each session, the files can be opened immediately in a browser.

---

## KEY DESIGN DECISIONS TABLE

| Decision | Why | What you'd do differently without this constraint |
|---|---|---|
| **FastAPI over Django/Flask** | Async-first, automatic OpenAPI docs, Pydantic V2 native, fastest Python framework for I/O-bound routes | Django REST Framework if team already knows Django; Flask if project is simple CRUD only |
| **Supabase SDK (not SQLAlchemy)** | Supabase client respects RLS automatically; SQLAlchemy bypasses RLS and requires a separate row-level auth layer | SQLAlchemy + manual WHERE manager_id=? on every query (error-prone); or Prisma if using Node |
| **Two Supabase clients (anon + service)** | Anon client with `postgrest.auth(token)` enforces RLS for user routes; service-role client is needed for webhooks (no JWT), admin ops, and specific INSERT policies | Single service-role client everywhere — simpler but dangerous (any bug exposes all tenant data) |
| **No `/api` prefix on routes** | Keeps URLs shorter; frontend proxy rewrites `/complaints` → `http://localhost:8000/complaints`; avoids double-prefix bugs | Standard `/api/v1/` prefix if deploying multiple API versions or if frontend is on the same domain |
| **All frontend HTTP through `apiService.js`** | Single place to add/change auth headers, base URL, and error handling; prevents 30+ duplicated `fetch()` calls each needing their own auth logic | Inline fetch per component — works but means changing auth requires touching every component |
| **Pydantic V2 `model_validator` (not V1 `@validator`)** | V1 validators are deprecated and removed in V2; `model_validator(mode='after')` runs after all fields are set, needed for computed fields that depend on multiple fields | Pydantic V1 if on an older codebase — but migration to V2 is painful to defer |
| **VAPI endpoints always return HTTP 200** | VAPI SDK interprets non-200 as a fatal error and kills the call session immediately; error info is returned in the JSON body instead | Standard REST error codes (400/404/500) for non-voice endpoints — always correct for browser clients |
| **Date format `YYYY-MM-DDTHH:MM:SS` (T separator)** | JavaScript `parseISO` (date-fns) requires the T separator; space separator causes silent parse failures that show as "Invalid Date" in the UI | ISO 8601 with timezone offset (`+05:30`) if storing UTC and converting in frontend — cleaner but requires frontend timezone handling |
| **Data stored as IST (not UTC)** | Simpler for a Canada-focused product (IST is a business decision, not best practice); avoids timezone conversion bugs on display | Store as UTC + convert to user's timezone on display — correct approach for multi-timezone products |
| **Error mapping `_clean_db_error()`** | PostgreSQL error codes (`42501`, `23505`, `23503`) are opaque to users; mapping them to English prevents "duplicate key value violates unique constraint" leaking to the UI | Catch-all "Database error, please try again" message — simpler but loses actionable information |
| **Stripe trial + $1 verification** | Reduces churn by letting users try before paying; $1 card verify prevents fake signups without charging real money | Free tier with no card — maximizes top-of-funnel but attracts non-serious users; immediate charge — maximizes revenue per user but lowers conversion |
| **VAPI per-manager provisioning (not per-group)** | One phone number per manager (not per property group) reduces Twilio number cost; all groups share the same lease line | One number per property group — cleaner caller experience but 10x the phone number costs |
| **Twilio number pool** | Pre-purchased Twilio numbers are assigned on demand; avoids Twilio API rate limits during account creation; numbers can be recycled | Buy Twilio number programmatically on provisioning — requires Twilio API credentials with number-purchase permission and is slower |
| **`BackgroundTask` for VAPI provisioning** | VAPI assistant creation takes 2-5 seconds; doing it in the request handler would time out the HTTP response | Celery/RQ task queue — better for production scale, adds Redis dependency |
| **OpenAI for chatbot, Groq for extraction** | gpt-4o-mini handles complex multi-turn tool calling reliably; Groq llama is faster/cheaper for one-shot extraction | Single provider — simpler config but either paying more for extraction or getting worse tool calling |
| **`refresh_needed` signal from chatbot** | Chatbot mutations (add building, reschedule appointment) need to trigger UI refresh; returning a boolean in the chat response is simpler than SSE or WebSocket | WebSocket for real-time push — correct at scale, but overkill for a chatbot that mutates data |
| **Functional React components + hooks only** | React 18 best practice; class components are legacy and incompatible with modern hooks (useContext, useEffect patterns) | Class components + lifecycle methods — works but verbose and harder to share logic |
| **All CSS/JS inline in HTML learning files** | Files must work with `file://` protocol in any browser with no server, no build step, no CDN — zero dependencies | External CSS/JS files — smaller HTML but requires a local server (`python -m http.server`) to load |

---

## OPEN QUESTIONS FOR YOU

Before building starts, please decide:

1. **Where should `learning_material/` live?**
   - Option A: `C:\Users\BIT\Coding\Tenant_management_MVP\learning_material\` (project root)
   - Option B: `C:\Users\BIT\Coding\Tenant_management_MVP\docs\learning_material\` (alongside existing md guides)
   - _(Existing markdown guides are in `docs/learning_guides/` — does the HTML material go in `docs/` or root?)_
OPTION B
2. **Which session do you want to build first?**
   - All sessions in order (Sessions 1–6 across 6 conversations)
   - Jump to a specific session (e.g., start with frontend, Session 5)
All sessions in order (Sessions 1–6 across 6 conversations)

3. **Frontend modules — depth of coverage?**
   - Deep: quote every JSX file line-by-line (produces very large HTML files, ~1000+ lines each)
   - Standard: cover every component's purpose, key patterns, and one full walkthrough per module
Deep: quote every JSX file line-by-line (produces very large HTML files, ~1000+ lines each)
4. **Do you want exercises to have full worked solutions?**
   - Yes — full solution code in a deeply nested collapsible (recommended, learner can choose to peek)
   - No — hints only, learner figures it out
Yes — full solution code in a deeply nested collapsible (recommended, learner can choose to peek)
5. **External service accounts** — which of these do you already have set up?
   (This affects which Module 00 setup steps to include as "do this now" vs "you will need later")
   - [ ] Supabase project + service key
   - [ ] Stripe account + webhook endpoint
   - [ ] VAPI.ai account + API key
   - [ ] Twilio account + purchased number
   - [ ] OpenAI API key
   - [ ] Groq API key
   - [ ] SendGrid account + verified sender
I have setup accounts for all of them, i just wanna learn about integration,how to do it, what bugs i faced,how to solve it etc
---

> Review this plan and reply **"approved"** (optionally answering the open questions) when ready to build.
> If you want to change any module scope or add/remove modules, say so before approving.
