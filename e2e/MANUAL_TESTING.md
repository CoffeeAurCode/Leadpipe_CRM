# Manual Testing Checklist — Tenant Management MVP

Tests that cannot be automated (live phone calls, file upload flows) plus a structured
walkthrough for verifying the whole product before a release.

---

## How to use this document

Work through each section in order. For each test:
- [ ] Mark the checkbox when passed
- Add a note next to any failure: what you did, what you expected, what happened

**Prerequisite:** Backend running on `:8000`, frontend on `:5173` (or use the hosted URLs).
Log in as the manager account before starting.

---

## Part A — Auto-Delist on Assign

### A4 — CSV Bulk Import deactivates active listings

**What to test:** Uploading a CSV that assigns tenants to units deactivates any active
listing for those units.

**Steps:**
1. Go to **Leasing AI** tab. Note 2–3 units that have an **Active** listing badge.
2. Prepare a CSV with those flat numbers mapped to unassigned tenants.
3. Go to **Tenants** → "Import CSV" button.
4. Upload the CSV and confirm the import succeeds (no error toast).
5. Navigate back to **Leasing AI**.

**Expected:** Each unit you imported now shows an **Inactive** listing badge.

**Notes:**
- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Part B — Edit Property Group & Building

### B6 — Complaint routing still works after renaming a property group

**What to test:** After renaming a property group, VAPI's complaint agent correctly
identifies the property and routes the complaint to the right manager.

**Steps:**
1. Go to **Properties**. Note the name of a property group that has a VAPI complaint
   agent configured (e.g., "Sunrise Estate").
2. Edit the property group name to "Sunrise Estate Renamed".
3. Call the complaint phone number for that property group.
4. Leave a complaint mentioning the building name.
5. After the call ends, go to **Complaints** tab.

**Expected:** A new complaint appears, linked to the correct property group under its
new name. Manager notification is sent (check email/SMS).

**Revert:** Rename the property group back to its original name after testing.

**Notes:**
- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Part C — Tenant Name + Phone Edit

### C8 — Changing a tenant's phone number updates VAPI caller identity

**What to test:** After updating a tenant's phone number, the VAPI caller-identity
check (`/flats/verify-phone`) correctly recognises calls from the new number and
rejects calls from the old number.

**Steps:**
1. Pick any tenant who has an active lease. Note their current phone number (old).
2. In **Tenants** → open TenantProfile → **Edit** → change phone to a new test number
   (e.g., `+15145559999`) → **Save Changes**.
3. Using the new number, call the inbound VAPI number for that tenant's building.
4. The agent should greet you by name and let you raise a complaint.
5. End the call. Verify a call log appears with the correct tenant.
6. Now call from the old number. The agent should either not recognise you or treat you
   as an unknown caller.

**Revert:** Restore the original phone number after testing.

**Notes:**
- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Part D — Full Feature Regression (Manual Spot-check)

These are quick sanity checks that aren't covered by automation.

### D4 — Dashboard loads with correct stats

**Steps:** Log in, land on Dashboard. Verify:
- [ ] Total tenants count is non-zero
- [ ] Total units / occupancy % is displayed
- [ ] Recent activity feed is visible and not empty

**Notes:** _______________________________________________________

### D5 — Rent tab shows correct summaries

**Steps:**
1. Click **Rent** in sidebar.
2. Verify the rent summary table loads (at least one row).
3. Change a filter (e.g., month or building) — table should update.

- [ ] Pass / [ ] Fail — _______________________________________________________

### D6 — Notifications created and visible

**Steps:**
1. Trigger a condition that auto-creates a notification (e.g., mark a rent as overdue,
   or create a new complaint via the voice agent).
2. Go to **Notifications** (bell icon or dedicated view).
3. Verify the notification appears with correct title and timestamp.

- [ ] Pass / [ ] Fail — _______________________________________________________

### D7 — Leasing AI tab: new listing creation

**Steps:**
1. Go to **Leasing AI** → **Add Listing**.
2. Select a vacant unit, set a monthly rent, and save.
3. Verify the listing card appears with **Active** status.
4. Clean up: delete the listing.

- [ ] Pass / [ ] Fail — _______________________________________________________

### D8 — Complaint AI tab: call log visible

**Steps:**
1. Go to **Complaint AI** tab.
2. Verify call logs load (not a blank screen).
3. Click a call log entry — verify the detail view opens with transcript or summary.

- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Voice / VAPI Integration Smoke Tests

These require access to the VAPI-registered phone numbers.

### V1 — Inbound complaint call: full round-trip

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call the inbound number for any property group | Agent answers, asks tenant to identify |
| 2 | State your name and flat number | Agent greets you by name |
| 3 | Describe a complaint | Agent acknowledges and logs it |
| 4 | Hang up | Call log + complaint record appear in app within 60 s |

- [ ] Pass / [ ] Fail — _______________________________________________________

### V2 — VAPI caller-identity check: unknown number

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call the inbound number from a number NOT in the tenant DB | Agent treats caller as unknown |
| 2 | Agent asks for name and flat | Agent verifies (or escalates) without auto-identifying |

- [ ] Pass / [ ] Fail — _______________________________________________________

### V3 — Lease agent: end-of-call report saved

| Step | Action | Expected |
|------|--------|----------|
| 1 | Call the lease agent number | Agent discusses a flat |
| 2 | End call | End-of-call report webhook fires; record saved in `call_logs` |

- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Stripe / Payment Smoke Tests

### P1 — Stripe checkout session is created

**Steps:**
1. Navigate to the rent/payment flow for a tenant.
2. Click "Pay Now" or equivalent.
3. Verify Stripe Checkout loads (test mode).

- [ ] Pass / [ ] Fail — _______________________________________________________

### P2 — Webhook updates rent status

**Steps:**
1. Complete a Stripe test checkout using card `4242 4242 4242 4242`.
2. Check the tenant's rent status in the app.

**Expected:** Status changes to "Paid" within a few seconds.

- [ ] Pass / [ ] Fail — _______________________________________________________

---

## Cross-Browser Spot-check

Run these manually in a non-Chromium browser if you have one available.

| Test | Firefox | Safari / Edge |
|------|---------|---------------|
| Login + sidebar visible | [ ] | [ ] |
| Open tenant profile | [ ] | [ ] |
| Edit tenant name + save | [ ] | [ ] |
| Open property group edit modal | [ ] | [ ] |

---

## Accessibility Quick-check

- [ ] All modal dialogs are reachable by keyboard (Tab / Enter / Escape)
- [ ] Sidebar navigation is keyboard-navigable
- [ ] Error messages in forms are visible at 2× zoom

---

## Sign-off

| Tester | Date | Build / Commit | Overall result |
|--------|------|----------------|----------------|
|        |      |                | Pass / Fail    |
