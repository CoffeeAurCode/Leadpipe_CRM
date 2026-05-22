# Performance Improvements — Tenant Management CRM

A code-grounded performance audit across three layers: **frontend rendering**, **backend/DB queries**, and **the network boundary** between them. Every item cites a real file and line. Findings are ranked by impact.

> **The single highest-leverage theme:** the app fetches *entire tables* and does the filtering/aggregation in JavaScript (frontend) or Python (backend), then ships it all uncompressed over the wire on aggressive polling timers. Fix the fetch-all + poll pattern first; everything else is secondary.

---

## TL;DR — Do these 7 first

| # | Fix | Layer | File | Effort |
|---|-----|-------|------|--------|
| 1 | Add `GZipMiddleware` (1 line) | Network | `backend/app/main.py:24` | Trivial |
| 2 | Guard polls with `document.hidden`, raise intervals | Network | `App.jsx:108`, `Dashboard.jsx:38` | Low |
| 3 | Fix N+1 in live VAPI call path | Backend | `routes/appointments.py:69-82` | Low |
| 4 | Pre-bucket calendar events into a `Map` (kill O(n×days) on hover) | Frontend | `CalendarView.jsx:98-199` | Med |
| 5 | Push tenant/rent filters to the DB instead of Python | Backend | `routes/tenants.py:274-308`, `rents.py:62-98` | Med |
| 6 | Cache the Supabase session token instead of `getSession()` per request | Network | `apiService.js:15-16` | Low |
| 7 | `React.memo` list children + stable handlers | Frontend | `ComplaintsPage.jsx:46`, CalendarView | Med |

---

# 1. Network / Data-Fetching Layer

### 1.1 [HIGH] No HTTP compression on the backend
**`backend/app/main.py:24`** — only `CORSMiddleware` is registered. Every JSON list endpoint (`/flats`, `/tenants`, `/complaints`, `/appointments`, `/buildings`) ships **uncompressed**. JSON with joined objects compresses 5–10×.

