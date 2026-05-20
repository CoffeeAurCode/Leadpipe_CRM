# Learning Guide — Session 21
## Topic: Feature Roadmap Execution + RLS Auditing

> **Continues from Session 20** (Google OAuth / PKCE flow).  
> This session built 6 product features end-to-end and audited the database security layer.

---

## What We Built This Session

| Feature | What it does |
|---------|-------------|
| Add Tenant + Assign | Modal to create tenants, assign/unassign to flats bidirectionally |
| Rent Tab | New sidebar view — summary cards, table, inline rent edit, status change |
| Notifications Bell | Bell icon in TopBar with 30-second polling and mark-read |
| Voice Agent Stats | Call volume chart, totals, recent call log with transcript |
| Image Upload audit | Confirmed already working end-to-end |
| VAPI Multi-Manager | Already built — `/flats/identify-caller` existed |

---

## Part 1 — How to Execute a Feature Roadmap

### The Intuition

When you get a list of features to build, the instinct is to start coding immediately. That's a trap. The right sequence is:

```
Read the spec → Explore what already exists → Plan what's missing → Build backend → Build frontend
```

If you build frontend before backend, you're guessing at the API shape. If you build before exploring, you'll duplicate things that already exist (wasting hours) or miss things that are partially built (breaking the codebase).

### The Exploration Methodology We Used

Before writing a single line of code, we read every file that would be touched:

```
backend/app/routes/flats.py        ← what endpoints exist?
backend/app/routes/tenants.py      ← what filters exist?
backend/app/routes/rents.py        ← what's missing?
backend/app/routes/call_logs.py    ← what's missing?
backend/app/main.py                ← what routers are registered?
frontend/src/components/TopBar.jsx ← is the bell already there?
frontend/src/components/Sidebar.jsx ← what nav items exist?
frontend/src/components/TenantManagement.jsx ← is Add Tenant there?
frontend/src/services/apiService.js ← what API calls exist?
frontend/src/App.jsx               ← what views are routed?
```

**Why read all of these?** Because features are never isolated. A "Rent Tab" requires:
- A new backend endpoint (`rents.py`)
- A new API method (`apiService.js`)
- A new component (`RentTab.jsx`)
- A new nav item (`Sidebar.jsx`)
- A new view case (`App.jsx`)

Miss any one of these and the feature doesn't work.

### Establishing Priority Order

The roadmap defined this order:

```
Priority 1: Add Tenant + Assign   ← Core data entry gap
Priority 2: Image Upload          ← Already mostly built — quick win
Priority 3: Rent Tab              ← High business value
Priority 4: Notifications Bell    ← Needs new DB table
Priority 5: VAPI Multi-Manager    ← Backend already done
Priority 6: Voice Agent Stats     ← Analytics, nice-to-have
```

**Principle:** Do foundational data features before display features. You can't show rent data if tenants can't be added. Do quick wins early to build momentum.

---

## Part 2 — FastAPI Patterns (Backend)

### 2.1 Query Parameters for Filtering

The problem: `GET /flats` returns all flats. We need a way to ask for only vacant ones.

**The wrong way:** Create a separate endpoint `GET /flats/vacant`. This creates route explosion — you'd end up with `/flats/vacant`, `/flats/occupied`, `/flats/by-building`, etc.

**The right way:** Add an optional query parameter:

```python
@router.get("")
async def get_all_flats(
    vacant: Optional[bool] = Query(None, description="Return only vacant flats"),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    query = db.table("flats").select("*").order("flat_number")
    if vacant:
        query = query.is_("tenant_uuid", "null")  # IS NULL in Supabase SDK
    return query.execute().data
```

**Supabase SDK note:** To filter for NULL in Supabase Python SDK, use `.is_("column", "null")` — NOT `.eq("column", None)`. The `.eq()` generates `= NULL` which is always false in SQL (NULL comparisons require `IS NULL`).

**Usage:**
```
GET /flats              → all flats
GET /flats?vacant=true  → only flats with no tenant
```

The same pattern was used for tenants:
```python
if unassigned:
    tenants = [t for t in tenants if not t.get("flat_uuid")]
```

Here we fetch all first, then filter in Python. This is fine for small datasets. For large datasets, push the filter to the database query.

### 2.2 The Critical Path Ordering Trap

FastAPI routes are matched **top to bottom**. This creates a well-known trap with literal vs dynamic segments:

```python
# ❌ WRONG ORDER — /rents/summary will match /{flat_uuid} with flat_uuid="summary"
@router.get("/{flat_uuid}")
async def get_active_rent(flat_uuid: str, ...):
    ...

@router.get("/summary")  # This is unreachable
async def get_rent_summary(...):
    ...
```

```python
# ✅ CORRECT ORDER — literal routes before dynamic routes
@router.get("/summary")    # matched first — literal wins
async def get_rent_summary(...):
    ...

@router.get("/{flat_uuid}")  # matched second — dynamic, catches everything else
async def get_active_rent(flat_uuid: str, ...):
    ...
```

**The rule:** Always put literal path segments (`/summary`, `/stats`, `/me`) **before** path parameters (`/{id}`, `/{uuid}`) in the same router.

This was applied in both `rents.py` and `call_logs.py`:

```python
# rents.py — summary BEFORE /{flat_uuid}
@router.get("/summary")
async def get_rent_summary(...): ...

@router.get("/{flat_uuid}")
async def get_active_rent(...): ...
```

```python
# call_logs.py — stats BEFORE the generic GET ""
@router.get("/stats")
async def get_call_stats(...): ...

@router.get("")
async def get_all_call_logs(...): ...
```

### 2.3 Pydantic Models for Request Bodies

Every POST/PATCH endpoint needs a Pydantic model for its request body. Never accept raw dicts — Pydantic validates types, rejects unexpected fields, and generates automatic API docs.

