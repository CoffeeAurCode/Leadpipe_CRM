/**
 * Part B — Edit Property Group & Building
 * All tests use the UI exclusively.
 */

import { test, expect } from '@playwright/test';
import { navigateTo, openPropertyGroupEditModal, openBuildingEditModal } from '../helpers/app';

const ORIGINAL_NAME = 'Sunrise Estate';
const EDITED_NAME   = 'Sunrise Estate (Edited)';
const BUILDING_NAME = 'Block A';
const EDITED_BUILDING = 'Block A (Edited)';

test.describe('Part B — Edit Property Group & Building', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await navigateTo(page, 'Properties');
    // Wait for property group cards to load
    await page.waitForSelector('[aria-label="Edit property group"]', { timeout: 15000 });
  });

  // ── B1 ─────────────────────────────────────────────────────────────────────
  test('B1 — edit property group name and verify UI updates', async ({ page }) => {
    // Grab the first property group name from the page
    const firstCard = page.locator('.bg-card h3').first();
    const originalName = (await firstCard.textContent())?.trim() ?? '';
    test.skip(!originalName, 'No property group cards visible');

    await openPropertyGroupEditModal(page, originalName);

    const nameInput = page.locator('input[name="name"]');
    await nameInput.clear();
    await nameInput.fill(`${originalName} (Edited)`);

    await page.locator('button[type="submit"]:has-text("Save Changes")').click();

    // Modal should close
    await expect(page.locator('h2:has-text("Edit Property Group")')).not.toBeVisible({ timeout: 8000 });

    // Card should now show the new name
    await expect(page.locator(`h3:has-text("${originalName} (Edited)")`).first()).toBeVisible();

    // ── Revert ──
    await openPropertyGroupEditModal(page, `${originalName} (Edited)`);
    const revertInput = page.locator('input[name="name"]');
    await revertInput.clear();
    await revertInput.fill(originalName);
    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Property Group")')).not.toBeVisible({ timeout: 8000 });
  });

  // ── B2 ─────────────────────────────────────────────────────────────────────
  test('B2 — edit property group address fields', async ({ page }) => {
    const firstCard = page.locator('.bg-card h3').first();
    const groupName = (await firstCard.textContent())?.trim() ?? '';
    test.skip(!groupName, 'No property group cards visible');

    await openPropertyGroupEditModal(page, groupName);

    // Remember original values for revert
    const cityInput = page.locator('input[name="city"]');
    const stateInput = page.locator('input[name="state"]');
    const originalCity = await cityInput.inputValue();
    const originalState = await stateInput.inputValue();

    await cityInput.clear();
    await cityInput.fill('Vancouver');
    await stateInput.clear();
    await stateInput.fill('BC');

    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Property Group")')).not.toBeVisible({ timeout: 8000 });

    // Address line on the card should contain "Vancouver"
    await expect(page.locator('.bg-card').filter({ has: page.locator(`h3:has-text("${groupName}")`) })
      .locator('p.text-muted-foreground')).toContainText('Vancouver', { timeout: 5000 });

    // ── Revert ──
    await openPropertyGroupEditModal(page, groupName);
    await page.locator('input[name="city"]').fill(originalCity || 'Toronto');
    await page.locator('input[name="state"]').fill(originalState || 'Ontario');
    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Property Group")')).not.toBeVisible({ timeout: 8000 });
  });

  // ── B3 ─────────────────────────────────────────────────────────────────────
  test('B3 — empty name is blocked with inline error (no API call)', async ({ page }) => {
    const firstCard = page.locator('.bg-card h3').first();
    const groupName = (await firstCard.textContent())?.trim() ?? '';
    test.skip(!groupName, 'No property group cards visible');

    await openPropertyGroupEditModal(page, groupName);

    // Clear name and attempt to save
    const nameInput = page.locator('input[name="name"]');
    await nameInput.clear();

    let apiCalled = false;
    page.on('request', req => {
      if (req.method() === 'PATCH' && req.url().includes('/property-groups/')) apiCalled = true;
    });

    await page.locator('button[type="submit"]:has-text("Save Changes")').click();

    // Inline error should appear, modal should stay open
    await expect(page.locator('.text-red-500').first()).toBeVisible({ timeout: 3000 });
    expect(apiCalled).toBe(false);

    // Close modal without saving
    await page.locator('button').filter({ has: page.locator('svg') }).last().click(); // X button
    await expect(page.locator('h2:has-text("Edit Property Group")')).not.toBeVisible({ timeout: 5000 });
  });

  // ── B4 ─────────────────────────────────────────────────────────────────────
  test('B4 — edit building name', async ({ page }) => {
    // Drill into the first property group to see buildings
    await page.locator('.bg-card').first().click();

    // Wait for building cards to appear
    await page.waitForSelector('[aria-label="Edit building"]', { timeout: 10000 });

    const firstBuildingCard = page.locator('.bg-card h3').first();
    const buildingName = (await firstBuildingCard.textContent())?.trim() ?? '';
    test.skip(!buildingName, 'No building cards visible');

    await openBuildingEditModal(page, buildingName);

    const nameInput = page.locator('input[name="name"]');
    await nameInput.clear();
    await nameInput.fill(`${buildingName} (Edited)`);

    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Building")')).not.toBeVisible({ timeout: 8000 });

    await expect(page.locator(`h3:has-text("${buildingName} (Edited)")`).first()).toBeVisible();

    // ── Revert ──
    await openBuildingEditModal(page, `${buildingName} (Edited)`);
    await page.locator('input[name="name"]').fill(buildingName);
    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Building")')).not.toBeVisible({ timeout: 8000 });
  });

  // ── B5 ─────────────────────────────────────────────────────────────────────
  test('B5 — editing one building does not affect other buildings', async ({ page }) => {
    // Drill into property group
    await page.locator('.bg-card').first().click();
    await page.waitForSelector('[aria-label="Edit building"]', { timeout: 10000 });

    const buildingHeadings = page.locator('.bg-card h3');
    const count = await buildingHeadings.count();
    test.skip(count < 2, 'Need at least 2 buildings to verify isolation');

    // Capture all names before edit
    const namesBefore: string[] = [];
    for (let i = 0; i < count; i++) {
      namesBefore.push((await buildingHeadings.nth(i).textContent())?.trim() ?? '');
    }

    // Edit only the first building
    const target = namesBefore[0];
    await openBuildingEditModal(page, target);
    await page.locator('input[name="name"]').fill(`${target} Temp`);
    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Building")')).not.toBeVisible({ timeout: 8000 });

    // All other building names must be unchanged
    for (let i = 1; i < count; i++) {
      await expect(page.locator(`h3:has-text("${namesBefore[i]}")`)).toBeVisible();
    }

    // Revert
    await openBuildingEditModal(page, `${target} Temp`);
    await page.locator('input[name="name"]').fill(target);
    await page.locator('button[type="submit"]:has-text("Save Changes")').click();
    await expect(page.locator('h2:has-text("Edit Building")')).not.toBeVisible({ timeout: 8000 });
  });

  // ── B6 ─────────────────────────────────────────────────────────────────────
  // Requires a live phone call to the complaint agent — manual only.
  test.skip('B6 — complaint routing after rename (manual only)', async () => {});

  // ── B7 ─────────────────────────────────────────────────────────────────────
  test('B7 — unit/flat edit still works (regression)', async ({ page }) => {
    // Drill into property group → building → unit
    await page.locator('.bg-card').first().click(); // property group
    await page.waitForSelector('[aria-label="Edit building"]', { timeout: 10000 });
    await page.locator('.bg-card').first().click(); // building → units

    // Wait for unit cards
    await page.waitForSelector('p:has-text("Unit #")', { timeout: 10000 });

    // Open FlatDetailModal for first unit
    await page.locator('.bg-card').first().click();

    // Wait for FlatDetailModal
    await expect(page.locator('h2:has-text("Unit #")')).toBeVisible({ timeout: 8000 });

    // Click Edit (pencil icon at top-right of modal)
    await page.locator('button[title="Edit Flat"]').click();

    // FlatEditModal opens
    await expect(page.locator('h2').filter({ hasText: /Edit Unit/ })).toBeVisible({ timeout: 5000 });

    // Ensure we're on details tab and save (no change needed — just verify it doesn't crash)
    await page.locator('button:has-text("Details")').click();

    // The floor input — just read its value and save to confirm no regression
    await page.locator('button:has-text("Save Changes"), button:has-text("Save")').first().click();

    // Modal should close without error
    await expect(page.locator('h2').filter({ hasText: /Edit Unit/ })).not.toBeVisible({ timeout: 8000 });
  });

  // ── B8 ─────────────────────────────────────────────────────────────────────
  test('B8 — listing edit still works (regression)', async ({ page }) => {
    await navigateTo(page, 'Leasing AI');
    await page.waitForSelector('[data-tour="leasing-listings"]');

    // Check there's at least one listing
    const editButtons = page.locator('[data-tour="leasing-listings"] button:has-text("Edit")');
    const count = await editButtons.count();
    test.skip(count === 0, 'No listings to edit — create one first');

    await editButtons.first().click();

    // AddListingModal opens in edit mode
    await expect(page.locator('h2').filter({ hasText: /Edit Listing|Add Listing/ })).toBeVisible({ timeout: 5000 });

    // Change rent field slightly and save
    const rentInput = page.locator('input[name="monthly_rent"], input[placeholder*="rent"], input[type="number"]').first();
    const current = await rentInput.inputValue();
    const newRent = String(parseInt(current || '20000') + 100);
    await rentInput.clear();
    await rentInput.fill(newRent);

    await page.locator('button[type="submit"]:has-text("Save"), button[type="submit"]:has-text("Update")').first().click();

    // Modal closes
    await expect(page.locator('h2').filter({ hasText: /Edit Listing|Add Listing/ })).not.toBeVisible({ timeout: 8000 });

    // Updated rent appears somewhere in the listings section
    await expect(page.locator('[data-tour="leasing-listings"]')).toContainText(newRent.slice(0, 3));
  });
});
