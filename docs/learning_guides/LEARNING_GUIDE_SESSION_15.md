# Learning Guide Session 15: VAPI Tool Endpoints, Background SMS Notifications, and Rich Calendar UI

**Role:** Senior Staff Engineer Mentorship
**Objective:** Master building AI-callable API tools, non-blocking SMS notification pipelines, Python parameter rules, Supabase client edge cases, and rewriting a complex React calendar from scratch with modern Tailwind/framer-motion patterns.

---

## 1. Overview of What Was Built in This Session

This session had two major pillars:

**Backend:**
- Added `PATCH /appointments/cancel` as a new VAPI-callable tool endpoint
- Wired automated tenant SMS notifications into all four appointment lifecycle events: **created, rescheduled, cancelled** (from both CRUD and VAPI routes)
- Fixed two critical bugs: Python parameter ordering `SyntaxError` and a `supabase-py` `maybe_single()` edge case that returned `NoneType` instead of a proper response object

**Frontend:**
- Fully rewrote `CalendarView.jsx` — dropped the internal `localhost:8000` fetch, fixed the month-start day alignment bug, introduced event mini-cards, a framer-motion slide-over panel, hover tooltips, and a status color legend
- Cleaned up `BentoDashboard.jsx` — removed `CompactCalendar`, `DateComplaintsModal`, and all their dead state
- Added a Calendar nav item to `Sidebar.jsx`
- Passed `appointments` prop correctly from `App.jsx` into `CalendarView`

---

## 2. Core Concept: What is VAPI and Why Do Tool Endpoints Matter?

### What is VAPI?
VAPI is a voice AI platform. It allows you to configure an AI phone assistant that talks to tenants. The AI can be given "tools" — these are HTTP endpoints on your backend that the AI calls during a conversation to get or change data.

Think of it like giving the AI a set of REST API buttons it can press depending on what the tenant says.

**Example conversation:**
> Tenant: "Can you cancel my appointment for flat 104?"
> VAPI AI: *(calls your backend: `PATCH /appointments/cancel?flat_number=104&id=8`)*
> AI: "Done! Your appointment has been cancelled."

### Why query parameters instead of request body?
VAPI tools send data as URL query parameters, not JSON bodies. This is why all three VAPI endpoints (`/view`, `/update`, `/cancel`) use `Query(...)` in FastAPI instead of a Pydantic request body model:

```python
# VAPI style — parameters in the URL
@router.patch("/cancel")
async def vapi_cancel_appointment(
    flat_number: str = Query(...),
    id: int = Query(...),
    ...
):
```

vs. the regular CRUD style — parameters in the JSON body:
```python
# CRUD style — parameters in request body
@router.patch("/{appointment_id}")
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,  # Pydantic model = JSON body
    ...
):
```

### VAPI Endpoint Design Rules
| Rule | Reason |
|------|--------|
| Use `PATCH` not `GET` for mutations | GET must never change data. Cancelling is a mutation. |
| Idempotent cancel | VAPI may retry. If already cancelled → return 200 silently, don't send a duplicate SMS. |
| Refuse completed appointments | You can't uncomplete a visit. Return 400. |
| Normalize `flat_number` with `.strip().upper()` | Voice AI may say "a 101" → "A 101" → should still match "A101". Use `.ilike()` on the DB query. |
| Place VAPI routes BEFORE `/{appointment_id}` | FastAPI matches routes top-down. `/update` would match `/{appointment_id}` with `appointment_id="update"` if not placed first. |

---

## 3. FastAPI `BackgroundTasks` — Non-Blocking Notifications

### The Problem
When a tenant books an appointment, you want to send them an SMS. But sending an SMS takes 1-2 seconds (Twilio network call). You don't want the API response to wait for it.

### The Solution: BackgroundTasks
FastAPI's `BackgroundTasks` lets you queue a function to run **after** the HTTP response is already sent to the client. The client gets their `201 Created` instantly. The SMS fires in the background.

```python
from fastapi import BackgroundTasks

@router.post("")
async def create_appointment(
    appointment_data: AppointmentCreate,
    background_tasks: BackgroundTasks,   # FastAPI injects this automatically
    db: Client = Depends(get_db)
):
    # ... create appointment ...
    created = response.data[0]

    # Queue notifications — fire after response is sent
    background_tasks.add_task(notify_manager_appointment_scheduled, created)
    background_tasks.add_task(notify_tenant_appointment, flat_uuid, "created", flat_number, db)

    return created  # ← client gets this immediately
```

**Key rule:** The function passed to `add_task()` must be a regular `def` (sync), not `async def`. FastAPI runs it in a thread pool.

### How to Use BackgroundTasks in Every Route Type

| Route type | How to get BackgroundTasks |
|-----------|---------------------------|
| POST / PATCH body routes | Add `background_tasks: BackgroundTasks` as a parameter anywhere **before** `= Query(...)` params |
| GET/PATCH query-param routes (VAPI) | Add `background_tasks: BackgroundTasks` as the **first** parameter |
| DELETE routes | Add `background_tasks: BackgroundTasks` as a parameter |

---

## 4. CRITICAL BUG: Python Parameter Ordering — `SyntaxError`

### The Error
```
SyntaxError: parameter without a default follows parameter with a default
```

### Why It Happens
In Python, a function parameter without a default value **cannot** come after one with a default value. `Query(...)` counts as a default value (it assigns a `Query` object as the default). `BackgroundTasks` has no default.

```python
# ❌ WRONG — BackgroundTasks has no default, comes after Query(...) defaults
async def vapi_cancel_appointment(
    flat_number: str = Query(...),   # has default
    id: int = Query(...),            # has default
    background_tasks: BackgroundTasks,  # NO default — SyntaxError!
    db: Client = Depends(get_db),
):
```

```python
# ✅ CORRECT — BackgroundTasks comes FIRST, before any Query(...) defaults
async def vapi_cancel_appointment(
    background_tasks: BackgroundTasks,  # no default — must be first
    flat_number: str = Query(...),
    id: int = Query(...),
    db: Client = Depends(get_db),
):
```

**Why FastAPI still injects it correctly:** FastAPI uses type annotations, not argument position, to decide what to inject. It sees `BackgroundTasks` type and knows to inject the background task queue, regardless of where it sits in the signature. So putting it first doesn't break anything from FastAPI's perspective — only Python's own parser cares about the ordering.

---

## 5. CRITICAL BUG: Supabase `maybe_single()` Returns `None`

### The Error
```
"detail": "Error cancelling appointment: 'NoneType' object has no attribute 'data'"
```

### What `maybe_single()` Is Supposed To Do
In the Supabase Python client, `.maybe_single()` tells PostgREST to return one row or `None` (instead of a list). It's supposed to return a response object with `.data = None` when zero rows match.

### What Actually Happened
When combined with `.eq()` + `.ilike()` filters that match **no rows**, in some versions of `supabase-py`/`postgrest-py`, `.maybe_single().execute()` returns `None` itself — not an object with `.data = None`. Calling `.data` on `None` raises `AttributeError`.