```python
from pydantic import BaseModel

class AssignTenantRequest(BaseModel):
    tenant_uuid: str

class RentStatusUpdate(BaseModel):
    rent_status: str

@router.patch("/{flat_uuid}/assign-tenant")
async def assign_tenant(flat_uuid: str, body: AssignTenantRequest, ...):
    # body.tenant_uuid is a validated string — guaranteed to exist
    ...
```

**Why not just use `request: Request` and read the JSON manually?** You could, but you lose:
- Automatic 422 error if client sends wrong type
- Auto-generated Swagger docs at `/docs`
- IDE autocomplete on `body.field_name`

### 2.4 Bidirectional Foreign Key Updates

The database has two FKs pointing at each other:
- `flats.tenant_uuid` → points to the tenant living there
- `tenants.flat_uuid` → points to the flat the tenant lives in

When you assign a tenant to a flat, you must update **both** or the data is inconsistent. One record would say "flat A101 has tenant X" while the tenant record says "I live in no flat."

```python
# Assign: update BOTH tables
db.table("flats").update({
    "tenant_uuid": body.tenant_uuid,
    "occupied": True,
}).eq("uuid", flat_uuid).execute()

db.table("tenants").update({
    "flat_uuid": flat_uuid,
}).eq("uuid", body.tenant_uuid).execute()
```

```python
# Unassign: clear BOTH tables
db.table("tenants").update({"flat_uuid": None}).eq("uuid", tenant_uuid).execute()
db.table("flats").update({"tenant_uuid": None, "occupied": False}).eq("uuid", flat_uuid).execute()
```

**Order matters for unassign:** Read the flat first (to get `tenant_uuid`), then update the tenant, then update the flat. If you clear `flat.tenant_uuid` first, you lose the reference to which tenant to update.

```python
# ✅ Read first, then update
flat_resp = db.table("flats").select("tenant_uuid").eq("uuid", flat_uuid).execute()
tenant_uuid = flat_resp.data[0].get("tenant_uuid")
if tenant_uuid:
    db.table("tenants").update({"flat_uuid": None}).eq("uuid", tenant_uuid).execute()
db.table("flats").update({"tenant_uuid": None, "occupied": False}).eq("uuid", flat_uuid).execute()
```

### 2.5 Aggregation Endpoints — Joining Data in Python vs SQL

The `/rents/summary` endpoint needed to combine data from three tables: `tenants`, `rents`, `flats`.

**Option A: SQL JOIN**
```sql
SELECT t.name, f.flat_number, r.monthly_rent
FROM tenants t
LEFT JOIN flats f ON t.flat_uuid = f.uuid
LEFT JOIN rents r ON r.flat_uuid = f.uuid AND r.is_active = true
```

In Supabase PostgREST, complex joins require specific syntax and sometimes don't work cleanly with all filter combinations. For a one-off summary endpoint, it's often cleaner to do three simple queries and join in Python.

**Option B: Python join (what we used)**
```python
# Query 1: all tenants
tenants = db.table("tenants").select("uuid, name, phone, flat_uuid, rent_status").execute().data

# Query 2: all active rents
rents = db.table("rents").select("flat_uuid, monthly_rent, effective_from").eq("is_active", True).execute().data
rent_by_flat = {r["flat_uuid"]: r for r in rents}  # dict keyed by flat_uuid for O(1) lookup

# Query 3: all flats (just uuid + flat_number)
flats = db.table("flats").select("uuid, flat_number").execute().data
flat_by_uuid = {f["uuid"]: f for f in flats}

# Merge in Python
for tenant in tenants:
    flat = flat_by_uuid.get(tenant["flat_uuid"])
    rent = rent_by_flat.get(tenant["flat_uuid"])
    row = {
        "flat_number": flat["flat_number"] if flat else None,
        "monthly_rent": rent["monthly_rent"] if rent else None,
        ...
    }
```

**The dict-keying pattern** (`{r["flat_uuid"]: r for r in rents}`) is critical for performance. Without it, for each tenant you'd loop through all rents to find a match — O(n²). With a dict, each lookup is O(1).

**When to use SQL join vs Python join:**
- SQL join: when the dataset is large (>10k rows), when you need pagination, or when you're doing aggregations like COUNT/SUM
- Python join: when datasets are small, when the join logic is complex or conditional, when you need to handle missing data gracefully

### 2.6 The `user["sub"]` Pattern

Every authenticated endpoint can access the logged-in manager's user ID via `user["sub"]`:

```python
async def some_endpoint(
    user: dict = Depends(require_active_subscription),  # returns the JWT payload
    db: Client = Depends(get_authenticated_db),
):
    manager_id = user["sub"]  # "sub" is the JWT standard claim for subject (user ID)
    # use manager_id to scope DB queries...
```

`"sub"` comes from the JWT standard (RFC 7519) — it stands for "subject" and contains the user's unique identifier. Supabase sets this to the UUID from `auth.users`.

### 2.7 Graceful Degradation on Missing Tables

The notifications endpoint was written to not crash if the DB table doesn't exist yet:

```python
@router.get("")
async def get_notifications(...):
    try:
        resp = db.table("notifications").select("*").execute()
        return resp.data or []
    except Exception as e:
        print(f"[notifications] fetch error (table may not exist): {e}")
        return []  # Return empty list — don't crash the app
```

**Why:** The notification table requires a manual SQL migration. If a developer runs the backend before running the migration, the endpoint returns `[]` instead of a 500 error. The bell shows "No notifications" which is correct behavior.

**The principle:** APIs that power UI elements should degrade gracefully. An empty state is always better than a crash.

---

## Part 3 — React Patterns (Frontend)

### 3.1 Modal Pattern

All modals in this codebase follow the same structure. Here's the pattern used in `AddTenantModal.jsx`:

