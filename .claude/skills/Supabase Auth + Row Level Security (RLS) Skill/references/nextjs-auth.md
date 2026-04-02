# Next.js App Router — Supabase Auth Implementation

This reference covers adding Supabase Auth to a Next.js App Router application.

## Table of Contents

1. [Package installation](#package-installation)
2. [Environment variables](#environment-variables)
3. [Supabase client utilities](#supabase-client-utilities)
4. [Middleware for session refresh](#middleware-for-session-refresh)
5. [Auth callback route](#auth-callback-route)
6. [Login and signup pages](#login-and-signup-pages)
7. [Route protection](#route-protection)
8. [Sign out](#sign-out)
9. [Accessing the user in components](#accessing-the-user-in-components)

---

## Package installation

```bash
npm install @supabase/supabase-js @supabase/ssr
```

---

## Environment variables

Add to `.env.local`:

```
NEXT_PUBLIC_SUPABASE_URL=https://<project-ref>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
```

If admin operations are needed server-side, also add:

```
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

---

## Supabase client utilities

Create these utility files. The key concept: Next.js App Router needs **different client creation strategies** for server components, client components, and middleware, because cookies are accessed differently in each context.

### `lib/supabase/server.ts` — For Server Components, Server Actions, Route Handlers

```typescript
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export async function createClient() {
  const cookieStore = await cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options)
            )
          } catch {
            // The `setAll` method is called from a Server Component.
            // This can be ignored if you have middleware refreshing sessions.
          }
        },
      },
    }
  )
}
```

### `lib/supabase/client.ts` — For Client Components

```typescript
import { createBrowserClient } from '@supabase/ssr'

export function createClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
  )
}
```

### `lib/supabase/middleware.ts` — Helper for middleware

```typescript
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function updateSession(request: NextRequest) {
  let supabaseResponse = NextResponse.next({
    request,
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            request.cookies.set(name, value)
          )
          supabaseResponse = NextResponse.next({
            request,
          })
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          )
        },
      },
    }
  )

  // IMPORTANT: Do not run code between createServerClient and
  // supabase.auth.getUser(). A simple mistake could make it very
  // hard to debug issues with users being randomly logged out.

  const {
    data: { user },
  } = await supabase.auth.getUser()

  if (
    !user &&
    !request.nextUrl.pathname.startsWith('/login') &&
    !request.nextUrl.pathname.startsWith('/signup') &&
    !request.nextUrl.pathname.startsWith('/auth')
  ) {
    // Redirect unauthenticated users to login
    const url = request.nextUrl.clone()
    url.pathname = '/login'
    return NextResponse.redirect(url)
  }

  return supabaseResponse
}
```

---

## Middleware for session refresh

Create `middleware.ts` at the project root:

```typescript
import { type NextRequest } from 'next/server'
import { updateSession } from '@/lib/supabase/middleware'

export async function middleware(request: NextRequest) {
  return await updateSession(request)
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * Feel free to modify this pattern to include more paths.
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
```

**Why middleware is needed**: Supabase Auth uses cookie-based sessions in SSR. The middleware refreshes the session token before it expires and forwards the updated cookies to the response.

---

## Auth callback route

Create `app/auth/callback/route.ts`:

```typescript
import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function GET(request: Request) {
  const { searchParams, origin } = new URL(request.url)
  const code = searchParams.get('code')
  const next = searchParams.get('next') ?? '/'

  if (code) {
    const supabase = await createClient()
    const { error } = await supabase.auth.exchangeCodeForSession(code)
    if (!error) {
      return NextResponse.redirect(`${origin}${next}`)
    }
  }

  // Return the user to an error page with instructions
  return NextResponse.redirect(`${origin}/auth/auth-code-error`)
}
```

This route handles:
- Email confirmation links (magic links)
- OAuth redirect callbacks
- Password reset confirmation

---

## Login and signup pages

### `app/login/page.tsx`

```tsx
import { login, signup } from './actions'

export default function LoginPage() {
  return (
    <form>
      <label htmlFor="email">Email:</label>
      <input id="email" name="email" type="email" required />
      <label htmlFor="password">Password:</label>
      <input id="password" name="password" type="password" required />
      <button formAction={login}>Log in</button>
      <button formAction={signup}>Sign up</button>
    </form>
  )
}
```

### `app/login/actions.ts`

```typescript
'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

export async function login(formData: FormData) {
  const supabase = await createClient()

  const data = {
    email: formData.get('email') as string,
    password: formData.get('password') as string,
  }

  const { error } = await supabase.auth.signInWithPassword(data)

  if (error) {
    redirect('/error')
  }

  revalidatePath('/', 'layout')
  redirect('/')
}

export async function signup(formData: FormData) {
  const supabase = await createClient()

  const data = {
    email: formData.get('email') as string,
    password: formData.get('password') as string,
  }

  const { error } = await supabase.auth.signUp(data)

  if (error) {
    redirect('/error')
  }

  revalidatePath('/', 'layout')
  redirect('/')
}
```

### Adding OAuth (e.g., Google, GitHub)

```typescript
'use server'

import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { headers } from 'next/headers'

export async function signInWithGoogle() {
  const supabase = await createClient()
  const origin = (await headers()).get('origin')

  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${origin}/auth/callback`,
    },
  })

  if (data.url) {
    redirect(data.url)
  }
}
```

---

## Route protection

The middleware already handles redirecting unauthenticated users. For additional protection in server components:

```typescript
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

export default async function ProtectedPage() {
  const supabase = await createClient()

  const { data: { user }, error } = await supabase.auth.getUser()

  if (!user) {
    redirect('/login')
  }

  return <div>Hello {user.email}</div>
}
```

**Important**: Always use `supabase.auth.getUser()` for server-side auth checks. Do NOT use `supabase.auth.getSession()` for authorization — it reads from cookies/storage without validating the JWT with the Supabase Auth server and can be spoofed.

---

## Sign out

### Server Action approach

```typescript
// app/actions/auth.ts
'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'

export async function signOut() {
  const supabase = await createClient()
  await supabase.auth.signOut()
  revalidatePath('/', 'layout')
  redirect('/login')
}
```

### In a component

```tsx
import { signOut } from '@/app/actions/auth'

export function SignOutButton() {
  return (
    <form action={signOut}>
      <button type="submit">Sign out</button>
    </form>
  )
}
```

---

## Accessing the user in components

### Server Component

```typescript
import { createClient } from '@/lib/supabase/server'

export default async function Dashboard() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  // Queries automatically scoped by RLS
  const { data: todos } = await supabase.from('todos').select('*')

  return (
    <div>
      <h1>Welcome, {user?.email}</h1>
      {/* todos only contains this user's rows thanks to RLS */}
    </div>
  )
}
```

### Client Component

```tsx
'use client'

import { useEffect, useState } from 'react'
import { createClient } from '@/lib/supabase/client'
import type { User } from '@supabase/supabase-js'

export function UserGreeting() {
  const [user, setUser] = useState<User | null>(null)
  const supabase = createClient()

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      setUser(user)
    })
  }, [])

  if (!user) return null
  return <span>Hello, {user.email}</span>
}
```

---

## Adaptation notes

- **Next.js Pages Router**: Uses `getServerSideProps` instead of server components. The cookie handling is similar but uses `req`/`res` from the context. Consider migrating to App Router if feasible.
- **Customize the protected routes list**: Edit the `if` condition in `middleware.ts` to add public routes that don't require auth (e.g., landing page, pricing page, docs).
- **Email confirmation**: By default, Supabase requires email confirmation. For development, you can disable this in the Supabase Dashboard under Auth → Settings → "Enable email confirmations".
