/**
 * One-time auth setup: injects the Supabase session into localStorage
 * so all tests start already authenticated.
 *
 * Run automatically before tests via the 'setup' project in playwright.config.ts.
 * Requires AUTH_TOKEN (Supabase access_token) in e2e/.env.
 */

import { test as setup, expect } from '@playwright/test';
import * as path from 'path';

const AUTH_FILE = path.join(__dirname, '.auth/manager.json');
const SUPABASE_PROJECT_REF = 'nfgnxndktecqeleabbip';
const STORAGE_KEY = `sb-${SUPABASE_PROJECT_REF}-auth-token`;

setup('authenticate', async ({ page }) => {
  const token = process.env.AUTH_TOKEN;
  if (!token) throw new Error('AUTH_TOKEN is required in e2e/.env');

  // Decode JWT payload (no signature verification — we trust our own token)
  const parts = token.split('.');
  if (parts.length !== 3) throw new Error('AUTH_TOKEN does not look like a JWT');

  const payload = JSON.parse(
    Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString('utf-8')
  );

  const session = {
    access_token: token,
    // Use real refresh_token if provided, otherwise use placeholder
    refresh_token: process.env.REFRESH_TOKEN || 'playwright-placeholder-refresh',
    expires_in: 3600,
    // Set expires_at 55 minutes from now (prevents premature refresh)
    expires_at: Math.floor(Date.now() / 1000) + 3300,
    token_type: 'bearer',
    user: {
      id: payload.sub || 'unknown',
      email: payload.email || payload.user_email || '',
      role: 'authenticated',
      aud: 'authenticated',
      app_metadata: {},
      user_metadata: {},
    },
  };

  // Inject the session into localStorage BEFORE the page loads
  await page.addInitScript(({ key, value }) => {
    localStorage.setItem(key, value);
  }, { key: STORAGE_KEY, value: JSON.stringify(session) });

  await page.goto('/');

  // Wait until the sidebar nav is visible (means AuthGate passed)
  await expect(
    page.locator('[data-tour="sidebar-nav"]')
  ).toBeVisible({ timeout: 20000 });

  // Save the authenticated storage state for all subsequent tests
  await page.context().storageState({ path: AUTH_FILE });
  console.log('Auth setup complete — storage state saved to', AUTH_FILE);
});
