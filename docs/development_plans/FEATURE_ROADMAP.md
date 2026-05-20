# Feature Roadmap — Tenant Management MVP

**Date:** 2026-04-23  
**Author:** Pranav Raj  
**Scope:** Multi-manager scaling + 5 new features

---

## Overview

This document plans the implementation of the following features:

| # | Feature | Status |
|---|---------|--------|
| 1 | Single Number + Caller Phone Lookup (VAPI multi-manager) | Partially built |
| 2 | Rent Tab | New |
| 3 | AI Voice Agent Stats Tab | New |
| 4 | In-App Notifications + Bell Alerts | New (backend done) |
| 5 | Add Tenant (Tenant Section) + Assign in Properties | New |
| 6 | Image Upload for Properties | Mostly built — gaps below |

---

## Feature 1: Single Number + Caller Phone Lookup

### Current State

The `/flats/identify-caller` endpoint **already exists** in `backend/app/routes/flats.py`. It walks the chain:

```
phone → flat → building → property_group → manager
```

and returns `society_name`, `property_group_id`, `manager_name`, `manager_phone`.

### What Is Missing

The endpoint is built but **not wired into VAPI** as the first tool call. Current VAPI flow still uses `/flats/verify-phone` (which requires the tenant to first say their flat number). The multi-manager pattern requires `identify_caller` to fire *before* anything else.

### Implementation Plan

#### Step 1 — Audit `identify_caller` endpoint

File: `backend/app/routes/flats.py` (lines ~141–250)

- [ ] Confirm the Supabase join query works correctly: `flats → buildings!inner → properties_list!inner`
- [ ] Confirm `tenant_phone` column exists on `flats` table (check migrations)
- [ ] Add phone normalization: strip spaces, handle `+91` prefix vs `91` vs `0` prefix variants
- [ ] Ensure it always returns HTTP 200 (never raises 404/500) — VAPI requirement

```python
# Normalize phone before DB lookup
def normalize_phone(raw: str) -> list[str]:
    digits = re.sub(r"\D", "", raw)
    # Return all plausible variants VAPI might send
    return [digits, digits[-10:], "91" + digits[-10:], "+91" + digits[-10:]]
```

Then query with `.in_("tenant_phone", normalize_phone(phone))`.

#### Step 2 — Update VAPI Assistant System Prompt

In the VAPI dashboard (or your assistant config JSON), update the system prompt:

```
You are a property management voice assistant.

CRITICAL — At the very start of every call, before saying anything else:
1. Call identify_caller() with the caller's phone number.
2. If identified is true: greet them by name, use society_name in your greeting,
   and use property_group_id in ALL subsequent tool calls.
3. If identified is false: ask "Could you please tell me your society name and
   flat number?" then proceed with manual verification.

Never ask for information that identify_caller() already returned.
```

#### Step 3 — Register `identify_caller` as First Tool in VAPI

In the VAPI assistant tool list, add this as tool #1:

```json
{
  "type": "function",
  "function": {
    "name": "identify_caller",
    "description": "Identify the caller by their phone number. Call this first on every call.",
    "parameters": {
      "type": "object",
      "properties": {
        "phone": {
          "type": "string",
          "description": "The caller's phone number as provided by the telephony system"
        }
      },
      "required": ["phone"]
    }
  },
  "server": {
    "url": "https://your-backend.com/flats/identify-caller"
  }
}
```

#### Step 4 — Propagate `property_group_id` to Downstream Tool Calls

All downstream tools (`schedule_appointment`, `file_complaint`, `get_rent_status`) need a `property_group_id` parameter added so the backend knows which manager's data to touch. Update each endpoint to filter by `property_group_id` where relevant.

**Affected endpoints to audit:**
- `POST /appointments/schedule-by-phone` — add `property_group_id` filter
- `POST /appointments/cancel` — verify it scopes to correct manager
- `POST /complaints` (if VAPI creates complaints) — add `property_group_id`

#### Step 5 — Add `tenant_phone` to Flats Table (if not present)

```sql
-- Run in Supabase SQL editor if column doesn't exist
ALTER TABLE flats ADD COLUMN IF NOT EXISTS tenant_phone TEXT;

-- Backfill from tenants table
UPDATE flats f
SET tenant_phone = t.phone
FROM tenants t
WHERE t.flat_uuid = f.uuid::text OR t.id::text = f.tenant_uuid;
```

#### Step 6 — Test

