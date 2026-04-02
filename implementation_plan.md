# SaaS Implementation Plan (v2) — Production-Ready

## Goal

Transform the existing Tenant Management MVP into a multi-tenant SaaS with:
- **Supabase Auth** for login/signup (manager-only role)
- **Stripe** for subscription billing with 14-day free trial + $1 card verification
- **VAPI Option B** (single phone number + caller lookup) for voice agent multi-tenancy
- **Row Level Security (RLS)** on all tables for full data isolation between managers

The landing page ([`Leadpipe-1`](C:\Users\BIT\Coding\Leadpipe-1)) handles user acquisition, auth, and payment. Upon login, users are redirected to the CRM app (`Tenant_management_MVP/frontend`), which shares the same Supabase project.

## Key Decisions (Documented)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| VAPI multi-tenancy | **Option B** — single number + caller lookup | Scales better than one number per property group |
| Subscription model | **14-day free trial** with $1 card verification upfront | Qualifies leads before trial starts |
| Rent collection | **Deferred** — manual status tracking only (no Razorpay) | Not in scope for this phase |
| Roles | **Manager-only** — no tenant or super_admin roles yet | Dashboard is manager-only |
| Session handoff | **Supabase `detectSessionInUrl`** (upgrade to subdomain cookies later) | Simplest cross-origin approach |
| Existing data | **Mock manager** created, existing rows assigned to it | Prevents data loss when RLS activates |
| Unknown caller | **Generic message + hang up** | Clean UX, no confusion |
| Deployment | **Netlify** (CRM frontend), **Render** (backend), all URLs as env vars | Existing infra |

---

## Phase 0: Database Schema Changes

> **Run these in the Supabase Dashboard SQL Editor, in order.**

### Step 0A: Create the mock manager in Supabase Auth

Before running migrations, create a manager account via the Supabase Dashboard (Authentication > Users > Add User). Note the UUID — it's used in Step 0C.

- Email: `mock-manager@yourdomain.com`
- Password: a strong throwaway password

### Step 0B: Schema migrations

```sql
-- ============================================================
-- 1. Manager Profiles table
-- ============================================================
CREATE TABLE IF NOT EXISTS manager_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  phone TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE manager_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "managers_see_own_profile"
ON manager_profiles FOR ALL
USING (user_id = auth.uid());

-- ============================================================
-- 2. Subscriptions table (Stripe billing)
-- ============================================================
CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  stripe_customer_id TEXT NOT NULL,
  stripe_subscription_id TEXT UNIQUE,
  plan TEXT NOT NULL DEFAULT 'trial',
  status TEXT NOT NULL DEFAULT 'trialing',
    -- status values: trialing, active, past_due, canceled, incomplete
  trial_ends_at TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Unique constraint: one active subscription per manager
CREATE UNIQUE INDEX idx_subscriptions_active_manager
ON subscriptions(manager_id) WHERE status IN ('trialing', 'active');

ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "managers_see_own_subscription"
ON subscriptions FOR SELECT
USING (manager_id = auth.uid());

-- ============================================================
-- 3. Stripe webhook events log (idempotency)
-- ============================================================
CREATE TABLE IF NOT EXISTS stripe_events (
  event_id TEXT PRIMARY KEY,  -- Stripe event ID (evt_xxx)
  event_type TEXT NOT NULL,
  processed_at TIMESTAMPTZ DEFAULT now()
);

-- ============================================================
-- 4. Add manager_id to properties_list
-- ============================================================
ALTER TABLE properties_list
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

-- ============================================================
-- 5. Add columns to complaints
-- ============================================================
ALTER TABLE complaints
  ADD COLUMN IF NOT EXISTS property_group_id UUID REFERENCES properties_list(id),
  ADD COLUMN IF NOT EXISTS assigned_manager_id UUID REFERENCES auth.users(id);

-- ============================================================
-- 6. Enable RLS on ALL data tables
-- ============================================================

-- properties_list
ALTER TABLE properties_list ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_properties"
ON properties_list FOR ALL
USING (manager_id = auth.uid());

-- buildings (via property_id -> properties_list.manager_id)
ALTER TABLE buildings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_buildings"
ON buildings FOR ALL
USING (
  property_id IN (SELECT id FROM properties_list WHERE manager_id = auth.uid())
);

-- flats (via building_id -> buildings -> properties_list)
ALTER TABLE flats ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_flats"
ON flats FOR ALL
USING (
  building_id IN (
    SELECT b.id FROM buildings b
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- tenants (via flat_uuid -> flats -> buildings -> properties_list)
ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_tenants"
ON tenants FOR ALL
USING (
  flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- complaints
ALTER TABLE complaints ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_complaints"
ON complaints FOR ALL
USING (assigned_manager_id = auth.uid());

-- appointments (via complaint_uuid -> complaints)
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_appointments"
ON appointments FOR ALL
USING (
  complaint_uuid IN (
    SELECT uuid FROM complaints WHERE assigned_manager_id = auth.uid()
  )
);

-- rents (via flat_uuid -> flats chain)
ALTER TABLE rents ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_rents"
ON rents FOR ALL
USING (
  flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
  )
);

-- call_logs
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_call_logs"
ON call_logs FOR ALL
USING (
  property_group_id IN (SELECT id FROM properties_list WHERE manager_id = auth.uid())
);

-- feature_toggles (via property_id -> properties_list)
ALTER TABLE feature_toggles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "manager_owns_feature_toggles"
ON feature_toggles FOR ALL
USING (
  property_id IN (SELECT id FROM properties_list WHERE manager_id = auth.uid())
);
```

