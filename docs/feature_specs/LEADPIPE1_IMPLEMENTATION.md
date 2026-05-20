# Leadpipe-1 Implementation Plan

> This document describes the changes needed in the **Leadpipe-1** (Next.js) project to complete the SaaS auth + payments flow. The CRM backend and frontend are already wired up — Leadpipe-1 is the last piece.

## What Leadpipe-1 Does

| Role | Description |
|------|-------------|
| Marketing site | Landing page, feature showcase |
| Auth portal | Login / Sign Up via Supabase Auth |
| Payment checkout | Stripe subscription with 14-day trial + $1 card verification |
| Redirect hub | Sends authenticated users to the CRM app |

## Prerequisites

```bash
cd C:\Users\BIT\Coding\Leadpipe-1
pnpm install @supabase/supabase-js
```

## Environment Variables

Create `.env.local`:
```env
# Supabase (same project as CRM)
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...

# CRM backend (for creating checkout sessions)
NEXT_PUBLIC_BACKEND_URL=https://your-backend.onrender.com

# CRM frontend (redirect target after login)
NEXT_PUBLIC_FRONTEND_URL=https://your-app.netlify.app

# Stripe (server-side only — NO NEXT_PUBLIC_ prefix)
STRIPE_SECRET_KEY=sk_live_xxx
```

---

## Files to Create / Modify

### 1. `src/lib/supabase.ts` [NEW]

```typescript
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
)
```

### 2. `src/app/auth/page.tsx` [NEW]

**Auth page with Login and Sign Up tabs.**

Implementation details:
- Two tabs: "Log In" and "Sign Up"
- Fields: Email, Password (+ Name and Phone on Sign Up)
- On **Sign Up**:
  1. Call `supabase.auth.signUp({ email, password })`
  2. On success, create a `manager_profiles` row:
     ```typescript
     const { data: { user } } = await supabase.auth.signUp({ email, password })
     if (user) {
       await supabase.from('manager_profiles').insert({
         user_id: user.id,
         name: nameField,
         phone: phoneField,
       })
     }
     ```
  3. Redirect to `/pricing` (new user needs a subscription)
- On **Log In**:
  1. Call `supabase.auth.signInWithPassword({ email, password })`
  2. On success, get the session tokens:
     ```typescript
     const { data: { session } } = await supabase.auth.getSession()
     ```
  3. Redirect to the CRM frontend with the session embedded in the URL hash so `detectSessionInUrl` picks it up:
     ```typescript
     const frontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL
     window.location.href = `${frontendUrl}#access_token=${session.access_token}&refresh_token=${session.refresh_token}&token_type=bearer&type=recovery`
     ```
     The CRM's Supabase client automatically detects and extracts the session from the URL hash.
- On **Error**: Show inline error message (wrong password, email taken, etc.)

### 3. `src/app/pricing/page.tsx` [NEW]

**Pricing page with subscription tiers.**

Implementation details:
- Display your plan(s) with pricing info
- "Start 14-Day Free Trial" CTA button
- On click:
  1. Get the current user session:
     ```typescript
     const { data: { session } } = await supabase.auth.getSession()
     if (!session) {
       router.push('/auth')
       return
     }
     ```
  2. Call the CRM backend to create a Stripe Checkout Session:
     ```typescript
     const response = await fetch(
       `${process.env.NEXT_PUBLIC_BACKEND_URL}/payments/create-checkout-session`,
       {
         method: 'POST',
         headers: {
           'Content-Type': 'application/json',
           'Authorization': `Bearer ${session.access_token}`,
         },
       }
     )
     const { checkout_url } = await response.json()
     window.location.href = checkout_url
     ```
  3. Stripe handles card entry + $1 verification charge
- If user lands here with `?canceled=true` query param, show "Checkout canceled" message
- If user is already subscribed (check via backend or local state), show "You're already subscribed" and link to CRM

### 4. `src/app/pricing/success/page.tsx` [NEW]

**Post-checkout success page.**

Implementation details:
- Show "You're all set! Your 14-day free trial has started."
- Auto-redirect to CRM frontend after 3 seconds:
  ```typescript
  useEffect(() => {
    const timer = setTimeout(() => {
      window.location.href = process.env.NEXT_PUBLIC_FRONTEND_URL
    }, 3000)
    return () => clearTimeout(timer)
  }, [])
  ```
- Fallback "Go to Dashboard" button for manual redirect

### 5. Existing landing page modifications [MODIFY]

Update the existing landing page to include:
- **"Login"** button in the navbar → links to `/auth`
- **"Get Started" / "Try Free"** CTA buttons → link to `/auth` (sign up tab)
- **"Pricing"** nav link → links to `/pricing`

---

## Auth Flow Diagram

```
User visits leadpipe-1.com
    │
    ├─ Clicks "Get Started" ──→ /auth (Sign Up tab)
    │       │
    │       ├─ Creates account ──→ /pricing
    │       │       │
    │       │       ├─ Clicks "Start Free Trial" ──→ Stripe Checkout
    │       │       │       │
    │       │       │       ├─ Card verified ($1) ──→ /pricing/success ──→ CRM Dashboard
    │       │       │       └─ Canceled ──→ /pricing?canceled=true
    │       │       │
    │       │       └─ Skips ──→ (Can't access CRM — 403 from backend)
    │       │
    │       └─ Sign up error ──→ Show inline error
    │
    └─ Clicks "Login" ──→ /auth (Login tab)
            │
            ├─ Correct credentials ──→ CRM Dashboard (via URL hash handoff)
            └─ Wrong credentials ──→ Show inline error
```

## Session Handoff: How It Works

1. User logs in on Leadpipe-1 (`localhost:3000`)
2. Leadpipe-1 gets the Supabase `access_token` and `refresh_token`
3. Redirects to CRM with tokens in the URL hash:
   ```
   https://your-app.netlify.app#access_token=eyJ...&refresh_token=xxx&token_type=bearer&type=recovery
   ```
4. The CRM's Supabase client (`@supabase/supabase-js`) automatically detects the hash via `detectSessionInUrl` (enabled by default)
5. Supabase stores the session in `localStorage` on the CRM's origin
6. The hash is cleared from the URL
7. Subsequent page loads use the stored session — no re-auth needed

## Stripe Webhook Configuration

After deploying, register the webhook URL in your Stripe Dashboard:
1. Go to **Stripe Dashboard > Developers > Webhooks**
2. Add endpoint: `https://your-backend.onrender.com/payments/webhook`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the **Signing Secret** (`whsec_...`) to your backend's `STRIPE_WEBHOOK_SECRET` env var

## Testing Checklist

- [ ] Sign up on `/auth` → profile created in `manager_profiles` table
- [ ] Login on `/auth` → redirected to CRM with active session
- [ ] Click "Start Free Trial" on `/pricing` → Stripe Checkout opens
- [ ] Enter test card `4242 4242 4242 4242` → $1 charge succeeds → redirected to `/pricing/success`
- [ ] Webhook fires → `subscriptions` table shows `status=trialing`
- [ ] Auto-redirect to CRM → dashboard loads, data visible
- [ ] Login with wrong password → inline error shown
- [ ] Access CRM without subscription → redirected to `/pricing`
- [ ] Logout from CRM → redirected to Leadpipe-1 landing page

## Stripe Test Cards

| Card | Result |
|------|--------|
| `4242 4242 4242 4242` | Success |
| `4000 0000 0000 3220` | 3D Secure required |
| `4000 0000 0000 0002` | Declined |

Use any future expiry date and any 3-digit CVC.