Manual test sequence:
1. Set a real phone number in a flat's `tenant_phone` field
2. Hit `POST /flats/identify-caller` with `{"phone": "+91XXXXXXXXXX"}`
3. Confirm chain resolves: flat → building → property_group → manager
4. Confirm unknown phone returns `{"identified": false}` without error

---

## Feature 2: Rent Tab

### Current State

- `rents` table exists with `flat_uuid`, `monthly_rent`, `effective_from`, `is_active`
- `GET /rents/{flat_uuid}` and `POST /rents/set` endpoints exist in `backend/app/routes/rents.py`
- `rent_status` field on tenants table (text: "On-time", "Upcoming", "Overdue", "At Risk") — manually managed

### What the Rent Tab Should Show

A dedicated tab in the sidebar showing:
- All flats with current monthly rent
- Per-tenant rent status (with color badges)
- Ability to update rent amount inline
- Rent collection summary (counts per status)
- Overdue/at-risk tenant list for quick action

### Implementation Plan

#### Backend

**New endpoint:** `GET /rents/summary` — returns all flats joined with their active rent and tenant info

```python
# backend/app/routes/rents.py
@router.get("/rents/summary")
async def get_rent_summary(db: Client = Depends(get_db)):
    # Join flats + active rents + tenants
    flats = db.table("flats").select(
        "id, uuid, flat_number, tenant_uuid, "
        "tenants!inner(name, phone, rent_status), "
        "rents(monthly_rent, effective_from, is_active)"
    ).execute()
    # Filter rents to is_active=true in post-processing
    ...
```

**New endpoint:** `PATCH /tenants/{uuid}/rent-status` — update rent_status field

```python
@router.patch("/tenants/{tenant_uuid}/rent-status")
async def update_rent_status(tenant_uuid: str, body: RentStatusUpdate, db: Client = Depends(get_db)):
    allowed = {"On-time", "Upcoming", "Overdue", "At Risk"}
    if body.rent_status not in allowed:
        raise HTTPException(400, "Invalid rent_status")
    ...
```

#### Frontend

**New file:** `frontend/src/components/RentTab.jsx`

Layout:
```
┌─────────────────────────────────────────────────────┐
│  Rent Overview                                       │
│  [On-time: 12] [Upcoming: 3] [Overdue: 5] [At Risk: 2] │
├─────────────────────────────────────────────────────┤
│  Search: [__________]  Filter: [All ▼]               │
├──────┬──────────┬──────────┬────────┬──────────────┤
│ Flat │ Tenant   │ Rent/mo  │ Status │ Actions       │
├──────┼──────────┼──────────┼────────┼──────────────┤
│ A101 │ Raj K.   │ ₹12,000  │ ●On-time│ [Edit] [Mark]│
│ B204 │ Priya S. │ ₹15,000  │ ●Overdue│ [Edit] [Mark]│
└──────┴──────────┴──────────┴────────┴──────────────┘
```

**Wire into Sidebar:** Add "Rent" entry to `Sidebar.jsx` nav list with `IndianRupee` icon from Lucide.

**Add to `apiService.js`:**
```js
getRentSummary: () => apiFetch('/rents/summary'),
updateRentStatus: (uuid, status) => apiFetch(`/tenants/${uuid}/rent-status`, { method: 'PATCH', body: { rent_status: status } }),
setRent: (flat_uuid, monthly_rent, effective_from) => apiFetch('/rents/set', { method: 'POST', body: { flat_uuid, monthly_rent, effective_from } }),
```

---

## Feature 3: AI Voice Agent Stats Tab

### Current State

- `call_logs` table exists with: `call_id`, `phone_number`, `transcript`, `raw_event_type`, `complaint_status`, `created_at`, `complaint_id`
- `backend/app/routes/call_logs.py` exists (check current endpoints)
- Voice webhook handled in `backend/app/routes/voice.py`

### What the Stats Tab Should Show

```
┌───────────────────────────────────────────────────┐
│  Voice Agent Stats          Last 30 days ▼         │
├─────────────┬─────────────┬─────────────┬─────────┤
│ Total Calls │ Resolved    │ Escalated   │ Avg Dur │
│     48      │    31 (65%) │    9 (19%)  │  3m 42s │
├───────────────────────────────────────────────────┤
│  Call Volume (bar chart by day)                    │
│  ████▁▁██▁▁███▁▁▁███▁▁██▁▁▁████                   │
├───────────────────────────────────────────────────┤
│  Recent Calls                                     │
│  +919XXXXXXXX | Complaint filed | 2hr ago         │
│  +918XXXXXXXX | Appointment set | 5hr ago         │
└───────────────────────────────────────────────────┘
```