### Step 0C: Seed existing data to mock manager

```sql
-- Replace <MOCK_MANAGER_UUID> with the UUID from Step 0A.

-- Assign all existing property groups
UPDATE properties_list SET manager_id = '<MOCK_MANAGER_UUID>' WHERE manager_id IS NULL;

-- Assign all existing complaints
UPDATE complaints SET assigned_manager_id = '<MOCK_MANAGER_UUID>' WHERE assigned_manager_id IS NULL;

-- Create the mock manager profile
INSERT INTO manager_profiles (user_id, name, phone)
VALUES ('<MOCK_MANAGER_UUID>', 'Test Manager', '+910000000000');

-- Create a trial subscription for the mock manager
INSERT INTO subscriptions (manager_id, stripe_customer_id, plan, status, trial_ends_at)
VALUES (
  '<MOCK_MANAGER_UUID>',
  'cus_mock_test',
  'trial',
  'trialing',
  now() + interval '14 days'
);
```

### Step 0D: Add `property_group_id` to `call_logs` (if missing)

```sql
-- Only run if call_logs doesn't already have this column
ALTER TABLE call_logs
  ADD COLUMN IF NOT EXISTS property_group_id UUID REFERENCES properties_list(id);
```

> **After running all SQL:** Verify with `SELECT * FROM properties_list LIMIT 5;` that `manager_id` is populated.

---

## Phase 1: Backend — Auth & Authorization

### 1A. Dual Supabase Client Setup

**Why:** The anon-key client respects RLS (used for authenticated manager requests). The service-role client bypasses RLS (used for webhooks, VAPI caller lookup, and admin operations).

**[MODIFY] `backend/app/config.py`**
Add new environment variables:
```python
# New fields to add to Settings class:
SUPABASE_JWT_SECRET: str  # Found in Supabase Dashboard > Settings > API > JWT Secret
STRIPE_SECRET_KEY: str
STRIPE_WEBHOOK_SECRET: str
FRONTEND_URL: str          # e.g., https://your-app.netlify.app
LANDING_PAGE_URL: str      # e.g., https://your-landing.vercel.app
```

**[MODIFY] `backend/app/db/session.py`**
```python
from supabase import create_client, Client
from app.config import settings

# Anon client — respects RLS, used with user JWT for authenticated requests
_anon_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Service-role client — bypasses RLS, used for webhooks/admin/VAPI
_service_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

def get_db() -> Client:
    """Anon client for user-scoped queries (RLS enforced)."""
    return _anon_client

def get_service_db() -> Client:
    """Service-role client for admin operations (RLS bypassed)."""
    return _service_client
```

### 1B. JWT Validation Dependency

**[NEW] `backend/app/dependencies/auth.py`**

Validates the Supabase JWT from the `Authorization: Bearer <token>` header.

```python
import jwt  # PyJWT — already in requirements.txt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.config import settings
from app.db.session import get_db

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Decode and verify the Supabase JWT.
    Returns the full JWT payload (sub, email, role, etc.).
    Raises 401 if invalid/expired.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

    return payload  # payload["sub"] is the auth.users UUID
```