```jsx
export default function AddTenantModal({ isOpen, onClose, onSuccess }) {
    const [form, setForm] = useState(EMPTY_FORM);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    // Reset form whenever modal opens
    useEffect(() => {
        if (!isOpen) return;
        setForm(EMPTY_FORM);
        setError('');
        // Also fetch data needed by the form (e.g., vacant flats dropdown)
        fetchVacantFlats().then(setVacantFlats);
    }, [isOpen]);

    const handleSubmit = async (e) => {
        e.preventDefault();        // Prevent page reload
        setLoading(true);
        setError('');
        try {
            const result = await createTenant(form);
            onSuccess?.(result);   // Tell parent about the new record
            onClose();             // Close the modal
        } catch (err) {
            setError(err.message); // Show error in the modal, not an alert
        } finally {
            setLoading(false);     // Always re-enable the button
        }
    };

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
                    onClick={(e) => { if (e.target === e.currentTarget) onClose(); }} // click outside to close
                >
                    {/* Modal content */}
                </motion.div>
            )}
        </AnimatePresence>
    );
}
```

**Key decisions:**
- `AnimatePresence` + `motion.div`: Framer Motion handles the fade-in/out animation
- `if (e.target === e.currentTarget) onClose()`: Only close when clicking the dark overlay, not the modal card itself
- `useEffect([isOpen])`: Re-fetch data every time the modal opens — avoids stale data
- `onSuccess?.(result)`: The `?.` is optional chaining — safe to call even if `onSuccess` wasn't passed
- Error in UI, not `alert()`: Never use `alert()` in production UI. Show errors inline.

### 3.2 Optimistic vs Server-Confirmed Updates

When the user changes a rent status in the table, we have two options:

**Optimistic update** (update UI immediately, then sync):
```jsx
// Update UI first, API call second
setData(prev => ({
    ...prev,
    rows: prev.rows.map(r => r.tenant_uuid === id ? { ...r, rent_status: newStatus } : r)
}));
await updateTenantRentStatus(id, newStatus); // if this fails, UI is wrong
```

**Server-confirmed update** (wait for API, then update):
```jsx
// API call first, update UI on success
await updateTenantRentStatus(id, newStatus);
setData(prev => ({
    ...prev,
    rows: prev.rows.map(r => r.tenant_uuid === id ? { ...r, rent_status: newStatus } : r)
}));
```

**We used server-confirmed** in `RentTab.jsx` because rent status is financial data — showing incorrect data even briefly is worse than a slight UI delay.

**Use optimistic updates for:** likes, toggles, non-critical preferences  
**Use server-confirmed for:** financial data, permissions, anything shown to others

### 3.3 Lazy Loading Routes

In `App.jsx`, new views are loaded lazily:

```jsx
// These are NOT imported at the top of the file with regular imports
const RentTab       = lazy(() => import('./components/RentTab'));
const VoiceStatsTab = lazy(() => import('./components/VoiceStatsTab'));
```

**Why lazy?** Regular imports bundle everything into one JS file. With lazy imports, `RentTab.jsx` is only downloaded when the user first clicks "Rent" in the sidebar.

**Why does this matter?** A user who never uses the Rent tab never downloads that code. Smaller initial bundle = faster first page load.

**How it works:**
1. `lazy()` returns a special React component
2. `<Suspense fallback={<Loading />}>` wraps the component
3. When first rendered, React pauses, downloads the chunk, then renders
4. On subsequent renders, it's cached — instant

### 3.4 Polling Pattern for Notifications

The notification bell polls the server every 30 seconds:

```jsx
useEffect(() => {
    load(); // load immediately on mount

    // Poll every 30 seconds, but only when tab is visible
    const id = setInterval(() => {
        if (!document.hidden) load(); // document.hidden = true when tab is in background
    }, 30000);

    // Also reload when user switches back to this tab
    const onVisible = () => { if (!document.hidden) load(); };
    document.addEventListener('visibilitychange', onVisible);

    // Cleanup: stop polling when component unmounts
    return () => {
        clearInterval(id);
        document.removeEventListener('visibilitychange', onVisible);
    };
}, [load]);
```

**`document.hidden`**: Browser API that tells you if the tab is in the background. When true, the user can't see the page — no point making API calls. This is called the Page Visibility API.

**Why 30 seconds?** Notifications are not real-time critical. 30 seconds is frequent enough to feel responsive but doesn't hammer the server. WebSockets would be instant but overkill for MVP.

**The cleanup function:** The `return` from `useEffect` is called when the component unmounts (e.g., user logs out). Without it, the interval keeps running and calling `load` on a dead component — causing memory leaks and "can't update unmounted component" errors.

### 3.5 Click-Outside-to-Close Pattern

The notification panel closes when you click anywhere outside it:

```jsx
const panelRef = useRef(null);

useEffect(() => {
    if (!open) return;
    const handle = (e) => {
        // If the click target is NOT inside the panel, close it
        if (panelRef.current && !panelRef.current.contains(e.target)) {
            setOpen(false);
        }
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
}, [open]);

return (
    <div ref={panelRef}>  {/* Attach ref to the panel container */}
        <button onClick={() => setOpen(o => !o)}>...</button>
        {open && <div>...panel content...</div>}
    </div>
);
```

**How `contains()` works:** `element.contains(target)` returns true if `target` is the element itself OR any of its descendants. So clicking anywhere inside the panel (buttons, text, scrollbar) returns true and does NOT close it. Clicking outside returns false and closes it.

### 3.6 SVG-Free Bar Chart

The voice stats chart uses only divs and CSS — no chart library needed:

