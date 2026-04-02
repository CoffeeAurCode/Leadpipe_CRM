---
name: stripe-auth-payments
description: >
  Add Stripe payments, authentication, and multi-user support to any existing product.
  Converts a single-user app into a multi-user SaaS with auth, subscription billing,
  and access control. Use this skill whenever the user mentions: Stripe, payments,
  subscriptions, billing, checkout, pricing page, paywall, multi-user, add auth,
  add authentication, add login, monetize, SaaS conversion, recurring billing,
  payment integration, Stripe Checkout, Stripe webhooks, customer portal,
  subscription management, or wants to convert a single-user tool into a paid product.
  Also trigger when the user wants to gate features behind a subscription, add a
  pricing/plans page, or connect Stripe to their existing app. Even if the user
  only mentions "add payments" or "make it multi-user" without saying Stripe, use
  this skill — Stripe is the default payment provider.
---

# Stripe Auth Payments Skill

This skill adds three capabilities to an existing product that currently has no auth and is built for a single user:

1. **Authentication** — Email/password or OAuth login so multiple users can access the product
2. **Stripe Payments** — Subscription billing via Stripe Checkout with webhook handling
3. **Access Control** — Gate features/pages based on subscription status

## Before You Start

Read the reference files in this skill's `references/` directory based on what stack you detect:

- **Always read**: `references/stripe-integration.md` — Core Stripe patterns (Checkout, webhooks, portal)
- **If Next.js detected**: `references/nextjs-implementation.md` — Next.js-specific routes, middleware, patterns
- **If other framework**: Adapt the Next.js patterns to the detected framework

## Step 0: Detect the Existing Stack

Before writing any code, examine the user's project to understand:

1. **Framework**: Next.js (App Router or Pages Router), React + Express, Vue, SvelteKit, Django, Rails, etc.
2. **Language**: TypeScript or JavaScript (or Python, Ruby, etc.)
3. **Database**: Is there one? Postgres, MySQL, SQLite, MongoDB, Supabase, Firebase, Prisma, Drizzle?
4. **Existing auth**: Is there truly none, or is there something partial?
5. **Hosting**: Vercel, AWS, Railway, self-hosted?

Adapt ALL instructions below to match the detected stack. The reference files give Next.js examples — translate to the actual framework.

## Step 1: Add Authentication

Choose an auth approach based on what's already in the project:

### Option A: NextAuth.js / Auth.js (Recommended for Next.js)
- Install `next-auth`
- Configure providers (Google, GitHub, Email/password — ask user which)
- Create the auth API route and session provider
- Add a `User` model to the database with fields: `id`, `email`, `name`, `image`, `stripeCustomerId`, `subscriptionStatus`, `subscriptionPlanId`

### Option B: Supabase Auth (If Supabase is already in the project)
- Use Supabase's built-in auth
- Add subscription columns to the user's profile table

### Option C: Custom JWT Auth (For non-Next.js backends)
- Create register/login endpoints
- Hash passwords with bcrypt
- Issue JWTs, store in httpOnly cookies
- Add middleware to protect routes

### Key Auth Schema Fields

Regardless of auth choice, the user record MUST include these fields for Stripe integration:

```
User {
  id              String   @id @default(uuid)
  email           String   @unique
  name            String?
  password        String?  // null if OAuth only
  image           String?
  stripeCustomerId    String?  @unique
  subscriptionId      String?
  subscriptionStatus  String?  @default("inactive")  // "active", "trialing", "past_due", "canceled", "inactive"
  planId              String?  // Stripe Price ID
  currentPeriodEnd    DateTime?
  createdAt       DateTime @default(now())
  updatedAt       DateTime @updatedAt
}
```

## Step 2: Set Up Stripe

### Environment Variables

Create or update `.env.local` (or `.env`):

```env
# Stripe keys — get from https://dashboard.stripe.com/apikeys
STRIPE_SECRET_KEY=sk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# App URL
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

### Install Stripe SDK

```bash
# Server-side
npm install stripe

# Client-side (for redirect to Checkout)
npm install @stripe/stripe-js
```

### Create Stripe Helper (Server-Side Singleton)

```typescript
// lib/stripe.ts
import Stripe from 'stripe';

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: '2024-12-18.acacia',  // pin to a specific version
  typescript: true,
});
```

### Create Stripe Client Helper (Browser Singleton)

```typescript
// lib/stripe-client.ts
import { loadStripe, Stripe } from '@stripe/stripe-js';

let stripePromise: Promise<Stripe | null>;

