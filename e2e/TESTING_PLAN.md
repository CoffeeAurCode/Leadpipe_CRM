# E2E Testing Plan — Tenant Management MVP

## Overview

The `e2e/` directory contains a Playwright test suite covering the four feature areas
delivered in the recent sprint. Tests run in serial (one worker, no parallelism) against
a live app — either local dev servers or a hosted deployment.

---

## Test Coverage Matrix

| ID  | Description                                              | Automated | Environment |
|-----|----------------------------------------------------------|-----------|-------------|
| A1  | Assigning tenant deactivates active listing              | ✅        | API + UI    |
| A2  | Unassigning does NOT reactivate listing                  | ✅        | API + UI    |
| A3  | Assigning to a unit with no listing succeeds cleanly     | ✅        | API only    |
| A4  | CSV import deactivates listing                           | ⬜ skipped | Manual      |
| B1  | Edit property group name — UI updates                    | ✅        | UI          |
| B2  | Edit property group address fields                       | ✅        | UI          |
| B3  | Empty name blocked — no API call fired                   | ✅        | UI          |
| B4  | Edit building name                                       | ✅        | UI          |
| B5  | Editing one building does not affect others              | ✅        | UI          |
| B6  | Complaint routing after rename                           | ⬜ skipped | Manual (live call) |
| B7  | Unit/flat edit regression                                | ✅        | UI          |
| B8  | Listing edit regression                                  | ✅        | UI          |
| C1  | Edit tenant name — panel header + table row update       | ✅        | UI          |
| C2  | Edit phone to valid E.164 — saves without error          | ✅        | UI          |
| C3  | Invalid phone format — inline error, no PATCH sent       | ✅        | UI          |
| C4  | Duplicate phone rejected with inline error               | ✅        | UI          |
| C5  | Empty name blocked — inline error, no PATCH sent         | ✅        | UI          |
| C6  | Update name + phone + email in one save                  | ✅        | UI          |
| C7  | Editing tenant A does not affect tenant B                | ✅        | UI          |
| C8  | Phone change + complaint agent                           | ⬜ skipped | Manual (live call) |
| D1  | Existing tenant fields (manager_notes) still save        | ✅        | UI          |
| D2  | Create new property group still works                    | ✅        | UI + API    |
| D3  | Create new building still works                          | ✅        | UI + API    |

**Totals:** 19 automated, 4 skipped (require live phone calls or file upload).

---

## Running Tests Locally

### Prerequisites

Both servers must be running before you invoke Playwright:

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev          # starts on http://localhost:5173
```

### One-time setup

1. Copy the env template:
   ```
   cp e2e/.env.example e2e/.env
   ```

2. Get your Supabase access token:
   - Open the app in the browser
   - DevTools → Application → Local Storage → `http://localhost:5173`
   - Find key `sb-nfgnxndktecqeleabbip-auth-token`
   - Copy the `access_token` value

3. Paste it into `e2e/.env`:
   ```
   AUTH_TOKEN=eyJ...your-token...
   ```

### Run commands

```bash
cd e2e
npm test                  # full suite (headless)
npm run test:headed       # see the browser
npm run test:ui           # Playwright interactive UI
npm run test:part-a       # Part A only
npm run test:part-b       # Part B only
npm run test:part-c       # Part C only
npm run test:part-d       # Part D only
```

---

## Running Tests Against a Hosted Deployment

The suite supports running against any deployed environment via two env vars.

### `.env` for hosted

```
# Hosted frontend URL (no trailing slash)
FRONTEND_URL=https://your-app.vercel.app

# Hosted backend URL (no trailing slash)
BACKEND_URL=https://your-api.railway.app

# Supabase access_token from the HOSTED app's localStorage
# (open the hosted URL in the browser, copy from DevTools)
AUTH_TOKEN=eyJ...token-for-hosted-env...
REFRESH_TOKEN=...optional...
```

### Getting the hosted auth token

The token is environment-specific — you need one issued by the hosted Supabase project,
not your local dev session.

1. Open the hosted frontend URL in a browser and log in
2. DevTools → Application → Local Storage → `https://your-app.vercel.app`
3. Find key `sb-nfgnxndktecqeleabbip-auth-token`
4. Copy the `access_token` value into `e2e/.env`

### Important notes for hosted runs

- **Token expiry:** Supabase access tokens expire after 1 hour. If tests start failing
  with 401s, refresh your token. The `REFRESH_TOKEN` env var enables auto-renewal.
