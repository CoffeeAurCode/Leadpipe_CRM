# Stripe Integration Reference

Detailed implementation patterns for Stripe Checkout, webhooks, and Customer Portal.

## Table of Contents
1. [Checkout Session Creation](#checkout-session-creation)
2. [Webhook Handler](#webhook-handler)
3. [Customer Portal](#customer-portal)
4. [Stripe Customer Management](#stripe-customer-management)
5. [Subscription Status Sync](#subscription-status-sync)
6. [Error Handling](#error-handling)
7. [Idempotency](#idempotency)

---

## Checkout Session Creation

The checkout API endpoint creates a Stripe Checkout Session and returns the URL to redirect the user. This is a server-side operation — never expose your secret key to the client.

### One-Time Payment Session

```typescript
const session = await stripe.checkout.sessions.create({
  mode: 'payment',
  payment_method_types: ['card'],
  line_items: [
    {
      price_data: {
        currency: 'usd',
        product_data: {
          name: 'Product Name',
          description: 'Product description',
        },
        unit_amount: 2000, // $20.00 in cents
      },
      quantity: 1,
    },
  ],
  customer_email: user.email, // pre-fill email
  success_url: `${appUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
  cancel_url: `${appUrl}/pricing`,
  metadata: {
    userId: user.id, // link session to your user
  },
});
```

### Subscription Session

```typescript
const session = await stripe.checkout.sessions.create({
  mode: 'subscription',
  payment_method_types: ['card'],
  line_items: [
    {
      price: priceId, // Stripe Price ID like price_1234
      quantity: 1,
    },
  ],
  customer: user.stripeCustomerId || undefined,
  customer_email: user.stripeCustomerId ? undefined : user.email,
  success_url: `${appUrl}/success?session_id={CHECKOUT_SESSION_ID}`,
  cancel_url: `${appUrl}/pricing`,
  allow_promotion_codes: true,
  subscription_data: {
    metadata: {
      userId: user.id,
    },
  },
  metadata: {
    userId: user.id,
  },
});
```

Key points:
- Use `customer` if user already has a `stripeCustomerId`, otherwise use `customer_email` — never both
- Put `userId` in metadata so webhooks can link back to your user
- `{CHECKOUT_SESSION_ID}` is a Stripe template variable — Stripe replaces it with the actual session ID in the redirect URL
- Set `allow_promotion_codes: true` if you want coupon support

### Returning the Session

After creating the session, redirect the user. Two patterns:

**Pattern A: Server redirect (API route returns URL)**
```typescript
// Server
return Response.json({ url: session.url });

// Client
const res = await fetch('/api/stripe/checkout', {
  method: 'POST',
  body: JSON.stringify({ priceId }),
  headers: { 'Content-Type': 'application/json' },
});
const { url } = await res.json();
window.location.href = url;
```

**Pattern B: Client-side redirect with Stripe.js**
```typescript
// Server
return Response.json({ sessionId: session.id });

// Client
const stripe = await getStripe();
const { error } = await stripe.redirectToCheckout({ sessionId });
```

Pattern A is simpler and recommended.

---

## Webhook Handler

Webhooks are the most critical part. Stripe sends POST requests to your endpoint when events occur. You MUST verify the signature.

### Full Webhook Handler (Next.js App Router)

```typescript
// app/api/webhooks/stripe/route.ts
import { headers } from 'next/headers';
import { stripe } from '@/lib/stripe';
import Stripe from 'stripe';

// Disable body parsing — Stripe needs the raw body
export const dynamic = 'force-dynamic';

export async function POST(req: Request) {
  const body = await req.text();
  const headersList = await headers();
  const signature = headersList.get('stripe-signature');

  if (!signature) {
    return new Response('No signature', { status: 400 });
  }

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      body,
      signature,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err: any) {
    console.error(`Webhook signature verification failed: ${err.message}`);
    return new Response(`Webhook Error: ${err.message}`, { status: 400 });
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        await handleCheckoutCompleted(session);
        break;
      }
      case 'invoice.payment_succeeded': {
        const invoice = event.data.object as Stripe.Invoice;
        await handlePaymentSucceeded(invoice);
        break;
      }
      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice;
        await handlePaymentFailed(invoice);
        break;
      }
      case 'customer.subscription.updated': {
        const subscription = event.data.object as Stripe.Subscription;
        await handleSubscriptionUpdated(subscription);
        break;
      }
      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription;
        await handleSubscriptionDeleted(subscription);
        break;
      }
      default:
        console.log(`Unhandled event type: ${event.type}`);
    }
  } catch (error) {
    console.error('Webhook handler error:', error);
    // Return 200 anyway to prevent Stripe from retrying
    // Log the error for investigation
  }

  return new Response('OK', { status: 200 });
}
```

### Webhook Handler Functions

```typescript
async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const userId = session.metadata?.userId;
  if (!userId) {
    console.error('No userId in session metadata');
    return;
  }

  const customerId = session.customer as string;
  const subscriptionId = session.subscription as string;

  // Retrieve the full subscription to get plan details
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);

  await db.user.update({
    where: { id: userId },
    data: {
      stripeCustomerId: customerId,
      subscriptionId: subscriptionId,
      subscriptionStatus: subscription.status,
      planId: subscription.items.data[0]?.price.id,
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
    },
  });
}