```jsx
function BarChart({ byDate }) {
    const entries = Object.entries(byDate).sort((a, b) => a[0].localeCompare(b[0]));
    const maxVal = Math.max(...entries.map(([, v]) => v), 1); // avoid division by zero

    return (
        <div className="flex items-end gap-1 h-24">
            {entries.map(([date, count]) => (
                <div key={date} title={`${date}: ${count} calls`}
                    className="flex flex-col items-center flex-1">
                    <div
                        className="w-full rounded-t bg-primary/60"
                        style={{ height: `${(count / maxVal) * 80}px` }} // scale to max height
                    />
                </div>
            ))}
        </div>
    );
}
```

**The math:** `(count / maxVal) * 80` — divide by max to normalize to 0–1 range, multiply by 80 (max pixel height). The tallest bar is always 80px; all others scale proportionally.

**When to use a chart library (recharts, chart.js):** When you need tooltips, zoom, axes labels, legends, animations, or line/pie/scatter charts. For a simple bar chart like this, a div is 100 lines vs 300 lines and zero dependencies.

### 3.7 Tabbed Modal Pattern

`AssignTenantModal.jsx` uses two tabs — "Existing Tenant" vs "New Tenant":

```jsx
const [tab, setTab] = useState('existing');

// Tab buttons
{['existing', 'new'].map(id => (
    <button
        key={id}
        onClick={() => setTab(id)}
        className={tab === id ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground'}
    >
        {id === 'existing' ? 'Existing Tenant' : 'New Tenant'}
    </button>
))}

// Conditional content
{tab === 'existing' ? (
    <select>...</select>  // dropdown of unassigned tenants
) : (
    <input placeholder="Name" />  // mini form for new tenant
)}
```

**Why tabs instead of two modals?** One modal with tabs keeps the UX compact and the code co-located. The parent component (`PropertiesPage`) only needs to manage one `isOpen` boolean.

---

## Part 4 — Database Row Level Security (RLS) Audit

### 4.1 What is RLS and Why it Matters

Row Level Security (RLS) is a PostgreSQL feature that adds an automatic WHERE clause to every query based on who's asking.

**Without RLS:**
```sql
SELECT * FROM tenants;
-- Returns ALL tenants from ALL managers
-- Manager A can see Manager B's tenants
```

**With RLS + policy:**
```sql
-- Policy: (flat_uuid IN (SELECT f.uuid FROM flats f JOIN buildings b ... WHERE p.manager_id = auth.uid()))
SELECT * FROM tenants;
-- PostgreSQL automatically adds the policy as a WHERE clause
-- Returns ONLY the tenants belonging to the authenticated manager
```

**The key insight:** RLS enforces multi-tenancy at the database layer, not just the application layer. Even if a bug in the FastAPI code tried to fetch all tenants, the database would silently filter to only the current user's data.

**Two levels of protection in this codebase:**
1. **FastAPI** (`require_active_subscription` dependency) — checks JWT, checks subscription status
2. **Supabase RLS** (at DB level) — filters rows by `auth.uid()` regardless of the query

Both layers must be healthy. If the FastAPI layer had a bug, RLS is the safety net.

### 4.2 Querying RLS Status

Run these in the Supabase SQL editor to audit your database:

**Which tables have RLS enabled?**
```sql
SELECT tablename, rowsecurity AS rls_enabled
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;
```

**What policies exist on each table?**
```sql
SELECT tablename, policyname, roles, cmd AS operation, qual AS using_expr, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

**Combined view — most useful for auditing:**
```sql
SELECT
    t.tablename,
    t.rowsecurity AS rls_on,
    p.policyname,
    p.roles,
    p.cmd AS operation,
    p.qual AS using_expr
FROM pg_tables t
LEFT JOIN pg_policies p
    ON t.tablename = p.tablename AND t.schemaname = p.schemaname
WHERE t.schemaname = 'public'
ORDER BY t.tablename, p.policyname;
```

**Check if a specific column exists:**
```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'call_logs' AND column_name = 'property_group_id';
```

### 4.3 Reading the Audit Results

Here's what we found and what each result means:

| State | Meaning | Risk |
|-------|---------|------|
| `rls_on = false`, no policy | Table is fully open — any authenticated user can read/write all rows | 🔴 HIGH (unless intentional) |
| `rls_on = true`, no policy | RLS is on but no policy allows anything — **all access is blocked** | 🔴 HIGH (broken feature) |
| `rls_on = true`, policy with `auth.uid()` | Normal — each manager sees only their own data | ✅ Correct |
| `rls_on = false`, only service role writes | Intentional bypass — webhook uses service role which ignores RLS | ✅ OK if understood |

**What we found:**

```
notifications  → rls_on = true, policy = null (in LEFT JOIN output)
```

This looked like a problem (no policy = blocked). But when we queried `pg_policies` directly, the policy existed with correct `auth.uid()` filtering. The LEFT JOIN showed null because of how the query rendered — not a real gap.

**The ownership chain pattern used throughout:**

```sql
-- tenants policy: can only see tenants whose flat is in your building
(flat_uuid IN (
    SELECT f.uuid FROM flats f
    JOIN buildings b ON f.building_id = b.id
    JOIN properties_list p ON b.property_id = p.id
    WHERE p.manager_id = auth.uid()
))
```

This walks: `tenant → flat → building → property → manager_id`. Every table that's more than one hop from `properties_list` uses this chain.

### 4.4 The `service_role` vs `anon`/`authenticated` Pattern

Supabase has multiple client types:

| Client | Key used | Bypasses RLS? | Use case |
|--------|----------|--------------|---------|
| `anon` | Anon key | No | Public pages |
| `authenticated` | User JWT | No (RLS applies) | Normal user operations |
| `service_role` | Service role key | **Yes** | Webhooks, admin operations, migrations |

In this codebase, there are two DB clients:

```python
# backend/app/db/session.py
def get_authenticated_db():
    # Uses the user's JWT — RLS applies
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=ClientOptions(
        headers={"Authorization": f"Bearer {user_token}"}
    ))