```python
# ❌ FRAGILE — maybe_single() can return None itself when no rows match
apt_resp = (
    db.table("appointments")
    .select("*")
    .eq("id", id)
    .ilike("flat_number", normalized_flat)
    .maybe_single()  # ← dangerous
    .execute()
)
if not apt_resp.data:  # ← crashes if apt_resp is None
```

```python
# ✅ SAFE — .execute() always returns a proper response object with .data as a list
apt_resp = (
    db.table("appointments")
    .select("*")
    .eq("id", id)
    .ilike("flat_number", normalized_flat)
    .execute()         # ← always safe
)
if not apt_resp.data:  # .data is [] when no rows match
    raise HTTPException(status_code=404, detail="Appointment not found")

apt = apt_resp.data[0]  # safe to index now
```

### The Rule
**Always prefer `.execute()` over `.maybe_single().execute()` for query-and-check patterns.** Use `.maybe_single()` only when you can guarantee the query will either find exactly one row or zero rows, and you've verified the supabase-py version handles the zero-row case correctly.

---

## 6. `notify_tenant_appointment()` — Designing a Notification Service Function

### Design Goals
1. **Never raise** — SMS failure must not crash the appointment route
2. **Single responsibility** — one function handles all three event types
3. **Reusable** — called from 5 different routes with the same interface
4. **Sync** — works as a FastAPI background task (must be `def`, not `async def`)

### Function Signature
```python
def notify_tenant_appointment(
    flat_uuid: str,
    event: str,          # "created" | "rescheduled" | "cancelled"
    flat_number: str,    # used in SMS message text
    db: Client,          # supabase client (safe to pass to background task)
    new_date: Optional[str] = None,  # only for "rescheduled"
) -> None:
```

### Lookup Chain
The function doesn't know the tenant's phone number — it only knows the flat. It fetches it:
```
flat_uuid → tenants table (WHERE flat_uuid = flat_uuid) → phone, name
```

For VAPI routes that only have `flat_number` (not `flat_uuid`):
```
flat_number → flats table (ilike) → uuid → tenants table → phone, name
```

This is why the flat query in VAPI routes was changed from `.select("id")` to `.select("id, uuid")` — the uuid is needed to look up the tenant.

### Message Templates
```python
if event == "created":
    message = f"Hi {name}, a new maintenance appointment has been scheduled for flat {flat_number}."
elif event == "rescheduled":
    formatted_date = dt.strftime("%d %b %Y at %I:%M %p")  # "14 Mar 2026 at 02:30 PM"
    message = f"Hi {name}, your maintenance appointment for flat {flat_number} has been rescheduled to {formatted_date}."
elif event == "cancelled":
    message = f"Hi {name}, your maintenance appointment for flat {flat_number} has been cancelled."
```

### Why Not Feature-Flag Tenant SMS?
Manager SMS/email notifications are gated by `sms_reminders` / `email_reminders` feature flags because they are **bulk reminders** — the manager explicitly chooses to receive them.

Tenant SMS notifications are **transactional confirmations** — they are triggered by an action the tenant initiated (booking a visit). Feature-flagging transactional messages is wrong UX: the tenant would be confused why they got no confirmation. So tenant SMS fires unconditionally as long as the tenant has a phone number.

---

## 7. Passing the Supabase Client to Background Tasks

### Is it Safe?
Yes. The Supabase Python client is **stateless** — every call it makes opens a fresh HTTP connection. There is no connection pool or socket that could be closed while the background task runs. You can safely pass `db` (the Client instance) to a background task.

This is unlike SQLAlchemy `Session` objects, which ARE tied to connection lifecycle and should NEVER be passed to background tasks.

```python
# ✅ Safe — Supabase Client is HTTP-based and stateless
background_tasks.add_task(notify_tenant_appointment, flat_uuid, "created", flat_num, db)

# ❌ Unsafe — SQLAlchemy session would be closed by the time the background task runs
# background_tasks.add_task(some_fn, db_session)  # don't do this with SQLAlchemy
```

---

## 8. Idempotency in API Design

### What is Idempotency?
An operation is **idempotent** if calling it multiple times produces the same result as calling it once. PUT and DELETE are supposed to be idempotent by HTTP spec.

### Why VAPI Cancel Must Be Idempotent
VAPI may retry a tool call if the network response was lost. If the first call cancelled the appointment and sent the SMS, a second call should NOT send a second SMS and NOT return an error.

```python
# 3. Idempotent: already cancelled → return 200 silently (no duplicate SMS)
if apt.get("status") == "cancelled":
    return VapiAppointmentCancelResponse(id=apt["id"], status="cancelled")

# 4. Refuse if already completed
if apt.get("status") == "completed":
    raise HTTPException(status_code=400, detail="Cannot cancel a completed appointment")
```

**Rule:** Already in desired state → return success silently. Wrong terminal state → return 400. Only attempt the mutation if the current state allows it.

---

## 9. Testing API Endpoints with `curl`

### Why Test with curl Instead of Just the Frontend?
- Faster feedback loop — no browser required
- Tests the API contract in isolation from the UI
- Can test error cases (wrong IDs, wrong flat numbers) without UI validation getting in the way
- Reveals real HTTP status codes

### Useful curl Patterns

```bash
# GET with query parameters
curl -s "http://127.0.0.1:8000/appointments/view?flat_number=A201"

# PATCH with query parameters
curl -s -X PATCH "http://127.0.0.1:8000/appointments/cancel?flat_number=A201&id=5"

# PATCH with JSON body
curl -s -X PATCH "http://127.0.0.1:8000/appointments/8" \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'

# Show HTTP status code only
curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/appointments/9999"

# Show both body and status code
curl -s "http://127.0.0.1:8000/appointments" -w "\nHTTP %{http_code}"

# Parse JSON response with Python
curl -s "http://127.0.0.1:8000/appointments" | python -c "
import sys, json
data = json.load(sys.stdin)
print(f'Total: {len(data)}')
for a in data[:5]:
    print(f'  id={a[\"id\"]} flat={a.get(\"flat_number\")} status={a[\"status\"]}')
"
```

### The Test Matrix for Every Endpoint
Always test these scenarios:
1. ✅ Happy path — correct data, expected response
2. ✅ Wrong flat — 404 "Flat not found"
3. ✅ Wrong id — 404 "Appointment not found"
4. ✅ Idempotent repeat — same result, no side effects
5. ✅ Terminal state — 400 for completed appointments

---

## 10. React Calendar — Month-Start Day Offset Bug

### The Bug
A calendar grid has 7 columns (Sun–Sat). If March 1 falls on a Saturday (column index 6), the first 6 cells should be empty. Without the offset, day 1 renders in the Sunday column no matter what.

