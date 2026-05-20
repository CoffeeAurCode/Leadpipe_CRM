# Learning Guide — Session 20
## Topic: Google OAuth Sign-In / Sign-Up (CRM App + Landing Page)

---

## Overview

This session added Google OAuth sign-in and sign-up across both projects:
- **CRM app** (`Tenant_management_MVP/frontend`) — React + Vite
- **Landing page** (`Leadpipe-1`) — Next.js App Router

The goal: Google OAuth must wire into the full payment and onboarding flow exactly like email auth does.

---

## Part 1 — CRM App (React + Vite)

### What was already there
The Google OAuth button and handler were **already coded** in `AuthPage.jsx`:
```js
const handleGoogleAuth = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin },
    });
};
```
`AuthContext.jsx` already had `ensureManagerProfile()` to auto-create a `manager_profiles` row for new OAuth users.

### What was missing / fixed

**1. `frontend/src/lib/supabase.js` — flow type**
```js
// Before
flowType: 'implicit'

// After
flowType: 'pkce'
```
`implicit` puts the access token in the URL hash. `pkce` (Proof Key for Code Exchange) is the modern, secure default for Supabase v2 — it uses a code + verifier exchange instead. Changing this only affects OAuth/magic link flows, **not** email/password.

**2. `frontend/src/components/AuthPage.jsx` — loading state**
Added `googleLoading` state so the button shows a spinner and "Connecting to Google..." text while the redirect is being initiated (prevents double-clicks and gives visual feedback).

### Why the existing flow works end-to-end
| Concern | How it works |
|---|---|
| Profile creation | `ensureManagerProfile()` in `AuthContext.jsx` — checks `manager_profiles`, inserts if missing |
| Payment | Backend uses `user.email` from JWT — Google email works fine |
| Subscription gate | 403 → `apiService.js` redirects to pricing — same for all users |
| Onboarding | Keyed on `user.id` (Supabase UUID) — auth method doesn't matter |
| JWT auth | Google OAuth users get standard Supabase JWTs; backend validates the same way |

---

## Part 2 — Landing Page (Next.js App Router)

### Tech difference vs CRM
The landing page is **Next.js** (server-side rendering + client hydration), not a pure SPA. This matters a lot for OAuth callbacks — it caused three rounds of debugging.

### What was added

**`src/lib/supabase.ts`**
Added PKCE flow options (same as CRM).

**`src/app/auth/page.tsx`**
Added Google button above the Login/Sign Up tabs. The button is shared for both modes — there's no way to tell upfront if a click is "sign in" or "sign up"; the callback page makes that determination.

```tsx
const handleGoogleAuth = async () => {
    setGoogleLoading(true);
    const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) { toast.error(error.message); setGoogleLoading(false); }
};
```

**`src/app/auth/callback/page.tsx` (new file)**
The OAuth callback route. Handles new vs existing users:
- **New user** (no `manager_profiles` row) → create profile → `router.push("/pricing")`
- **Existing user** → redirect to CRM with tokens in URL hash (same pattern as email sign-in)

---

## The Debugging Journey (Important Lessons)

### Attempt 1 — Manual `exchangeCodeForSession` (failed)
```tsx
const code = new URLSearchParams(window.location.search).get("code");
const { data: { session }, error } = await supabase.auth.exchangeCodeForSession(code);
// → oauth_failed every time
```
**Why it failed:** `detectSessionInUrl: true` (default in Supabase) was already auto-exchanging the `?code=` during client initialization. By the time `useEffect` ran, the code was already consumed. The manual call hit an already-used code and got an error.

### Attempt 2 — `onAuthStateChange` with `INITIAL_SESSION` (got stuck)
```tsx
supabase.auth.onAuthStateChange(async (event, session) => {
    if (event === 'SIGNED_IN' || event === 'INITIAL_SESSION') {
        // route user
    }
});
```
**Why it got stuck:** In Next.js, the timing between module initialization, SSR hydration, and React Strict Mode's double-invocation of `useEffect` made `INITIAL_SESSION` unreliable. The event didn't always reach the listener.

### Attempt 3 — Dual strategy: events + polling (still stuck)
Added `setInterval` polling `getSession()` every 500ms as a fallback alongside `onAuthStateChange`. **Still stuck on first load, but worked on page reload.**

**The key observation from the user:** "If I reload the same callback URL, it works."

**Root cause identified:** On first load, `detectSessionInUrl: true` auto-exchanges the code and **holds Supabase's internal lock** during the HTTP request. `getSession()` waits on that same lock — so every poll was waiting for the exchange to finish. When it finished, the session was in localStorage but something in the lock release prevented polls from returning it cleanly. On reload, the session was already in localStorage from the first load, so it returned instantly.

### Attempt 4 — `detectSessionInUrl: false` + manual exchange (FINAL FIX)

**`src/lib/supabase.ts`:**
```ts
auth: {
    detectSessionInUrl: false,  // We own the callback, no auto-exchange
    flowType: 'pkce',
}
```