def get_service_db():
    # Uses the service role key — RLS bypassed
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
```

**The Stripe webhook uses `get_service_db`:**
```python
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Client = Depends(get_service_db),  # ← service role!
):
```

**Why?** The webhook comes from Stripe's servers — there's no user logged in. There's no JWT to validate. The webhook must write to `subscriptions` and `stripe_events` without being a logged-in manager. Service role is the only way.

**Why is `stripe_events` RLS-off safe?** Because only the webhook writes to it, and the webhook is authenticated by Stripe's signature verification (`stripe.Webhook.construct_event`). No user can reach that table — it's just for idempotency tracking.

### 4.5 The Subscription Policy Gap (Intentional)

```
subscriptions → rls_on = true, policy = SELECT only (no INSERT or UPDATE)
```

This looks like a bug — managers can't insert or update their own subscription. But it's intentional:

- **INSERT** happens in the webhook (`get_service_db`, bypasses RLS) and in `verify-session` (`get_service_db`)
- **UPDATE** happens in the webhook only
- **SELECT** is what managers need — to check if they have an active subscription

If a manager could INSERT their own subscription row (without going through Stripe payment), they could give themselves free access. The SELECT-only policy prevents this while still allowing the subscription check.

**Rule of thumb:** Subscription/billing tables should only be writable via service role (backend webhooks). Users should only be able to read them.

---

## Part 5 — Diagnosing Issues (Commands Reference)

### 5.1 Syntax-Check Python Files Without Running the Server

After editing backend files, check for syntax errors instantly:

```bash
python -c "
import ast, sys
files = [
    'backend/app/routes/flats.py',
    'backend/app/routes/tenants.py',
    'backend/app/routes/rents.py',
    'backend/app/routes/call_logs.py',
    'backend/app/routes/notifications.py',
    'backend/app/main.py',
]
for f in files:
    try:
        with open(f) as fh:
            ast.parse(fh.read())
        print(f'OK: {f}')
    except SyntaxError as e:
        print(f'ERROR: {f} — {e}')
        sys.exit(1)
"
```

`ast.parse()` runs Python's parser without executing any code. It catches syntax errors, wrong indentation, unclosed brackets — everything that would crash the server on startup.

### 5.2 Verify All Frontend Files Exist

```bash
node -e "
const fs = require('fs');
const files = [
    'frontend/src/components/AddTenantModal.jsx',
    'frontend/src/components/RentTab.jsx',
    'frontend/src/components/NotificationPanel.jsx',
];
files.forEach(f => {
    const exists = fs.existsSync(f);
    console.log(exists ? 'OK' : 'MISSING', f, exists ? fs.statSync(f).size + 'B' : '');
});
"
```

### 5.3 Check Which Routes Are Registered

```bash
# Start the backend and query the OpenAPI spec
curl http://localhost:8000/openapi.json | python -c "
import json, sys
spec = json.load(sys.stdin)
for path in sorted(spec['paths'].keys()):
    methods = list(spec['paths'][path].keys())
    print(f'{\" \".join(m.upper() for m in methods):30s} {path}')
"
```

Or just open `http://localhost:8000/docs` in a browser — FastAPI auto-generates Swagger UI.

### 5.4 Test a New Endpoint Manually

```bash
# Test the rent summary endpoint (replace TOKEN with a real JWT)
curl -s \
  -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/rents/summary | python -m json.tool
```

```bash
# Test with vacant=true filter
curl -s \
  -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/flats?vacant=true" | python -m json.tool
```

### 5.5 Check a Database Column Exists (SQL)

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'call_logs'
ORDER BY ordinal_position;
```

---

## Part 6 — Full File Change Map

### New Backend Files
```
backend/app/routes/notifications.py   ← GET/POST /notifications, PATCH /read, POST /read-all
```

### Modified Backend Files
```
backend/app/routes/flats.py
  + vacant query param on GET /flats
  + PATCH /{uuid}/assign-tenant
  + PATCH /{uuid}/unassign-tenant
  + AssignTenantRequest Pydantic model

backend/app/routes/tenants.py
  + unassigned query param on GET /tenants
  + bidirectional flat link in POST /tenants
  + PATCH /{uuid}/rent-status
  + RentStatusUpdate Pydantic model

backend/app/routes/rents.py
  + GET /rents/summary  (placed BEFORE /{flat_uuid})

backend/app/routes/call_logs.py
  + GET /call_logs/stats  (placed BEFORE GET "")

backend/app/main.py
  + import notifications
  + app.include_router(notifications.router)
```

### New Frontend Files
```
frontend/src/components/AddTenantModal.jsx    ← full add-tenant form
frontend/src/components/AssignTenantModal.jsx ← assign existing or new tenant to flat
frontend/src/components/RentTab.jsx           ← rent overview page
frontend/src/components/VoiceStatsTab.jsx     ← voice agent analytics page
frontend/src/components/NotificationPanel.jsx ← bell dropdown with polling
```

### Modified Frontend Files
```
frontend/src/services/apiService.js
  + fetchVacantFlats, fetchUnassignedTenants
  + createTenant, updateTenantRentStatus
  + assignTenantToFlat, unassignTenantFromFlat
  + fetchRentSummary, fetchCallStats, fetchCallLogs
  + fetchNotifications, markNotificationRead, markAllNotificationsRead, createNotification

frontend/src/components/TopBar.jsx
  + <NotificationPanel /> added to header

frontend/src/components/Sidebar.jsx
  + IndianRupee, PhoneCall added to Lucide imports
  + 'rent' nav item (after Properties)
  + 'voice-stats' nav item (after Complaints)

frontend/src/components/TenantManagement.jsx
  + UserPlus icon import
  + AddTenantModal import
  + addModalOpen state
  + "Add Tenant" button in header
  + <AddTenantModal> rendered with onSuccess handler

