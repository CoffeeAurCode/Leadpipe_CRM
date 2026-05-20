# Implementation Log — Feature Roadmap Execution

**Date:** 2026-04-23  
**Session:** Claude Code (Sonnet 4.6)  
**Based on:** FEATURE_ROADMAP.md

---

## DB Migrations Required (run in Supabase SQL editor)

```sql
-- 1. Notifications table (Feature 4)
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT NOT NULL,  -- 'appointment' | 'complaint' | 'rent' | 'system'
  entity_id UUID,
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_notifications_manager ON notifications(manager_id, created_at DESC);

-- 2. Add image to property groups if missing (Feature 6 — likely already exists)
ALTER TABLE properties_list ADD COLUMN IF NOT EXISTS cover_image_url TEXT;

-- 3. Add tenant_phone to flats if missing (Feature 1 — VAPI multi-manager)
ALTER TABLE flats ADD COLUMN IF NOT EXISTS tenant_phone TEXT;
```

---

## Files Created (New)

| File | Purpose | Feature |
|------|---------|---------|
| `backend/app/routes/notifications.py` | `GET /notifications`, `PATCH /notifications/{id}/read`, `POST /notifications/read-all`, `POST /notifications` | F4 |
| `frontend/src/components/AddTenantModal.jsx` | Full add-tenant form with flat assignment, lease dates, rent | F5 |
| `frontend/src/components/AssignTenantModal.jsx` | Assign existing or new tenant to a specific flat | F5 |
| `frontend/src/components/RentTab.jsx` | Rent overview: summary cards, table, inline rent edit, status change | F2 |
| `frontend/src/components/VoiceStatsTab.jsx` | Voice agent stats: call counts, SVG bar chart, recent calls with transcript | F3 |
| `frontend/src/components/NotificationPanel.jsx` | Bell icon + dropdown panel, 30s polling, mark-read | F4 |

---

## Files Modified

### Backend

#### `backend/app/routes/flats.py`
- Added `vacant: Optional[bool]` query param to `GET /flats` — filters `tenant_uuid IS NULL`
- Added `PATCH /flats/{flat_uuid}/assign-tenant` — assigns existing tenant to flat (bidirectional)
- Added `PATCH /flats/{flat_uuid}/unassign-tenant` — removes tenant from flat (bidirectional)
- Added `AssignTenantRequest` Pydantic model

#### `backend/app/routes/tenants.py`
- Added `unassigned: Optional[bool]` query param to `GET /tenants` — filters tenants with no flat
- Updated `POST /tenants` (create_tenant) to bidirectionally link flat: after insert, updates `flats.tenant_uuid` and `flats.occupied = True`
- Added `PATCH /tenants/{tenant_uuid}/rent-status` — updates only rent_status field (validates allowed values)
- Added `RentStatusUpdate` Pydantic model

#### `backend/app/routes/rents.py`
- Added `GET /rents/summary` — returns per-status counts + all tenant+rent rows joined in Python. Placed **before** `/{flat_uuid}` to avoid path shadowing.

#### `backend/app/routes/call_logs.py`
- Added `GET /call_logs/stats?days=30` — returns total/resolved/escalated counts, by_date chart data, and recent 20 calls. Placed **before** `GET /call_logs` generic route.

#### `backend/app/main.py`
- Imported `notifications` router
- Registered `notifications.router`

### Frontend

#### `frontend/src/services/apiService.js`
New exports added:
- `fetchVacantFlats()` — `GET /flats?vacant=true`
- `fetchUnassignedTenants()` — `GET /tenants?unassigned=true`
- `createTenant(data)` — `POST /tenants`
- `updateTenantRentStatus(tenantUuid, rentStatus)` — `PATCH /tenants/{uuid}/rent-status`
- `assignTenantToFlat(flatUuid, tenantUuid)` — `PATCH /flats/{uuid}/assign-tenant`
- `unassignTenantFromFlat(flatUuid)` — `PATCH /flats/{uuid}/unassign-tenant`
- `fetchRentSummary()` — `GET /rents/summary`
- `fetchCallStats(days)` — `GET /call_logs/stats`
- `fetchCallLogs()` — `GET /call_logs`
- `fetchNotifications()` — `GET /notifications`
- `markNotificationRead(id)` — `PATCH /notifications/{id}/read`
- `markAllNotificationsRead()` — `POST /notifications/read-all`
- `createNotification(data)` — `POST /notifications`

#### `frontend/src/components/TopBar.jsx`
- Imported `NotificationPanel`
- Added `<NotificationPanel />` between existing controls

#### `frontend/src/components/Sidebar.jsx`
- Added `IndianRupee`, `PhoneCall` to Lucide imports
- Added `{ id: 'rent', icon: IndianRupee, label: 'Rent' }` nav item (after Properties)
- Added `{ id: 'voice-stats', icon: PhoneCall, label: 'Voice Stats' }` nav item (after Complaints)

#### `frontend/src/components/TenantManagement.jsx`
- Added `UserPlus` to Lucide imports
- Imported `AddTenantModal`
- Added `addModalOpen` state
- Added "Add Tenant" primary button (top-right)
- Rendered `<AddTenantModal>` with `onSuccess` that prepends new tenant to list

#### `frontend/src/App.jsx`
- Lazy-imported `RentTab` and `VoiceStatsTab`
- Added view routing: `currentView === 'rent'` → `<RentTab />`, `currentView === 'voice-stats'` → `<VoiceStatsTab />`

---

## Feature Status

| # | Feature | Status |
|---|---------|--------|
| 1 | VAPI Multi-Manager (identify_caller) | Already built — endpoint exists in `flats.py` |
| 2 | Rent Tab | **Done** — backend `/rents/summary`, frontend `RentTab.jsx` |
| 3 | AI Voice Agent Stats | **Done** — backend `/call_logs/stats`, frontend `VoiceStatsTab.jsx` |
| 4 | Notifications Bell | **Done** — backend routes, frontend `NotificationPanel.jsx` + `TopBar.jsx`. **Requires DB migration (step 1 above).** |
| 5 | Add Tenant + Assign | **Done** — `AddTenantModal.jsx`, `AssignTenantModal.jsx`, backend endpoints, bidirectional flat link |
| 6 | Image Upload for Properties | Already built — `AddPropertyGroupModal.jsx` uses `ImageUploadField`, backend stores `image_url`, `PropertiesPage.jsx` renders it |

---

## What Still Needs Doing (Post-MVP)

1. **Run DB migration** — create `notifications` table before Feature 4 works
2. **VAPI System Prompt update** — update the VAPI assistant to call `identify_caller` first (manual step in VAPI dashboard — see FEATURE_ROADMAP.md Step 2)
3. **Assign Tenant in PropertiesPage** — `AssignTenantModal.jsx` is built but not wired into `FlatDetailModal.jsx` yet (requires reading and editing that component)
4. **Notification service integration** — `backend/app/services/notifications.py` could call `_save_notification()` after each SMS/email (optional enhancement)
5. **`unassign-tenant` on flat delete** — consider whether the REMOVE_TENANT action in the flat PATCH endpoint should also call the unassign-tenant logic