### The Fix
```javascript
// Get which weekday the 1st falls on (0=Sunday, 1=Monday ... 6=Saturday)
const startOffset = useMemo(
    () => startOfMonth(currentDate).getDay(),
    [currentDate]
);

// In the grid — render N empty divs before day 1
{Array.from({ length: startOffset }).map((_, i) => (
    <div key={`empty-${i}`} className="bg-card min-h-[90px]" />
))}

{monthDays.map(day => ( ... ))}
```

`date-fns`'s `startOfMonth(date).getDay()` returns 0–6. This is all you need — no extra math, no libraries.

---

## 11. Event Data in the Calendar — Two Sources, One Grid

### The Design Decision
The calendar shows two types of events:
- **Appointments** → shown on their `appointment_date` (when the visit is scheduled)
- **Complaints** → shown on their `created_at` (when the complaint was filed)

This was a deliberate product decision. An appointment card tells the manager "go visit flat X on this day." A complaint card tells the manager "flat X filed a complaint on this day." Both are useful on a calendar.

### The `getEventsForDate` Helper
```javascript
function getEventsForDate(date) {
    const appts = appointments.filter(a => {
        try { return a.appointment_date && isSameDay(parseISO(a.appointment_date), date); }
        catch { return false; }  // guard against malformed ISO strings
    }).map(a => ({ ...a, _type: 'appointment' }));

    const comps = complaints.filter(c => {
        try { return c.created_at && isSameDay(parseISO(c.created_at), date); }
        catch { return false; }
    }).map(c => ({ ...c, _type: 'complaint' }));

    return [...appts, ...comps];
}
```

The `_type` field is added as a discriminator so downstream rendering knows which template to use. It's added on the fly (not from the API) using `.map(a => ({ ...a, _type: 'appointment' }))` — spread the original object, add `_type`.

### Why `try/catch` in the filter?
API data is not always clean. A `created_at` or `appointment_date` might be `null`, an empty string, or a malformed date string. `parseISO` on bad data throws. Catching inside the filter means one bad record doesn't crash the entire calendar render.

---

## 12. Hardcoded URLs are a Production Bug

### What Was Wrong
The original `CalendarView.jsx` had:
```javascript
const response = await fetch(
    `http://localhost:8000/appointments?start_date=${startDate}&end_date=${endDate}`
);
```

This works on your laptop. It **silently fails** in production (Render.com) because `localhost:8000` doesn't exist there.

### The Fix — Prop-Drill from App.jsx
`App.jsx` already fetches appointments at the top level and stores them in state. Instead of fetching inside `CalendarView`, just pass the data down:

```jsx
// App.jsx — already had this
const [appointments, setAppointments] = useState([]);

// App.jsx — add the prop
<CalendarView complaints={complaints} appointments={appointments} />

// CalendarView.jsx — accept the prop, no internal fetch needed
export default function CalendarView({ complaints = [], appointments = [] }) {
    // no useEffect, no fetch — data comes from props
}
```

**Rule:** Fetch data as high up the component tree as you need it. Pass it down as props. Don't fetch the same data in multiple places.

---

## 13. CSS Strategy — When to Use Tailwind vs Custom CSS

### This Project's Rule (Decided in This Session)
| Use Tailwind | Use custom CSS |
|-------------|----------------|
| Spacing, colors, borders, font sizes | Complex grid definitions |
| Hover/focus states | Browser-specific overrides |
| Flex/grid layout (simple) | Animation keyframes |
| Component-level styling | Anything Tailwind can't do |

### Why Tailwind is Better for Component Styling
1. **Co-located with markup** — you see the style when you read the JSX, no need to open a separate file
2. **No naming problem** — you don't have to invent `.calendar-day-active-selected-hover` class names
3. **Theme consistency** — Tailwind tokens like `bg-card`, `text-foreground`, `border-border` automatically follow the app's dark/light theme via CSS variables
4. **Purging** — production build removes unused classes automatically

### Why the Old CalendarView.css Was a Problem
The old CSS had `.appointment-indicator`, `.status-scheduled`, `.date-details` — 295 lines of custom CSS. When changing the design, you had to:
1. Find the JSX element
2. Find its CSS class
3. Edit the CSS file
4. Hope no other element used that class

With Tailwind, step 2 and 3 don't exist. The style IS the JSX.

### Tailwind Color Tokens vs Raw Colors
```jsx
// ❌ Hardcoded — breaks in dark mode, inconsistent with theme
<div className="bg-white border-gray-200 text-gray-900">

// ✅ Theme tokens — auto-adapts to dark/light mode
<div className="bg-card border-border text-foreground">
```

The theme tokens (`bg-card`, `bg-background`, `text-foreground`, `text-muted-foreground`, `border-border`) are defined as CSS variables in the global stylesheet and changed by the Tailwind dark mode class. Always use tokens for background and text colors in structural components.

---

## 14. Dynamic Tailwind Classes — The Purge Problem

### The Problem
Tailwind scans your source files at build time to find which classes you use, then only includes those in the final CSS. If you build class names dynamically, they won't be found:

```javascript
// ❌ Tailwind will NOT include these — they're never seen as complete strings
const color = 'blue';
<div className={`bg-${color}-500`} />          // dynamic — purged
<div className={`border-l-${status}-500`} />   // dynamic — purged
```

### The Fix — Static Class Maps
Define all possible class strings upfront as a complete, static object. Tailwind's scanner finds them:

```javascript
// ✅ All class strings are visible in source — Tailwind includes them all
const MINI_STATUS = {
    scheduled:   'border-blue-500 bg-blue-50 text-blue-700',
    in_progress: 'border-orange-500 bg-orange-50 text-orange-700',
    completed:   'border-green-500 bg-green-50 text-green-700',
    cancelled:   'border-red-500 bg-red-50 text-red-700',
};

// Then use it:
<div className={cn('border-l-2 rounded px-1', MINI_STATUS[status] || 'border-gray-400 bg-gray-50')} />
```

**Rule:** Never build Tailwind class names by string interpolation. Always use a lookup map of complete class strings.

---

## 15. The `cn()` Utility — Conditional Class Merging

### What It Is
`cn()` (from `@/lib`) is a helper that combines `clsx` (conditional class logic) and `tailwind-merge` (removes conflicting Tailwind classes). It's the standard pattern in shadcn/ui projects.

```javascript
import { cn } from '@/lib';

// Conditional classes
<div className={cn(
    'base-class another-class',            // always applied
    isSelected && 'bg-primary/10',          // applied when isSelected is true
    isToday ? 'text-primary' : 'text-foreground',  // ternary
    getStatusClasses(status)               // returned from a function
)} />
```

Without `cn()`:
```javascript
// ❌ Messy and breaks with falsy values
<div className={`base ${isSelected ? 'bg-primary/10' : ''} ${isToday ? 'text-primary' : 'text-foreground'}`} />
```

### Why tailwind-merge Matters
```javascript
// Without tailwind-merge, both bg-* classes are in the DOM — browser applies the last one
cn('bg-card', 'bg-blue-50')  // → 'bg-card bg-blue-50' (conflict, unpredictable)