### Implementation Plan

#### Backend

**New endpoint:** `GET /call-logs/stats?days=30`

```python
# backend/app/routes/call_logs.py
@router.get("/call-logs/stats")
async def get_call_stats(days: int = 30, db: Client = Depends(get_db)):
    since = (datetime.now(IST) - timedelta(days=days)).isoformat()
    logs = db.table("call_logs").select("*").gte("created_at", since).order("created_at", desc=True).execute()

    total = len(logs.data)
    resolved = sum(1 for l in logs.data if l.get("complaint_status") in ("resolved", "closed"))
    escalated = sum(1 for l in logs.data if l.get("complaint_status") == "escalated")

    # Group by date for chart
    by_date = {}
    for log in logs.data:
        date = log["created_at"][:10]
        by_date[date] = by_date.get(date, 0) + 1

    return {
        "total": total,
        "resolved": resolved,
        "escalated": escalated,
        "by_date": by_date,
        "recent": logs.data[:20]
    }
```

#### Frontend

**New file:** `frontend/src/components/VoiceStatsTab.jsx`

- Stat cards at top (Total, Resolved, Escalated, Avg Duration)
- Bar chart — use a minimal inline SVG bar chart or the `recharts` library if already installed
- Recent call log list with transcript preview on click
- Date range filter: Last 7d / 30d / 90d

**Wire into Sidebar:** Add "Voice Stats" entry with `PhoneCall` or `BarChart2` icon from Lucide.

**Add to `apiService.js`:**
```js
getCallStats: (days = 30) => apiFetch(`/call-logs/stats?days=${days}`),
getCallLogs: () => apiFetch('/call-logs'),
```

---

## Feature 4: In-App Notifications + Bell Alerts

### Current State

- **Backend:** Full SMS/email notification service in `backend/app/services/notifications.py` (Twilio + SendGrid) — fires on appointment events
- **Frontend:** TopBar.jsx has NO notification bell currently. The user recalls a bell — check if it was recently added; if not, add it.

### Plan

Create an in-app notification feed that mirrors the external SMS/email events. When a notification is sent externally, also write a record to a new `notifications` table and display it in the bell.

#### Step 1 — Create `notifications` Table

```sql
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT NOT NULL,           -- 'appointment', 'complaint', 'rent', 'system'
  entity_id UUID,               -- reference to appointment/complaint/etc.
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_notifications_manager ON notifications(manager_id, created_at DESC);
```

#### Step 2 — Write Notifications in Backend

In `backend/app/services/notifications.py`, after sending SMS/email, write to DB:

```python
async def _save_notification(db: Client, manager_id: str, title: str, body: str, type: str, entity_id: str = None):
    db.table("notifications").insert({
        "manager_id": manager_id,
        "title": title,
        "body": body,
        "type": type,
        "entity_id": entity_id,
        "is_read": False
    }).execute()
```

Call `_save_notification()` at the end of each `notify_manager_*` function.

**New endpoints in a new file `backend/app/routes/notifications.py`:**

```python
GET  /notifications           # list unread + recent for current manager
PATCH /notifications/{id}/read  # mark one as read
POST /notifications/read-all    # mark all as read
```

#### Step 3 — Add Bell to TopBar

In `frontend/src/components/TopBar.jsx`:

```jsx
// Add bell icon with badge
<button onClick={() => setNotifOpen(true)} className="relative p-2 ...">
  <Bell size={20} />
  {unreadCount > 0 && (
    <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
      {unreadCount > 9 ? '9+' : unreadCount}
    </span>
  )}
</button>
```

#### Step 4 — Notification Dropdown Panel

A slide-in panel (right side, below TopBar) listing recent notifications:

```
🔔 Notifications                    [Mark all read]
─────────────────────────────────────────────────
● Appointment scheduled — Flat A204   5 min ago
● New complaint — B/W leak in B101    2 hr ago
○ Appointment cancelled — C301        Yesterday
─────────────────────────────────────────────────
[See all]
```

**Polling:** Poll `GET /notifications` every 30 seconds while the tab is active (use `setInterval` + `visibilitychange` listener). No WebSocket needed for MVP.

**New file:** `frontend/src/components/NotificationPanel.jsx`

