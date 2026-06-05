/**
 * Part C — Tenant Name + Phone Edit
 * All tests use the TenantManagement UI → TenantProfile slide-in panel.
 */

import { test, expect } from '@playwright/test';
import { navigateTo } from '../helpers/app';

const PANEL_SELECTOR = '.fixed.right-0.top-0.h-full';

async function openTenantPanel(page: import('@playwright/test').Page, index = 0) {
  await navigateTo(page, 'Tenants');
  await page.waitForSelector('[data-tour="tenant-table"] tbody tr', { timeout: 15000 });

  const rows = page.locator('[data-tour="tenant-table"] tbody tr');
  await rows.nth(index).click();
  await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });
}

async function clickEdit(page: import('@playwright/test').Page) {
  await page.locator(`${PANEL_SELECTOR} button:has-text("Edit")`).click();
  // Name input appears in edit mode
  await expect(page.locator('input[placeholder="John Doe"]')).toBeVisible({ timeout: 5000 });
}

async function clickSave(page: import('@playwright/test').Page) {
  await page.locator(`${PANEL_SELECTOR} button:has-text("Save Changes")`).click();
}

test.describe('Part C — Tenant Name + Phone Edit', () => {

  // ── C1 ─────────────────────────────────────────────────────────────────────
  test('C1 — edit tenant name updates header and list row', async ({ page }) => {
    await openTenantPanel(page, 0);

    // Record original name from panel header
    const originalName = (await page.locator(`${PANEL_SELECTOR} h2`).first().textContent())?.trim() ?? '';
    test.skip(!originalName, 'No tenant found');

    await clickEdit(page);

    // Name field should exist and be pre-filled
    const nameInput = page.locator('input[placeholder="John Doe"]');
    await expect(nameInput).toBeVisible();
    await nameInput.clear();
    await nameInput.fill('New Test Name');

    await clickSave(page);

    // Panel header should update immediately
    await expect(page.locator(`${PANEL_SELECTOR} h2`).first()).toContainText('New Test Name', { timeout: 8000 });

    // List row should also update
    await expect(page.locator('[data-tour="tenant-table"] tbody')).toContainText('New Test Name');

    // ── Revert ──
    await clickEdit(page);
    await page.locator('input[placeholder="John Doe"]').fill(originalName);
    await clickSave(page);
    await expect(page.locator(`${PANEL_SELECTOR} h2`).first()).toContainText(originalName, { timeout: 8000 });
  });

  // ── C2 ─────────────────────────────────────────────────────────────────────
  test('C2 — edit phone to valid E.164 saves without error', async ({ page }) => {
    await openTenantPanel(page, 0);

    // Get original phone to revert later
    const originalPhone = (await page.locator(`${PANEL_SELECTOR} p`).first().textContent())?.trim() ?? '';

    await clickEdit(page);

    const phoneInput = page.locator('input[type="tel"]');
    await expect(phoneInput).toBeVisible();
    const originalVal = await phoneInput.inputValue();

    // Use a unique test phone to avoid duplicate conflict
    const testPhone = '+15145550001';
    await phoneInput.clear();
    await phoneInput.fill(testPhone);

    // Intercept the PATCH to verify phone is included
    let patchBody: Record<string, unknown> = {};
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/tenants/')) {
        try { patchBody = JSON.parse(req.postData() || '{}'); } catch {}
      }
    });

    await clickSave(page);

    // No error, and edit mode closed
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });

    // If save was called, verify phone was in the payload
    if (patchBody && Object.keys(patchBody).length > 0) {
      expect(patchBody).toHaveProperty('phone', testPhone);
    }

    // ── Revert ──
    await clickEdit(page);
    await page.locator('input[type="tel"]').fill(originalVal || originalPhone);
    await clickSave(page);
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });
  });

  // ── C3 ─────────────────────────────────────────────────────────────────────
  test('C3 — invalid phone format shows inline error, no PATCH sent', async ({ page }) => {
    await openTenantPanel(page, 0);
    await clickEdit(page);

    const phoneInput = page.locator('input[type="tel"]');
    await phoneInput.clear();
    await phoneInput.fill('5145551234'); // missing leading +

    let apiCalled = false;
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/tenants/')) apiCalled = true;
    });

    await clickSave(page);

    // Inline error should appear
    await expect(page.locator(`${PANEL_SELECTOR} p.text-red-400`)).toBeVisible({ timeout: 4000 });
    await expect(page.locator(`${PANEL_SELECTOR} p.text-red-400`)).toContainText('E.164');
    expect(apiCalled).toBe(false);

    // Close without saving
    await page.locator(`${PANEL_SELECTOR} button`).filter({ has: page.locator('svg') }).last().click();
  });

  // ── C4 ─────────────────────────────────────────────────────────────────────
  test('C4 — duplicate phone rejected with inline error', async ({ page }) => {
    await navigateTo(page, 'Tenants');
    await page.waitForSelector('[data-tour="tenant-table"] tbody tr', { timeout: 15000 });

    const rows = page.locator('[data-tour="tenant-table"] tbody tr');
    const count = await rows.count();
    test.skip(count < 2, 'Need at least 2 tenants to test duplicate rejection');

    // Get phone of Tenant B (row 1)
    await rows.nth(1).click();
    await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });
    const tenantBPhone = (await page.locator(`${PANEL_SELECTOR} p`).first().textContent())?.trim() ?? '';
    // Close Tenant B panel
    await page.locator(`${PANEL_SELECTOR} button`).filter({ has: page.locator('svg') }).last().click();
    await expect(page.locator(PANEL_SELECTOR)).not.toBeVisible({ timeout: 5000 });

    // Open Tenant A (row 0) and try to set it to Tenant B's phone
    await rows.nth(0).click();
    await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });
    await clickEdit(page);

    const phoneInput = page.locator('input[type="tel"]');
    await phoneInput.clear();
    await phoneInput.fill(tenantBPhone);
    await clickSave(page);

    // Expect error about duplicate
    await expect(page.locator(`${PANEL_SELECTOR} p.text-red-400`)).toContainText('already exists', { timeout: 8000 });

    // Close
    await page.locator(`${PANEL_SELECTOR} button`).filter({ has: page.locator('svg') }).last().click();
  });

  // ── C5 ─────────────────────────────────────────────────────────────────────
  test('C5 — empty name blocked with inline error, no PATCH sent', async ({ page }) => {
    await openTenantPanel(page, 0);
    await clickEdit(page);

    const nameInput = page.locator('input[placeholder="John Doe"]');
    await nameInput.clear();

    let apiCalled = false;
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/tenants/')) apiCalled = true;
    });

    await clickSave(page);

    await expect(page.locator(`${PANEL_SELECTOR} p.text-red-400`)).toBeVisible({ timeout: 4000 });
    expect(apiCalled).toBe(false);

    // Close
    await page.locator(`${PANEL_SELECTOR} button`).filter({ has: page.locator('svg') }).last().click();
  });

  // ── C6 ─────────────────────────────────────────────────────────────────────
  test('C6 — update name + phone + email in one save', async ({ page }) => {
    await openTenantPanel(page, 0);

    const originalName = (await page.locator(`${PANEL_SELECTOR} h2`).first().textContent())?.trim() ?? '';
    await clickEdit(page);

    const nameInput = page.locator('input[placeholder="John Doe"]');
    const phoneInput = page.locator('input[type="tel"]');
    const emailInput = page.locator('input[type="email"]');

    const origPhone = await phoneInput.inputValue();
    const origEmail = await emailInput.inputValue();

    const uniquePhone = '+15145550099';
    const uniqueEmail = 'playwright-test@example.com';

    await nameInput.clear(); await nameInput.fill('C6 Test Name');
    await phoneInput.clear(); await phoneInput.fill(uniquePhone);
    await emailInput.clear(); await emailInput.fill(uniqueEmail);

    let patchBody: Record<string, unknown> = {};
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/tenants/')) {
        try { patchBody = JSON.parse(req.postData() || '{}'); } catch {}
      }
    });

    await clickSave(page);
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });

    // All three fields must have been in the PATCH payload
    expect(patchBody).toHaveProperty('name', 'C6 Test Name');
    expect(patchBody).toHaveProperty('phone', uniquePhone);
    expect(patchBody).toHaveProperty('email', uniqueEmail);

    // ── Revert ──
    await clickEdit(page);
    await page.locator('input[placeholder="John Doe"]').fill(originalName);
    await page.locator('input[type="tel"]').fill(origPhone);
    await page.locator('input[type="email"]').fill(origEmail);
    await clickSave(page);
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });
  });

  // ── C7 ─────────────────────────────────────────────────────────────────────
  test('C7 — editing tenant A does not affect tenant B', async ({ page }) => {
    await navigateTo(page, 'Tenants');
    await page.waitForSelector('[data-tour="tenant-table"] tbody tr', { timeout: 15000 });

    const rows = page.locator('[data-tour="tenant-table"] tbody tr');
    test.skip(await rows.count() < 2, 'Need at least 2 tenants');

    // Record Tenant B's name before edit
    const tenantBNameEl = rows.nth(1).locator('td:first-child .font-medium');
    const tenantBNameBefore = (await tenantBNameEl.textContent())?.trim() ?? '';

    // Edit Tenant A
    await rows.nth(0).click();
    await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });
    const originalNameA = (await page.locator(`${PANEL_SELECTOR} h2`).first().textContent())?.trim() ?? '';
    await clickEdit(page);
    await page.locator('input[placeholder="John Doe"]').fill('C7 Edited A');
    await clickSave(page);
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });
    // Close panel
    await page.locator(`${PANEL_SELECTOR} button`).filter({ has: page.locator('svg') }).last().click();
    await expect(page.locator(PANEL_SELECTOR)).not.toBeVisible({ timeout: 5000 });

    // Tenant B's name should be unchanged
    await expect(tenantBNameEl).toHaveText(tenantBNameBefore);

    // ── Revert ──
    await rows.nth(0).click();
    await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });
    await clickEdit(page);
    await page.locator('input[placeholder="John Doe"]').fill(originalNameA);
    await clickSave(page);
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });
  });

  // ── C8 ─────────────────────────────────────────────────────────────────────
  // Requires live phone call to complaint agent — manual only.
  test.skip('C8 — phone change + complaint agent (manual only)', async () => {});
});