**`src/app/auth/callback/page.tsx`:**
```tsx
useEffect(() => {
    const handle = async () => {
        // Step 1: existing session? (handles reload case)
        const { data: { session: stored } } = await supabase.auth.getSession();
        if (stored) { await routeUser(stored); return; }

        // Step 2: fresh exchange
        const code = new URLSearchParams(window.location.search).get("code");
        if (!code) { router.push("/auth"); return; }

        const { data: { session }, error } = await supabase.auth.exchangeCodeForSession(code);
        if (error || !session) { router.push("/auth"); return; }

        await routeUser(session);
    };
    handle();
}, [router]);
```

**Why this works:**
- No auto-exchange → no lock contention → no race condition
- `exchangeCodeForSession` reads the PKCE code verifier from localStorage (stored by `signInWithOAuth` before the Google redirect) and exchanges it
- Step 1 handles reloads gracefully (session already in storage)
- Step 2 handles fresh loads cleanly

---

## The New vs Existing User Determination

This is needed because OAuth doesn't split into "sign in" and "sign up" flows upfront:

```tsx
const { data: profile } = await supabase
    .from("manager_profiles")
    .select("user_id")
    .eq("user_id", session.user.id)
    .maybeSingle();

if (!profile) {
    // NEW USER — create profile, go to pricing
    await supabase.from("manager_profiles").insert({
        user_id: session.user.id,
        name: session.user.user_metadata?.full_name || session.user.email?.split("@")[0] || "Manager",
        phone: null,
    });
    router.push("/pricing");
} else {
    // EXISTING USER — go to CRM with tokens
    window.location.href = `${frontendUrl}#access_token=${session.access_token}&refresh_token=${session.refresh_token}&token_type=bearer&type=recovery`;
}
```

---

## The "Flash to Walkthrough" Observation (Security Analysis)

After Google sign-up, the user briefly saw the CRM walkthrough page for 1–2 seconds before landing on pricing.

**Why it happens:** On a repeat Google sign-up attempt, the `manager_profiles` row already exists (created on the first attempt). The callback treats this as an "existing user" and routes to the CRM. The CRM loads its onboarding shell, fires API calls, gets 403 (no subscription), and `apiService.js` redirects to `${LANDING_PAGE_URL}/pricing`.

**Is it a security bug? No:**
1. No data is returned during that flash — API calls get 403 before any data comes back
2. The backend enforces subscription independently via `require_active_subscription` FastAPI dependency
3. Supabase RLS policies scope all queries to `auth.uid()` — even if both gates were bypassed, no data is reachable

**It is a UX/flow bug** (new users routed to CRM instead of pricing on repeat attempts), but the security boundary holds at the backend layer.

---

## Supabase Dashboard Setup Required

For Google OAuth to work, these steps must be done in the Supabase dashboard (cannot be done from code):

1. **Google Cloud Console** — Create OAuth 2.0 Client ID (Web application), add authorized redirect URI:
   ```
   https://<project-ref>.supabase.co/auth/v1/callback
   ```

2. **Supabase → Auth → Providers → Google** — Enable, paste Client ID and Secret

3. **Supabase → Auth → URL Configuration → Redirect URLs** — Add:
   - `http://localhost:5173` (CRM dev)
   - `http://localhost:3000/auth/callback` (landing page dev)
   - Production URLs when deployed

---

## Key Concepts Summary

| Concept | Explanation |
|---|---|
| PKCE flow | Code + verifier exchange; more secure than implicit (no token in URL hash) |
| `detectSessionInUrl` | When true, Supabase auto-processes `?code=` on page load; turn off if you handle the callback manually |
| `INITIAL_SESSION` | Supabase event fired after client initialization; unreliable in Next.js due to SSR/hydration timing |
| `exchangeCodeForSession` | Manual PKCE exchange; reads code verifier from localStorage (stored by `signInWithOAuth`) |
| Implicit vs PKCE | Implicit: token in URL hash. PKCE: code in query string, exchanged for token via HTTP |
| `ensureManagerProfile` | Idempotent profile creation for OAuth users who bypass the signup form |
| New vs existing user (OAuth) | Check `manager_profiles` row — no row = new user → pricing; row exists = returning user → CRM |

---

## Files Changed

### CRM App (`Tenant_management_MVP/frontend`)
| File | Change |
|---|---|
| `src/lib/supabase.js` | `flowType: 'implicit'` → `flowType: 'pkce'` |
| `src/components/AuthPage.jsx` | Added `googleLoading` state + spinner on Google button |

### Landing Page (`Leadpipe-1`)
| File | Change |
|---|---|
| `src/lib/supabase.ts` | Added `detectSessionInUrl: false`, `flowType: 'pkce'` |
| `src/app/auth/page.tsx` | Added Google button + "Or" divider above tabs; `handleGoogleAuth` function |
| `src/app/auth/callback/page.tsx` | **New file** — OAuth callback; session-first check + manual code exchange; routes new vs existing users |
