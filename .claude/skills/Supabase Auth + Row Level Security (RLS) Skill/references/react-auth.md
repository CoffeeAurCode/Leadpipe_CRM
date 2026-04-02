# React (Vite / CRA) — Supabase Auth Implementation

This reference covers adding Supabase Auth to a client-side React application (Vite, Create React App, or similar SPA frameworks).

## Table of Contents

1. [Package installation](#package-installation)
2. [Environment variables](#environment-variables)
3. [Supabase client](#supabase-client)
4. [Auth context provider](#auth-context-provider)
5. [Login and signup components](#login-and-signup-components)
6. [Route protection](#route-protection)
7. [Sign out](#sign-out)
8. [Accessing the user in components](#accessing-the-user-in-components)

---

## Package installation

```bash
npm install @supabase/supabase-js
```

Optionally, for a pre-built login UI:

```bash
npm install @supabase/auth-ui-react @supabase/auth-ui-shared
```

---

## Environment variables

For Vite, add to `.env`:

```
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

For CRA, use `REACT_APP_` prefix instead of `VITE_`.

---

## Supabase client

Create `src/lib/supabase.ts`:

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

For CRA, replace `import.meta.env.VITE_` with `process.env.REACT_APP_`.

**Important**: In client-side React, you create a single shared client instance. This is different from Next.js SSR where you create a new client per request.

---

## Auth context provider

Create `src/contexts/AuthContext.tsx`:

```tsx
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import type { User, Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  signOut: async () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get the initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      setUser(session?.user ?? null)
      setLoading(false)
    })

    // Listen for auth state changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        setSession(session)
        setUser(session?.user ?? null)
        setLoading(false)
      }
    )

    return () => subscription.unsubscribe()
  }, [])

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  return (
    <AuthContext.Provider value={{ user, session, loading, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
```

Wrap your app with this provider in `src/main.tsx` (or `src/App.tsx`):

```tsx
import { AuthProvider } from './contexts/AuthContext'

function App() {
  return (
    <AuthProvider>
      {/* your routes/app here */}
    </AuthProvider>
  )
}
```

---

## Login and signup components

### Custom form approach

Create `src/components/LoginForm.tsx`:

```tsx
import { useState, FormEvent } from 'react'
import { supabase } from '../lib/supabase'

export function LoginForm() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isSignUp, setIsSignUp] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    const { error } = isSignUp
      ? await supabase.auth.signUp({ email, password })
      : await supabase.auth.signInWithPassword({ email, password })

    if (error) {
      setError(error.message)
    }
    // On success, the onAuthStateChange listener in AuthContext
    // will update the user state automatically.

    setLoading(false)
  }

  const handleOAuthLogin = async (provider: 'google' | 'github') => {
    await supabase.auth.signInWithOAuth({
      provider,
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
      },
    })
  }

  return (
    <form onSubmit={handleSubmit}>
      <h2>{isSignUp ? 'Sign Up' : 'Log In'}</h2>
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <button type="submit" disabled={loading}>
        {loading ? 'Loading...' : isSignUp ? 'Sign Up' : 'Log In'}
      </button>

      <button type="button" onClick={() => handleOAuthLogin('google')}>
        Continue with Google
      </button>

      <button type="button" onClick={() => setIsSignUp(!isSignUp)}>
        {isSignUp ? 'Already have an account? Log in' : "Don't have an account? Sign up"}
      </button>
    </form>
  )
}
```

### Pre-built Auth UI approach

```tsx
import { Auth } from '@supabase/auth-ui-react'
import { ThemeSupa } from '@supabase/auth-ui-shared'
import { supabase } from '../lib/supabase'

export function LoginForm() {
  return (
    <Auth
      supabaseClient={supabase}
      appearance={{ theme: ThemeSupa }}
      providers={['google', 'github']}
      redirectTo={`${window.location.origin}/auth/callback`}
    />
  )
}
```

---

## Auth callback handler

For OAuth and magic link flows, create a component that handles the callback. If using React Router:

Create `src/pages/AuthCallback.tsx`:

```tsx
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'

export function AuthCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    // Supabase client automatically handles the OAuth callback
    // by reading the URL hash/params.
    // Just wait for the session to be established and redirect.
    supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') {
        navigate('/')
      }
    })
  }, [navigate])

  return <div>Logging you in...</div>
}
```

Add the route:

```tsx
<Route path="/auth/callback" element={<AuthCallback />} />
```

---

## Route protection

### Protected Route wrapper

Create `src/components/ProtectedRoute.tsx`:

```tsx
import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}
```

Use it in your routes:

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { LoginForm } from './components/LoginForm'
import { Dashboard } from './pages/Dashboard'
import { AuthCallback } from './pages/AuthCallback'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginForm />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
```

---

## Sign out

```tsx
import { useAuth } from '../contexts/AuthContext'

export function SignOutButton() {
  const { signOut } = useAuth()

  return <button onClick={signOut}>Sign out</button>
}
```

---

## Accessing the user in components

```tsx
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'

export function TodoList() {
  const { user } = useAuth()
  const [todos, setTodos] = useState([])

  useEffect(() => {
    // RLS automatically filters to the current user's rows
    supabase
      .from('todos')
      .select('*')
      .then(({ data }) => setTodos(data ?? []))
  }, [])

  const addTodo = async (title: string) => {
    const { data, error } = await supabase
      .from('todos')
      .insert({ title, user_id: user!.id })
      .select()
      .single()

    if (data) setTodos([...todos, data])
  }

  return (
    <div>
      <h1>Welcome, {user?.email}</h1>
      {/* render todos */}
    </div>
  )
}
```

---

## Adaptation notes for other frameworks

- **Svelte / SvelteKit**: Use `@supabase/supabase-js` directly. SvelteKit has server-side capabilities — use `@supabase/ssr` similar to Next.js. Use Svelte stores instead of React context.
- **Vue / Nuxt**: Use `@supabase/supabase-js`. Nuxt has the `@nuxtjs/supabase` module. Use Vue composables or Pinia stores instead of React context.
- **Remix**: Use `@supabase/ssr` with loader/action functions, similar to Next.js server-side patterns.
- **Plain HTML/JS**: Use `@supabase/supabase-js` directly via CDN or bundler. No context needed — just use the client instance.