- **Data isolation:** Tests revert their own changes in teardown, but they still need
  seed data present (at least one active listing, at least two tenants, etc.).
  The hosted DB is shared — don't run tests against a production tenant's live data
  without confirming with them first.
- **Network timeouts:** Hosted backends are slower than localhost. The config already
  uses generous timeouts (`actionTimeout: 15000`, `navigationTimeout: 30000`); you
  may need to increase these for cold-start deployments.

---

## CI / GitHub Actions

Below is a ready-to-use workflow. It runs on every push to `main` and every PR.

```yaml
# .github/workflows/e2e.yml
name: E2E Tests

on:
  push:
    branches: [main]
  pull_request:

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: e2e/package-lock.json

      - name: Install Playwright deps
        working-directory: e2e
        run: npm ci && npx playwright install --with-deps chromium

      - name: Run E2E tests
        working-directory: e2e
        env:
          FRONTEND_URL: ${{ secrets.E2E_FRONTEND_URL }}
          BACKEND_URL: ${{ secrets.E2E_BACKEND_URL }}
          AUTH_TOKEN: ${{ secrets.E2E_AUTH_TOKEN }}
          REFRESH_TOKEN: ${{ secrets.E2E_REFRESH_TOKEN }}
        run: npm test

      - name: Upload Playwright report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: e2e/playwright-report/
          retention-days: 7
```

**Required GitHub Secrets** (Settings → Secrets → Actions):

| Secret               | Value                                                   |
|----------------------|---------------------------------------------------------|
| `E2E_FRONTEND_URL`   | `https://your-app.vercel.app`                           |
| `E2E_BACKEND_URL`    | `https://your-api.railway.app`                          |
| `E2E_AUTH_TOKEN`     | Supabase access_token for the CI service account        |
| `E2E_REFRESH_TOKEN`  | Supabase refresh_token (optional but recommended)       |

**Tip:** Create a dedicated "CI service account" in Supabase rather than using a
personal token. Rotate it independently of developer accounts.

---

## Architecture Notes

### Auth flow

`auth.setup.ts` runs once before all tests. It injects the Supabase session into
localStorage via `addInitScript` (before the page loads), navigates to `/`, and waits
for the sidebar nav to confirm the AuthGate passed. The resulting storage state is saved
to `.auth/manager.json` and reused by all subsequent tests.

### Helper module (`helpers/app.ts`)

| Export                       | Purpose                                              |
|------------------------------|------------------------------------------------------|
| `navigateTo(page, label)`    | Click a sidebar nav button and wait 600 ms           |
| `apiGet(page, path)`         | Authenticated GET to the backend API                 |
| `apiPatch(page, path, body)` | Authenticated PATCH to the backend API               |
| `openTenant(page, name)`     | Click a tenant row; wait for the slide-in panel      |
| `openPropertyGroupEditModal` | Hover a property group card; click its edit button   |
| `openBuildingEditModal`      | Hover a building card; click its edit button         |

`API_BASE` in `helpers/app.ts` is driven by `BACKEND_URL` env var (falls back to
`http://localhost:8000`). The frontend `baseURL` in `playwright.config.ts` is driven
by `FRONTEND_URL` (falls back to `http://localhost:5173`).

### Test isolation

Every test that mutates data contains a teardown block that restores the original state
via the API. This means:
- Tests can run in any order
- Tests can be re-run without manual DB cleanup
- The suite is safe against a shared/staging DB

### Skipped tests

Tests that require a live VAPI phone call (`B6`, `C8`) or a file-upload interaction
(`A4`) are skipped permanently. They are kept as `test.skip(...)` stubs so they appear
in the report as "skipped" rather than silently absent.

---

## Troubleshooting

| Symptom                              | Likely cause                         | Fix                                     |
|--------------------------------------|--------------------------------------|-----------------------------------------|
| `AUTH_TOKEN is required` error       | `.env` not created or empty          | Create `e2e/.env` from `.env.example`   |
| `AuthGate` never passes (timeout)    | Token expired or wrong environment   | Refresh the token from the correct app  |
| 401 responses from API               | Token expired mid-run                | Add `REFRESH_TOKEN` to `.env`           |
| Tests pass locally, fail in CI       | CI hitting localhost instead of prod | Confirm `FRONTEND_URL`/`BACKEND_URL` secrets are set |
| `No active listing found` skip       | Seed data missing                    | Create at least one active listing via the UI |
| `Need at least 2 tenants` skip       | Seed data missing                    | Ensure the DB has ≥ 2 tenants           |
