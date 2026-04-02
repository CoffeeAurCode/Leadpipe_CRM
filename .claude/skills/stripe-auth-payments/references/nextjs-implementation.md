# Next.js Implementation Reference

Next.js-specific patterns for integrating Stripe + Auth into a Next.js application.

## Table of Contents
1. [Auth Setup with NextAuth.js](#auth-setup)
2. [Database Schema with Prisma](#database-schema)
3. [API Routes](#api-routes)
4. [Middleware for Access Control](#middleware)
5. [UI Components](#ui-components)
6. [Full File-by-File Implementation](#full-implementation)

---

## Auth Setup

### Install Dependencies

```bash
npm install next-auth @auth/prisma-adapter prisma @prisma/client
npm install stripe @stripe/stripe-js
npm install bcryptjs     # if using email/password
npm install -D @types/bcryptjs
```

### NextAuth Configuration (App Router)

```typescript
// lib/auth.ts
import { NextAuthOptions } from 'next-auth';
import { PrismaAdapter } from '@auth/prisma-adapter';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';
import bcrypt from 'bcryptjs';
import { db } from './db';

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(db),
  session: { strategy: 'jwt' },
  pages: {
    signIn: '/login',
    newUser: '/pricing',  // redirect new users to pricing
  },
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    CredentialsProvider({
      name: 'credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await db.user.findUnique({
          where: { email: credentials.email },
        });

        if (!user || !user.password) return null;

        const isValid = await bcrypt.compare(credentials.password, user.password);
        if (!isValid) return null;

        return {
          id: user.id,
          email: user.email,
          name: user.name,
          image: user.image,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.id = user.id;
      }
      // Fetch subscription status on every token refresh
      if (token.id) {
        const dbUser = await db.user.findUnique({
          where: { id: token.id as string },
          select: {
            subscriptionStatus: true,
            planId: true,
            currentPeriodEnd: true,
          },
        });
        if (dbUser) {
          token.subscriptionStatus = dbUser.subscriptionStatus;
          token.planId = dbUser.planId;
          token.currentPeriodEnd = dbUser.currentPeriodEnd?.toISOString();
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.subscriptionStatus = token.subscriptionStatus as string;
        session.user.planId = token.planId as string;
        session.user.currentPeriodEnd = token.currentPeriodEnd as string;
      }
      return session;
    },
  },
};
```

### Auth API Route

```typescript
// app/api/auth/[...nextauth]/route.ts
import NextAuth from 'next-auth';
import { authOptions } from '@/lib/auth';

const handler = NextAuth(authOptions);
export { handler as GET, handler as POST };
```

### Session Provider

```typescript
// components/Providers.tsx
'use client';
import { SessionProvider } from 'next-auth/react';

export function Providers({ children }: { children: React.ReactNode }) {
  return <SessionProvider>{children}</SessionProvider>;
}

// app/layout.tsx — wrap your app
import { Providers } from '@/components/Providers';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Extend NextAuth Types

```typescript
// types/next-auth.d.ts
import 'next-auth';

declare module 'next-auth' {
  interface User {
    id: string;
    subscriptionStatus?: string;
    planId?: string;
    currentPeriodEnd?: string;
  }

  interface Session {
    user: User & {
      id: string;
      subscriptionStatus?: string;
      planId?: string;
      currentPeriodEnd?: string;
    };
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    id?: string;
    subscriptionStatus?: string;
    planId?: string;
    currentPeriodEnd?: string;
  }
}
```

---

## Database Schema

### Prisma Schema

```prisma
// prisma/schema.prisma
datasource db {
  provider = "postgresql"  // or sqlite, mysql
  url      = env("DATABASE_URL")
}

generator client {
  provider = "prisma-client-js"
}

model User {
  id                  String    @id @default(cuid())
  email               String    @unique
  name                String?
  password            String?
  image               String?
  emailVerified       DateTime?
  stripeCustomerId    String?   @unique
  subscriptionId      String?   @unique
  subscriptionStatus  String?   @default("inactive")
  planId              String?
  currentPeriodEnd    DateTime?
  createdAt           DateTime  @default(now())
  updatedAt           DateTime  @updatedAt
  accounts            Account[]
  sessions            Session[]
}

// Required by NextAuth Prisma Adapter
model Account {
  id                String  @id @default(cuid())
  userId            String
  type              String
  provider          String
  providerAccountId String
  refresh_token     String?
  access_token      String?
  expires_at        Int?
  token_type        String?
  scope             String?
  id_token          String?
  session_state     String?
  user              User    @relation(fields: [userId], references: [id], onDelete: Cascade)
  @@unique([provider, providerAccountId])
}

model Session {
  id           String   @id @default(cuid())
  sessionToken String   @unique
  userId       String
  expires      DateTime
  user         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
}

model VerificationToken {
  identifier String
  token      String   @unique
  expires    DateTime
  @@unique([identifier, token])
}
```

### Database Client

```typescript
// lib/db.ts
import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient };

export const db = globalForPrisma.prisma || new PrismaClient();

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db;
```

---

## API Routes

### Checkout Route

```typescript
// app/api/stripe/checkout/route.ts
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const session = await getServerSession(authOptions);

    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const { priceId } = await req.json();

    if (!priceId) {
      return NextResponse.json({ error: 'Price ID required' }, { status: 400 });
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
    });

    if (!user) {
      return NextResponse.json({ error: 'User not found' }, { status: 404 });
    }

    // Build checkout session config
    const checkoutConfig: any = {
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing`,
      allow_promotion_codes: true,
      subscription_data: {
        metadata: { userId: user.id },
      },
      metadata: { userId: user.id },
    };

    // Use existing customer or pre-fill email
    if (user.stripeCustomerId) {
      checkoutConfig.customer = user.stripeCustomerId;
    } else {
      checkoutConfig.customer_email = user.email;
    }

    const checkoutSession = await stripe.checkout.sessions.create(checkoutConfig);

    return NextResponse.json({ url: checkoutSession.url });
  } catch (error: any) {
    console.error('Checkout error:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}
```

### Portal Route

```typescript
// app/api/stripe/portal/route.ts
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { stripe } from '@/lib/stripe';
import { db } from '@/lib/db';
import { NextResponse } from 'next/server';

export async function POST() {
  try {
    const session = await getServerSession(authOptions);
    if (!session?.user?.id) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const user = await db.user.findUnique({
      where: { id: session.user.id },
    });

    if (!user?.stripeCustomerId) {
      return NextResponse.json(
        { error: 'No billing account found' },
        { status: 400 }
      );
    }

    const portalSession = await stripe.billingPortal.sessions.create({
      customer: user.stripeCustomerId,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard/billing`,
    });

    return NextResponse.json({ url: portalSession.url });
  } catch (error: any) {
    console.error('Portal error:', error);
    return NextResponse.json(
      { error: 'Failed to create portal session' },
      { status: 500 }
    );
  }
}
```

### Register Route (if using Credentials auth)

```typescript
// app/api/auth/register/route.ts
import { db } from '@/lib/db';
import bcrypt from 'bcryptjs';
import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  try {
    const { email, password, name } = await req.json();

    if (!email || !password) {
      return NextResponse.json(
        { error: 'Email and password required' },
        { status: 400 }
      );
    }

    const existing = await db.user.findUnique({ where: { email } });
    if (existing) {
      return NextResponse.json(
        { error: 'Email already registered' },
        { status: 409 }
      );
    }

    const hashedPassword = await bcrypt.hash(password, 12);

    const user = await db.user.create({
      data: { email, password: hashedPassword, name },
    });

    return NextResponse.json(
      { message: 'Account created', userId: user.id },
      { status: 201 }
    );
  } catch (error) {
    console.error('Registration error:', error);
    return NextResponse.json(
      { error: 'Registration failed' },
      { status: 500 }
    );
  }
}
```

---

## Middleware

### Next.js Middleware for Route Protection

```typescript
// middleware.ts
import { getToken } from 'next-auth/jwt';
import { NextRequest, NextResponse } from 'next/server';

