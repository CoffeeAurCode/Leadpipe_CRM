/**
 * Shared helpers for navigating the app and interacting with common UI patterns.
 */

import { Page, expect } from '@playwright/test';

const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

export function authHeader(): { Authorization: string } {
  const token = process.env.AUTH_TOKEN;
  if (!token) throw new Error('AUTH_TOKEN not set');
  return { Authorization: `Bearer ${token}` };
}

// ── Navigation ────────────────────────────────────────────────────────────────

type AppView = 'Dashboard' | 'Tenants' | 'Properties' | 'Leasing AI' | 'Rent' | 'Settings';

export async function navigateTo(page: Page, label: AppView): Promise<void> {
  const nav = page.locator('[data-tour="sidebar-nav"]');
  await nav.locator(`button:has-text("${label}")`).click();
  // Wait for content to settle after navigation
  await page.waitForTimeout(600);
}

// ── API helpers (direct HTTP, bypasses UI) ────────────────────────────────────

export async function apiGet<T>(page: Page, path: string): Promise<T> {
  const resp = await page.request.get(`${API_BASE}${path}`, { headers: authHeader() });
  if (!resp.ok()) throw new Error(`GET ${path} failed: ${resp.status()}`);
  return resp.json() as T;
}

export async function apiPatch<T>(page: Page, path: string, body: object): Promise<T> {
  const resp = await page.request.patch(`${API_BASE}${path}`, {
    data: body,
    headers: authHeader(),
  });
  if (!resp.ok()) throw new Error(`PATCH ${path} failed: ${resp.status()} ${await resp.text()}`);
  return resp.json() as T;
}

// ── LeasingTab helpers ────────────────────────────────────────────────────────

export async function getListingStatus(page: Page, flatNumber: string): Promise<string | null> {
  // Find the listing card that contains the flat number
  const card = page.locator('[data-tour="leasing-listings"] .bg-card').filter({
    has: page.locator(`text="${flatNumber}"`),
  });
  await card.waitFor({ timeout: 8000 });
  const badge = card.locator('span').filter({ hasText: /^(Active|Inactive)$/ });
  return badge.textContent();
}

// ── TenantManagement helpers ──────────────────────────────────────────────────

export async function openTenant(page: Page, tenantName: string): Promise<void> {
  const row = page.locator('[data-tour="tenant-table"] tbody tr').filter({
    has: page.locator(`text="${tenantName}"`),
  });
  await row.first().click();
  // TenantProfile panel slides in from the right
  await expect(page.locator('.fixed.right-0.top-0.h-full')).toBeVisible({ timeout: 8000 });
}

// ── Properties helpers ────────────────────────────────────────────────────────

export async function openPropertyGroupEditModal(page: Page, groupName: string): Promise<void> {
  // The edit button is on the card image and shows on hover
  const card = page.locator('.bg-card').filter({ has: page.locator(`h3:has-text("${groupName}")`) });
  await card.hover();
  await card.locator('button[aria-label="Edit property group"]').click();
  await expect(page.locator('h2:has-text("Edit Property Group")')).toBeVisible({ timeout: 5000 });
}

export async function openBuildingEditModal(page: Page, buildingName: string): Promise<void> {
  const card = page.locator('.bg-card').filter({ has: page.locator(`h3:has-text("${buildingName}")`) });
  await card.hover();
  await card.locator('button[aria-label="Edit building"]').click();
  // Building edit uses AddBuildingModal — header says "Edit Building"
  await expect(page.locator('h2:has-text("Edit Building")')).toBeVisible({ timeout: 5000 });
}