**Add to `apiService.js`:**
```js
getNotifications: () => apiFetch('/notifications'),
markNotificationRead: (id) => apiFetch(`/notifications/${id}/read`, { method: 'PATCH' }),
markAllRead: () => apiFetch('/notifications/read-all', { method: 'POST' }),
```

---

## Feature 5: Add Tenant + Assign Tenant to Flat

### Current State

- `POST /tenants` exists but no frontend modal to call it
- `TenantManagement.jsx` has no "Add Tenant" button
- `PropertiesPage.jsx` shows flat detail but no assignment UI
- Vacancy tracking: `flat.tenant_uuid` (FK to tenants) and `tenant.flat_uuid` (FK to flats)

### 5a — Add Tenant Modal (Tenant Section)

#### Frontend

**New file:** `frontend/src/components/AddTenantModal.jsx`

Fields:
- Tenant Name (required)
- Phone Number (required, 10-digit)
- Flat Assignment — dropdown of vacant flats fetched from `GET /flats?vacant=true`
- Lease Start Date / Lease End Date (date pickers)
- Monthly Rent (auto-fills if flat already has an active rent)
- Rent Status (dropdown: On-time / Upcoming / Overdue / At Risk)
- Manager Notes (textarea, optional)

**In `TenantManagement.jsx`:** Add an "Add Tenant" button (top-right, next to Refresh) that opens `AddTenantModal`.

**In `apiService.js`:**
```js
createTenant: (data) => apiFetch('/tenants', { method: 'POST', body: data }),
getVacantFlats: () => apiFetch('/flats?vacant=true'),
```

#### Backend

**New query param for `GET /flats`:** `?vacant=true` — returns flats where `tenant_uuid IS NULL`

```python
# backend/app/routes/flats.py
@router.get("/flats")
async def get_flats(vacant: bool = False, db: Client = Depends(get_db)):
    query = db.table("flats").select("*")
    if vacant:
        query = query.is_("tenant_uuid", None)
    return query.execute().data
```

**`POST /tenants` update:** When creating a tenant with a `flat_uuid`, also update `flats.tenant_uuid` bidirectionally:

```python
# After inserting tenant, link flat
if body.flat_uuid:
    db.table("flats").update({"tenant_uuid": new_tenant["uuid"]}).eq("uuid", body.flat_uuid).execute()
```

### 5b — Assign Tenant in Properties Section

#### Frontend

In `PropertiesPage.jsx`, inside the Flat detail modal/panel (currently shows flat info):

- If flat has no tenant: show **"Assign Tenant"** button
- If flat has a tenant: show tenant name + **"Unassign"** button

**Assign Tenant Flow:**
1. Click "Assign Tenant" → opens a small modal
2. Shows two tabs: **"Existing Tenant"** (dropdown of unassigned tenants) | **"New Tenant"** (inline mini form)
3. On confirm: calls `PATCH /flats/{id}/assign-tenant`

**New endpoint:** `PATCH /flats/{flat_id}/assign-tenant`

```python
@router.patch("/flats/{flat_id}/assign-tenant")
async def assign_tenant(flat_id: str, body: AssignTenantRequest, db: Client = Depends(get_db)):
    # body: { tenant_uuid: str }
    # 1. Update flat.tenant_uuid
    db.table("flats").update({"tenant_uuid": body.tenant_uuid}).eq("id", flat_id).execute()
    # 2. Update tenant.flat_uuid
    db.table("tenants").update({"flat_uuid": body.flat_uuid}).eq("uuid", body.tenant_uuid).execute()
```

**New endpoint:** `PATCH /flats/{flat_id}/unassign-tenant`

```python
@router.patch("/flats/{flat_id}/unassign-tenant")
async def unassign_tenant(flat_id: str, db: Client = Depends(get_db)):
    flat = db.table("flats").select("tenant_uuid").eq("id", flat_id).single().execute()
    if flat.data and flat.data["tenant_uuid"]:
        db.table("tenants").update({"flat_uuid": None}).eq("uuid", flat.data["tenant_uuid"]).execute()
    db.table("flats").update({"tenant_uuid": None}).eq("id", flat_id).execute()
```

**Add to `apiService.js`:**
```js
assignTenant: (flatId, tenantUuid) => apiFetch(`/flats/${flatId}/assign-tenant`, { method: 'PATCH', body: { tenant_uuid: tenantUuid } }),
unassignTenant: (flatId) => apiFetch(`/flats/${flatId}/unassign-tenant`, { method: 'PATCH' }),
getUnassignedTenants: () => apiFetch('/tenants?unassigned=true'),
```