// With tailwind-merge (inside cn), the later class wins properly
cn('bg-card', 'bg-blue-50')  // → 'bg-blue-50' (merge removes conflict)
```

---

## 16. Framer Motion — Slide-Over Panel with Backdrop

### The Pattern
A slide-over panel that animates in from the right is a very common UI pattern. Here's the complete recipe:

```jsx
import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence>
    {isOpen && (
        <>
            {/* Backdrop — clicking it closes the panel */}
            <motion.div
                key="backdrop"
                className="fixed inset-0 bg-black/25 z-30"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                onClick={closePanel}
            />

            {/* Panel — slides in from right */}
            <motion.div
                key="panel"
                className="fixed right-0 top-0 h-screen w-96 bg-card border-l border-border shadow-2xl z-40 flex flex-col"
                initial={{ x: '100%' }}   // start off-screen to the right
                animate={{ x: 0 }}        // slide to natural position
                exit={{ x: '100%' }}      // slide back off-screen on close
                transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            >
                {/* content */}
            </motion.div>
        </>
    )}
</AnimatePresence>
```

### Key Details
| Detail | Why |
|--------|-----|
| `AnimatePresence` wraps the conditional | Without it, framer-motion can't animate the exit because the element is removed from the DOM before the animation can play |
| `key` on both elements | Required for AnimatePresence to track mount/unmount |
| Backdrop `z-30`, Panel `z-40` | Backdrop must be above content but below the panel |
| Panel has `flex flex-col` | So you can have a fixed header + scrollable body inside |
| `h-screen` on panel | Full viewport height |
| `spring` transition | Feels more natural than a linear ease. `stiffness: 320, damping: 32` is a good starting point — high stiffness = fast, high damping = less bounce |

### Why `x: '100%'` not `x: 380`?
`'100%'` is relative to the panel's own width. If you change `w-96` (384px) to a different width, `'100%'` still works. `x: 380` would be wrong after a resize.

---

## 17. Hover Tooltip Pattern in React

### The Pattern
```jsx
const [hoveredDate, setHoveredDate] = useState(null);

<div
    className="relative"                          // parent needs relative
    onMouseEnter={() => setHoveredDate(day)}
    onMouseLeave={() => setHoveredDate(null)}
>
    {/* cell content */}

    {/* Tooltip — only visible when hovered */}
    {isSameDay(hoveredDate, day) && (
        <div className="absolute bottom-full left-0 mb-1 z-20 w-52 bg-popover border border-border rounded-lg shadow-xl p-2.5 pointer-events-none">
            {/* tooltip content */}
        </div>
    )}
</div>
```

### Key Details
| Detail | Why |
|--------|-----|
| `pointer-events-none` on tooltip | Prevents the tooltip itself from triggering `onMouseLeave` on the parent (which would cause the tooltip to flicker) |
| `absolute bottom-full` | Positions the tooltip ABOVE the element. `bottom-full` = bottom of tooltip aligns with top of parent. |
| `z-20` | Must be above sibling cells in the grid |
| `overflow: visible` on parent | If the parent clips overflow, the tooltip gets cut off. Ensure no ancestor has `overflow: hidden` |
| Suppressed when panel is open | `isHovered && !isSelected` — no need for a tooltip if you're already looking at the details panel |

---

## 18. Calendar Grid — The `gap-px bg-border` Pattern

### The Trick
Instead of adding borders to every cell (which doubles borders at shared edges and creates 2px gaps), use this pattern:

```jsx
// The grid background IS the border color
// Each cell covers the grid background except for the 1px gap
<div className="grid grid-cols-7 gap-px bg-border">
    {cells.map(cell => (
        <div className="bg-card min-h-[90px]">
            {/* content */}
        </div>
    ))}
</div>
```

**How it works:** The grid container is `bg-border` (your border color). Each cell is `bg-card`. The `gap-px` (1px gap between cells) exposes the container's background color, which appears as a thin border between cells. Every cell shares exactly 1px of border with its neighbor — no doubling.

This is cleaner than:
```jsx
// ❌ Naive — creates 2px borders at shared edges
<div className="border border-border">
```

---

## 19. BentoDashboard Cleanup — Removing Dead Code

### What Was Removed
When `CompactCalendar` and `DateComplaintsModal` were removed from `BentoDashboard.jsx`, these things also had to be removed to avoid dead code:

```javascript
// Dead state — nothing sets or reads these anymore
const [selectedDate, setSelectedDate] = useState(null);
const [complaintsForDate, setComplaintsForDate] = useState([]);

// Dead handlers — nothing calls these
const openDateModal = (date, complaintsOnDate) => { ... };
const closeDateModal = () => { ... };
```

**Rule:** When you remove a component, trace every piece of state and every handler that it owned. If nothing else uses them, delete them. Dead state causes confusion for future developers who wonder "what sets `selectedDate`?"

### Expanding the Grid
The complaints section was inside a `lg:grid-cols-3` outer grid, taking `lg:col-span-2`. After removing the calendar column, the grid was replaced with a flat `space-y-3` container, and the inner complaint card grid was expanded from `md:grid-cols-2` to `md:grid-cols-2 lg:grid-cols-3` to use the full width.

---

## 20. Implementation Plan Auditing — Finding Gaps Before Writing Code

### Why Audit First?
Writing code from a plan that has gaps is expensive. You implement something, discover the gap mid-way, and have to rethink and rewrite. A 10-minute audit saves hours of rework.

### What to Look For in an Audit

| Gap Type | Example from This Session |
|----------|--------------------------|
| **Hardcoded URLs** | CalendarView fetched from `localhost:8000` — breaks in prod |
| **Missing prop** | `appointments` wasn't being passed to CalendarView from App.jsx |
| **Undefined action** | "Schedule Appointment" button — what does it open? No modal existed. |
| **Ambiguous layout** | "Left panel" vs "Right panel" — plan had both, which one? |
| **Existing bugs not addressed** | Month-start offset — day 1 always rendered in Sunday column |
| **Data source conflict** | Should complaints show on `created_at` or `appointment_date`? |
| **Dead code after removal** | Removing CompactCalendar leaves orphaned state/handlers |
| **CSS strategy gap** | Plan said "update CSS" but didn't say what the target structure was |

### The Audit Process
1. **Read the plan** — understand intent
2. **Read the existing files** — understand reality
3. **Cross-reference** — for each plan step, ask: "Does the current code support this? What's missing?"
4. **List gaps** — write them out explicitly
5. **Get decisions** — some gaps need product decisions (e.g., "no left panel"), others need technical decisions (e.g., "use fetchAppointments from apiService")
6. **Update the plan** — rewrite it with decisions resolved before touching code

---

## 21. Idiomatic React Patterns Used

### `useMemo` for Derived State
```javascript
// ✅ Recomputed only when currentDate changes
const monthDays = useMemo(
    () => eachDayOfInterval({ start: startOfMonth(currentDate), end: endOfMonth(currentDate) }),
    [currentDate]
);