### 1C. Subscription Gate Dependency

**[NEW] `backend/app/dependencies/subscription.py`**

Checks that the manager has an active or trialing subscription before allowing CRM access.

```python
from fastapi import Depends, HTTPException
from supabase import Client
from app.db.session import get_service_db
from app.dependencies.auth import get_current_user

async def require_active_subscription(
    user: dict = Depends(get_current_user),
    db: Client = Depends(get_service_db),
):
    """
    Raises 403 if the manager's subscription is not active or trialing.
    Uses service client to bypass RLS (subscriptions table is SELECT-only for managers).
    """
    manager_id = user["sub"]

    result = db.table("subscriptions") \
        .select("status, trial_ends_at") \
        .eq("manager_id", manager_id) \
        .in_("status", ["trialing", "active"]) \
        .limit(1) \
        .execute()

    if not result.data:
        raise HTTPException(
            status_code=403,
            detail="No active subscription. Please subscribe to continue.",
        )

    return user  # Pass through for downstream use
```

### 1D. Set User JWT on Anon Client (per-request)

**[NEW] `backend/app/dependencies/authenticated_db.py`**

For RLS to work, the anon client must carry the user's JWT so Supabase knows which `auth.uid()` to resolve.

```python
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import Client
from app.db.session import get_db

security = HTTPBearer()

async def get_authenticated_db(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Client = Depends(get_db),
) -> Client:
    """
    Set the user's JWT on the Supabase client so RLS policies
    resolve auth.uid() correctly for this request.
    """
    db.postgrest.auth(credentials.credentials)
    return db
```

### 1E. Retrofit All Existing Routes

Every existing route file (16 total) must be updated to:
1. Accept `user: dict = Depends(require_active_subscription)` as a parameter
2. Use `db: Client = Depends(get_authenticated_db)` instead of `Depends(get_db)`
3. RLS handles data isolation automatically — no manual `WHERE manager_id = ...` needed

**Files to modify:**
- `routes/complaints.py`
- `routes/flats.py`
- `routes/appointments.py`
- `routes/tenants.py`
- `routes/properties.py`
- `routes/property_groups.py`
- `routes/buildings.py`
- `routes/property_types.py`
- `routes/rents.py`
- `routes/settings.py` (feature toggles)
- `routes/call_logs.py`
- `routes/upload.py`
- `routes/workflow.py`
- `routes/chat.py`

**Exempt from auth (use service client, no user JWT):**
- `routes/voice.py` — VAPI webhook (machine-to-machine, validated by VAPI signature)
- `routes/payments.py` — Stripe webhook (validated by Stripe signature)
- `routes/flats.py: /flats/identify-caller` — VAPI tool call (service client, bypasses RLS)

### 1F. CORS Lockdown

**[MODIFY] `backend/app/main.py`**

Replace the current `allow_origins=["*"]` with explicit origins:

```python
from app.config import settings as config

allowed_origins = [
    origin.strip()
    for origin in config.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,   # Required for cookies/auth headers
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Set `ALLOWED_ORIGINS` env var to: `https://your-app.netlify.app,https://your-landing.vercel.app`

> **Note on VAPI:** VAPI calls your backend server-to-server (not from a browser), so CORS does not apply to VAPI webhook requests. No special CORS exception is needed.

### 1G. Rate Limiting

**[NEW] Add `slowapi` to `requirements.txt`**

Apply rate limits to abuse-prone endpoints:

| Endpoint | Limit | Why |
|----------|-------|-----|
| `POST /payments/webhook` | 30/min | Stripe retries, but cap abuse |
| `POST /flats/identify-caller` | 60/min | VAPI calls, but cap abuse |
| `POST /chat` | 20/min per user | LLM cost protection |
| Auth-related (handled by Supabase) | N/A | Supabase has built-in rate limits |

---

## Phase 2: Backend — Stripe Integration

### 2A. Payments Route

**[NEW] `backend/app/routes/payments.py`**

Two responsibilities:
1. **Create Checkout Session** — called by Leadpipe-1 to start a subscription with $1 card verification + 14-day trial
2. **Webhook Handler** — receives Stripe events to update subscription status