frontend/src/App.jsx
  + lazy import RentTab, VoiceStatsTab
  + currentView === 'rent' → <RentTab />
  + currentView === 'voice-stats' → <VoiceStatsTab />
```

---

## Part 7 — DB Migration Required

Run this in the Supabase SQL editor **before using the notifications bell**:

```sql
-- Create notifications table
CREATE TABLE IF NOT EXISTS notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  manager_id UUID REFERENCES auth.users(id),
  title TEXT NOT NULL,
  body TEXT NOT NULL,
  type TEXT NOT NULL,          -- 'appointment' | 'complaint' | 'rent' | 'system'
  entity_id UUID,              -- optional: link to appointment/complaint/etc.
  is_read BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for fast per-manager queries sorted by time
CREATE INDEX IF NOT EXISTS idx_notifications_manager
  ON notifications(manager_id, created_at DESC);

-- RLS policy (if not already created)
CREATE POLICY manager_owns_notifications ON notifications
FOR ALL TO public
USING (manager_id = auth.uid())
WITH CHECK (manager_id = auth.uid());
```

---

## Part 8 — Key Concepts Summary

| Concept | One-line explanation |
|---------|---------------------|
| Query parameter | Optional `?key=value` appended to URL — use for filters, not for required data |
| Path ordering in FastAPI | Literal routes (`/summary`) must come before dynamic routes (`/{id}`) |
| Bidirectional FK | Two tables pointing at each other — always update both in the same operation |
| Python dict join | Build a `{key: row}` dict from one table, then O(1) lookup for each row of another |
| Pydantic model | Python class that validates request body shape — required for every POST/PATCH body |
| `user["sub"]` | The logged-in manager's UUID — comes from the JWT `sub` (subject) claim |
| RLS | PostgreSQL feature that adds automatic WHERE clauses based on who's querying |
| `service_role` | DB client that bypasses RLS — use only for webhooks and admin operations |
| Ownership chain | RLS policy that walks `table → flat → building → property → manager_id = auth.uid()` |
| Lazy import | React `lazy()` defers downloading a component until first rendered — faster initial load |
| `useEffect` cleanup | Returning a function from useEffect that stops intervals/listeners when component unmounts |
| Graceful degradation | API returns `[]` instead of crashing when DB table doesn't exist yet |
| `document.hidden` | Browser API — true when tab is in background; use to pause polling |
| `contains()` | DOM method: `el.contains(target)` — true if target is inside el; used for click-outside detection |

---

## Resources to Learn More

### FastAPI
- [FastAPI Query Parameters](https://fastapi.tiangolo.com/tutorial/query-params/) — how optional params work
- [FastAPI Path Operation Order](https://fastapi.tiangolo.com/tutorial/path-params/#order-matters) — why literal before dynamic
- [FastAPI Body with Pydantic](https://fastapi.tiangolo.com/tutorial/body/) — request body models
- [FastAPI Dependencies](https://fastapi.tiangolo.com/tutorial/dependencies/) — how `Depends()` works

### Supabase / PostgreSQL
- [Supabase RLS Guide](https://supabase.com/docs/guides/database/postgres/row-level-security) — full RLS documentation
- [Supabase Python SDK](https://supabase.com/docs/reference/python/introduction) — all client methods including `.is_()`, `.in_()`, etc.
- [PostgreSQL IS NULL](https://www.postgresql.org/docs/current/functions-comparison.html) — why `= NULL` is wrong
- [pg_policies system catalog](https://www.postgresql.org/docs/current/catalog-pg-policy.html) — all columns available for RLS audit
- [JWT Claims (RFC 7519)](https://www.rfc-editor.org/rfc/rfc7519#section-4.1) — what `sub`, `aud`, `exp` mean

### React Patterns
- [React lazy + Suspense](https://react.dev/reference/react/lazy) — code splitting
- [useEffect cleanup](https://react.dev/learn/synchronizing-with-effects#how-to-handle-the-effect-firing-twice-in-development) — why and how to clean up
- [Page Visibility API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API) — `document.hidden` and `visibilitychange`
- [Node.contains (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Node/contains) — click-outside detection
- [Framer Motion AnimatePresence](https://www.framer.com/motion/animate-presence/) — mounting/unmounting animations

### General
- [SQL NULL handling](https://www.postgresql.org/docs/current/functions-comparison.html) — IS NULL vs = NULL
- [O(1) vs O(n²) lookups](https://www.bigocheatsheet.com/) — why dict-keying matters for performance
- [Stripe webhook verification](https://stripe.com/docs/webhooks/signatures) — how `construct_event` validates the signature

---

---

# Appendix — Session 21 Addendum: Google OAuth Deployment Debugging

> Added after deploying the multi-app auth system to production.
> The code was correct. Everything below is configuration — the hardest kind of bug to debug.

---

## The Architecture (Read This First)

This project has **three separate deployments** that work together for auth:

```
[1] leadpipe.ca          — Next.js landing + auth page (Google OAuth starts here)
         |
         ↓  redirectTo: https://www.leadpipe.ca/auth/callback
[2] Supabase             — Auth server (OAuth callback handler)
    (nfgnxndktecqeleabbip.supabase.co/auth/v1/callback)
         |
         ↓  redirects back to: https://www.leadpipe.ca/auth/callback?code=...
[1] leadpipe.ca/auth/callback  — Exchanges code, checks manager_profiles
         |
         ├── New user  → /pricing  (on leadpipe.ca)
         |
         └── Existing user → https://test--leadpipecrm.netlify.app
                             #access_token=...&refresh_token=...
                                      |
[3] test--leadpipecrm.netlify.app — React CRM app
    detects tokens in URL hash via detectSessionInUrl: true