// ✅ Recomputed only when selectedDate, appointments, or complaints change
const panelEvents = useMemo(
    () => (selectedDate ? getEventsForDate(selectedDate) : []),
    [selectedDate, appointments, complaints]
);
```

### Functional State Updates for Month Navigation
```javascript
// ✅ Uses functional form — safe even if multiple state updates queue up
const goToPrev = () => {
    setCurrentDate(d => new Date(d.getFullYear(), d.getMonth() - 1, 1));
    setSelectedDate(null);
};
```

### Toggle Pattern for Clicking a Selected Day
```javascript
// Click the already-selected day → close panel (toggle)
onClick={() => setSelectedDate(isSelected ? null : day)}
```

---

## 22. The `date-fns` Functions Used — Quick Reference

| Function | What it does | Example |
|---------|-------------|---------|
| `startOfMonth(date)` | Returns the first day of the month | `startOfMonth(new Date())` → March 1 |
| `endOfMonth(date)` | Returns the last day of the month | March 31 |
| `eachDayOfInterval({start, end})` | Array of every day between start and end | `[Mar 1, Mar 2, ..., Mar 31]` |
| `isSameDay(a, b)` | True if two dates are the same calendar day | Ignores time |
| `isToday(date)` | True if date is today | |
| `parseISO(string)` | Parses an ISO 8601 string to a Date | `"2026-03-14T10:00:00"` → Date |
| `format(date, pattern)` | Formats a Date to a string | `format(d, 'MMMM yyyy')` → `"March 2026"` |
| `format(date, 'HH:mm')` | 24-hour time | `"14:30"` |
| `format(date, 'h:mm a')` | 12-hour time with AM/PM | `"2:30 PM"` |
| `format(date, 'EEEE')` | Full weekday name | `"Saturday"` |
| `format(date, 'MMM d, yyyy')` | Short date | `"Mar 14, 2026"` |
| `.getDay()` | 0=Sunday, 1=Monday ... 6=Saturday | Used for month offset |

---

## 23. Full-Stack Feature Delivery Checklist

Every feature in this project touches multiple layers. Use this checklist:

```
Backend:
  [ ] Schema (Pydantic) — new request/response models
  [ ] Route — endpoint logic, error handling, background tasks
  [ ] Service — notification/business logic functions
  [ ] Test — curl test all happy paths and error cases

Frontend:
  [ ] Data — is the data fetched? Is it passed down as props?
  [ ] Navigation — is there a way to reach this page/feature?
  [ ] Component — renders correctly with real data
  [ ] Empty state — what shows when there's no data?
  [ ] Error state — what shows when the API fails?
  [ ] Dead code — did removing something leave orphan state/handlers/imports?
  [ ] Build — does `npm run build` pass with no errors?
```

---

## Summary Table — Bugs Fixed in This Session

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `SyntaxError: parameter without a default follows parameter with a default` | `BackgroundTasks` (no default) placed after `Query(...)` params (have defaults) in function signature | Move `BackgroundTasks` to be the first parameter in the function |
| `'NoneType' object has no attribute 'data'` | `.maybe_single().execute()` returns `None` itself (not `Response(data=None)`) when no rows match with combined `.eq()` + `.ilike()` filters | Replace `.maybe_single().execute()` with plain `.execute()`, check `if not resp.data:`, then index `resp.data[0]` |
| Appointments fetch breaks in production | `CalendarView` had hardcoded `http://localhost:8000` URL | Remove internal fetch; receive `appointments` as a prop from `App.jsx` which already fetches it via `apiService` |
| Calendar day 1 always renders in Sunday column | No empty offset cells before day 1 | `Array.from({ length: startOfMonth(date).getDay() })` prepended as empty `<div>`s |
| VAPI cancel sent duplicate SMS on retry | No idempotency check | Added early return when `apt.get("status") == "cancelled"` — silently returns 200, skips SMS |
| `strftime("%-d")` raises `ValueError` on Windows | `%-d` is a Linux/macOS glibc extension; not supported on Windows | Use `f"{due.strftime('%B')} {due.day}"` — `date.day` is an int property, never has a leading zero |

---

## 24. Implementation Plan Auditing — What Gaps to Look For (Extended)

The audit done in this session found seven distinct gap types. Each is a class of problem you will encounter on every non-trivial feature.

