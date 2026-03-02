# Bug Fixes & Refactoring Prompt

You are tasked with fixing two specific front-end issues in the Tenant Management MVP. The goal is to correct these bugs while maintaining zero regressions, adhering to existing UI/UX patterns, and keeping the codebase clean.

## Issue 1: Appointment Status Full-Page Refresh

**Problem:** 
Currently, when a user changes the status of a scheduled visit (an appointment) from the UI, the update is successful, but it triggers a full page refresh. This is an annoying UX, unlike changing the status of a complaint, which happens smoothly in the background.

**Required Fix:**
- Identify where the appointment status update API is called (likely in `AppointmentDetailModal.jsx` or the component housing it).
- Ensure the API call uses asynchronous fetch/axios without triggering any default form submissions or window reloads.
- The UI should show the "updating..." intermediate state (keep this, it's good UX) and then optimistically update the state locally upon success, exactly mirroring how complaint status updates are handled.
- **Goal:** Get rid of the full-page refresh completely while keeping the local status update smooth.

---

## Issue 2: Settings Page Orphaned Units & Navigation Bar

**Problem:**
On the Settings page, the current dropdown for selecting units is listing all units indiscriminately, including orphaned units that are not assigned to any property or building. Furthermore, the selection UI is just basic dropdowns rather than mirroring the primary app navigation experience.

**Required Fix:**
- Refactor the hierarchy selector on the Settings page to use a navigation bar style, exactly mirroring the hierarchical navigation bar used on the main Property Management page.
- Apply the exact same filtering rules used in the Property Management module so that **orphaned units are strictly excluded**. Units must only be selectable if they correctly belong to the currently selected Property and/or Building.
- Ensure the selected scope (Property -> Building -> Unit) correctly cascades the context for the settings being edited.

## General Guidelines
- Ensure all React state updates are handled immutably.
- Check that the fix for Issue 1 does not break modal closure or reopening logic.
- For Issue 2, trace how the Property Page fetches and filters its hierarchy (likely via specific API responses or frontend mapping) and reuse those exact same functions or logic on the Settings page.