async function handlePaymentSucceeded(invoice: Stripe.Invoice) {
  const subscriptionId = invoice.subscription as string;
  if (!subscriptionId) return;

  const subscription = await stripe.subscriptions.retrieve(subscriptionId);

  await db.user.update({
    where: { subscriptionId },
    data: {
      subscriptionStatus: 'active',
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
    },
  });
}

async function handlePaymentFailed(invoice: Stripe.Invoice) {
  const subscriptionId = invoice.subscription as string;
  if (!subscriptionId) return;

  await db.user.update({
    where: { subscriptionId },
    data: {
      subscriptionStatus: 'past_due',
    },
  });
  // TODO: Send email to user about failed payment
}

async function handleSubscriptionUpdated(subscription: Stripe.Subscription) {
  await db.user.update({
    where: { subscriptionId: subscription.id },
    data: {
      subscriptionStatus: subscription.status,
      planId: subscription.items.data[0]?.price.id,
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
    },
  });
}

async function handleSubscriptionDeleted(subscription: Stripe.Subscription) {
  await db.user.update({
    where: { subscriptionId: subscription.id },
    data: {
      subscriptionStatus: 'canceled',
      subscriptionId: null,
      planId: null,
    },
  });
}
```

### Webhook Handler (Express.js)

```typescript
import express from 'express';

// IMPORTANT: Use express.raw() ONLY for the webhook route
app.post(
  '/api/webhooks/stripe',
  express.raw({ type: 'application/json' }),
  async (req, res) => {
    const signature = req.headers['stripe-signature'];

    let event;
    try {
      event = stripe.webhooks.constructEvent(
        req.body,
        signature,
        process.env.STRIPE_WEBHOOK_SECRET
      );
    } catch (err) {
      return res.status(400).send(`Webhook Error: ${err.message}`);
    }

    // Handle events same as above...

    res.json({ received: true });
  }
);
```

### Webhook Handler (Python / Flask)

```python
import stripe
from flask import Flask, request, jsonify

@app.route('/api/webhooks/stripe', methods=['POST'])
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    # Handle events...

    return jsonify(success=True), 200
