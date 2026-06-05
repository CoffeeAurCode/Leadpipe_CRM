/**
 * Part A — Auto-Delist on Assign
 * Tests that assigning a tenant deactivates the active listing for that unit.
 * Uses direct API calls for assign/unassign since the UI routes to those
 * endpoints are via FlatEditModal (ADD_TENANT / REMOVE_TENANT actions), while
 * listing deactivation is wired to PATCH /flats/{uuid}/assign-tenant.
 * The LeasingTab UI is used to verify the resulting state.
 */

import { test, expect } from '@playwright/test';
import { navigateTo, apiGet, apiPatch, authHeader } from '../helpers/app';

const API_BASE = process.env.BACKEND_URL || 'http://localhost:8000';

type Listing = { uuid: string; flat_uuid: string; flat_number: string; is_active: boolean };
type Tenant = { uuid: string; name: string; phone: string };

test.describe('Part A — Auto-Delist on Assign', () => {

  // ── A1 ─────────────────────────────────────────────────────────────────────
  test('A1 — assigning a tenant deactivates the active listing', async ({ page }) => {
    // 1. Find an active listing so we know its flat_number
    await navigateTo(page, 'Leasing AI');
    await page.waitForSelector('[data-tour="leasing-listings"]', { timeout: 10000 });

    const listings: Listing[] = await apiGet(page, '/leasing/listings');
    const activeListing = listings.find(l => l.is_active);
    test.skip(!activeListing, 'No active listing found — create one in LeasingTab first');

    // Verify it shows as Active in the UI before assigning
    const listingCard = page.locator('[data-tour="leasing-listings"] .bg-card').filter({
      has: page.locator(`text="${activeListing!.flat_number}"`),
    });
    await expect(listingCard).toBeVisible();
    await expect(listingCard.locator('span').filter({ hasText: 'Active' })).toBeVisible();

    // 2. Get an unassigned tenant to use
    const unassigned: Tenant[] = await apiGet(page, '/tenants?unassigned=true');
    test.skip(unassigned.length === 0, 'No unassigned tenants — create one first');

    // 3. Call assign-tenant endpoint (tests the feature under test)
    await apiPatch(page, `/flats/${activeListing!.flat_uuid}/assign-tenant`, {
      tenant_uuid: unassigned[0].uuid,
    });

    // 4. Refresh the Leasing page and confirm the listing is now Inactive
    await navigateTo(page, 'Properties');   // navigate away to force re-fetch
    await navigateTo(page, 'Leasing AI');
    await page.waitForSelector('[data-tour="leasing-listings"]');

    const updatedCard = page.locator('[data-tour="leasing-listings"] .bg-card').filter({
      has: page.locator(`text="${activeListing!.flat_number}"`),
    });
    await expect(updatedCard.locator('span').filter({ hasText: 'Inactive' })).toBeVisible({
      timeout: 8000,
    });

    // ── Teardown: unassign so the next test has a clean state ──
    await apiPatch(page, `/flats/${activeListing!.flat_uuid}/unassign-tenant`, {});
  });

  // ── A2 ─────────────────────────────────────────────────────────────────────
  test('A2 — unassigning does NOT reactivate the listing', async ({ page }) => {
    const listings: Listing[] = await apiGet(page, '/leasing/listings');
    const activeListing = listings.find(l => l.is_active);
    test.skip(!activeListing, 'No active listing — create one first');

    const unassigned: Tenant[] = await apiGet(page, '/tenants?unassigned=true');
    test.skip(unassigned.length === 0, 'No unassigned tenants — create one first');

    // Assign a tenant (deactivates listing)
    await apiPatch(page, `/flats/${activeListing!.flat_uuid}/assign-tenant`, {
      tenant_uuid: unassigned[0].uuid,
    });

    // Unassign the tenant
    await apiPatch(page, `/flats/${activeListing!.flat_uuid}/unassign-tenant`, {});

    // Reload LeasingTab — listing must STILL be Inactive
    await navigateTo(page, 'Leasing AI');
    await page.waitForSelector('[data-tour="leasing-listings"]');

    const card = page.locator('[data-tour="leasing-listings"] .bg-card').filter({
      has: page.locator(`text="${activeListing!.flat_number}"`),
    });
    await expect(card.locator('span').filter({ hasText: 'Inactive' })).toBeVisible({
      timeout: 8000,
    });
  });

  // ── A3 ─────────────────────────────────────────────────────────────────────
  test('A3 — assigning to a unit with no listing succeeds with no error', async ({ page }) => {
    // Find a vacant flat that has NO active listing
    const listings: Listing[] = await apiGet(page, '/leasing/listings');
    const activeListingFlatUuids = new Set(listings.filter(l => l.is_active).map(l => l.flat_uuid));

    const vacantFlats: Array<{ uuid: string; tenant_uuid: string | null }> = await apiGet(page, '/flats?vacant=true');
    const flatWithNoListing = vacantFlats.find(f => !activeListingFlatUuids.has(f.uuid));
    test.skip(!flatWithNoListing, 'Cannot find a vacant flat without an active listing');

    const unassigned: Tenant[] = await apiGet(page, '/tenants?unassigned=true');
    test.skip(unassigned.length === 0, 'No unassigned tenants');

    // Assign — must return 200 with success: true, no exception
    const resp = await page.request.patch(
      `${API_BASE}/flats/${flatWithNoListing!.uuid}/assign-tenant`,
      {
        data: { tenant_uuid: unassigned[0].uuid },
        headers: authHeader(),
      }
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.success).toBe(true);

    // Teardown
    await apiPatch(page, `/flats/${flatWithNoListing!.uuid}/unassign-tenant`, {});
  });

  // ── A4 ─────────────────────────────────────────────────────────────────────
  // A4 tests the CSV import path — skipped in automation (file upload + parse cycle
  // is covered by backend integration tests; manual verification is faster).
  test.skip('A4 — CSV import deactivates listing (manual only)', async () => {});
});