export const getStripe = () => {
  if (!stripePromise) {
    stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);
  }
  return stripePromise;
};
```

## Step 3: Create Stripe Products and Prices

Tell the user to create products in the Stripe Dashboard (or via API). They need:

1. Go to **Stripe Dashboard → Products → Add Product**
2. Create plans (e.g., "Pro Monthly", "Pro Yearly")
3. Set pricing (e.g., $10/month, $96/year)
4. Copy the **Price IDs** (start with `price_...`)

Store these Price IDs in a config file:

```typescript
// config/pricing.ts
export const PLANS = {
  free: {
    name: 'Free',
    description: 'Basic access',
    price: 0,
    priceId: null,
    features: ['Feature A', 'Feature B'],
  },
  pro: {
    name: 'Pro',
    description: 'Full access',
    price: 10,
    priceId: process.env.STRIPE_PRO_PRICE_ID || 'price_XXXXX',
    features: ['Everything in Free', 'Feature C', 'Feature D'],
  },
} as const;
```

## Step 4: Implement Checkout Flow

Read `references/stripe-integration.md` for the full pattern. The high-level flow is:

1. **User clicks "Subscribe"** on the pricing page
2. **Server creates a Checkout Session** with the Price ID and the user's email
3. **User is redirected to Stripe Checkout** (hosted by Stripe — handles card input, 3DS, etc.)
4. **On success**, Stripe redirects back to your success URL
5. **Webhook fires** with `checkout.session.completed` — this is where you update the database

### Critical Rules

- **NEVER fulfill based on redirect alone** — always use webhooks for fulfillment
- **NEVER store card numbers** — Stripe handles all PCI compliance
- **ALWAYS verify webhook signatures** — prevents spoofed events
- **ALWAYS use idempotency** — webhooks can fire multiple times
- **Create Stripe Customer on first checkout** — link it to your user via `stripeCustomerId`

## Step 5: Handle Webhooks

Webhooks are the backbone of the integration. Handle these events:

| Event | Action |
|-------|--------|
| `checkout.session.completed` | Create/update subscription in DB, set status to "active" |
| `invoice.payment_succeeded` | Confirm ongoing subscription, update `currentPeriodEnd` |
| `invoice.payment_failed` | Set status to "past_due", notify user |
| `customer.subscription.updated` | Sync plan changes (upgrade/downgrade) |
| `customer.subscription.deleted` | Set status to "canceled", revoke access |

Read `references/stripe-integration.md` for the full webhook handler implementation.

## Step 6: Add Access Control Middleware

Protect routes/pages based on subscription status:

```typescript
// middleware.ts (Next.js example)
// Check if user is authenticated
// Check if user has active subscription for premium routes
// Redirect to pricing page if not subscribed
// Redirect to login page if not authenticated
```

Create a helper function:

```typescript
// lib/access.ts
export function hasActiveSubscription(user: User): boolean {
  return (
    user.subscriptionStatus === 'active' ||
    user.subscriptionStatus === 'trialing'
  ) && user.currentPeriodEnd && new Date(user.currentPeriodEnd) > new Date();
}
```

## Step 7: Add Customer Portal

Let users manage their own subscriptions (update card, cancel, change plan):

```typescript
// API route to create portal session
const portalSession = await stripe.billingPortal.sessions.create({
  customer: user.stripeCustomerId,
  return_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing`,
});
// Redirect user to portalSession.url
```

Configure the Customer Portal in Stripe Dashboard → Settings → Billing → Customer Portal.

## Step 8: Build the UI Pages

Create these pages/components:

1. **Login / Register page** — Auth forms
2. **Pricing page** — Show plans with checkout buttons
3. **Dashboard** — Main app (protected, requires auth)
4. **Billing page** — Show current plan, link to Customer Portal
5. **Success page** — Post-checkout confirmation

## Step 9: Testing

Guide the user through testing:

1. Use Stripe **test mode** keys (start with `sk_test_` / `pk_test_`)
2. Test card numbers:
   - `4242 4242 4242 4242` — Succeeds
   - `4000 0025 0000 3155` — Requires 3DS authentication
   - `4000 0000 0000 9995` — Declined
3. Use Stripe CLI for local webhook testing:
   ```bash
   stripe listen --forward-to localhost:3000/api/webhooks/stripe
   ```
4. Test the full flow: Register → Login → Subscribe → Access premium → Cancel → Lose access

## File Structure (Next.js App Router Example)

```
app/
├── (auth)/
│   ├── login/page.tsx
│   └── register/page.tsx
├── (protected)/
│   ├── dashboard/
│   │   ├── page.tsx
│   │   └── billing/page.tsx
│   └── layout.tsx          # Auth check wrapper
├── pricing/page.tsx
├── success/page.tsx
├── api/
│   ├── auth/[...nextauth]/route.ts
│   ├── stripe/
│   │   ├── checkout/route.ts
│   │   └── portal/route.ts
│   └── webhooks/
│       └── stripe/route.ts
lib/
├── stripe.ts               # Server-side Stripe instance
├── stripe-client.ts        # Client-side Stripe loader
├── auth.ts                 # Auth config
├── db.ts                   # Database client
└── access.ts               # Subscription check helpers
config/
└── pricing.ts              # Plan definitions
```

## Common Pitfalls to Avoid

1. **Don't use `bodyParser` on webhook routes** — Stripe needs the raw body for signature verification
2. **Don't redirect-only for fulfillment** — Users close tabs; always use webhooks
3. **Don't hardcode Price IDs** — Use env vars or config files
4. **Don't forget to handle `past_due`** — Give users a grace period, show a banner
5. **Don't skip idempotency checks** — Webhooks can fire more than once
6. **Don't expose `STRIPE_SECRET_KEY`** client-side — it must only be on the server
7. **Don't create duplicate Stripe customers** — Always check if user already has a `stripeCustomerId`

## Adapting to Non-Next.js Stacks

If the project uses a different framework, translate the patterns:

- **Express/Node**: Use `express.raw()` middleware for webhook route, standard route handlers for checkout/portal
- **Django/Python**: Use `stripe` Python package, `@csrf_exempt` on webhook view, Django auth or django-allauth
- **Rails/Ruby**: Use `stripe` gem, skip CSRF on webhook controller, Devise for auth
- **SvelteKit**: Use server endpoints (`+server.ts`), hooks for auth middleware
- **Go**: Use `stripe-go` package, `net/http` handlers

The Stripe API calls are identical regardless of framework — only the HTTP routing layer changes.