```
POST /payments/create-checkout-session
  - Accepts: { manager_id, email }
  - Creates a Stripe Customer (if not exists)
  - Creates a Checkout Session with:
      - mode: "subscription"
      - subscription_data.trial_period_days: 14
      - subscription_data.trial_settings.end_behavior.missing_payment_method: "cancel"
      - payment_method_collection: "always" (forces card entry)
      - A $1 setup_fee line item (type: "one_time") to verify card
  - Returns: { checkout_url }

POST /payments/webhook
  - Validates Stripe-Signature header using stripe.Webhook.construct_event()
  - Idempotency: check stripe_events table before processing
      - INSERT event_id; if conflict (duplicate), skip
  - Handles these events:
      - customer.subscription.created → INSERT into subscriptions (status=trialing)
      - customer.subscription.updated → UPDATE status, current_period_end
      - customer.subscription.deleted → UPDATE status=canceled
      - invoice.payment_succeeded → UPDATE status=active (trial converted)
      - invoice.payment_failed → UPDATE status=past_due
  - Always returns HTTP 200 (Stripe retries on non-2xx)
```

### 2B. Stripe Idempotency Pattern

```python
# Inside webhook handler — prevents duplicate processing
def is_duplicate_event(db: Client, event_id: str) -> bool:
    """Returns True if this Stripe event was already processed."""
    try:
        db.table("stripe_events").insert({
            "event_id": event_id,
            "event_type": event.type,
        }).execute()
        return False  # New event, process it
    except Exception:
        return True  # Duplicate, skip
```

---

## Phase 3: Backend — VAPI Option B (Caller Lookup)

### 3A. Identify Caller Endpoint

**[MODIFY] `backend/app/routes/flats.py`**

Add a new endpoint alongside the existing ones. This uses the **service-role client** because it must search across ALL managers' data (RLS would block cross-tenant lookups).

```
POST /flats/identify-caller
  - Input: { "phone_number": "+91XXXXXXXXXX" }
  - Uses service client (bypasses RLS)
  - Performs a single-pass lookup:
      Phone → tenants.tenant_phone → flat_uuid → flats → building_id → buildings → property_id → properties_list → manager_id → manager_profiles
  - Returns (200):
      {
        "exists": true,
        "tenant_name": "...",
        "flat_number": "...",
        "building_name": "...",
        "society_name": "...",          // properties_list.name
        "property_group_id": "...",     // for subsequent VAPI tool calls
        "manager_name": "...",
        "manager_phone": "..."
      }
  - Returns (200, not found):
      {
        "exists": false,
        "message": "We don't recognize your number. Please contact your property manager directly."
      }
  - VAPI behavior on exists=false: play the message and end the call
```

### 3B. VAPI Assistant Configuration

Update the VAPI assistant to:
1. Call `/flats/identify-caller` as the **first tool** at the start of every inbound call
2. Use the returned `property_group_id` for all subsequent tool calls (file complaint, check appointments, etc.)
3. If `exists: false`, speak the fallback message and hang up

> **Note:** This is configured in the VAPI Dashboard, not in code.

---

## Phase 4: Frontend CRM — Auth Integration

### 4A. Install Dependencies

```bash
cd frontend
npm install @supabase/supabase-js
```

### 4B. Supabase Client

**[NEW] `frontend/src/lib/supabase.js`**

```javascript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  import.meta.env.VITE_SUPABASE_URL,
  import.meta.env.VITE_SUPABASE_ANON_KEY,
)
```

### 4C. Auth Context

**[NEW] `frontend/src/context/AuthContext.jsx`**

```javascript
// Provides: { user, session, loading, signOut }
// On mount: supabase.auth.getSession() + onAuthStateChange listener
// If session found via URL hash (detectSessionInUrl): auto-login
// If no session: redirect to LANDING_PAGE_URL/auth
```

### 4D. Auth Guard on App.jsx

**[MODIFY] `frontend/src/App.jsx`**

Wrap the entire app in `<AuthProvider>`. If `loading`, show spinner. If `!session`, redirect to Leadpipe-1 auth page. If session exists, render the dashboard.

### 4E. Add Bearer Token to All API Calls

**[MODIFY] `frontend/src/services/apiService.js`**

Create a helper that attaches the JWT:

