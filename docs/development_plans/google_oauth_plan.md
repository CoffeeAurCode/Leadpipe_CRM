# Plan: Add Google OAuth Sign-In / Sign-Up

## Context

The user wants Google sign-in and sign-up in the Tenant Management MVP, with the full payment gateway and tutorial/onboarding workflow working end-to-end for Google OAuth users. The existing email/password auth must not break.

**Key finding:** The Google OAuth frontend code is already 90% in place:
- `AuthPage.jsx` already has a "Continue with Google" button calling `supabase.auth.signInWithOAuth`
- `AuthContext.jsx` already has `ensureManagerProfile()` that auto-creates a `manager_profiles` row for new Google users
- `supabase.js` already has `detectSessionInUrl: true` to pick up the OAuth redirect

The only code change needed is updating the OAuth flow type from deprecated `implicit` to the modern `pkce`. Everything else (payment, onboarding, JWT auth) already works correctly regardless of how the user authenticated.

---

## Why The Existing Flow Works End-to-End

| Concern | How it's handled |
|---|---|
| **Profile creation** | `ensureManagerProfile()` in `AuthContext.jsx` — runs on first sign-in, upserts row with name from `user_metadata.full_name` |
| **Payment** | `POST /payments/create-checkout-session` uses `user.email` from JWT — Google email works |
| **Subscription gate** | Backend 403 → `apiService.js` redirects to `${LANDING_PAGE_URL}/pricing` — same for all users |
| **Onboarding** | Uses localStorage key `crm-onboarding-checklist-{user.id}` where `user.id` is the Supabase UUID — auth-method agnostic |
| **JWT auth** | Google OAuth users get a standard Supabase JWT; backend validates via JWKS or JWT secret |

---

## Code Changes

### 1. `frontend/src/lib/supabase.js` — Switch from implicit to pkce flow

**Why:** Supabase v2 defaults to PKCE for all new projects. Using `implicit` may cause OAuth to silently fail on newer Supabase projects because the auth server expects a PKCE code exchange, not a fragment redirect. PKCE is also more secure (no `access_token` in URL hash).

**Change:** `flowType: 'implicit'` → `flowType: 'pkce'`

> Does not affect email/password or sign-out; only touches OAuth and magic link flows.

---

### 2. `frontend/src/components/AuthPage.jsx` — Add loading state to Google button

**Why:** Currently clicking "Continue with Google" gives zero visual feedback before the redirect. Add a `googleLoading` state that disables the button and shows "Connecting to Google..." while the OAuth redirect is being initiated.

---

## Required Supabase Dashboard Configuration

> These steps must be completed in the Supabase dashboard for Google OAuth to work. They **cannot** be done from code.

### Step 1 — Google Cloud Console

1. Go to [https://console.cloud.google.com](https://console.cloud.google.com) → **APIs & Services** → **Credentials**
2. Create an **OAuth 2.0 Client ID** (Application type: **Web application**)
3. Add to **Authorized redirect URIs**:
   ```
   https://<your-project-ref>.supabase.co/auth/v1/callback
   ```
4. Copy the **Client ID** and **Client Secret**

### Step 2 — Supabase Auth Settings

1. Go to **Supabase dashboard** → **Authentication** → **Providers** → **Google**
2. Enable Google provider
3. Paste the **Client ID** and **Client Secret** from Step 1
4. Save

### Step 3 — Supabase URL Configuration

1. Go to **Supabase dashboard** → **Authentication** → **URL Configuration**
2. Add your app URL to **Redirect URLs**:
   - Development: `http://localhost:5173`
   - Production: `https://your-app-domain.com`
3. Confirm **Site URL** is set to your app's root URL

---

## Critical Files

| File | Action |
|---|---|
| `frontend/src/lib/supabase.js` | ✏️ Change `flowType` to `pkce` |
| `frontend/src/components/AuthPage.jsx` | ✏️ Add Google button loading state |
| `frontend/src/context/AuthContext.jsx` | ✅ No changes needed (already handles Google OAuth) |
| `frontend/src/context/OnboardingContext.jsx` | ✅ No changes needed |
| `frontend/src/services/apiService.js` | ✅ No changes needed |

---

## Verification

1. Start dev server (`npm run dev`)
2. Navigate to the auth page — confirm "Continue with Google" button is visible on both **Login** and **Signup** modes
3. Click the button — confirm redirect to Google's consent screen
4. Complete Google sign-in — confirm redirect back to `http://localhost:5173`
5. Confirm app loads the onboarding checklist (new user with no subscription)
6. Confirm API calls get `403` → app redirects to pricing page
7. For existing email/password users: confirm login still works unchanged