**Fix** — one line:
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```
This is the best effort-to-impact ratio in the whole audit.

---

### 1.2 [HIGH] Two polling loops refetch full collections, neither pauses in background tabs
- **`App.jsx:108`** — polls `getCallStatus()` every **10s**; on change fires *both* `loadComplaints()` + `loadAppointments()`. No `document.hidden` guard → runs forever in background tabs.
- **`components/Dashboard.jsx:38`** — polls `fetchData()` (complaints + callLogs via `Promise.all`) **every 5 seconds, unconditionally**. That's ~720 full double-fetches/hour per open tab. *(Verify this component is still mounted — the live shell is `BentoDashboard` at `App.jsx:249`. If `Dashboard.jsx` is dead code, delete it so the 5s poll can't be revived by accident.)*
- **`NotificationPanel.jsx:43`** — polls every 30s but *correctly* guards with `!document.hidden`. **Copy this pattern.**

**Fix:**
1. Add `if (document.hidden) return;` to every polling callback (and re-sync on `visibilitychange`).
2. Raise the 5s/10s intervals to 30–60s.
3. Better: replace call-driven refresh with a **Supabase realtime subscription** on `complaints`/`appointments`. The frontend already has the Supabase client (`lib/supabase.js`); realtime would eliminate polling entirely.

---

### 1.3 [HIGH] No client-side caching or request deduplication
`apiService.js` is a thin `fetch` wrapper — every call hits the network. Switching views remounts lazy components (`TenantManagement.jsx:64`, `PropertiesPage`, `RentTab`), each refetching from scratch on mount. Reference data (`fetchPropertyTypes`, `fetchBuildings`, `fetchProperties`) is refetched on every visit despite rarely changing.

**Fix:** adopt **React Query (TanStack Query)** or SWR for all GET endpoints. Gives you dedup, stale-while-revalidate, and view-switch caching for free. If you'd rather not add a dependency, a small in-memory `Map` cache with a TTL on the reference-data calls captures most of the win.

---

### 1.4 [HIGH] `authFetch` calls `supabase.auth.getSession()` on *every* request
**`apiService.js:15-16`** — every API call awaits `getSession()` before fetching, adding an async hop per request. (It reads from local storage, so not a network call — but it serializes an await in front of every request, and the always-on polls multiply it.)

**Fix:** subscribe once via `supabase.auth.onAuthStateChange` and hold the token in a module-level variable; read that synchronously in `authFetch`.

---

### 1.5 [MED] 120-day appointment window fetched on every load
**`App.jsx:112-117`** — `fetchAppointments(subDays(90), addDays(30))` pulls a 120-day window on initial load, then *again* on every call-poll hit and every `refresh-appointments` event. The dashboard only surfaces upcoming items.

**Fix:** narrow to the visible window (e.g. `-7d .. +30d`). The calendar view already fetches its own month (`CompactCalendar.jsx:24` — good), so the wide window isn't even needed for it.

---

### 1.6 [MED] No `AbortController` — stale responses race
No fetch cancels on unmount. Rapid view switching or filter toggling (`TenantManagement.jsx:62`, `load` keyed on 4 filter states) can resolve in-flight requests into unmounted components, causing last-response-wins races.

**Fix:** thread an `AbortSignal` through `authFetch`, abort in effect cleanup.

---

### 1.7 [MED] Redundant double-dispatch refetch
**`DateComplaintsModal.jsx:33-34`** dispatches *both* `refresh-data` and `refresh-calendar` on a single save → two full fetches per modal action. Coalesce into one.

### 1.8 [LOW] No pagination params anywhere
`fetchFlats`, `fetchTenants`, `fetchComplaints`, `getLeaseLeads`, `fetchCallLogs` accept no `limit`/`offset`. Fine at MVP scale; add the plumbing before a large portfolio onboards.

### 1.9 [LOW] No debounce on search inputs
`RentTab.jsx:138`, `SmsWorkflow.jsx:567` set search state per keystroke. Currently client-side filtering (low risk), but add a debounce before any of these move server-side.

---

# 2. Backend / Database Layer

> **Systemic multiplier (affects everything below):** every route is `async def` but uses the **synchronous** Supabase SDK. Each `.execute()` is a *blocking* HTTP round-trip on the event loop, serializing requests under load. Only `voice.py:627` does it right with `asyncio.to_thread`. Wrapping hot-path DB/external calls in `asyncio.to_thread` is the highest-leverage backend change.

### 2.1 [HIGH] N+1 in `/appointments/view` — on the live voice-call path
**`routes/appointments.py:69-82`** — fetches all appointments for a flat, then loops and runs **one `complaints` query per appointment** to fetch `category`. This runs *during a live VAPI call*, where latency is most painful.

**Fix** — single embedded join (already done correctly at `get_appointments` line 434):
```python
.select("id, uuid, flat_number, appointment_date, status, complaint_id, "
        "complaints!fk_appointments_complaint_uuid(category)")