```

The backend (`tenant-management-mvp.onrender.com`) is **not involved in auth at all** — it only receives API calls after the user is logged in.

---

## Mistake 1 — Wrong Google Console "Authorized JavaScript Origins"

### What was set
```
https://tenant-management-mvp.onrender.com
```

### Why it's wrong
The "Authorized JavaScript origins" field tells Google **which domain is allowed to initiate the OAuth flow**. The OAuth flow starts when the user clicks "Continue with Google" on `leadpipe.ca`.

`tenant-management-mvp.onrender.com` is the **FastAPI backend** — it has no browser UI and never initiates any OAuth flow. Putting the backend URL there does nothing useful.

### What it should be
```
https://www.leadpipe.ca
```

### The rule
> Authorized JavaScript Origins = the domain where your `signInWithOAuth()` call runs in the browser.

If you also have a Google OAuth button directly on the CRM frontend (which `AuthPage.jsx` does have as a fallback), you'd add that too:
```
https://www.leadpipe.ca
https://test--leadpipecrm.netlify.app
```

### How to remember this
Draw the flow. Find the line that says `signInWithOAuth({ provider: 'google' })`. Look at what domain that code runs on. That's your JS origin.

---

## Mistake 2 — Supabase Redirect URLs Not Set for Production

### What happens without this
After Google authenticates the user, Supabase redirects to your `redirectTo` URL:
```
https://www.leadpipe.ca/auth/callback
```

Supabase maintains a **whitelist** of allowed redirect destinations. If `https://www.leadpipe.ca/auth/callback` is not in that list, Supabase rejects the callback and the user gets an error — even though Google auth succeeded.

### Where to fix it
Supabase Dashboard → Authentication → URL Configuration:

| Setting | Value |
|---------|-------|
| Site URL | `https://www.leadpipe.ca` |
| Redirect URLs | `https://www.leadpipe.ca/auth/callback` |
| Redirect URLs (add) | `https://test--leadpipecrm.netlify.app` |

