# Architecture Plan — Scaling the Tenant CRM

> Written for internal use. Covers auth, payments, and VAPI multi-tenancy.
> Stack: FastAPI + Supabase + React/Vite + VAPI + Twilio + Groq

---

## Table of Contents

1. [Auth — Supabase Auth](#1-auth--supabase-auth)
2. [Payments — Stripe](#2-payments--stripe)
3. [VAPI Multi-Tenancy — The Core Problem](#3-vapi-multi-tenancy--the-core-problem)
   - [Option A: One Phone Number per PropertyGroup](#option-a-one-phone-number-per-propertygroup-recommended)
   - [Option B: Single Number + Caller Phone Lookup](#option-b-single-number--caller-phone-lookup)
   - [Option C: VAPI Server URL Webhook for Dynamic Context](#option-c-vapi-server-url-webhook-for-dynamic-context)
   - [Option D: IVR Tree (Press 1 for Society A...)](#option-d-ivr-tree-press-1-for-society-a)
4. [Complaint Routing to Different Managers](#4-complaint-routing-to-different-managers)
5. [DB Schema Changes Needed](#5-db-schema-changes-needed)
6. [Recommended Implementation Order](#6-recommended-implementation-order)
7. [Pricing — What to Charge](#7-pricing--what-to-charge)

---

## 1. Auth — Supabase Auth

### Is this a good plan?

**Yes. It is the right choice given the existing stack.** You are already using the Supabase Python client (`supabase.Client`). Adding auth does not require a new library — it uses the same client you already have.

### How it works technically

Supabase Auth is a managed JWT service sitting on top of PostgreSQL.

```
User logs in → Supabase issues JWT → JWT sent with every API request
FastAPI verifies JWT → extracts user_id + role → scopes data access
```

**Backend — JWT verification in FastAPI:**

```python
# backend/app/dependencies/auth.py (new file)
from fastapi import Depends, HTTPException, Header
from supabase import Client
from app.db.session import get_db

async def get_current_user(authorization: str = Header(...), db: Client = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    try:
        user = db.auth.get_user(token)
        return user.user  # has .id, .email, .user_metadata
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
```

**Frontend — login flow:**

```js
// frontend/src/services/apiService.js
const { data, error } = await supabase.auth.signInWithPassword({
  email, password
})
// data.session.access_token — attach to all API calls as Bearer token
```

### Row Level Security (RLS) — the real power

Once auth is in place, you add RLS policies directly in Supabase SQL editor. This means the database itself enforces data isolation — no manager can ever see another manager's tenants, even if a bug exists in your FastAPI code.

```sql
-- Only show buildings that belong to this user's property groups
CREATE POLICY "manager_sees_own_buildings"
ON buildings FOR ALL
USING (
  property_id IN (
    SELECT id FROM properties_list
    WHERE manager_id = auth.uid()
  )
);
```

### Roles to implement

| Role | What they see |
|------|---------------|
| `super_admin` | All PropertyGroups, all data |
| `manager` | Only their assigned PropertyGroups |
| `tenant` (future) | Only their own flat + complaints |

### Pros

- No extra library needed — same `supabase.Client` you already use
- RLS makes multi-tenancy data isolation automatic and bulletproof
- Free tier covers up to 50,000 monthly active users
- Built-in password reset, email confirmation, OAuth (Google login)
- Pairs directly with VAPI multi-tenancy: once you know `auth.uid()` you know which society to scope

### Cons

- Requires adding `manager_id UUID REFERENCES auth.users(id)` to `properties_list` table
- Every existing API endpoint needs the `get_current_user` dependency injected
- RLS policies need careful testing — wrong policy = silently empty results, not an error
- The Python SDK's `get_user(token)` makes a network call every request — consider caching the decoded JWT locally for performance

---

## 2. Payments — Stripe

### Is this a good plan?

**Yes. Stripe is the industry standard and the right choice.** For an Indian market product, also evaluate Razorpay (better INR support, lower fees for domestic cards, UPI), but Stripe works fine if clients are okay with card/international payments.

### What you are likely charging for

There are two different payment use cases in a property CRM:

| Use Case | What it is |
|----------|------------|
| **SaaS billing** | You charge the property manager a monthly subscription to use your CRM |
| **Rent collection** | Tenants pay rent through the app, you take a transaction fee |

Both are valid. Most CRMs start with SaaS billing and add rent collection later.

### SaaS Billing — Technical Flow

```
Manager signs up → selects plan → Stripe Checkout → webhook to your backend →
activate subscription in DB → gate features behind subscription status
```

**Backend — Stripe webhook endpoint:**

```python
# backend/app/routes/payments.py (new file)
import stripe
from fastapi import APIRouter, Request, Header, HTTPException

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None)):
    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "customer.subscription.created":
        # activate property group in DB
        pass
    elif event["type"] == "customer.subscription.deleted":
        # deactivate / lock out manager
        pass

    return {"status": "ok"}
```

**Key Stripe objects you need:**

- `Customer` — one per property manager (linked to `auth.uid()`)
- `Product` — your CRM plan (Basic, Pro, Enterprise)
- `Price` — monthly recurring price for each product
- `Subscription` — links customer to product
- `Webhook` — notifies your server when subscription status changes

### Pros

- Stripe handles PCI compliance — you never touch raw card numbers
- Excellent developer docs and Python library (`pip install stripe`)
- Subscription management, invoices, refunds all built-in
- Test mode lets you simulate payments without real money
- Stripe Portal: tenants/managers can manage their own subscription without you building a UI

### Cons

- 2.9% + $0.30 per transaction fee (cuts into margins on small rent amounts)
- Stripe is US-registered — Indian payouts require KYC/business registration
- UPI is NOT supported on Stripe — huge gap for Indian tenants paying rent
- If rent collection is the goal, **Razorpay is a better fit** for India (supports UPI, NetBanking, UPI AutoPay for recurring)

### Recommendation

Use **Stripe for SaaS billing** (manager pays you monthly). Use **Razorpay for rent collection** (tenant pays rent). They can coexist — different routes, different webhooks.

---

## 3. VAPI Multi-Tenancy — The Core Problem

### What is the problem?

Currently your VAPI setup has a single AI voice agent that answers calls. It has no concept of "which society is this call for." When a tenant calls, the agent:

- Calls `/flats/verify-phone` to identify the tenant ✓
- Calls `/tenants/by-flat/{flat_no}` to get tenant info ✓
- But does NOT know which PropertyGroup to scope complaints to ✗
- Does NOT know which manager to notify when a complaint is filed ✗
- Does NOT greet the tenant with their society's name ✗

Your current `PropertyGroup → Building → Flat → Tenant` chain has the information — it just isn't being passed to VAPI properly.

---

### Option A: One Phone Number per PropertyGroup (Recommended)

**How it works:**

Each client (society/real estate company) gets a dedicated phone number assigned to their own VAPI assistant. The `property_group_id` is hardcoded into that assistant's system prompt as a constant.

```
Society "Green Meadows" → +91-XXXXX-00001 → VAPI Assistant (pg_id = "abc-123")
Society "Blue Heights"  → +91-XXXXX-00002 → VAPI Assistant (pg_id = "def-456")
Society "Sunset Villas" → +91-XXXXX-00003 → VAPI Assistant (pg_id = "ghi-789")
```

**VAPI assistant system prompt (per assistant):**

```
You are the voice assistant for Green Meadows Housing Society.
Your property_group_id is: abc-123-...
When calling any tool, always pass property_group_id: "abc-123-..."
Manager on duty: Mr. Sharma (complaints are routed to him automatically)
```

**Your FastAPI tool endpoints change to accept `property_group_id`:**

```python
# backend/app/routes/flats.py
class VerifyPhoneRequest(BaseModel):
    phone: str
    property_group_id: str  # NEW — sent by VAPI from its constant

@router.post("/flats/verify-phone")
async def verify_phone(request: VerifyPhoneRequest, db: Client = Depends(get_db)):
    phone = request.phone.strip()
    # Scope lookup to this society only
    flat_resp = (
        db.table("flats")
        .select("*, buildings!inner(property_id)")
        .eq("tenant_phone", phone)
        .eq("buildings.property_id", request.property_group_id)
        .execute()
    )
    exists = bool(flat_resp.data)
    return {"exists": exists, "flat_no": flat_resp.data[0]["flat_number"] if exists else None}
```

**Complaint filing tool — routes to the right manager:**

```python
# In chatbot.py tool handler
def file_complaint(flat_no: str, category: str, description: str, property_group_id: str):
    # 1. Find the manager for this property group
    pg = db.table("properties_list").select("manager_id").eq("id", property_group_id).single().execute()
    manager_id = pg.data["manager_id"]

    # 2. Insert complaint linked to manager
    db.table("complaints").insert({
        "flat_no": flat_no,
        "category": category,
        "description": description,
        "property_group_id": property_group_id,
        "assigned_to": manager_id,
        "status": "open"
    }).execute()

    # 3. Notify manager via Twilio SMS
    send_sms(manager_phone, f"New complaint from Flat {flat_no}: {description}")

    return "Complaint filed. Your manager has been notified."
```

**Cost:** VAPI phone numbers cost approximately $2–5/month per number. For 10 societies = $20–50/month. Pass this cost to the client.

### Pros
- Cleanest architecture — zero routing logic, zero ambiguity
- Each assistant can have a custom greeting, custom manager name, custom escalation number
- Easy to debug — you always know which society a call came from
- Society-specific call logs and analytics are automatic
- Can customize the AI's persona per society ("Hi, welcome to Green Meadows...")

### Cons
- Cost scales with number of clients ($2–5/number/month)
- Creating a new VAPI assistant for each client is manual work — needs automation later (VAPI API lets you create assistants programmatically)
- VAPI dashboard gets cluttered with many assistants

### Pricing

| | Cost | Notes |
|-|------|-------|
| **Your dev fee (charge manager)** | ₹3,500 – ₹5,000 | Update verify-phone + complaint routes, add `property_group_id` to tool calls, configure VAPI assistants per client in dashboard |
| **VAPI phone number** | ~$3/month per society (~₹250/month) | Recurring infrastructure — not your cost, pass to manager/client |
| **10 societies running cost** | ~$30/month (~₹2,500/month) | Entirely on the client side |

---

### Option B: Single Number + Caller Phone Lookup

**How it works:**

One phone number for everything. When a tenant calls, the very first VAPI tool call is `identify_caller(phone)`. Your backend looks up the tenant by phone number, resolves the chain to find their society and manager, and returns all the context. VAPI injects this into the conversation via the tool response.

```
Tenant calls +91-XXXXX-00001 (single number)
→ VAPI calls identify_caller("+919XXXXXXXX")
→ Your API: phone → Flat A-204 → Building "Tower A" → Green Meadows → Manager Sharma
→ Returns: { society: "Green Meadows", manager: "Mr. Sharma", property_group_id: "abc-123" }
→ VAPI now has full context for all subsequent tool calls
```

**New identify_caller endpoint:**

```python
# backend/app/routes/flats.py
@router.post("/flats/identify-caller")
async def identify_caller(request: IdentifyCallerRequest, db: Client = Depends(get_db)):
    phone = request.phone.strip()

    # Single query with full chain join
    result = (
        db.table("flats")
        .select("flat_number, tenant_uuid, buildings!inner(id, name, property_id, properties_list!inner(id, name, manager_id))")
        .eq("tenant_phone", phone)
        .execute()
    )

    if not result.data:
        return {"identified": False}

    flat = result.data[0]
    building = flat["buildings"]
    society = building["properties_list"]

    # Get manager phone for notification
    manager = db.table("manager_profiles").select("name, phone").eq("user_id", society["manager_id"]).single().execute()

    return {
        "identified": True,
        "flat_no": flat["flat_number"],
        "building_name": building["name"],
        "society_name": society["name"],
        "property_group_id": society["id"],
        "manager_name": manager.data["name"],
        "manager_phone": manager.data["phone"]
    }
```

**The VAPI system prompt tells the agent:**

```
At the start of every call, call identify_caller() with the caller's phone number.
Use the returned society_name in your greeting.
Use the returned property_group_id in all subsequent tool calls.
If identified is false, ask the tenant to state their society name and flat number.
```

### Pros
- Single phone number — easier for tenants to remember one number
- No per-society VAPI assistant maintenance
- Tenants who move between societies still work (their new phone registration covers them)
- No additional phone number cost

### Cons
- Relies entirely on the tenant's phone number being registered in your DB — if it isn't, fallback logic is needed
- Every call has an extra identify_caller roundtrip at the start (adds ~1s latency)
- If a tenant calls from a different number (office phone, borrowed phone), identification fails
- One VAPI assistant serves all societies — harder to customize the greeting/persona per society
- A bug in identification = wrong society context for the entire call

### Pricing

| | Cost | Notes |
|-|------|-------|
| **Your dev fee (charge manager)** | ₹4,500 – ₹6,500 | New `/identify-caller` endpoint with full chain join (flat→building→society→manager), fallback flow for unknown callers, VAPI system prompt update |
| **VAPI phone number** | ~$3/month (~₹250/month) | One number for all societies — fixed cost regardless of how many clients you add |
| **Running cost at scale** | ~$3–5/month (~₹250–415/month) | Does not grow with number of societies — big advantage over Option A at scale |

---

### Option C: VAPI Server URL Webhook for Dynamic Context

**How it works:**

VAPI has a `serverUrl` field on every assistant. When a call starts, VAPI sends a POST to your `serverUrl` with `{message: {type: "assistant-request"}}` or `{type: "call.started"}`. Your server responds with `overrideAssistantSettings` — you can inject variables, update the system prompt, swap tools, all dynamically before the call begins.

```
Call starts → VAPI POST /vapi/call-hook → Your server looks up caller phone
→ Returns overrideAssistantSettings with injected variableValues
→ VAPI's system prompt now has {{society_name}}, {{manager_name}} filled in
→ Call proceeds with fully contextualized agent
```

**Backend webhook handler:**

```python
# backend/app/routes/voice.py (add to existing file)
@router.post("/vapi/call-hook")
async def vapi_call_hook(payload: dict, db: Client = Depends(get_db)):
    msg_type = payload.get("message", {}).get("type", "")

    if msg_type == "assistant-request":
        caller_phone = payload.get("message", {}).get("call", {}).get("customer", {}).get("number", "")
        context = await resolve_caller_context(caller_phone, db)

        return {
            "assistant": {
                "variableValues": {
                    "society_name": context.get("society_name", "your society"),
                    "manager_name": context.get("manager_name", "the manager"),
                    "property_group_id": context.get("property_group_id", ""),
                }
            }
        }

    return {}  # VAPI ignores empty responses for other event types
```

**VAPI assistant system prompt uses variables:**

```
You are the voice assistant for {{society_name}}.
Always use property_group_id={{property_group_id}} in tool calls.
The manager for this society is {{manager_name}}.
```

### Pros
- Most powerful and flexible approach
- Single assistant, unlimited societies, fully dynamic context
- Context is injected BEFORE the agent speaks — greeting is correct from word one
- Variables are available to all tools for the entire call duration
- No extra tool call latency at the start of the conversation

### Cons
- Hardest to implement and debug
- Your server must respond to the webhook within VAPI's timeout window (~2 seconds)
- If your server is down or slow, VAPI falls back to the default (uncontextualized) assistant
- Requires solid understanding of VAPI's webhook payload structure (changes between VAPI versions)
- Requires your server to be publicly accessible (ngrok or deployed — no localhost)

### Pricing

| | Cost | Notes |
|-|------|-------|
| **Your dev fee (charge manager)** | ₹7,000 – ₹10,000 | Webhook handler, `resolve_caller_context()` logic, VAPI variable injection, timeout/fallback handling, deployment config — most work of any option |
| **VAPI phone number** | ~$3/month (~₹250/month) | Single number, same as Option B |
| **Deployment requirement** | ₹500–1,500/month | Server must be publicly accessible — Railway/Render free tier works; this cost applies to the whole backend, not just VAPI |
| **Running cost at scale** | ~$3–5/month (~₹250–415/month) | Same as Option B — flat cost regardless of client count |

The higher dev fee here is justified: you are building uptime-sensitive infrastructure. If the webhook handler crashes or times out, every call across all societies breaks simultaneously.

---

### Option D: IVR Tree ("Press 1 for Society A...")

**How it works:**

Single number, caller presses a digit to select their society. VAPI routes to different assistant flows based on the digit pressed.

```
"Welcome. Press 1 for Green Meadows, Press 2 for Blue Heights, Press 3 for Sunset Villas"
→ Caller presses 2 → VAPI transfers to Blue Heights assistant
```

### Pros
- Familiar experience for non-tech-savvy tenants
- No phone number DB requirement

### Cons
- Bad UX — tenants hate phone trees
- Doesn't scale past 4-5 societies on a single number
- Feels like a 2005 call center, not a modern AI assistant
- Hard to maintain as societies are added

### Pricing

| | Cost | Notes |
|-|------|-------|
| **Your dev fee (charge manager)** | ₹1,500 – ₹2,500 | Mostly VAPI flow configuration, minimal backend changes |
| **VAPI phone number** | ~$3/month (~₹250/month) | Single number |
| **Running cost at scale** | ~$3–5/month (~₹250–415/month) | Flat cost |

Low dev fee because there is barely any backend work. Do not recommend this to your manager — the low cost is not worth the poor tenant experience and the hard ceiling of 4–5 societies.

**This is the worst option. Avoid it.**

---

## 4. Complaint Routing to Different Managers

### Required DB changes

```sql
-- Add manager_id to properties_list (your PropertyGroup table)
ALTER TABLE properties_list
ADD COLUMN manager_id UUID REFERENCES auth.users(id);

-- Add assigned_manager_id to complaints table
ALTER TABLE complaints
ADD COLUMN assigned_manager_id UUID REFERENCES auth.users(id);

-- New table for manager profiles (extends auth.users)
CREATE TABLE manager_profiles (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  phone       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

### Routing flow (regardless of VAPI option chosen)

```
Complaint created (via VAPI or CRM dashboard)
    │
    ▼
Look up flat → building → property_group → manager_id
    │
    ▼
INSERT into complaints with assigned_manager_id = manager_id
    │
    ├──▶ Send Twilio SMS to manager phone: "New complaint from Flat X-204"
    │
    └──▶ (Future) Send push notification / email
```

### Manager dashboard scoping (with RLS)

```sql
-- Managers only see complaints assigned to them
CREATE POLICY "manager_sees_own_complaints"
ON complaints FOR SELECT
USING (assigned_manager_id = auth.uid());
```

This is the cleanest way to do it — the DB enforces isolation, the frontend just shows whatever it gets.

---

## 5. DB Schema Changes Needed

Here is a complete list of changes required across auth + payments + VAPI multi-tenancy:

| Table | Change | Why |
|-------|--------|-----|
| `properties_list` | Add `manager_id UUID REFERENCES auth.users` | Link society to a manager |
| `complaints` | Add `assigned_manager_id UUID` | Route to correct manager |
| `complaints` | Add `property_group_id UUID` | Filter by society in dashboard |
| `buildings` | `property_id` already exists | No change needed |
| NEW: `manager_profiles` | `user_id, name, phone` | Manager contact info for SMS |
| NEW: `subscriptions` | `manager_id, stripe_customer_id, plan, status` | Track SaaS billing |
| NEW: `payments` (optional) | `flat_uuid, amount, stripe_payment_id, paid_at` | Rent collection ledger |

---

## 6. Recommended Implementation Order

Build in this order — each step unblocks the next:

```
Step 1: Supabase Auth
        ├── Add manager_id to properties_list
        ├── Create manager_profiles table
        ├── Add login/logout to frontend
        └── Add get_current_user dependency to all routes

Step 2: VAPI Multi-tenancy (Option A recommended)
        ├── Add property_group_id to verify-phone + complaint tools
        ├── Add assigned_manager_id to complaint creation
        └── Create one VAPI assistant per existing client (test with 2-3 first)

Step 3: Complaint Routing
        ├── Wire up Twilio SMS notification on complaint creation
        └── Add RLS policies

Step 4: Stripe SaaS Billing
        ├── Create Stripe products and prices
        ├── Add /payments/checkout and /payments/webhook routes
        └── Gate dashboard access behind active subscription

Step 5: Razorpay Rent Collection (if needed)
        └── Separate from Stripe — different SDK, different webhook
```

---

## 7. Pricing — What to Charge Your Manager

### Your situation

- Base CRM already delivered for ₹22,000
- Manager knows Claude Code was used
- You are a first-time freelance developer
- These are add-on features to an existing, working codebase

The prices below are what you charge your **manager** for each new feature. They are calibrated honestly — not aspirational freelancer rates, not rock-bottom intern rates. They reflect real work done faster with AI tools.

---

### Auth — Supabase Auth + RLS

**What you are building:**
Login/logout UI, JWT verification dependency added to all 16 existing routes, RLS policies in Supabase, `manager_profiles` table, role-based access (super_admin vs manager).

**Effort with Claude Code:** 2–3 days

**Charge: ₹5,000 – ₹7,000**

This is non-trivial even with AI — RLS policies require understanding the full DB schema, and wiring the JWT dependency into 16 routes means touching every single route file.

---

### Payment Gateway

#### Stripe (SaaS billing — manager pays monthly to use the CRM)

**What you are building:**
Stripe SDK setup, `/payments/checkout` + `/payments/webhook` routes, `subscriptions` table in DB, frontend payment/plan selection page, feature gating behind subscription status.

**Effort with Claude Code:** 2–3 days

**Charge: ₹4,500 – ₹6,500**

#### Razorpay (rent collection — tenant pays rent through the app)

**What you are building:**
Razorpay SDK, payment order creation endpoint, webhook for payment confirmation, `payments` ledger table, rent status update on successful payment.

**Effort with Claude Code:** 2–3 days

**Charge: ₹4,500 – ₹6,500**

> If the manager wants both Stripe + Razorpay: charge ₹8,000 – ₹11,000 total (there is overlap in the webhook handling pattern so it is not double the work).

---

### Voice Agent Multi-Tenancy — Summary

| Option | What you build | Your fee | Infra cost (client pays) |
|--------|---------------|----------|--------------------------|
| **A — One number per society** | Route scoping, update 2 endpoints, configure VAPI per client | ₹3,500 – ₹5,000 | ~₹250/month per society |
| **B — Single number + caller lookup** | New identify-caller endpoint with full DB chain, fallback logic | ₹4,500 – ₹6,500 | ~₹250/month flat |
| **C — Server URL webhook** | Webhook handler, dynamic context injection, deployment setup | ₹7,000 – ₹10,000 | ~₹250/month flat + hosting |
| **D — IVR press-1** | VAPI flow config only, no real backend work | ₹1,500 – ₹2,500 | ~₹250/month flat |

Detailed breakdown for each is in the option sections above. **Recommend Option A** — lowest risk, easiest to explain to manager.

---

### Full New Scope — What to Quote

Assuming auth + payments (Stripe only) + VAPI Option A:

| Feature | Charge |
|---------|--------|
| Supabase Auth + RLS | ₹5,500 |
| Stripe payment gateway | ₹5,500 |
| VAPI Option A multi-tenancy | ₹4,000 |
| **Total** | **₹15,000** |

Quote your manager **₹15,000** for all three. Your floor if they negotiate is **₹12,000** — do not go below that. This is on top of the ₹22,000 already paid.

---

### What to say

Keep it short:

> "For auth, the payment gateway, and upgrading the voice agent to handle multiple societies, I'm quoting ₹15,000. These are three separate features each touching the full stack."

Do not explain Claude Code unless directly asked. If asked, say: "I use AI tools to code faster — same as every developer does now. The architecture, debugging, and integration work is still mine."

---

*Document last updated: March 2026*
*Author: Internal dev team*