### Gap 1: Feature Already Implemented
**Example:** The plan said "Add a live character counter." The counter already existed at [SmsWorkflow.jsx:109-111](frontend/src/components/SmsWorkflow.jsx#L109).

**How to avoid:** Before writing a plan item, open the target file and search for it. `Grep` for "character" or "length" before writing "add character counter."

### Gap 2: UI Feature Requires Architectural Change That the Plan Doesn't Address
**Example:** The plan said "show `Sending 1/3` progress." But `sendWorkflowSms` is a **single batch POST**. There is no per-tenant lifecycle event to hook into. You cannot show per-item progress without either: (a) looping individual POSTs, or (b) faking a spinner on the single call.

**How to avoid:** For any "show progress" plan item, immediately ask: "Does the underlying API give me per-item callbacks or events?" Read `apiService.js` before writing the plan.

### Gap 3: Backend Doesn't Support a Variable The Frontend Plans to Use
**Example:** The plan added `{rent}` and `{date}` variable chips to the frontend. But [workflow.py](backend/app/routes/workflow.py) only replaced `{name}` and `{unit}`. Sending `{rent}` would have delivered the literal string `{rent}` to tenants.

**How to avoid:** For every new variable/token, check the actual backend template-resolution code — not just the API schema.

### Gap 4: Missing Column Before Sorting
**Example:** The plan said "sort by Rent Status." The table had no Rent Status column. You cannot sort by a column that doesn't exist in the UI.

**How to avoid:** Sort features have a dependency: the column must be visible before it can be a sort target. Always check whether the column exists in the rendered table, not just in the API response.

### Gap 5: Sort Strategy Not Specified
**Example:** The plan said "sort by Name, Flat, Rent Status" but didn't say whether to trigger a new API call (server-side sort) or re-order the loaded array in memory (client-side sort).

**The decision rule:**
- **Server-side sort** → use when data is paginated (you only have page 1 loaded, backend must sort the full dataset)
- **Client-side sort** → use when all data is already in memory (small datasets, no pagination). Our tenant list is fully loaded — client-side is the right call.

**`fetchTenants` already supports `sort_by` / `sort_order` params** — knowing this exists doesn't mean you should use it. Client-side sort is simpler, zero network cost, and instant for the user.

### Gap 6: Prerequisite Condition Not Widened
**Example:** In [workflow.py](backend/app/routes/workflow.py), `flat_uuids` was only collected inside `if needs_unit:`. Adding `{rent}` and `{date}` support also needs `flat_uuids` (to query the rents table by flat). Without widening the condition, `flat_uuids` would be undefined when `needs_unit` is `False` but `needs_rent` or `needs_date` is `True`.

**Fix:**
```python
# Before — only collected when {unit} is needed
if needs_unit:
    flat_uuids = [...]

# After — collected whenever ANY flat-level lookup is needed
if needs_unit or needs_rent or needs_date:
    flat_uuids = [...]
```

**General rule:** When multiple independent features share a prerequisite (e.g., "get flat UUIDs"), the condition that triggers collection of the prerequisite must be the OR of all feature flags, not just the first one added.

### Gap 7: New Component File Location Not Specified
**Example:** The plan said "add a new `DashboardListModal`" but didn't say which directory. In a project with an existing `frontend/src/components/dashboard/` folder, the answer is obvious — but the plan should state it explicitly to avoid inconsistency.

---

## 25. Python `strftime` Platform Portability — The `%-d` Bug

### The Bug
```python
due.strftime("%B %-d")  # "April 5" on Linux/macOS
                        # ValueError: Invalid format string on Windows
```

`%-d` is a **glibc extension** (Linux/macOS). It removes the leading zero from the day (`04` → `4`). Python on Windows uses the Windows CRT, which does not support this flag.

### Why It's Dangerous
The backend runs on Linux in production (Render, Railway, etc.) so `%-d` works there. It also runs on your Windows laptop in local dev, where it crashes. This means the bug is invisible in CI/CD and only surfaces during local development.

### Cross-Platform Fix
```python
# ❌ Linux/macOS only
due.strftime("%B %-d")   # "April 5"

# ❌ Always has leading zero
due.strftime("%B %d")    # "April 05"

# ✅ Cross-platform — date.day is an int property, never has a leading zero
f"{due.strftime('%B')} {due.day}"   # "April 5" on all platforms
```

`date.day` is a Python integer attribute (not a formatted string), so it never has a leading zero. This approach works identically on Windows, macOS, and Linux.

**Rule:** Never use `%-d`, `%-m`, `%-H` in Python `strftime`. Use the numeric date/time attributes directly (`date.day`, `date.month`, `datetime.hour`) for zero-free formatting.

---

## 26. Next Rent Due Date Calculation — Billing Cycle Logic

### The Design Decision
The `rents` table stores `effective_from` — the date the current rent rate became active (e.g., `2024-01-05`). There is no separate `due_day` field.

**Convention:** The billing day each month is the same day-of-month as `effective_from`. If a tenant's rent started on the 5th, their rent is due on the 5th of every month.

### The Algorithm
```python
billing_day = effective_from.day  # e.g., 5
```
1. Build `candidate = this month on billing_day`
2. If `today < candidate` → next due is candidate (this month, not yet passed)
3. If `today >= candidate` → next due is next month on billing_day

### The Edge Case: Short Months
If `billing_day = 31` and the next month is April (30 days), `date(year, 4, 31)` raises `ValueError`. The fix is `calendar.monthrange`:

```python
import calendar
from dateutil.relativedelta import relativedelta

def _next_due_date(billing_day: int, today: date) -> date:
    def clamp(year: int, month: int, day: int) -> date:
        last = calendar.monthrange(year, month)[1]  # last valid day of that month
        return date(year, month, min(day, last))

    candidate = clamp(today.year, today.month, billing_day)
    if today < candidate:
        return candidate
    next_month = today + relativedelta(months=1)
    return clamp(next_month.year, next_month.month, billing_day)
```

`calendar.monthrange(year, month)` returns `(weekday_of_first_day, number_of_days)`. Index `[1]` gives the number of days in that month (28/29/30/31). `min(billing_day, last)` clamps 31 → 28 in February.

**Why `relativedelta` instead of adding 30 days?**
`today + timedelta(days=30)` is wrong — it doesn't advance exactly one calendar month. `relativedelta(months=1)` from `python-dateutil` correctly moves from March 31 to April 30, not to April 30 via timedelta arithmetic.

### Resources
- [`python-dateutil` docs](https://dateutil.readthedocs.io/en/stable/)
- [`calendar.monthrange` Python docs](https://docs.python.org/3/library/calendar.html#calendar.monthrange)

---

## 27. localStorage for Frontend Feature State — SMS Templates

### What localStorage Is
`localStorage` is a browser-provided key-value store that persists data between page refreshes and browser sessions. It survives closing and reopening the browser tab. It is scoped to the **origin** (protocol + domain + port), so `http://localhost:5173` and `https://yourapp.com` have separate storage.

### The Pattern Used
```javascript
const STORAGE_KEY = 'sms_templates';

// Read on mount — returns defaults if nothing saved yet
function loadTemplates() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : DEFAULT_TEMPLATES;
    } catch {
        return DEFAULT_TEMPLATES;   // JSON.parse can throw on corrupted data
    }
}

// Write on save
function saveTemplates(templates) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(templates));
}

// Initialize state directly from localStorage (not in useEffect)
const [templates, setTemplates] = useState(loadTemplates);
//                                          ^^^^^^^^^^^
//                                          Pass function reference, not call.
//                                          useState calls it once on first render.
```

**Why `useState(loadTemplates)` not `useState(loadTemplates())`?**
The second form calls `loadTemplates()` on every render — even re-renders where the result is discarded. The first form (lazy initializer) only calls it once on mount. Since `localStorage.getItem` is synchronous and cheap, the difference is small, but the lazy form is the correct React pattern for any computed initial state.

### How Templates Are Stored
Each template is a plain JS object:
```javascript
{
    id: 'default-1',          // unique string ID
    name: 'Rent Reminder',    // display name in the dropdown
    body: 'Hi {name}...',     // the message body with variable tokens
}
```
The entire array is serialized to JSON and stored under the key `'sms_templates'`. On next load, `JSON.parse` restores it.

### Default Templates and First-Run Behaviour
When `localStorage.getItem('sms_templates')` returns `null` (never stored), `loadTemplates` returns `DEFAULT_TEMPLATES`. The first time the user saves changes in "Manage Templates", `saveTemplates` writes to localStorage and subsequent loads return their customized list.

This means **default templates are hardcoded in source** — they are not pushed to localStorage until the user first saves. If you later want to update a default template for all users, you cannot do it via localStorage (it's already saved on their browser). You would need a versioning scheme (e.g., `'sms_templates_v2'` key) or migrate to backend storage.

### What localStorage Is Safe For
| Safe | Not Safe |
|------|----------|
| UI preferences (templates, column widths, theme) | Passwords, tokens, PII |
| Non-sensitive user customizations | Data that must sync across devices |
| Offline-friendly data | Data other users or the server need to read |

### Limits and Risks
- **5 MB limit** per origin — template JSON is tiny, no concern
- **Cleared by users** — browser's "Clear Site Data" wipes it. Users lose their custom templates. This is acceptable for UI customization; not acceptable for business-critical data.
- **Not encrypted** — any JS on your page can read it. Don't store tokens or PII.
- **Synchronous API** — `getItem`/`setItem` block the JS thread. For large data, use `IndexedDB` instead.

### Resources
- [MDN: Window.localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- [MDN: Web Storage API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API)

---

## 28. The "Manage Templates" Modal — How It Was Built

The modal is a self-contained React component (`TemplatesModal`) defined in the same file as `SmsWorkflow.jsx`. It is not a separate file because it is only used in one place and shares no logic with any other component.

### State Inside the Modal
```javascript
const [list, setList]       = useState(templates);   // working copy of templates
const [editing, setEditing] = useState(null);        // { id, name, body } | null
const [isNew, setIsNew]     = useState(false);       // distinguishes new vs edit
```

**Key design:** The modal works on a **local copy** (`list`) of the templates array. Changes inside the modal don't affect the parent until the user clicks "Save Changes". If they close without saving, the parent's `templates` state is unchanged.

When "Save Changes" is clicked:
```javascript
function handleSave() {
    onSave(list);   // calls setTemplates + saveTemplates in parent
    onClose();
}
```

### New vs Edit — Same Form, Different State
Both creating and editing use the same `editing` state object. The only difference is `isNew`:
- `isNew = true` → `commitEdit` appends to list: `[...list, editing]`
- `isNew = false` → `commitEdit` replaces: `list.map(t => t.id === editing.id ? editing : t)`

This avoids duplicating form JSX.

### ID Generation for New Templates
```javascript
{ id: `t-${Date.now()}`, name: '', body: '' }
```
`Date.now()` returns milliseconds since epoch (e.g., `1710432000000`). Combined with the `t-` prefix it produces a practically unique ID for client-side purposes. This is fine for localStorage data. For database storage you would use a UUID.

### Props Interface
```javascript
<TemplatesModal
    templates={templates}   // read: initial data
    onClose={fn}            // called when modal should close
    onSave={fn}             // called with the updated templates array
/>
```
The component is **controlled** — it takes data in and reports changes out. It owns no persistence logic itself.

---

## 29. Controlled vs Uncontrolled React Selects — The `defaultValue` Bug

### The Bug
```jsx
// ❌ Uncontrolled select — React does NOT manage the displayed value
<select
    onChange={e => {
        const tpl = templates.find(t => t.id === e.target.value);
        if (tpl) setMessage(tpl.body);
        e.target.value = '';   // THIS DOES NOTHING IN REACT
    }}
    defaultValue=""
>
```

After the user picks "Rent Reminder", the dropdown shows "Rent Reminder" permanently. `e.target.value = ''` mutates the DOM directly — React immediately overwrites it on the next render with the DOM node's own uncontrolled value.

### Why It Fails
`defaultValue` makes the select **uncontrolled**: React sets its initial value and then ignores it. After that, the browser's DOM manages the displayed value, not React state. Setting `e.target.value` directly bypasses React — it works for one frame, then React's reconciler restores the DOM to whatever the browser thinks the value is.

### The Fix
```jsx
// ✅ Controlled select — React owns the displayed value via state
const [selectedTemplateId, setSelectedTemplateId] = useState('');

<select
    value={selectedTemplateId}   // React drives the display
    onChange={e => {
        const id = e.target.value;
        const tpl = templates.find(t => t.id === id);
        if (tpl) setMessage(tpl.body);
        setSelectedTemplateId('');   // reset to placeholder — React re-renders with ''
    }}
>
    <option value="" disabled>Select a template…</option>
    ...
</select>
```

When `setSelectedTemplateId('')` is called, React re-renders the select with `value=""`, which matches the `<option value="" disabled>` placeholder — so the dropdown resets visually.

### The Rule
**Use `value` + state for any `<select>` that needs to reset after selection.** Use `defaultValue` only when you genuinely want the browser to manage the value and you never need to programmatically reset it.

### Resources
- [React Docs: Uncontrolled Components](https://react.dev/learn/sharing-state-between-components#controlled-and-uncontrolled-components)
- [React Docs: `<select>` element](https://react.dev/reference/react-dom/components/select)

---

## 30. Cursor-Position Variable Insertion in a Textarea

### The Goal
When a user clicks a variable chip (`{name}`, `{rent}`, etc.), the token should be inserted at wherever the cursor currently is in the textarea — not appended to the end.

### The Implementation
```javascript
const textareaRef = useRef(null);

function insertVariable(token) {
    const el = textareaRef.current;
    if (!el) {
        setMessage(prev => prev + token);   // fallback: append
        return;
    }
    const start = el.selectionStart ?? message.length;
    const end   = el.selectionEnd   ?? message.length;

    // Splice the token into the string at cursor position
    const updated = message.slice(0, start) + token + message.slice(end);
    setMessage(updated);

    // Re-focus and move cursor to just after the inserted token
    requestAnimationFrame(() => {
        el.focus();
        el.setSelectionRange(start + token.length, start + token.length);
    });
}
```

### Why Each Part Is Necessary

**`selectionStart` / `selectionEnd`**
These are DOM properties on `<textarea>` and `<input>` that hold the character index of the selection. If nothing is selected, both are equal (the cursor position). If text is selected, `start < end` — clicking a chip replaces the selected text with the token.

**`message.slice(0, start) + token + message.slice(end)`**
Standard string splice: take everything before the cursor, add the token, add everything after the cursor. Works for both cursor-only (start === end) and selection-replace (start < end) cases.

**`requestAnimationFrame`**
This is needed because `setMessage(updated)` triggers a re-render. The re-render resets the textarea's DOM content to the new value. If you call `el.setSelectionRange` synchronously after `setMessage`, the DOM hasn't updated yet — you'd be setting selection on the old content. `requestAnimationFrame` defers the cursor-setting to the next paint frame, after React has committed the new value to the DOM.

**`el.focus()`**
After clicking the chip button, focus moves from the textarea to the button. Without `el.focus()`, the user would need to click back into the textarea to continue typing.

### The `useRef` Attachment
```jsx
<textarea
    ref={textareaRef}
    value={message}
    onChange={e => setMessage(e.target.value)}
    ...
/>
```
`useRef` gives you a stable reference to the underlying DOM node across renders. Unlike `document.getElementById`, it's React-idiomatic and doesn't depend on IDs.

### Resources
- [MDN: HTMLTextAreaElement.selectionStart](https://developer.mozilla.org/en-US/docs/Web/API/HTMLTextAreaElement/selectionStart)
- [MDN: requestAnimationFrame](https://developer.mozilla.org/en-US/docs/Web/API/Window/requestAnimationFrame)
- [React Docs: useRef](https://react.dev/reference/react/useRef)

---

## 31. Optional/Conditional Interactivity on a Shared Component

### The Problem
`KPICard` needed to be clickable for some cards (Total Complaints, Pending, In Progress) and non-interactive for others (Daily Tasks — before we later made it clickable too). Making the component always clickable would require passing a no-op function (`onClick={() => {}}`) everywhere it isn't used, which is ugly and misleading.

### The Pattern
```javascript
export default function KPICard({ label, value, icon: Icon, iconColor, delay, onClick }) {
    const interactive = typeof onClick === 'function';

    return (
        <motion.div
            onClick={onClick}                              // undefined if not passed — no handler attached
            whileHover={interactive ? { scale: 1.02 } : undefined}  // animation only when interactive
            className={cn(
                'bg-card border border-border rounded-xl p-5 transition-all duration-300 group',
                interactive
                    ? 'cursor-pointer hover:border-primary hover:shadow-md'  // clickable styles
                    : 'hover:border-primary',                                 // non-clickable styles
            )}
        >
```

**`typeof onClick === 'function'`** is the guard. If the parent doesn't pass `onClick`, the prop is `undefined`. `undefined` is not a function, so `interactive = false`. The card renders without cursor-pointer, without the scale animation, and `onClick={undefined}` means React attaches no event listener.

**`whileHover={interactive ? { scale: 1.02 } : undefined}`** — passing `undefined` to a framer-motion prop disables it entirely. This is the correct way to conditionally opt out of a motion feature.

### Resources
- [framer-motion: Gestures](https://www.framer.com/motion/gestures/)

---

## 32. Client-Side Sort with Custom Enum Ordering

### The Pattern
The tenant table needed sorting by Name (alphabetic), Flat (alphabetic), and Rent Status (domain-specific order: On-time → Upcoming → At Risk → Overdue).

Alphabetic sort doesn't work for status — "Overdue" comes before "Upcoming" alphabetically, but Overdue is worse and should appear last in an ascending sort that shows best-first.

### The Solution: Order Map
```javascript
const RENT_STATUS_ORDER = { 'On-time': 0, Upcoming: 1, 'At Risk': 2, Overdue: 3 };

function sortTenants(tenants, field, dir) {
    if (!field) return tenants;
    return [...tenants].sort((a, b) => {
        let av, bv;
        if (field === 'name') {
            av = (a.name || '').toLowerCase();
            bv = (b.name || '').toLowerCase();
        } else if (field === 'flat') {
            av = (a.flat_number || '').toLowerCase();
            bv = (b.flat_number || '').toLowerCase();
        } else if (field === 'rent_status') {
            av = RENT_STATUS_ORDER[a.rent_status] ?? 99;   // unknown → sort to end
            bv = RENT_STATUS_ORDER[b.rent_status] ?? 99;
        }
        if (av < bv) return dir === 'asc' ? -1 : 1;
        if (av > bv) return dir === 'asc' ? 1 : -1;
        return 0;
    });
}
```

**`?? 99`** — if a tenant has a `rent_status` not in the map (null, unknown value), they sort to the end regardless of direction. Nullish coalescing (`??`) is safer than `||` here because `0` (index 0 = "On-time") is falsy — `RENT_STATUS_ORDER[x] || 99` would incorrectly give "On-time" the weight 99.

**`[...tenants].sort()`** — `.sort()` mutates the array in place. Spreading first creates a new array, preserving React's immutability contract.

### The Two-Stage Derived List Pipeline
```javascript
const displayTenants = useMemo(() => {
    // Stage 1: search filter
    const q = searchQuery.trim().toLowerCase();
    const filtered = q
        ? tenants.filter(t =>
            (t.name || '').toLowerCase().includes(q) ||
            (t.flat_number || '').toLowerCase().includes(q)
          )
        : tenants;
    // Stage 2: sort
    return sortTenants(filtered, sortField, sortDir);
}, [tenants, searchQuery, sortField, sortDir]);
```

`useMemo` recomputes only when any of the four dependencies change. The pipeline is: all loaded tenants → text filter → sort. This is the idiomatic pattern for client-side table controls.

---

## 33. Pyright Type Checker False Positives and Environment Errors

### Two Types of IDE Errors You'll See

**Type 1: Real code errors**
These are genuine problems in your logic or types. Pay attention to these.

**Type 2: Environment errors**
These appear because the IDE can't find Python packages. Example:
```
Could not find import of `fastapi`, looked at search roots () and site package path ()
```
This error appeared on `fastapi`, `supabase`, and `dateutil` imports in `workflow.py`. These imports existed in the original file and the backend runs fine — the IDE just doesn't have the virtual environment path configured. These are **not real bugs**. The code is correct.

**How to tell them apart:** If the import already existed in the file before you touched it and the backend was running, the error is environmental. If it's a new import you added, verify the package is actually installed.

### The Pyright `str` Slice Error
```
Cannot index into `str`
  No matching overload found for function `str.__getitem__`
```
This appeared on `str(raw)[:10]` — a perfectly valid Python slice. It's a **Pyright version bug**: newer Pyright versions have a regression where certain slice type overloads don't match `slice[int, int, int]`.

**Fix:** Replace the slice with a method call that Pyright can type-check cleanly:
```python
# ❌ Triggers Pyright false positive
date.fromisoformat(str(raw)[:10])

# ✅ Equivalent, no false positive
date.fromisoformat(str(raw).split("T")[0])
```
`split("T")[0]` works for both plain date strings (`"2024-01-15"` → `"2024-01-15"`) and datetime strings (`"2024-01-15T10:00:00"` → `"2024-01-15"`).

---

## 34. Separate Modal Components for Different Data Shapes

### The Decision
The dashboard needed two list modals:
- `DashboardListModal` → shows complaints (has priority badge, status, category, created_at)
- `DailyTasksModal` → shows appointments (has time, flat number, complaint category, notes)

The temptation was to generalize `DashboardListModal` to accept either type via a `type` prop. **This was rejected** because:
- The row structure is completely different
- Merging them would add conditional rendering inside the component, making it harder to read
- The two components will evolve independently

**Rule:** Generalize only when two things are actually the same shape with different data. When the structure is different (different fields, different badges, different actions), separate components are cleaner.

### The Consistent Shell Pattern
Both modals share the same outer structure so the UI feels consistent:
```
fixed inset-0 bg-black/60 backdrop-blur-sm   ← backdrop
  motion.div                                  ← panel (scale in/out)
    header: title + count + close button
    scrollable body: list of row cards
    footer: close button
```
The shell is consistent; only the row card content differs. This is the right granularity for code sharing — share the layout pattern in your head, not in a super-component.

---

## Summary Table — Bugs Fixed in This Chat

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| Template dropdown doesn't reset after selection | `defaultValue=""` makes the select uncontrolled; `e.target.value = ''` is ignored by React | Changed to controlled select with `value={selectedTemplateId}` state that resets to `''` after loading |
| `strftime("%-d")` raises `ValueError` on Windows | `%-d` is a Linux/macOS glibc extension, not available in Windows CRT | Changed to `f"{due.strftime('%B')} {due.day}"` — integer `date.day` has no leading zero |
| `{rent}` / `{date}` variables would send as literal strings | `workflow.py` only resolved `{name}` and `{unit}` | Added rents batch-fetch and per-tenant replacement in the workflow route |
| `flat_uuids` undefined when `{unit}` absent but `{rent}` or `{date}` present | Prerequisite collection was gated only on `needs_unit` | Widened condition to `if needs_unit or needs_rent or needs_date:` |
| Rent Status sort had no column to sort | Plan said "sort by Rent Status" but no Rent Status column existed in the table | Added Rent Status column explicitly before implementing sort |