```

### 2.2 [HIGH] `/rents/summary` — full-table scan + Python aggregation
**`routes/rents.py:62-98`** — pulls the **entire** `tenants`, `rents`, and `flats` tables (no manager scoping, no `.eq()`), joins them into dicts in Python, and groups status counts manually. Scales with the whole DB, not the manager's data.

**Fix:** scope to the manager; do status counts at the DB with `.select("rent_status", count="exact")` + `.eq()`; use column-scoped joins instead of `select("*")`.

### 2.3 [HIGH] `/tenants` GET — fetch-all-then-filter-in-Python
**`routes/tenants.py:274-308`** — always `select("*")` of *all* tenants, then filters `unassigned`, `unit_uuid`, `rent_status`, `lease_status` in Python. Building/property filters even pre-fetch flat-UUID sets to filter in Python.

**Fix:** push filters to the query — `unassigned` → `.is_("flat_uuid", "null")`, `unit_uuid`/`rent_status` → `.eq()`, building/property → `.in_("flat_uuid", uuids)`. (The batch-enrich block at 310–367 is already good — keep it.)

### 2.4 [HIGH] `/call_logs` + `/call_logs/stats` — unbounded + Python aggregation
**`routes/call_logs.py:54-64`** returns *every* call log, no limit. **`:16-49`** `/stats` pulls all rows with `select("*")` (including large `transcript` fields) then counts in Python though it only returns 20.

**Fix:** add `.limit()`/pagination to the list; for stats select only `created_at, complaint_status`, and use `count="exact"` + `.in_(...)` for totals; fetch the 20 recent separately.

### 2.5 [MED] `/flats/identify-caller` — full `tenants` scan + 4 serial lookups
**`routes/flats.py:192-255`** — scans all tenants for a phone suffix match in Python, then does 4 serial single-row lookups (flat→building→property→manager).

**Fix:** store a normalized digits-only phone column and `.eq()` on it; collapse the chain into one embedded join.

### 2.6 [MED] `voice_webhook` creates complaints via an HTTP call to its own public URL
**`routes/voice.py:337-343`** — creates the complaint by `httpx.post()` to `https://tenant-management-mvp.onrender.com/complaints` (10s timeout) *during a live webhook* — full network latency + re-auth, and a code comment already flags it breaks with multiple workers.

**Fix:** call the creation logic in-process (service function / direct `db.table("complaints").insert(...)`), not over HTTP.

### 2.7 [MED] Chatbot + notifications recreate clients per call
- **`ai/chatbot.py:927`** — `OpenAI(...)` constructed on every `run_chat`; tool loop makes up to 5 *sequential* blocking completions. Reuse a module-level client; run `run_chat` via `asyncio.to_thread`.
- **`services/notifications.py:98-223`** — recreates the Supabase client per call, runs two `is_feature_enabled` queries serially, and uses a fragile `nest_asyncio` + `run_until_complete` hack. Reuse a module-level client; combine the two flag checks into one `.in_("feature_key", [...])` query.

### 2.8 [LOW] `FeatureService` N+1 over units
**`services/feature_service.py:149-187`** — loops `unit_ids` calling `_get_unit_features_raw` once per unit. Replace with a single `.in_("unit_id", unit_ids)` and aggregate in Python.

---

# 3. Frontend / Rendering Layer

### 3.1 [HIGH] Calendar does O(days × complaints) scans on every hover
**`CalendarView.jsx:98-199`** — `getEventsForDate` is called inside `monthDays.map`, scanning the full complaints + appointments arrays per day cell. It's **not memoized**, and `setHoveredDate` re-renders the whole grid → ~30 full-array filters fire on a single hover.

**Fix:** pre-bucket events once into a `Map<dateKey, events[]>` via `useMemo` keyed on `[appointments, complaints]`; look up by key in the render.

### 3.2 [HIGH] Zero `React.memo` — list children re-render on any parent state change
Confirmed no `React.memo` usage in the codebase.
- **`ComplaintsPage.jsx:46-52`** — `CompactComplaintCard` gets a fresh inline `onClick` arrow each render *and* isn't memoized → all cards re-render when any one opens.
- **CalendarView** — every day cell re-renders + re-runs `getEventsForDate` on each hover.

**Fix:** wrap `CompactComplaintCard`, the calendar day cell, and `KPICard` in `React.memo`; pass stable handlers (pass the `id`/`complaint` and one memoized callback rather than a new closure per item).