```javascript
import { supabase } from '../lib/supabase'

async function authFetch(url, options = {}) {
  const { data: { session } } = await supabase.auth.getSession()

  if (!session) {
    window.location.href = import.meta.env.VITE_LANDING_PAGE_URL + '/auth'
    throw new Error('No active session')
  }

  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${session.access_token}`,
  }

  // Don't override Content-Type for FormData (browser sets multipart boundary)
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json'
  }

  const response = await fetch(url, { ...options, headers })

  if (response.status === 401) {
    // Token expired — redirect to re-auth
    await supabase.auth.signOut()
    window.location.href = import.meta.env.VITE_LANDING_PAGE_URL + '/auth'
    throw new Error('Session expired')
  }

  if (response.status === 403) {
    // No active subscription — redirect to pricing
    window.location.href = import.meta.env.VITE_LANDING_PAGE_URL + '/pricing'
    throw new Error('Subscription required')
  }

  return response
}
```

Replace all `fetch(...)` calls in `apiService.js` with `authFetch(...)`.

### 4F. Logout Flow

Add a logout button in the sidebar/topbar:
```javascript
await supabase.auth.signOut()
window.location.href = import.meta.env.VITE_LANDING_PAGE_URL
```

This clears the local Supabase session and redirects to the landing page.

---

## Phase 5: Leadpipe-1 — Auth Portal & Pricing

### 5A. Install Dependencies

```bash
cd Leadpipe-1
pnpm install @supabase/supabase-js stripe
```

### 5B. Supabase Client

**[NEW] `src/lib/supabase.ts`**

```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
)
```

### 5C. Auth Page

**[NEW] `src/app/auth/page.tsx`**

- Login + Sign Up form (email/password)
- On sign up success:
  1. Create `manager_profiles` row (via Supabase client or a backend endpoint)
  2. Redirect to pricing page for subscription setup
- On login success:
  1. Redirect to CRM: `{FRONTEND_URL}#access_token={token}&refresh_token={refresh}&type=recovery`
  2. The CRM's Supabase client picks this up via `detectSessionInUrl` (default behavior)

### 5D. Pricing Page

**[NEW] `src/app/pricing/page.tsx`**

- Display subscription tier(s) and pricing
- "Start 14-Day Free Trial" button
- On click:
  1. Call backend `POST /payments/create-checkout-session` with the manager's ID and email
  2. Redirect to the returned Stripe Checkout URL
- Stripe Checkout handles card entry + $1 verification charge
- On success: Stripe redirects to a success page, webhook activates the subscription
- On cancel: Stripe redirects back to pricing page

### 5E. Stripe Success Page

**[NEW] `src/app/pricing/success/page.tsx`**

- "You're all set! Redirecting to your dashboard..."
- Auto-redirect to CRM frontend URL after 3 seconds
- Fallback "Go to Dashboard" link

---

## Phase 6: Production Hardening

### 6A. Environment Variables — Complete Reference

**Backend (`Tenant_management_MVP/backend/.env`)**:
```env
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...                          # anon key
SUPABASE_SERVICE_KEY=eyJ...                  # service role key
SUPABASE_JWT_SECRET=your-jwt-secret          # Dashboard > Settings > API

# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRICE_ID=price_xxx                    # Your subscription price ID

# URLs
FRONTEND_URL=https://your-app.netlify.app
LANDING_PAGE_URL=https://your-landing.vercel.app
BACKEND_URL=https://your-backend.onrender.com

# CORS
ALLOWED_ORIGINS=https://your-app.netlify.app,https://your-landing.vercel.app

# Existing (unchanged)
OPEN_AI_API=...
PRIVATE_VAPI_API=...
VAPI_NUMBER_ID=...
VAPI_ASSISTANT_ID=...
GROQ_API_KEY=...
```

**Frontend CRM (`Tenant_management_MVP/frontend/.env`)**:
```env
VITE_API_URL=https://your-backend.onrender.com
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_LANDING_PAGE_URL=https://your-landing.vercel.app
```

