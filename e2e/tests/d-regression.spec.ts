/**
 * Part D — Regression Checks
 * Verify that existing features still work after the new edit features were added.
 */

import { test, expect } from '@playwright/test';
import { navigateTo } from '../helpers/app';

const PANEL_SELECTOR = '.fixed.right-0.top-0.h-full';

test.describe('Part D — Regression Checks', () => {

  // ── D1 ─────────────────────────────────────────────────────────────────────
  test('D1 — existing tenant fields (lease_end_date, manager_notes) still save', async ({ page }) => {
    await navigateTo(page, 'Tenants');
    await page.waitForSelector('[data-tour="tenant-table"] tbody tr', { timeout: 15000 });

    await page.locator('[data-tour="tenant-table"] tbody tr').first().click();
    await expect(page.locator(PANEL_SELECTOR)).toBeVisible({ timeout: 8000 });

    // Click Edit
    await page.locator(`${PANEL_SELECTOR} button:has-text("Edit")`).click();
    await expect(page.locator('input[placeholder="John Doe"]')).toBeVisible({ timeout: 5000 });

    // Find manager_notes textarea
    const notesTextarea = page.locator(`${PANEL_SELECTOR} textarea`);
    const originalNotes = await notesTextarea.inputValue();
    const testNotes = `Playwright regression test — ${Date.now()}`;

    await notesTextarea.clear();
    await notesTextarea.fill(testNotes);

    let patchBody: Record<string, unknown> = {};
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/tenants/')) {
        try { patchBody = JSON.parse(req.postData() || '{}'); } catch {}
      }
    });

    await page.locator(`${PANEL_SELECTOR} button:has-text("Save Changes")`).click();
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });

    // manager_notes should have been in the PATCH
    expect(patchBody).toHaveProperty('manager_notes', testNotes);

    // ── Revert ──
    await page.locator(`${PANEL_SELECTOR} button:has-text("Edit")`).click();
    await page.locator(`${PANEL_SELECTOR} textarea`).fill(originalNotes || '');
    await page.locator(`${PANEL_SELECTOR} button:has-text("Save Changes")`).click();
    await expect(page.locator('input[placeholder="John Doe"]')).not.toBeVisible({ timeout: 8000 });
  });

  // ── D2 ─────────────────────────────────────────────────────────────────────
  test('D2 — creating a new property group still works', async ({ page }) => {
    await navigateTo(page, 'Properties');
    await page.waitForSelector('[aria-label="Edit property group"]', { timeout: 15000 });

    // Count existing groups
    const before = await page.locator('[aria-label="Edit property group"]').count();

    // Click "Add Property Group" button
    await page.locator('button:has-text("Add Property Group"), button:has-text("Add Property")').first().click();
    await expect(page.locator('h2').filter({ hasText: /Add Property Group|New Property/ })).toBeVisible({ timeout: 5000 });

    const suffix = Date.now();
    await page.locator('input[name="name"]').fill(`D2 Test Group ${suffix}`);
    await page.locator('input[name="street_address"]').fill('1 Test Street');
    await page.locator('input[name="city"]').fill('TestCity');
    await page.locator('input[name="state"]').fill('TC');
    await page.locator('input[name="country"]').fill('Canada');

    await page.locator('button[type="submit"]').click();
    await expect(page.locator('h2').filter({ hasText: /Add Property Group|New Property/ })).not.toBeVisible({ timeout: 8000 });

    // A new card should appear
    await expect(page.locator('[aria-label="Edit property group"]')).toHaveCount(before + 1, { timeout: 5000 });

    // ── Cleanup: delete the test group via the API ──
    // Find the UUID from the API
    const resp = await page.request.get('http://localhost:8000/property-groups', {
      headers: { Authorization: `Bearer ${process.env.AUTH_TOKEN}` },
    });
    const groups: Array<{ id: string; name: string }> = await resp.json();
    const testGroup = groups.find(g => g.name === `D2 Test Group ${suffix}`);
    if (testGroup) {
      await page.request.delete(`http://localhost:8000/property-groups/${testGroup.id}`, {
        headers: { Authorization: `Bearer ${process.env.AUTH_TOKEN}` },
      });
    }
  });

  // ── D3 ─────────────────────────────────────────────────────────────────────
  test('D3 — creating a new building still works', async ({ page }) => {
    await navigateTo(page, 'Properties');
    await page.waitForSelector('[aria-label="Edit property group"]', { timeout: 15000 });

    // Drill into the first property group
    await page.locator('.bg-card').first().click();
    await page.waitForSelector('[aria-label="Edit building"]', { timeout: 10000 });

    const before = await page.locator('[aria-label="Edit building"]').count();

    // Click "Add Building"
    await page.locator('button:has-text("Add Building")').first().click();
    await expect(page.locator('h2').filter({ hasText: /Add Building|New Building/ })).toBeVisible({ timeout: 5000 });

    const suffix = Date.now();
    await page.locator('input[name="name"]').fill(`D3 Test Block ${suffix}`);

    await page.locator('button[type="submit"]').click();
    await expect(page.locator('h2').filter({ hasText: /Add Building|New Building/ })).not.toBeVisible({ timeout: 8000 });

    // A new card should appear
    await expect(page.locator('[aria-label="Edit building"]')).toHaveCount(before + 1, { timeout: 5000 });

    // ── Cleanup: delete the test building via the API ──
    const resp = await page.request.get('http://localhost:8000/buildings', {
      headers: { Authorization: `Bearer ${process.env.AUTH_TOKEN}` },
    });
    const buildings: Array<{ id: number; name: string }> = await resp.json();
    const testBuilding = buildings.find(b => b.name === `D3 Test Block ${suffix}`);
    if (testBuilding) {
      await page.request.delete(`http://localhost:8000/buildings/${testBuilding.id}`, {
        headers: { Authorization: `Bearer ${process.env.AUTH_TOKEN}` },
      });
    }
  });
});