```

---

## Customer Portal

The Stripe Customer Portal lets users manage their own subscriptions without you building UI for it.

### Create Portal Session

```typescript
// app/api/stripe/portal/route.ts
export async function POST(req: Request) {
  const session = await getAuthSession(); // your auth helper
  if (!session?.user) {
    return new Response('Unauthorized', { status: 401 });
  }

  const user = await db.user.findUnique({
    where: { id: session.user.id },
  });

  if (!user?.stripeCustomerId) {
    return new Response('No Stripe customer', { status: 400 });
  }

  const portalSession = await stripe.billingPortal.sessions.create({
    customer: user.stripeCustomerId,
    return_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing`,
  });

  return Response.json({ url: portalSession.url });
}
```

### Configure Portal in Stripe Dashboard

Go to **Stripe Dashboard → Settings → Billing → Customer Portal** and enable:
- Customers can update payment methods
- Customers can cancel subscriptions
- Customers can switch plans (if you have multiple)
- Show invoice history

---

## Stripe Customer Management

### Creating a Customer on First Checkout

The cleanest approach: let Stripe Checkout create the customer automatically (via `customer_email`), then save the `customerId` from the `checkout.session.completed` webhook.

### Creating a Customer Proactively

If you want a Stripe customer to exist before they ever check out:

```typescript
async function getOrCreateStripeCustomer(user: User): Promise<string> {
  if (user.stripeCustomerId) {
    return user.stripeCustomerId;
  }

  const customer = await stripe.customers.create({
    email: user.email,
    name: user.name || undefined,
    metadata: {
      userId: user.id,
    },
  });

  await db.user.update({
    where: { id: user.id },
    data: { stripeCustomerId: customer.id },
  });

  return customer.id;
}
```

---

## Subscription Status Sync

### Checking Subscription Status

```typescript
export function hasActiveSubscription(user: {
  subscriptionStatus: string | null;
  currentPeriodEnd: Date | null;
}): boolean {
  if (!user.subscriptionStatus || !user.currentPeriodEnd) return false;

  const isActiveStatus = ['active', 'trialing'].includes(user.subscriptionStatus);
  const isNotExpired = new Date(user.currentPeriodEnd) > new Date();

  return isActiveStatus && isNotExpired;
}

export function isInGracePeriod(user: {
  subscriptionStatus: string | null;
}): boolean {
  return user.subscriptionStatus === 'past_due';
}
```

### Periodic Sync (Optional Safety Net)

In case a webhook is missed, you can periodically verify subscription status:

```typescript
async function syncSubscriptionStatus(user: User) {
  if (!user.subscriptionId) return;

  const subscription = await stripe.subscriptions.retrieve(user.subscriptionId);

  await db.user.update({
    where: { id: user.id },
    data: {
      subscriptionStatus: subscription.status,
      planId: subscription.items.data[0]?.price.id,
      currentPeriodEnd: new Date(subscription.current_period_end * 1000),
    },
  });
}
```

---

## Error Handling

### Stripe API Errors

```typescript
try {
  const session = await stripe.checkout.sessions.create({...});
} catch (error) {
  if (error instanceof Stripe.errors.StripeCardError) {
    // Card was declined
    return Response.json({ error: 'Card declined' }, { status: 400 });
  } else if (error instanceof Stripe.errors.StripeRateLimitError) {
    // Too many requests — retry with backoff
    return Response.json({ error: 'Rate limited, try again' }, { status: 429 });
  } else if (error instanceof Stripe.errors.StripeInvalidRequestError) {
    // Invalid parameters
    console.error('Stripe invalid request:', error.message);
    return Response.json({ error: 'Invalid request' }, { status: 400 });
  } else if (error instanceof Stripe.errors.StripeAuthenticationError) {
    // API key is wrong
    console.error('Stripe auth failed — check API keys');
    return Response.json({ error: 'Configuration error' }, { status: 500 });
  } else {
    console.error('Unexpected Stripe error:', error);
    return Response.json({ error: 'Something went wrong' }, { status: 500 });
  }
}
```

---

## Idempotency

Stripe webhooks can fire multiple times. Protect against duplicate processing:

```typescript
async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const userId = session.metadata?.userId;

  // Check if already processed
  const user = await db.user.findUnique({ where: { id: userId } });
  if (user?.subscriptionId === session.subscription) {
    console.log('Already processed this checkout session');
    return; // Skip duplicate
  }

  // Process normally...
}
```

For write operations via the Stripe API, use idempotency keys:

```typescript
const customer = await stripe.customers.create(
  { email: user.email },
  { idempotencyKey: `create-customer-${user.id}` }
);
```