### Why both URLs?
- `https://www.leadpipe.ca/auth/callback` — where the PKCE code lands after Google redirects back
- `https://test--leadpipecrm.netlify.app` — where the cross-app token handoff delivers the session (the CRM's Supabase client must be allowed to receive it)

### The exact-match requirement
Supabase matches redirect URLs **exactly** — no trailing slash, no www vs non-www mismatch. The `redirectTo` value you pass in code must match character-for-character what's in the dashboard.

```js
// Code says:
redirectTo: `${window.location.origin}/auth/callback`
// window.location.origin on production = "https://www.leadpipe.ca"
// Final value: "https://www.leadpipe.ca/auth/callback"

// Dashboard must contain exactly:
// https://www.leadpipe.ca/auth/callback   ✓
// NOT: https://www.leadpipe.ca/auth/callback/  ← trailing slash = mismatch
// NOT: https://leadpipe.ca/auth/callback   ← missing www = mismatch
```

**Diagnostic trick:** Open the browser console on the deployed site and run:
```js
window.location.origin
```
Copy-paste that exact string (plus `/auth/callback`) into the Supabase redirect URLs list.

---

## Mistake 3 — Production Env Vars Left as Localhost

### In `Leadpipe-1/.env.local`
```bash
# NEXT_PUBLIC_BACKEND_URL=https://tenant-management-mvp.onrender.com  # commented out
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000                          # active

# NEXT_PUBLIC_FRONTEND_URL=https://test--leadpipecrm.netlify.app      # commented out
NEXT_PUBLIC_FRONTEND_URL=http://localhost:5173                         # active
```

**Effect:** In production, `auth/callback/page.tsx` line 55 does:
```js
const frontendUrl = process.env.NEXT_PUBLIC_FRONTEND_URL;
window.location.href = `${frontendUrl}#access_token=...`
// → http://localhost:5173#access_token=...
// The user's browser opens localhost — which doesn't exist on their machine
```

The user would get a "This site can't be reached" error after successfully authenticating.

### Fix
Set these as environment variables on the hosting platform (Vercel for Next.js):
```
NEXT_PUBLIC_BACKEND_URL  = https://tenant-management-mvp.onrender.com
NEXT_PUBLIC_FRONTEND_URL = https://test--leadpipecrm.netlify.app
```

### In `frontend/.env` (CRM on Netlify)
```bash
VITE_API_URL=http://localhost:8000   ← still localhost
```

**Effect:** Every API call from the CRM goes to localhost:8000 on the user's machine — which doesn't exist. Every feature breaks silently (network errors).

### Fix
Set in Netlify Dashboard → Site settings → Environment variables:
```
VITE_API_URL = https://tenant-management-mvp.onrender.com
```

### The pattern
`.env` files are for **local development defaults**. Production values must be set in the hosting platform's environment variable UI — they are never committed to the repo (and shouldn't be, since `.env` is in `.gitignore`).

---

## Mistake 4 — SPA Routing: `_redirects` File Missing

### The problem
The CRM is a **Single Page Application** (SPA). There is only one real HTML file: `index.html`. All routing (`/dashboard`, `/auth`, etc.) is handled by React in the browser.

When Netlify serves a SPA and the user lands directly on a deep URL like:
```
https://test--leadpipecrm.netlify.app#access_token=...
```
Netlify's CDN looks for a file at that path. It's a hash (`#`) so this particular case doesn't break — Netlify serves `index.html` for `/`. But if the landing were a path like `/auth/callback`, Netlify would return 404.

More critically: if Netlify does **any internal HTTP redirect** (e.g., HTTP → HTTPS, or `www` stripping) before reaching your React app, the browser opens a new navigation context, which **wipes `sessionStorage`**. With PKCE flow, the code verifier is in `sessionStorage` — if it's gone, `exchangeCodeForSession` fails.

### Fix
Add `frontend/public/_redirects`:
```
/*  /index.html  200
```

This tells Netlify to serve `index.html` for every URL path, letting React Router handle routing client-side without any server-side redirects. The PKCE verifier survives because there's no redirect — just a direct file serve.

### Vite + Netlify specifics
Files in `frontend/public/` are copied to the build output root (`dist/`) as-is during `vite build`. Netlify reads `_redirects` from the root of the published directory. So `frontend/public/_redirects` is the correct location.

---

## The Cross-Domain Token Handoff Pattern

The most architecturally interesting part of this system: how does a session created on `leadpipe.ca` end up authenticated on `test--leadpipecrm.netlify.app`?

### Why you can't share cookies
Browser cookies are scoped to a domain. A `Set-Cookie` header from `leadpipe.ca` is invisible to `netlify.app`. So you can't just "log in" on one domain and have the session carry over.

### The approach: URL hash token delivery
```js
// In leadpipe.ca/auth/callback
window.location.href = `${frontendUrl}#access_token=${session.access_token}&refresh_token=${session.refresh_token}&token_type=bearer&type=recovery`;
```

The access token and refresh token are placed in the **URL hash fragment** (`#`). Hash fragments are never sent to the server — they're only visible to JavaScript running in the browser.

### How the CRM receives it
`frontend/src/lib/supabase.js` has `detectSessionInUrl: true`. When the Supabase JS client initializes, it checks the URL. If it finds `#access_token=...&refresh_token=...` in the hash, it calls `setSession()` internally and fires `INITIAL_SESSION` via `onAuthStateChange`.

`AuthContext.jsx` listens for `INITIAL_SESSION` and sets the user state — the app is now authenticated.

### Why `type=recovery`?
This is a quirk of the Supabase JS client's hash parsing. The client parses hash fragments with a format originally designed for magic links and password resets. Using `type=recovery` signals to the client that the hash contains token data to be consumed. It's a convention from Supabase's internal format, not a security mechanism.

### Security considerations
- The tokens are visible in the browser's address bar during the redirect — only for a moment, but still visible
- They're cleared from the URL by Supabase's `detectSessionInUrl` once consumed
- The tokens are short-lived (access token: ~1 hour) and the refresh token is rotated on use
- HTTPS ensures the URL isn't intercepted in transit

This pattern is acceptable for a SaaS MVP. A more robust approach would use a short-lived one-time code in the URL and exchange it server-side — but that requires a backend session store, which adds significant complexity.

---

## Diagnostic Checklist (for future deployments)

Run through this in order when Google OAuth isn't working on a new deployment:

```
Step 1 — Open the browser console. Click "Continue with Google".
         Does the page redirect to accounts.google.com?
         NO → Google Console JS origin is wrong. Fix: add the current domain to Authorized JS Origins.
         YES → continue

Step 2 — After Google login, do you land back on your app or get a Google error page?
         Google error ("redirect_uri_mismatch") → The Supabase callback URL is not in Google Console Authorized Redirect URIs.
         Fix: add https://<project>.supabase.co/auth/v1/callback
         Lands on app → continue

Step 3 — Does the /auth/callback page show an error or redirect to login?
         YES → Supabase rejected the redirect. Check:
               - Supabase Dashboard → Auth → URL Configuration → Redirect URLs
               - Does it contain the exact URL (including /auth/callback path)?
               - Run window.location.origin in console and compare character by character

Step 4 — Does the callback redirect to localhost instead of production?
         YES → Environment variable NEXT_PUBLIC_FRONTEND_URL is not set in the hosting platform.
               Check Vercel/Netlify environment variables, not .env files.

Step 5 — Does the CRM load but show API errors / 404s?
         YES → VITE_API_URL is not set in Netlify environment variables.
               Set VITE_API_URL=https://tenant-management-mvp.onrender.com in Netlify dashboard.

Step 6 — Does the CRM load at all? Does refreshing the page break it?
         Refresh breaks it → Missing _redirects file for SPA routing.
         Add frontend/public/_redirects with content: /*  /index.html  200
```

---

## Summary Table — All Config Locations

| What | Where (not in code) | Correct Value |
|------|---------------------|---------------|
| Google OAuth JS origin | Google Cloud Console → OAuth client → Authorized JS origins | `https://www.leadpipe.ca` |
| Google OAuth redirect URI | Google Cloud Console → OAuth client → Authorized redirect URIs | `https://nfgnxndktecqeleabbip.supabase.co/auth/v1/callback` |
| Supabase site URL | Supabase Dashboard → Auth → URL Configuration | `https://www.leadpipe.ca` |
| Supabase redirect whitelist | Supabase Dashboard → Auth → Redirect URLs | `https://www.leadpipe.ca/auth/callback`, `https://test--leadpipecrm.netlify.app` |
| Landing page prod env vars | Vercel project settings → Environment Variables | `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_FRONTEND_URL` |
| CRM prod env vars | Netlify site settings → Environment Variables | `VITE_API_URL` |
| SPA routing (Netlify) | `frontend/public/_redirects` (in code) | `/*  /index.html  200` |

---

## Key Concepts from This Appendix

| Concept | One-line explanation |
|---------|---------------------|
| Authorized JS Origins | Google Console field — the domain where your `signInWithOAuth()` runs, NOT the backend |
| Authorized Redirect URIs | Google Console field — always the Supabase callback URL, never your app URL |
| Supabase Redirect Whitelist | Supabase rejects any `redirectTo` value not explicitly listed in the dashboard |
| Exact-match redirect URLs | No trailing slash tolerance — `leadpipe.ca/auth/callback` ≠ `leadpipe.ca/auth/callback/` |
| Cross-domain token handoff | Pass `access_token` + `refresh_token` in URL hash to share session across domains |
| `detectSessionInUrl` | When true, Supabase JS auto-reads `#access_token=` from the URL on page load |
| SPA `_redirects` | Tells Netlify/Render to serve `index.html` for all paths, preventing CDN 404s |
| Production env vars | Never set in `.env` (git-tracked); always set in hosting platform's environment variable UI |
