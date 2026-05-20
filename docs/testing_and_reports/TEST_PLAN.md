# Tenant Management MVP — Production Readiness Test Plan

> **Goal:** Exhaustive test coverage. When every test in this document passes, the system is production-ready.
> **Audience:** QA, developers, CI pipeline.
> **Reference:** [CODEBASE_CONTEXT.md](./CODEBASE_CONTEXT.md) for architecture details.

---

## Table of Contents

1. [Test Strategy](#1-test-strategy)
2. [Test Environment Setup](#2-test-environment-setup)
3. [Backend Unit Tests](#3-backend-unit-tests)
4. [Backend Integration Tests — All Routes](#4-backend-integration-tests--all-routes)
5. [Frontend Component Tests](#5-frontend-component-tests)
6. [Frontend E2E Tests](#6-frontend-e2e-tests)
7. [External Integration Tests](#7-external-integration-tests)
8. [Security & Authorization Tests](#8-security--authorization-tests)
9. [Performance & Load Tests](#9-performance--load-tests)
10. [Data Integrity Tests](#10-data-integrity-tests)
11. [Production Readiness Checklist](#11-production-readiness-checklist)

---

## 1. Test Strategy

### Test Pyramid
| Layer | Coverage Target | Tooling |
|---|---|---|
| Unit (backend logic, frontend helpers) | 80%+ | pytest + Vitest |
| Integration (routes + DB) | All endpoints, all status codes | pytest + httpx + test Supabase project |
| E2E (full user flows) | Critical happy paths + 3 error paths each | Playwright |
| Security | All RLS boundaries, auth, sub gate | pytest + manual penetration tests |
| Load | 100 concurrent users for 10 min | k6 |

### Tooling
- **Backend:** pytest, pytest-asyncio, httpx, faker, freezegun
- **Frontend:** Vitest, React Testing Library, MSW (mock service worker)
- **E2E:** Playwright (Chromium, Firefox, WebKit)
- **Load:** k6
- **Mocking:** Stripe test mode, Vapi test webhooks, Twilio test creds, SendGrid sandbox

---

## 2. Test Environment Setup

### Prerequisites
- [ ] Dedicated test Supabase project (mirrors production schema)
- [ ] Stripe test mode keys
- [ ] Vapi sandbox keys
- [ ] Twilio test credentials
- [ ] SendGrid sandbox API key
- [ ] Test OAuth client (Google) for E2E auth
- [ ] Seed data script (5 managers, 10 properties, 50 flats, 30 tenants, 20 complaints)

### Test User Accounts
| User | Email | Role | Notes |
|---|---|---|---|
| manager_active | test+active@example.com | Active sub | Trial expired, paying |
| manager_trial | test+trial@example.com | Trialing | Day 3 of 14 |
| manager_expired | test+expired@example.com | Past due | Failed payment |
| manager_no_sub | test+nosub@example.com | None | Never subscribed |
| manager_isolated | test+isolated@example.com | Active | Separate tenant data for RLS tests |

### CI Pipeline
```yaml
jobs:
  - unit_backend (pytest)
  - unit_frontend (vitest)
  - integration_backend (pytest with test Supabase)
  - e2e (playwright headless)
  - security_scan (bandit + npm audit)
  - lint (ruff + eslint)
```

---

## 3. Backend Unit Tests

### 3.1 `app/ai/extractor.py`
| Test | Input | Expected |
|---|---|---|
| Extracts complete complaint | Transcript: "Flat A-101, water leak in kitchen, urgent" | `{flat_number: "A-101", category: "water", priority: "high", description: "..."}` |
| Returns None for missing fields | Transcript: "I have a problem" | All fields None |
| Validates category against ALLOWED_CATEGORIES | Transcript with category "plumbing" | Falls back to "maintenance" or "other" |
| Never fabricates flat number | Transcript with no flat | `flat_number: None` |
| Handles empty transcript | `""` | All None, no exception |
| Handles non-English transcripts | Hindi/Spanish | Best-effort or all None |
| Handles 5000+ character transcripts | Long rambling | Truncates safely |
| Groq API failure | Mock 500 response | Returns None, logs error |
| Groq tool_use_failed BadRequestError | Mock error | Catches, retries without tools |

### 3.2 `app/ai/chatbot.py`
| Test | Input | Expected |
|---|---|---|
| Simple greeting | "Hello" | Returns reply, `refresh_needed=False` |
| Date awareness | "Schedule for tomorrow" | Uses correct date from `{today}` |
| Tool call: retrieve_building | "Show me Building Sunrise" | Calls `retrieve_building`, returns details |
| Tool call: add_appointment | "Book appointment for A-101 tomorrow 3pm" | Asks confirmation; on yes, creates appointment, `refresh_needed=True` |
| Confirmation required for writes | "Delete tenant John" | Asks "Are you sure?" before deletion |
| Truncates to last 10 messages | 20-message history | Only last 10 sent to OpenAI |
| Hallucinated tool name | LLM calls `brave_search` | Catches BadRequestError, retries as plain completion |
| Tool result returned as string | Mock tool returning dict | Coerced to string before LLM sees it |
| `building_name` lookup | Tool input has `building_name` | Internally resolved to `building_id` via ilike |
| Reschedule guard | "Reschedule appointment 999" (non-existent) | Returns error, doesn't hallucinate success |

### 3.3 `app/ai/validator.py`
| Test | Input | Expected |
|---|---|---|
| Complete data | All fields filled | `is_complete=True, missing_fields=[]` |
| Missing flat_number | `{category: "water", ...}` | `is_complete=False, missing_fields=["flat_number"]` |
| Missing category | No category | `is_complete=False, missing_fields=["category"]` |
| Missing appointment_date | No date | `is_complete=False, missing_fields=["appointment_date"]` |
| All fields missing | Empty dict | `missing_fields=["flat_number", "category", "appointment_date"]` |

### 3.4 `app/dependencies/auth.py`
| Test | Input | Expected |
|---|---|---|
| Valid ES256 JWT | Real Supabase token | Returns payload dict |
| Valid HS256 JWT | Fallback secret | Returns payload dict |
| Expired token | exp < now | HTTP 401 |
| Malformed token | Random string | HTTP 401 |
| Missing Authorization header | No header | HTTP 401 |
| Wrong scheme (Basic instead of Bearer) | "Basic xyz" | HTTP 401 |
| Empty Bearer token | "Bearer " | HTTP 401 |
| Tampered signature | Modified payload | HTTP 401 |
| Token from another Supabase project | Different audience | HTTP 401 |

### 3.5 `app/dependencies/subscription.py`
| Test | Input | Expected |
|---|---|---|
| Active subscription | status=active | Allows request |
| Trialing subscription | status=trialing | Allows request |
| Past due | status=past_due | HTTP 403 |
| Cancelled | status=cancelled | HTTP 403 |
| Expired | status=expired | HTTP 403 |
| No subscription record | User never subscribed | HTTP 403 |
| Service client used | Verify bypasses RLS | Successful query |

### 3.6 `app/services/notifications.py`
| Test | Input | Expected |
|---|---|---|
| Tenant SMS on appointment created | Event=created | Twilio called once |
| Tenant SMS on rescheduled | Event=rescheduled, new_date | SMS contains new date |
| Tenant SMS on cancelled | Event=cancelled | SMS sent |
| Tenant SMS on attended | Event=attended | SMS sent |
| Tenant SMS on reactivated | Event=reactivated | SMS sent |
| No SMS if tenant has no phone | tenant.phone=None | Twilio not called, no error |
| No SMS if SMS reminders disabled | Feature flag off | Twilio not called |
| Manager SMS + email on new appointment | Appointment created | Both Twilio and SendGrid called |
| Twilio failure doesn't raise | Mock 500 | Error logged, function returns |
| SendGrid failure doesn't raise | Mock 500 | Error logged, function returns |

### 3.7 `app/integrations/twilio_client.py`
| Test | Expected |
|---|---|
| Sends SMS to valid E.164 number | Twilio API called |
| Logs warning if credentials missing | No exception |
| Returns None on missing config | Graceful fallback |
| Invalid phone number format | Logged, no exception |

### 3.8 `app/integrations/email_client.py`
| Test | Expected |
|---|---|
| Sends HTML email | SendGrid API called |
| Reads credentials on each call | Live reconfig works |
| Missing API key | Logged, returns None |

### 3.9 `app/core/features.py`
| Test | Expected |
|---|---|
| `get_default_state(VOICE_CALLS)` | Returns True |
| `get_default_state(SMS_REMINDERS)` | Returns False |
| All Feature enum values have metadata | No KeyError |

---

## 4. Backend Integration Tests — All Routes

### 4.1 `/complaints` — `routes/complaints.py`

#### POST `/complaints`
| Case | Body | Expected |
|---|---|---|
| Valid complaint with tenant_uuid + flat_uuid | Full payload | 201, returns complaint |
| Valid complaint with legacy flat_number | flat_number="A-101" | 201, auto-resolves flat_uuid |
| Auto-creates appointment if appointment_date set | appointment_date in body | 201, appointment row created |
| Missing required field (category) | No category | 422 |
| Invalid category | category="nuclear" | 422 |
| Invalid status | status="open" | 422 |
| Non-existent tenant_uuid | Random UUID | 404 or auto-null tenant |
| Non-existent flat_uuid | Random UUID | 404 |
| Unauthenticated | No Bearer | 401 |
| No active subscription | manager_no_sub user | 403 |
| Cross-manager flat (RLS) | manager A inserts complaint on manager B's flat | RLS blocks insert |
| SQL injection in description | `'; DROP TABLE;` | Escaped safely |
| Description > 10000 chars | Long text | 422 or truncated |
| Source defaults to "web" | source omitted | source="web" in DB |

#### GET `/complaints`
| Case | Expected |
|---|---|
| Lists all complaints for manager | Only manager's complaints |
| Joined with appointments table | Returns appointment_status |
| Newest first | created_at DESC |
| Empty result | 200, [] |
| Manager B's complaints not visible | RLS isolates |

#### GET `/complaints/{id}`
| Case | Expected |
|---|---|
| Valid UUID | 200, complaint |
| Valid legacy int id | 200, complaint |
| Non-existent | 404 |
| Other manager's complaint | 404 (RLS) |

#### PATCH `/complaints/{id}`
| Case | Body | Expected |
|---|---|---|
| Update status to in-progress | `{status: "in-progress"}` | 200 |
| Update to resolved | `{status: "resolved"}` | 200 |
| Invalid status | `{status: "fixed"}` | 422 |
| Partial update (just description) | `{description: "..."}` | 200, other fields unchanged |
| Empty body | `{}` | 200 or 422 (decide) |

#### DELETE `/complaints/{id}`
| Case | Expected |
|---|---|
| Valid id | 204, row gone |
| Non-existent | 404 |
| Has linked appointments | Cascade or block (verify behavior) |

---

### 4.2 `/tenants` — `routes/tenants.py`

#### GET `/tenants/by-flat/{flat_no}` (VAPI)
| Case | Expected |
|---|---|
| Existing flat with tenant | 200, `{exists: true, tenant_name, tenant_phone, datetime}` |
| Existing flat, no tenant | 200, `{exists: false}` |
| Non-existent flat | 200, `{exists: false}` (NEVER 404 — VAPI rule) |
| Flat number lowercase | Normalized to UPPER, matches |
| Flat number with whitespace | Trimmed |
| Empty flat_no | 200, `{exists: false}` |
| SQL injection in flat_no | Safely escaped |

#### POST `/tenants`
| Case | Body | Expected |
|---|---|---|
| Valid tenant | Name, phone, email, flat_uuid | 201 |
| Duplicate phone | Same phone | 409 or 422 (decide policy) |
| Invalid email | "not-an-email" | 422 |
| Invalid phone format | "abc" | 422 |
| lease_end before lease_start | Date inversion | 422 |
| Missing flat_uuid | Omit | 422 |
| Cross-manager flat | Manager A's flat | RLS blocks |
| document_urls as array | List of URLs | Stored as array |
| Computed fields on response | lease_duration_months etc. | Present in response |

#### GET `/tenants`
| Case | Expected |
|---|---|
| List all | 200, array |
| Filter by flat_uuid | Only that flat's tenant |
| Empty | 200, [] |

#### GET `/tenants/{uuid}`
| Case | Expected |
|---|---|
| Valid uuid | 200, with computed lease fields |
| Tenancy duration calc | `tenancy_duration_months` = (today - lease_start) / 30 |
| Expiring soon (< 30 days) | `lease_status: "expiring_soon"` |
| Expired | `lease_status: "expired"` |
| Active | `lease_status: "active"` |

#### PATCH `/tenants/{uuid}` & `PATCH /tenants/{uuid}/rent-status`
| Case | Expected |
|---|---|
| Update rent_status to Overdue | 200 |
| Invalid rent_status | 422 (must be On-time/Upcoming/Overdue/At Risk) |
| Update phone | Tenant record updated |
| Add document_url | Array appended |

#### DELETE `/tenants/{uuid}`
| Case | Expected |
|---|---|
| Delete tenant | flat.tenant_uuid set to NULL |
| Tenant has complaints | Complaints orphaned (tenant_uuid=NULL) or blocked |

---

### 4.3 `/flats` — `routes/flats.py`

#### POST `/flats/verify-phone` (VAPI)
| Case | Body | Expected |
|---|---|---|
| Caller phone matches tenant | `{phone: "+919..."}` | 200, `{status: "valid", ...}` |
| Phone matches no tenant | Unknown number | 200, `{status: "invalid"}` |
| Phone matches flat with no tenant | Vacant flat | 200, `{status: "vacant"}` |
| Empty phone | `""` | 200, status=invalid (NEVER 422) |
| Non-E.164 format | "9876543210" | Normalized + matched |
| ALWAYS returns 200 | All cases | No 4xx/5xx ever |

#### POST `/flats/identify-caller`
| Case | Expected |
|---|---|
| Phone matches tenant | Returns flat_no, tenant_name |
| No match | Returns null fields, 200 |

#### POST `/flats`
| Case | Expected |
|---|---|
| Create flat with all fields | 201 |
| Duplicate flat_number | 409 |
| Missing flat_number | 422 |
| Invalid building_id | 422 |
| Flat_number normalized to upper | "a-101" → "A-101" |

#### GET `/flats` & `/flats/{uuid}`
| Case | Expected |
|---|---|
| List all | 200 |
| Filter by building_id | Only that building's flats |
| Single flat with tenant joined | Includes tenant details |
| Occupied computed | `occupied = (tenant_uuid IS NOT NULL)` |

#### PATCH/DELETE `/flats/{uuid}`
| Case | Expected |
|---|---|
| Update bedrooms | 200 |
| Delete flat with tenant | Cascade tenant or block |
| Delete flat with complaints | Cascade or block |

#### POST `/flats/{uuid}/upload-image`
| Case | Expected |
|---|---|
| Valid PNG | 200, returns signed URL |
| Valid JPEG | 200 |
| File > 5MB | 413 |
| Non-image file | 422 |
| Missing file | 422 |
| Updates flat.image_url | DB updated |

#### POST `/flats/{uuid}/assign-tenant` & `/unassign-tenant`
| Case | Expected |
|---|---|
| Assign existing tenant | flat.tenant_uuid updated, tenant.flat_uuid updated |
| Already-occupied flat | 409 or replace (decide policy) |
| Unassign | Both columns set to NULL |
| Tenant not found | 404 |

---

### 4.4 `/appointments` — `routes/appointments.py`

#### GET `/appointments/view?flat_number=` (VAPI)
| Case | Expected |
|---|---|
| Flat with active appointments | 200, list of scheduled |
| Flat with only cancelled | 200, [] |
| Non-existent flat | 200, [] (NEVER 404) |
| Date format `YYYY-MM-DDTHH:MM:SS` | T separator confirmed |

#### PATCH `/appointments/update?flat_number=&id=&new_appointment_date=` (VAPI)
| Case | Expected |
|---|---|
| Valid reschedule | 200, date updated, SMS sent to tenant |
| Invalid date format | 200 with error message (not 422) |
| Past date | Accepts (verify business rule) |
| Mismatched flat_number + id | 200 with error |

#### POST `/appointments/cancel?flat_number=&id=` (VAPI)
| Case | Expected |
|---|---|
| Valid cancel | 200, status=cancelled, SMS sent |
| Already cancelled | 200, idempotent |
| Non-existent | 200 with message |

#### POST `/appointments`
| Case | Expected |
|---|---|
| Create with complaint_uuid | 201, linked |
| Create standalone (no complaint) | 201 |
| Missing flat_uuid | 422 |
| Invalid status | 422 |
| Datetime in IST timezone | Stored as +05:30 |
| Format `T` separator | `2026-05-15T14:30:00` |

#### PATCH `/appointments/{id}` & DELETE
| Case | Expected |
|---|---|
| Mark attended | status=attended, SMS sent |
| Soft delete | status=cancelled (not row deletion) |

---

### 4.5 `/buildings` — `routes/buildings.py`

| Case | Expected |
|---|---|
| Create building with property_type_id | 201 |
| Create without property_id (orphan) | 201 or 422 (decide) |
| List with unit counts aggregated | `unit_count` = COUNT(flats) |
| Update name | 200 |
| Delete building with flats | Cascade or block |
| Cross-manager building | RLS isolates |

---

### 4.6 `/properties-list` — `routes/property_groups.py`

| Case | Expected |
|---|---|
| Create property group | 201 |
| List all | Only manager's groups |
| Update | 200 |
| Delete with buildings | Cascade or block |

---

### 4.7 `/property-types`

| Case | Expected |
|---|---|
| List | Returns Residential, Commercial, Mixed-use |
| Read-only | No POST/PATCH/DELETE exposed |

---

### 4.8 `/rents`

#### POST `/rents/set`
| Case | Expected |
|---|---|
| Set new rent | Previous deactivated, new is_active=true |
| Only one is_active per flat | DB constraint enforced |
| Set future effective_from | Stored correctly |
| Negative rent | 422 |
| Zero rent | 422 or warning |

#### GET `/rents/summary`
| Case | Expected |
|---|---|
| Returns all tenants with active rent | Includes flat info |
| Status counts | On-time, Upcoming, Overdue, At Risk totals |
| No rents set | Empty result |

---

### 4.9 `/call-logs`

| Case | Expected |
|---|---|
| List all | Only manager's logs |
| Filter by phone | Subset |
| Filter by flat_number | Subset |
| Filter by complaint_status | created/incomplete/failed |
| Single log fetch | 200 |

---

### 4.10 `/chat` — AI Chatbot

| Case | Expected |
|---|---|
| Simple message | 200, `{reply, refresh_needed}` |
| Conversation history > 10 | Truncated to last 10 |
| Tool call executes | DB updated, refresh_needed=true |
| OpenAI timeout | 500 with friendly message |
| Empty messages array | 422 |
| Non-array messages | 422 |
| No subscription | 403 |

---

### 4.11 `/voice/webhook` — VAPI Webhook

| Case | Expected |
|---|---|
| `tool-calls` event | Creates complaint if confirmed |
| `end-of-call-report` event | Creates CallLog |
| Duplicate call_id | Idempotent — no duplicate rows |
| Missing event type | 200, no DB write |
| Malformed JSON | 200, error logged |
| Always returns 200 | Even on internal error |
| Transcript stored | Full transcript saved |
| Phone normalized to E.164 | "+91..." |
| Complaint linked to tenant by phone | tenant_uuid set if match |
| Source set to "voice" or "AI_AGENT" | Verified |

#### GET `/voice/call-status`
| Case | Expected |
|---|---|
| Returns last_call_ended_at | Timestamp or null |
| Used by frontend polling | 3s interval |

---

### 4.12 `/notifications`

| Case | Expected |
|---|---|
| POST /test-sms | Twilio called, returns success |
| POST /test-email | SendGrid called |
| GET /preferences | Returns per-building settings |
| SMS to invalid number | 422 or graceful fail |

---

### 4.13 `/workflow`

| Case | Expected |
|---|---|
| Broadcast SMS to all tenants | All Twilio calls succeed |
| Filter by building | Only that building's tenants |
| Filter by rent_status | Only matching |
| Template with placeholders | `{tenant_name}` replaced |
| List templates | Returns array |
| Create custom template | 201 |

---

### 4.14 `/settings`

| Case | Expected |
|---|---|
| GET manager settings | name, email, phone, notifs |
| PATCH update name | 200 |
| GET features | Per-building map |
| POST enable feature | property_features row created |
| Disable feature | is_enabled=false |

---

### 4.15 `/import` — CSV Bulk Import

#### POST `/import/properties`
| Case | Expected |
|---|---|
| Valid CSV (5 properties, 10 buildings, 50 flats) | All created |
| Missing required column | 422 with line number |
| Duplicate flat_number in CSV | 409 with details |
| Existing flat_number in DB | Skip or update (decide) |
| Empty CSV | 422 |
| Non-CSV file (PDF) | 422 |
| > 10000 rows | Handles batching or rejects |
| Special chars in names | UTF-8 preserved |
| Transaction on failure | Rollback all on error |

#### POST `/import/tenants`
| Case | Expected |
|---|---|
| Valid tenants linked to existing flats | All created |
| Tenant for non-existent flat_number | Skipped with warning |
| Duplicate phone | Skipped or error |
| Invalid email format | Row error |
| Bulk 1000 tenants | Performance < 30s |

---

### 4.16 `/upload/image`

| Case | Expected |
|---|---|
| Valid PNG/JPEG | Signed URL returned |
| File > 5MB | 413 |
| SVG with script | Sanitized or rejected |
| Filename with `../` | Path traversal blocked |
| Concurrent uploads | No collision |

---

### 4.17 `/payments`

#### POST `/payments/create-checkout-session`
| Case | Expected |
|---|---|
| New user, no Stripe customer | Customer created, session URL returned |
| Existing customer | Reuses customer_id |
| Returns success_url + cancel_url | Both set correctly |
| Subscription mode | 14-day trial + $1 setup |
| Stripe API failure | 500 with error |

#### POST `/payments/webhook`
| Case | Expected |
|---|---|
| `customer.subscription.created` | subscriptions row inserted |
| `customer.subscription.updated` | Row updated |
| `customer.subscription.deleted` | Status=cancelled |
| `invoice.payment_failed` | Status=past_due |
| Duplicate event_id | Idempotent (stripe_events table) |
| Invalid signature | 400 |
| Missing signature header | 400 |
| Malformed payload | 400 |

#### GET `/payments/subscription-status`
| Case | Expected |
|---|---|
| Active sub | Returns status + period_end |
| No sub | Returns null/inactive |

---

## 5. Frontend Component Tests

### 5.1 `apiService.js`
| Test | Expected |
|---|---|
| `authFetch` adds Bearer token | Authorization header present |
| Handles 401 → signs out | supabase.auth.signOut called |
| Handles 403 → redirects to pricing | window.location updated |
| Network error | Throws with friendly message |
| All exported functions work | Each maps to correct endpoint |

### 5.2 `AuthContext.jsx`
| Test | Expected |
|---|---|
| Initial loading state | loading=true |
| Session exists | user populated |
| onAuthStateChange listener fires | State updates |
| `ensureManagerProfile` on first Google sign-in | manager_profiles row created |
| Sign out clears session | user=null |

### 5.3 `OnboardingContext.jsx`
| Test | Expected |
|---|---|
| Initial state from localStorage | Loaded correctly |
| `triggerTour('dashboard')` | Tour starts |
| Tour completion saves to Supabase | DB updated |
| DB is authority on conflict | DB > localStorage |

### 5.4 `Dashboard.jsx`
| Test | Expected |
|---|---|
| Renders KPI cards | 4 cards with mock data |
| Loading state shows skeleton | Skeleton component visible |
| Empty state | "No complaints yet" message |
| Polls call-status every 3s | Mock timer verified |
| Receives refresh-appointments event | Re-fetches data |

### 5.5 `Chatbot.jsx`
| Test | Expected |
|---|---|
| FAB visible bottom-4 right-4 | Positioned correctly |
| Opens on click | Dialog visible |
| Sends message | apiService.sendChatMessage called |
| Renders markdown response | react-markdown used |
| `refresh_needed=true` dispatches event | Event fired |
| Disables input during loading | Button disabled |
| Scroll to bottom on new message | Verified |

### 5.6 `ComplaintModal.jsx`
| Test | Expected |
|---|---|
| Create mode | Empty form |
| Edit mode | Form pre-filled |
| Validation: category required | Error shown |
| Validation: description min 5 chars | Error shown |
| Submit calls correct API | createComplaint or updateComplaint |
| Closes on success | onClose called |

### 5.7 `AppointmentModal.jsx`
| Test | Expected |
|---|---|
| Date picker shows future dates only | Past disabled |
| Time format hh:mm | Verified |
| Submit creates appointment | API called |
| IST timezone applied | +05:30 in payload |

### 5.8 `CalendarView.jsx`
| Test | Expected |
|---|---|
| Renders current month | 28-31 days |
| Day cells show appointment count | Badge with number |
| Click day opens DateComplaintsModal | Modal visible |
| Navigation next/prev month | Updates view |

### 5.9 `TenantManagement.jsx`
| Test | Expected |
|---|---|
| Lists all tenants | Table populated |
| Filter by rent_status | Filtered set |
| Search by name | Filtered set |
| Edit tenant | Modal opens with prefilled data |
| Delete confirmation | Modal asks "Are you sure?" |

### 5.10 `PropertiesPage.jsx`
| Test | Expected |
|---|---|
| Lists buildings | All visible |
| Expands building to show flats | UnitListPanel rendered |
| Add property modal opens | Modal visible |
| Image upload preview | ImageUploadField working |

### 5.11 `SettingsPage.jsx`
| Test | Expected |
|---|---|
| Tab switching (profile, features, notifications) | All tabs render |
| Toggle feature flag | API called, UI updates |
| Save profile changes | PATCH /settings called |
| Theme toggle persists | localStorage updated |

### 5.12 `RentTab.jsx`
| Test | Expected |
|---|---|
| Lists all tenants with rent | Table populated |
| Status counts visible | On-time/Upcoming/Overdue cards |
| Set new rent | Modal opens, API called |
| Update rent status | PATCH called |

### 5.13 `VoiceStatsTab.jsx`
| Test | Expected |
|---|---|
| Charts render | Recharts mounted |
| Empty state | Message shown |
| Date range filter | Updates data |

### 5.14 `SmsWorkflow.jsx`
| Test | Expected |
|---|---|
| Template dropdown populated | List visible |
| Recipient filter (building/status) | Updates count |
| Preview message | Placeholder substitution shown |
| Confirm before send | Confirmation modal |
| Send broadcasts | API called once |

### 5.15 `CsvImportModal.jsx`
| Test | Expected |
|---|---|
| File picker accepts .csv only | Other types rejected |
| Preview first 5 rows | Table shown |
| Validation errors per row | Listed |
| Submit imports | API called |
| Progress indicator | Shown during upload |

### 5.16 `AuthPage.jsx`
| Test | Expected |
|---|---|
| Google sign-in button | Visible |
| Click triggers OAuth | supabase.auth.signInWithOAuth |
| PKCE flow | code_verifier handled |
| Redirect on success | Dashboard shown |
| Error message on failure | Toast shown |

### 5.17 `OnboardingTour.jsx`
| Test | Expected |
|---|---|
| Tour starts for new user | Step 1 visible |
| Step navigation (next/prev/skip) | Works |
| Completion marks Supabase | tour_completed=true |
| Skip persists | Doesn't re-trigger |

### 5.18 Sidebar / TopBar
| Test | Expected |
|---|---|
| Sidebar collapses | Toggle works |
| Active route highlighted | Visual indicator |
| TopBar shows user email | Email visible |
| Profile menu opens | Dropdown visible |
| Sign out works | Session cleared |

### 5.19 Charts (TrendsChart, StatusDonut, etc.)
| Test | Expected |
|---|---|
| Render with mock data | SVG present |
| Empty data | Empty state message |
| Tooltip on hover | Tooltip visible |
| Color theme respects dark mode | Colors swap |

---

## 6. Frontend E2E Tests (Playwright)

### 6.1 Critical User Flows

#### Flow A: New User Signup → Subscription → First Property
1. Land on AuthPage
2. Click "Sign in with Google"
3. Mock OAuth callback
4. Redirected to pricing (no subscription)
5. Click "Start free trial"
6. Stripe Checkout (test mode)
7. Complete checkout
8. Redirected to dashboard
9. Onboarding tour starts
10. Skip or complete tour
11. Click "Add Property"
12. Fill modal (name, type)
13. Save → property visible
14. Click property → add building
15. Add flat to building
16. Add tenant to flat

**Assertions:** Each step succeeds; data persists across page refreshes; RLS isolates from other managers.

#### Flow B: Complaint Lifecycle
1. Login as manager_active
2. Open Complaints page
3. Click "Add Complaint"
4. Fill form (category, flat, description)
5. Set appointment_date → appointment auto-created
6. Save
7. Verify complaint appears in table
8. Open ComplaintDetailModal
9. Update status to "in-progress"
10. Open linked appointment
11. Mark as "attended" → tenant SMS triggered (mock)
12. Update complaint to "resolved"
13. Verify status counts updated on dashboard

#### Flow C: Voice Call Simulation
1. Mock VAPI webhook → `tool-calls` event
2. Verify CallLog created
3. Verify Complaint created with source="voice"
4. Verify SMS to manager sent (mock Twilio)
5. Frontend polling picks up new call
6. NotificationPanel shows alert
7. Open call log → transcript visible

#### Flow D: AI Chatbot
1. Open chatbot FAB
2. Type "Show me all flats in Building A"
3. Verify reply with flat list
4. Type "Schedule appointment for A-101 tomorrow 3pm"
5. Chatbot asks confirmation
6. Reply "Yes"
7. Appointment created in DB
8. refresh_needed event fires
9. Calendar updates without page refresh

#### Flow E: CSV Bulk Import
1. Open Properties page
2. Click "Import CSV"
3. Upload properties.csv (5 rows)
4. Preview shows rows
5. Submit → progress bar
6. Success → all properties visible
7. Upload tenants.csv
8. Tenants linked to flats correctly

#### Flow F: Rent Management
1. Open Rent tab
2. Click "Set Rent" on a flat
3. Enter monthly rent + effective_from
4. Save → rent active
5. Verify previous rent (if any) deactivated
6. Update tenant rent_status to "Overdue"
7. Status count updates

#### Flow G: SMS Broadcast
1. Open SMS Workflow
2. Select template
3. Filter recipients (building=X)
4. Preview message
5. Confirm and send
6. Verify Twilio mock called N times
7. Success toast shown

#### Flow H: Subscription Expiry
1. Login as manager_expired
2. Try to access dashboard
3. Redirected to pricing (403)
4. Click "Renew subscription"
5. Stripe Checkout completes
6. Webhook updates status to "active"
7. Dashboard accessible again

### 6.2 Error Path Tests

| Scenario | Expected |
|---|---|
| Network offline during action | Friendly error toast, retry button |
| 500 from backend | Toast: "Something went wrong" |
| 401 (expired token) | Auto sign-out + redirect to AuthPage |
| 403 (no sub) | Redirect to pricing |
| 404 (deleted entity) | "Not found" message |
| Form validation errors | Inline error messages |
| Concurrent edit conflict | Last-write-wins or warning |

### 6.3 Cross-Browser Tests
- [ ] Chromium (Chrome, Edge)
- [ ] Firefox
- [ ] WebKit (Safari)
- [ ] Mobile viewport (375x667 — iPhone SE)
- [ ] Tablet viewport (768x1024 — iPad)
- [ ] Desktop (1920x1080)

### 6.4 Accessibility Tests
- [ ] All buttons have accessible names
- [ ] Form fields have labels
- [ ] Color contrast WCAG AA
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Screen reader (NVDA/VoiceOver) announces critical updates
- [ ] Focus management in modals (focus trap)

---

## 7. External Integration Tests

### 7.1 Supabase
| Test | Expected |
|---|---|
| Auth: Google OAuth PKCE | Token returned, session created |
| Auth: token refresh | Auto-refreshes near expiry |
| Storage: image upload | Signed URL works, expires correctly |
| RLS: manager A can't read manager B | Verified at row level |
| Realtime (if used) | Subscriptions deliver updates |

### 7.2 Stripe
| Test | Expected |
|---|---|
| Test card 4242 4242 4242 4242 | Succeeds |
| Test card 4000 0000 0000 0002 (decline) | Fails gracefully |
| 3D Secure card | Handles SCA flow |
| Webhook signature verification | Invalid sig → 400 |
| Webhook replay attack | Idempotent via stripe_events |
| Subscription pause/resume | Status updates correctly |
| Customer portal (if exposed) | Works |
| Refund/cancellation flow | Status updates |

### 7.3 Vapi.ai
| Test | Expected |
|---|---|
| Inbound call to test number | Agent responds |
| Tool call to /flats/verify-phone | Caller identified |
| Tool call to /tenants/by-flat | Tenant returned |
| Tool call to /appointments/view | List returned |
| End-of-call webhook fires | CallLog created |
| Transcript captured | Full text stored |
| Outbound call via OutboundCallButton | Initiated |

### 7.4 OpenAI
| Test | Expected |
|---|---|
| Chatbot completion | < 5s response |
| Tool calling | Correct tool invoked |
| Rate limit handling | Backoff retry |
| API key rotation | Reload config |

### 7.5 Groq
| Test | Expected |
|---|---|
| Extraction from clear transcript | All fields parsed |
| Extraction from noisy transcript | Best-effort or None |
| Model: llama-3.3-70b-versatile | Confirmed (not 3.1 — decommissioned) |
| Tool hallucination handled | BadRequestError retry path works |

### 7.6 Twilio
| Test | Expected |
|---|---|
| Send SMS to test number | Delivered |
| Invalid number format | Logged, no crash |
| Rate limit | Queued or fails gracefully |
| Sender number config | Correct From: |

### 7.7 SendGrid
| Test | Expected |
|---|---|
| Send HTML email | Delivered to sandbox |
| Templated email | Variables substituted |
| Invalid email address | Logged, no crash |
| Bounce handling | Logged (if hooked) |

---

## 8. Security & Authorization Tests

### 8.1 Row-Level Security (RLS)
For EVERY table with `manager_id`, verify:
- [ ] Manager A's SELECT returns only their rows
- [ ] Manager A's INSERT with manager_id=B fails
- [ ] Manager A's UPDATE on manager B's row fails
- [ ] Manager A's DELETE on manager B's row fails
- [ ] Service-role client bypasses RLS (webhooks only)

Tables to test: `properties_list`, `buildings`, `flats`, `tenants`, `complaints`, `appointments`, `call_logs`, `rents`, `subscriptions`, `property_features`, `manager_notifications`.

### 8.2 JWT Security
| Test | Expected |
|---|---|
| Algorithm: none attack | Rejected |
| Algorithm: switch HS256 → RS256 with public key | Rejected |
| Token without `sub` | Rejected |
| Token with future `iat` | Rejected |
| Token signed by another project | Rejected |

### 8.3 Subscription Bypass Attempts
| Test | Expected |
|---|---|
| Manually set status=active in DB | Webhook will revert |
| Race condition: cancel during checkout | Final status correct |
| Hit `/chat` without sub | 403 |
| Hit any gated route without sub | 403 |

### 8.4 Input Validation
| Test | Expected |
|---|---|
| SQL injection in all string fields | Escaped (parameterized via SDK) |
| XSS in description / notes | Rendered safely (react escapes by default; verify markdown sanitization) |
| Path traversal in filename | Rejected (`../`, `..\\`) |
| XXE in XML uploads (if any) | N/A or blocked |
| ReDoS in regex inputs | Timeout safeguarded |
| Large payload DoS (10MB JSON) | Rejected by FastAPI/server limit |

### 8.5 CORS
| Test | Expected |
|---|---|
| Allowed origin | Header present |
| Disallowed origin | No header |
| Wildcard not used in prod | Verified |
| Credentials handling | Correct |

### 8.6 Rate Limiting (if implemented)
| Test | Expected |
|---|---|
| 100 req/min per user | 429 after limit |
| Webhook endpoints exempt | Stripe/Vapi not rate-limited |

### 8.7 Secrets Management
- [ ] No secrets in code (gitleaks scan)
- [ ] `.env` not committed
- [ ] Service-role key never sent to frontend
- [ ] JWT secret rotated periodically
- [ ] Stripe webhook secret matches dashboard

### 8.8 OWASP Top 10
- [ ] A01 Broken Access Control → RLS tests
- [ ] A02 Cryptographic Failures → HTTPS only, JWT alg correct
- [ ] A03 Injection → input validation tests
- [ ] A04 Insecure Design → review subscription gate
- [ ] A05 Security Misconfiguration → CORS, headers
- [ ] A06 Vulnerable Components → `npm audit`, `pip-audit`
- [ ] A07 Auth failures → JWT tests
- [ ] A08 Data Integrity → webhook signature
- [ ] A09 Logging failures → ensure no sensitive data in logs
- [ ] A10 SSRF → if URL fetching exists, validate

---

## 9. Performance & Load Tests

### 9.1 Backend (k6)
| Scenario | Target |
|---|---|
| 100 concurrent users on GET /complaints | p95 < 500ms |
| 50 concurrent POST /complaints | p95 < 800ms |
| 200 concurrent VAPI webhooks | All 200 OK, no drops |
| 100 concurrent /chat | p95 < 8s (OpenAI dependent) |
| Sustained 10 req/s for 10 min | No memory leaks, stable response time |

### 9.2 Database
- [ ] Indexes on `manager_id`, `flat_uuid`, `tenant_uuid`, `complaint_uuid` columns
- [ ] EXPLAIN ANALYZE on common queries < 100ms
- [ ] No N+1 queries (verify joins used)
- [ ] Connection pool sized appropriately

### 9.3 Frontend
- [ ] Lighthouse Performance score > 80
- [ ] Lighthouse Accessibility > 90
- [ ] Initial bundle < 500KB (gzipped)
- [ ] First Contentful Paint < 1.5s
- [ ] Time to Interactive < 3s
- [ ] Recharts/Framer Motion code-split (verify in build output)

### 9.4 Memory & Resource
- [ ] Backend: no memory growth over 1hr at steady load
- [ ] Frontend: no detached DOM nodes after navigation
- [ ] Supabase connection count stays within limits

---

## 10. Data Integrity Tests

### 10.1 Foreign Key Cascades
| Action | Expected |
|---|---|
| Delete tenant | flat.tenant_uuid → NULL |
| Delete flat | complaints orphaned or blocked |
| Delete building | flats orphaned or blocked |
| Delete property group | buildings orphaned or blocked |
| Delete manager | All cascade (or hard block) |

### 10.2 Uniqueness Constraints
- [ ] `flats.flat_number` unique per manager (or globally — confirm)
- [ ] `stripe_events.event_id` unique
- [ ] `call_logs.call_id` unique
- [ ] Only one `rents.is_active=true` per flat_uuid

### 10.3 Data Migration / Schema Changes
- [ ] All tables have `created_at`, `updated_at` (where applicable)
- [ ] Default values applied correctly
- [ ] Backfill scripts idempotent
- [ ] Alembic migrations reversible (or Supabase SQL migrations)

### 10.4 Timezone Consistency
- [ ] All datetimes stored in IST (+05:30) per project convention
- [ ] Display formatted via frontend `parseISO`
- [ ] No naive datetimes in DB
- [ ] DST transitions handled (N/A for IST but verify framework)

### 10.5 Encoding
- [ ] UTF-8 throughout (special chars: emoji, accents, Hindi/Tamil scripts)
- [ ] CSV import handles BOM
- [ ] Email/SMS preserve UTF-8

---

## 11. Production Readiness Checklist

### 11.1 Pre-Deploy
- [ ] All unit tests pass (CI green)
- [ ] All integration tests pass
- [ ] All E2E tests pass on all browsers
- [ ] Security scan passes (bandit, npm audit)
- [ ] No `console.log`, `print`, or debug code in main branches
- [ ] No TODO comments without tickets
- [ ] `.env.example` matches required env vars in `config.py`
- [ ] Database migrations applied to production Supabase
- [ ] RLS policies verified on production tables
- [ ] Stripe webhook configured with production endpoint
- [ ] Vapi assistant configured with production URLs
- [ ] DNS, SSL certificates valid
- [ ] CORS allowed_origins set to production frontend URL only

### 11.2 Observability
- [ ] Backend error logging (Sentry or equivalent)
- [ ] Frontend error logging (Sentry browser SDK)
- [ ] Request logging with request IDs
- [ ] Vapi webhook receipts logged
- [ ] Stripe webhook receipts logged
- [ ] Database query slow log enabled
- [ ] Health check endpoint `/` returns 200

### 11.3 Backup & Recovery
- [ ] Supabase point-in-time recovery enabled
- [ ] Daily backup verified by restore drill
- [ ] User-uploaded images in Supabase Storage replicated
- [ ] Disaster recovery runbook written

### 11.4 Monitoring
- [ ] Uptime monitor (UptimeRobot / Pingdom)
- [ ] Stripe failed-payment alerts
- [ ] Vapi call failure alerts
- [ ] Twilio/SendGrid quota alerts
- [ ] OpenAI/Groq token usage tracked
- [ ] Subscription churn dashboard

### 11.5 Compliance & Privacy
- [ ] Privacy policy linked
- [ ] Terms of service linked
- [ ] Cookie consent (if applicable for region)
- [ ] GDPR data export endpoint (if EU users)
- [ ] PII redaction in logs (phone numbers, emails)
- [ ] Recording disclosure for VAPI calls

### 11.6 Documentation
- [ ] README.md up to date
- [ ] CODEBASE_CONTEXT.md reflects current state
- [ ] API docs (OpenAPI/Swagger) generated
- [ ] Runbook for common incidents
- [ ] Onboarding doc for new developers

### 11.7 Rollback Plan
- [ ] Previous version tagged in Git
- [ ] Rollback steps documented
- [ ] Feature flags for risky changes
- [ ] Database migration rollback strategy

### 11.8 Final Smoke Tests (Production)
- [ ] Signup new user
- [ ] Complete Stripe checkout (real $1 charge, refund after)
- [ ] Create property/building/flat/tenant chain
- [ ] Make a real test call to VAPI number
- [ ] Verify SMS received on real phone
- [ ] Verify email received on real inbox
- [ ] Chatbot responds correctly
- [ ] Dashboard loads with real data
- [ ] Sign out and back in
- [ ] Cancel subscription works
- [ ] Re-subscribe works

---

## Sign-Off

| Role | Name | Date | Signature |
|---|---|---|---|
| Dev Lead | | | |
| QA Lead | | | |
| Security | | | |
| Product Owner | | | |

**When all sections above are checked and the sign-off complete, the system is production-ready.**