### 3.3 [HIGH] `fetchComplaints()` returns the whole table; dashboard filters it ~7×
**`apiService.js:65`** + **`BentoDashboard.jsx:35-93`** — `/complaints` has no pagination/date bound, then BentoDashboard runs ~7 separate `.filter()`/`.sort()` passes over the full array. (The passes are correctly `useMemo`'d, so this is mostly a payload/initial-cost problem — pairs with backend #2.4 and network #1.5.)

**Fix:** server-side pagination/date-range on `/complaints`.

### 3.4 [MED] `KPICard` runs a per-frame spring re-render
**`dashboard/KPICard.jsx:4-12`** — `AnimatedNumber` calls `setCurrent` every animation frame (~60 setState/sec × 4 cards), re-triggered whenever a poll changes the KPI values. Combined with `whileHover={{scale}}` + entry animations.

**Fix:** drop the counting animation (it's decoration, not information — see also `UI_IMPROVEMENTS.md`), or only animate when the delta is large.

### 3.5 [MED] Recharts trees re-render on unrelated dashboard state
**`BentoDashboard.jsx:181-197`, `TrendsChart.jsx:22-31`** — data arrays are memoized (good), but the 4 chart wrappers aren't memoized and `<Tooltip contentStyle={{...}}>` / `<XAxis tick={{...}}>` build fresh objects each render, so opening a modal (`setActiveModal`) re-renders all 4 Recharts trees (expensive reconciliation).

**Fix:** `React.memo` the four chart wrappers; hoist the static `contentStyle`/`tick` objects to module constants.

### 3.6 [MED] Filtered rows recomputed on every keystroke without `useMemo`
**`LeasingTab.jsx:109`, `RentTab.jsx:58`** — `filteredLeads`/`rows` computed inline in the render body; `RentTab` runs `.filter()` + two `.toLowerCase()` per row per keystroke. Wrap in `useMemo` keyed on the relevant filter state.

### 3.7 [MED] Always-mounted heavy FABs pull `react-markdown` on first paint
**`App.jsx:299, 322-323`** — `Chatbot`, `OutboundCallButton`, `OnboardingTour` are always mounted. `Chatbot` eagerly imports `react-markdown` (heavy parse cost) even though it's a collapsed FAB. `vite.config.js:24` already splits a `markdown` chunk, so a lazy import would actually defer it.

**Fix:** `lazy()` the Chatbot panel body; load `react-markdown` only when the chat opens (`open && <Suspense>`).

### 3.8 [LOW] `console.log` in a hot render path
**`apiService.js:159`** — `formatDate` logs `'formatDate called with:'` on every call; `CompactComplaintCard.jsx:41` calls it per card → N console writes per grid render. Remove the log.

### 3.9 [LOW] Staggered entry animations re-run on every view switch
**`App.jsx:219`** (`motion.div key={currentView}`) forces a full remount + opacity animation per navigation, plus cascading `delay: 0.25/0.35` rows. Minor jank on slow devices; keep if it's a deliberate UX choice.

---

## Already done well (don't touch)
- Routes are `lazy()`-loaded; `vite.config.js` `manualChunks` splits recharts/framer-motion/markdown/react.
- `date-fns` and `lucide-react` use tree-shakeable named imports.
- BentoDashboard analytics and ComplaintsPage filter are correctly `useMemo`'d.
- `get_appointments` (`appointments.py:434`) and `get_all_buildings` (`buildings.py:108`) already use embedded joins — no N+1.
- `NotificationPanel.jsx:43` polls with a `!document.hidden` guard — the model to copy.
- Frontend talks to Supabase for **auth only**; all data goes through FastAPI (clean separation).

---

## Suggested rollout order
1. **Quick wins (a few hours):** #1.1 GZip, #1.2 poll guards, #2.1 appointment N+1, #3.8 remove console.log, #1.4 cache session token.
2. **DB query fixes (half day):** #2.2 / #2.3 / #2.4 push filters & aggregation to the DB.
3. **Render fixes (half day):** #3.1 calendar Map, #3.2 React.memo, #3.5 chart memo.
4. **Structural (1–2 days):** #1.3 React Query caching, #2 systemic `asyncio.to_thread` on hot paths, optionally Supabase realtime to replace polling.