---

## Feature 6: Image Upload for Properties

### Current State

| Entity | Image Field | Upload Wired? |
|--------|-------------|--------------|
| Flat/Unit | `image_url` | Yes — `ImageUploadField.jsx` used in `AddPropertyModal` |
| Building | `cover_image_url` | Yes — `ImageUploadField.jsx` used in `AddBuildingModal` |
| Property Group | ??? | **Check `AddPropertyGroupModal` — likely missing** |

The upload infrastructure is complete:
- `POST /upload/image` → Supabase Storage `Property Pics` bucket → returns public URL
- `ImageUploadField.jsx` component handles drag-drop, preview, and upload

### What Needs Checking

1. **Does `properties_list` table have an image column?** Check Supabase schema or migrations. If not, add:

```sql
ALTER TABLE properties_list ADD COLUMN IF NOT EXISTS cover_image_url TEXT;
```

2. **Does `AddPropertyGroupModal.jsx` use `ImageUploadField`?** If not:
   - Add `ImageUploadField` to the form
   - Add `cover_image_url` to the POST body
   - Update `POST /property-groups` backend to accept and store it

3. **Does `PropertiesPage.jsx` show the property group image?** If not, display it as the card header/background.

### Steps

- [ ] Check `properties_list` table for image column — add via migration if missing
- [ ] Check `AddPropertyGroupModal.jsx` — add `ImageUploadField` if missing
- [ ] Confirm `PropertiesPage.jsx` renders property group image in the card
- [ ] Confirm Buildings show `cover_image_url` in the building card (not just in modals)
- [ ] No new infrastructure needed — `upload.py` and `ImageUploadField.jsx` are reusable as-is

---

## Implementation Order (Suggested)

| Priority | Feature | Effort | Why |
|----------|---------|--------|-----|
| 1 | Add Tenant + Assign (Feature 5) | Medium | Core data entry gap |
| 2 | Image Upload gaps (Feature 6) | Low | Mostly already built |
| 3 | Rent Tab (Feature 2) | Medium | High business value |
| 4 | Notifications Bell (Feature 4) | Medium | Needs new DB table |
| 5 | VAPI Multi-Manager (Feature 1) | Low-Medium | Backend mostly done |
| 6 | Voice Agent Stats (Feature 3) | Medium | Nice-to-have analytics |

---

## Files To Create (Net New)

| File | Purpose |
|------|---------|
| `frontend/src/components/RentTab.jsx` | Rent overview tab |
| `frontend/src/components/VoiceStatsTab.jsx` | Voice agent analytics |
| `frontend/src/components/NotificationPanel.jsx` | Bell dropdown |
| `frontend/src/components/AddTenantModal.jsx` | Add tenant form |
| `frontend/src/components/AssignTenantModal.jsx` | Assign to flat |
| `backend/app/routes/notifications.py` | Notification CRUD API |

## Files To Modify

| File | Change |
|------|--------|
| `backend/app/routes/flats.py` | Phone normalization, `?vacant=true`, assign/unassign endpoints |
| `backend/app/routes/tenants.py` | `?unassigned=true` filter, bidirectional flat link on create |
| `backend/app/routes/rents.py` | Add `GET /rents/summary` |
| `backend/app/routes/call_logs.py` | Add `GET /call-logs/stats` |
| `backend/app/services/notifications.py` | Write to DB after SMS/email |
| `backend/app/main.py` | Register notifications router |
| `frontend/src/components/TopBar.jsx` | Add bell icon + unread badge |
| `frontend/src/components/TenantManagement.jsx` | Add "Add Tenant" button |
| `frontend/src/components/PropertiesPage.jsx` | Assign/Unassign tenant UI |
| `frontend/src/components/Sidebar.jsx` | Add Rent + Voice Stats nav items |
| `frontend/src/services/apiService.js` | All new API methods |

## DB Migrations To Run

```sql
-- 1. Add notifications table
CREATE TABLE notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT NOT NULL,
  entity_id UUID,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_notifications_manager ON notifications(manager_id, created_at DESC);

-- 2. Add image to property groups (if missing)
ALTER TABLE properties_list ADD COLUMN IF NOT EXISTS cover_image_url TEXT;

-- 3. Add tenant_phone to flats (if missing)
ALTER TABLE flats ADD COLUMN IF NOT EXISTS tenant_phone TEXT;
```
