# Auth Loop Diagnosis — Leadpipe

**Date:** 2026-05-13  
**Symptom:** Infinite loop: `/auth` → Google OAuth → `/pricing` → "Please sign in first" → `/auth`
**project file**:"C:\Users\BIT\Coding\Leadpipe-1"
---

## Root Cause (One Line)

Supabase's registered OAuth redirect URLs include the **old Netlify preview domain** (`test--leadpipecrm.netlify.app`) but **not the production domain** (`www.leadpipe.ca`), so the auth code lands on the wrong domain and the session is never established on `leadpipe.ca`.

---

## The Full Loop, Step by Step

```
1. User visits https://www.leadpipe.ca/auth
2. Clicks "Continue with Google"
3. supabase.auth.signInWithOAuth() fires with redirectTo: https://www.leadpipe.ca/auth/callback
4. Google authenticates → sends code back to Supabase
5. Supabase checks its registered redirect URL allowlist
6. www.leadpipe.ca/auth/callback is NOT in the list
7. Supabase falls back to the registered URL: https://test--leadpipecrm.netlify.app
8. Browser lands on test--leadpipecrm.netlify.app/#access_token=... (WRONG domain)
9. The auth code/token is consumed by the Netlify app, not by www.leadpipe.ca
10. www.leadpipe.ca session → null (localStorage on leadpipe.ca is never populated)
11. User is somehow navigated to https://www.leadpipe.ca/pricing
12. Clicks "Start 14-Day Free Trial"
13. handleStartTrial() calls supabase.auth.getSession() → returns null
14. Toast fires: "Please sign in first"
15. router.push("/auth") → back to step 1 → LOOP
```

---

## Evidence in the Code

### `src/app/auth/page.tsx` — OAuth initiation (lines 33–40)

```typescript
const { error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        // At production this correctly becomes: https://www.leadpipe.ca/auth/callback
        // But Supabase never sends the code there because it isn't registered
    },
});
```

The code is correct. The problem is the Supabase dashboard configuration, not this file.

### `src/lib/supabase.ts` — Client config

```typescript
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,   // https://nfgnxndktecqeleabbip.supabase.co
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  {
    auth: {
      detectSessionInUrl: false,  // manual PKCE callback — correct
      flowType: 'pkce',           // PKCE flow — correct
    },
  }
)
```

PKCE is implemented correctly. The session is never set because the code exchange never happens on `leadpipe.ca`.

### `src/app/pricing/page.tsx` — The "sign in first" gate (lines 49–85)

```typescript
const { data: { session } } = await supabase.auth.getSession();

if (!session) {
    toast.error("Please sign in first");  // ← user sees this
    router.push("/auth");                 // ← sends them back to /auth → loop
    return;
}
```

This check is correct — the session genuinely is null because step 8 above consumed the token on a different domain.

### `.env.local` — Domain mismatch evidence (lines 22–24)

```env
# CRM frontend (redirect target after login)
# NEXT_PUBLIC_FRONTEND_URL=https://test--leadpipecrm.netlify.app  # <-- OLD, commented out
NEXT_PUBLIC_FRONTEND_URL=http://localhost:5173                     # <-- dev only
```

The old Netlify URL is present (commented out), confirming this was once the registered domain. It was never replaced in the Supabase dashboard when the project moved to `www.leadpipe.ca`.

---

## Domain Mismatch Table

| Component | Should point to | Actually registered | Status |
|-----------|----------------|---------------------|--------|
| OAuth callback | `https://www.leadpipe.ca/auth/callback` | `https://test--leadpipecrm.netlify.app/auth/callback` | ❌ WRONG |
| CRM redirect (env) | Production CRM domain | `http://localhost:5173` | ❌ Dev-only |

---

## What Is NOT the Problem

- The PKCE flow implementation is correct.
- `detectSessionInUrl: false` with manual `exchangeCodeForSession()` is correct.
- The pricing page session check is correct.
- The callback handler at `/auth/callback` is correct.
- No code bug — this is entirely a configuration issue.

---

## Fix (Two Actions Required)

### Fix 1 — Supabase Dashboard (critical, must do first)

1. Open [https://supabase.com/dashboard/project/nfgnxndktecqeleabbip/auth/url-configuration](https://supabase.com/dashboard/project/nfgnxndktecqeleabbip/auth/url-configuration)
2. Under **Redirect URLs**, add:
   ```
   https://www.leadpipe.ca/auth/callback
   ```
3. Also ensure these are present for dev/staging:
   ```
   http://localhost:3000/auth/callback
   https://test--leadpipecrm.netlify.app/auth/callback  (keep if still using for staging)
   ```
4. Save.

This is the single change that breaks the loop.

### Fix 2 — Production environment variables

Wherever the production build is deployed (Netlify / Vercel / other), set:

```env
NEXT_PUBLIC_FRONTEND_URL=https://<actual-crm-production-domain>
NEXT_PUBLIC_BACKEND_URL=https://tenant-management-mvp.onrender.com
```

Do **not** rely on `.env.local` for production — that file should only contain localhost values for local dev.

---

## Why the Token Showed Up on the Wrong Domain

The URL the user reported:
```
https://test--leadpipecrm.netlify.app/#access_token=eyJhbGci...
```

This is Supabase's **implicit flow fallback** — when the registered redirect URL is the Netlify domain, Supabase sends the token there in the hash fragment. The token is valid but it lands in a browser tab pointed at Netlify, not `leadpipe.ca`. The `leadpipe.ca` site's localStorage is never touched, so `getSession()` returns null there.

---

## Verification After Fix

After adding `https://www.leadpipe.ca/auth/callback` to Supabase's redirect allowlist:

1. Go to `https://www.leadpipe.ca/auth`
2. Click Google login
3. Confirm redirect lands on `https://www.leadpipe.ca/auth/callback?code=...` (NOT Netlify)
4. Confirm redirect from callback goes to `/pricing` (or `/dashboard`)
5. Click "Start 14-Day Free Trial"
6. Confirm Stripe checkout opens (no "please sign in" toast)