// Routes that require authentication
const protectedRoutes = ['/dashboard', '/settings', '/billing'];

// Routes that require an active subscription
const premiumRoutes = ['/dashboard'];

// Routes that authed users should NOT see (login, register)
const authRoutes = ['/login', '/register'];

export async function middleware(req: NextRequest) {
  const token = await getToken({ req });
  const { pathname } = req.nextUrl;

  // Redirect logged-in users away from auth pages
  if (authRoutes.some(route => pathname.startsWith(route))) {
    if (token) {
      return NextResponse.redirect(new URL('/dashboard', req.url));
    }
    return NextResponse.next();
  }

  // Check authentication for protected routes
  if (protectedRoutes.some(route => pathname.startsWith(route))) {
    if (!token) {
      const loginUrl = new URL('/login', req.url);
      loginUrl.searchParams.set('callbackUrl', pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  // Check subscription for premium routes
  if (premiumRoutes.some(route => pathname.startsWith(route))) {
    if (token) {
      const isActive = token.subscriptionStatus === 'active' ||
                       token.subscriptionStatus === 'trialing';
      if (!isActive) {
        return NextResponse.redirect(new URL('/pricing', req.url));
      }
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/settings/:path*',
    '/billing/:path*',
    '/login',
    '/register',
  ],
};
```

---

## UI Components

### Pricing Page

```tsx
// app/pricing/page.tsx
'use client';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { PLANS } from '@/config/pricing';
import { useState } from 'react';

export default function PricingPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [loading, setLoading] = useState<string | null>(null);

  async function handleCheckout(priceId: string) {
    if (!session) {
      router.push('/login?callbackUrl=/pricing');
      return;
    }

    setLoading(priceId);
    try {
      const res = await fetch('/api/stripe/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ priceId }),
      });

      const data = await res.json();

      if (data.url) {
        window.location.href = data.url;
      } else {
        console.error('No checkout URL returned');
      }
    } catch (error) {
      console.error('Checkout error:', error);
    } finally {
      setLoading(null);
    }
  }

  return (
    <div>
      <h1>Choose Your Plan</h1>
      <div style={{ display: 'flex', gap: '2rem' }}>
        {Object.entries(PLANS).map(([key, plan]) => (
          <div key={key} style={{ border: '1px solid #ccc', padding: '2rem', borderRadius: '8px' }}>
            <h2>{plan.name}</h2>
            <p>{plan.description}</p>
            <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>
              ${plan.price}/mo
            </p>
            <ul>
              {plan.features.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            {plan.priceId ? (
              <button
                onClick={() => handleCheckout(plan.priceId!)}
                disabled={loading === plan.priceId}
              >
                {loading === plan.priceId ? 'Loading...' : 'Subscribe'}
              </button>
            ) : (
              <button disabled>Current Plan</button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Billing Management Page

```tsx
// app/dashboard/billing/page.tsx
'use client';
import { useSession } from 'next-auth/react';
import { useState } from 'react';

export default function BillingPage() {
  const { data: session } = useSession();
  const [loading, setLoading] = useState(false);

  async function handleManageBilling() {
    setLoading(true);
    try {
      const res = await fetch('/api/stripe/portal', { method: 'POST' });
      const data = await res.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Portal error:', error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Billing</h1>
      <p>Status: {session?.user?.subscriptionStatus || 'No subscription'}</p>
      <p>Plan: {session?.user?.planId || 'None'}</p>
      {session?.user?.currentPeriodEnd && (
        <p>
          Renews: {new Date(session.user.currentPeriodEnd).toLocaleDateString()}
        </p>
      )}
      <button onClick={handleManageBilling} disabled={loading}>
        {loading ? 'Loading...' : 'Manage Subscription'}
      </button>
    </div>
  );
}
```

---

## Full Implementation

### Complete .env.local Template

```env
# Database
DATABASE_URL="postgresql://user:password@localhost:5432/myapp"

# NextAuth
NEXTAUTH_URL="http://localhost:3000"
NEXTAUTH_SECRET="generate-with-openssl-rand-base64-32"

# OAuth Providers (optional — remove if not using)
GOOGLE_CLIENT_ID=""
GOOGLE_CLIENT_SECRET=""

# Stripe
STRIPE_SECRET_KEY="sk_test_..."
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY="pk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
STRIPE_PRO_PRICE_ID="price_..."

# App
NEXT_PUBLIC_APP_URL="http://localhost:3000"
```

### Package.json Scripts to Add

```json
{
  "scripts": {
    "db:push": "prisma db push",
    "db:generate": "prisma generate",
    "db:studio": "prisma studio",
    "stripe:listen": "stripe listen --forward-to localhost:3000/api/webhooks/stripe"
  }
}
```