**Leadpipe-1 (`Leadpipe-1/.env.local`)**:
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com
NEXT_PUBLIC_FRONTEND_URL=https://your-app.netlify.app
STRIPE_SECRET_KEY=sk_live_xxx   # server-side only (no NEXT_PUBLIC_ prefix)
```

### 6B. Update `.env.example` Files

Update all three `.env.example` files to document every required variable (with placeholder values, no secrets).

### 6C. Error Handling & Logging

- **Stripe webhooks**: Log every event received (event ID, type, timestamp). On processing error, log the full error but still return HTTP 200 (to prevent Stripe retries flooding a broken handler).
- **Auth failures**: Log failed JWT validation attempts (IP, timestamp) for security monitoring.
- **VAPI identify-caller**: Log lookup attempts and results for debugging.

### 6D. Update `requirements.txt`

Add:
```
stripe>=7.0.0
slowapi>=0.1.9
```

---

## Phase 7: Testing

> **Tell me before starting this phase — I will outline the test implementation details at that time.**

### 7A. Unit Tests

| Test | What it validates |
|------|-------------------|
| `test_jwt_validation` | Valid token decodes correctly; expired/invalid tokens raise 401 |
| `test_subscription_gate` | Active/trialing passes; canceled/missing raises 403 |
| `test_stripe_webhook_signature` | Valid signature passes; tampered signature raises 400 |
| `test_stripe_idempotency` | Duplicate event ID is skipped, not double-processed |
| `test_identify_caller_found` | Known phone returns correct tenant + property chain |
| `test_identify_caller_not_found` | Unknown phone returns `exists: false` |
| `test_identify_caller_normalization` | Phone with/without +91, spaces, dashes all resolve |

### 7B. Integration Tests

| Test | What it validates |
|------|-------------------|
| `test_rls_isolation` | Manager A cannot see Manager B's properties, complaints, tenants |
| `test_auth_flow_e2e` | Sign up → create profile → get JWT → call protected route → success |
| `test_subscription_lifecycle` | Create checkout → webhook fires → subscription active → access granted |
| `test_trial_expiry` | After trial_ends_at passes, status changes, access denied |
| `test_unauthenticated_access` | All protected routes return 401 without token |

### 7C. End-to-End Tests

| Test | What it validates |
|------|-------------------|
| `test_signup_to_dashboard` | Leadpipe-1 signup → redirect to CRM → dashboard loads with session |
| `test_login_existing_user` | Login → redirect → see own properties only |
| `test_vapi_full_call_flow` | Simulate inbound call → identify caller → file complaint → verify in DB |
| `test_logout_and_redirect` | Logout from CRM → lands on Leadpipe-1 → CRM is inaccessible |
| `test_expired_trial_redirect` | Expired trial user → CRM redirects to pricing page |

---

## Implementation Order

```
Phase 0  ─── Database schema + RLS + mock manager seed
             ↓
Phase 1  ─── Backend auth (JWT, subscription gate, dual client, CORS)
             ↓
Phase 2  ─── Backend Stripe (checkout session, webhook, idempotency)
             ↓
Phase 3  ─── Backend VAPI Option B (identify-caller endpoint)
             ↓
Phase 4  ─── Frontend CRM (Supabase client, auth context, authFetch, logout)
             ↓
Phase 5  ─── Leadpipe-1 (auth page, pricing page, Stripe checkout redirect)
             ↓
Phase 6  ─── Production hardening (env vars, CORS, logging, rate limits)
             ↓
Phase 7  ─── Testing (unit → integration → e2e)
```

Each phase is deployable independently. Phase 0 (SQL) is a prerequisite for everything else. Phases 1-3 (backend) can be developed before Phases 4-5 (frontend) since they have no frontend dependency.

---

## Verification Checklist

- [ ] **Auth**: Create account on Leadpipe-1 → redirect to CRM → dashboard loads with active session
- [ ] **RLS**: Log in as Manager A → can only see Manager A's data. Log in as Manager B → isolated data
- [ ] **Trial**: New signup → 14-day trial active → CRM accessible → $1 card charge visible in Stripe
- [ ] **Payment**: Trial expires → CRM returns 403 → user redirected to pricing → subscribe → access restored
- [ ] **Webhook idempotency**: Send same Stripe event twice → only one DB write
- [ ] **VAPI caller lookup**: Known number → returns property chain. Unknown number → `exists: false`
- [ ] **Logout**: Click logout → session cleared → redirect to Leadpipe-1 → CRM inaccessible
- [ ] **CORS**: API rejects requests from unauthorized origins
- [ ] **Token expiry**: Expired JWT → 401 → auto-redirect to re-auth
