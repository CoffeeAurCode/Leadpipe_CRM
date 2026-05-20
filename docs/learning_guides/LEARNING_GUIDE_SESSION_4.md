# Learning Guide Session 4: Premium Dark-Themed Dashboard — Design Systems, Component Architecture, and API Integration

**Role:** Senior Staff Engineer Mentorship
**Objective:** Replace the basic frontend scaffold with a production-quality dark-themed dashboard. Learn to analyze a design reference, extract a design system, build reusable components, and handle real-world backend failures gracefully.

---

## 1. What Was Built in This Session

| Deliverable | Description |
|---|---|
| Dark design system | CSS custom properties + Tailwind config for consistent tokens |
| Bento grid layout | CSS Grid dashboard with variable-size complaint cards |
| Stats summary row | Total / Pending / Resolved / High-priority counters |
| Complaint card component | Status badge, category icon, truncated description, update action |
| Animated transitions | Framer Motion page transitions and card hover effects |
| Sidebar navigation | View switcher for Dashboard / Calendar / Properties / Tenants |
| Backend fallback | Graceful handling when backend is unreachable |

---

## 2. The Senior Developer Approach to Design Implementation

Before writing one line of code, analyze the reference design. Extract the design system from it. Then build the system — not individual screens.

### 2.1 Extract Before Coding

From any reference screenshot or Figma file, identify:

**Colors:**
```
Background: #0a0a0a   (near-black page background)
Surface: #141414      (slightly lighter card background)
Border: #2a2a2a       (subtle dividers)
Text primary: #ffffff  (headings)
Text muted: #6b7280   (secondary labels)
Accent blue: #3b82f6  (primary actions)
Accent green: #22c55e (success / resolved)
Accent yellow: #eab308 (warning / pending)
Accent red: #ef4444   (danger / high priority)
```

**Typography:**
```
Font: Inter (system sans-serif fallback)
Sizes: text-xs / text-sm / text-base / text-xl / text-2xl
Weights: font-normal / font-medium / font-semibold / font-bold
```

**Spacing:**
```
Base unit: 4px (1 = 0.25rem in Tailwind)
Card padding: p-4 (16px) or p-6 (24px)
Gap between cards: gap-4 or gap-6
Section spacing: mb-6 or mb-8
```

**Shape:**
```
Card radius: rounded-lg (8px) or rounded-xl (12px)
Badge radius: rounded-full
Button radius: rounded-md (6px)
```

Once you have these tokens, define them in one place.

### 2.2 Define the Design System

**File: `frontend/tailwind.config.js`**

```javascript
/** @type {import('tailwindcss').Config} */
export default {
    content: ["./src/**/*.{js,jsx,ts,tsx}"],
    theme: {
        extend: {
            colors: {
                // Semantic color tokens — use these in components, never raw hex
                background: "#0a0a0a",
                surface: "#141414",
                "surface-elevated": "#1a1a1a",
                border: "#2a2a2a",
                "border-subtle": "#1f1f1f",
                "text-primary": "#ffffff",
                "text-secondary": "#a1a1aa",
                "text-muted": "#6b7280",
                accent: "#3b82f6",
                "accent-hover": "#2563eb",
                success: "#22c55e",
                warning: "#eab308",
                danger: "#ef4444",
            },
            fontFamily: {
                sans: ["Inter", "system-ui", "sans-serif"],
            },
        },
    },
    plugins: [],
};
```

**Why semantic tokens instead of raw color classes?**
If you use `bg-[#141414]` everywhere and the design changes, you update 40 files. If you use `bg-surface` everywhere, you update one line in `tailwind.config.js`.

---

## 3. CSS Grid for the Bento Layout

Bento grids are CSS Grid layouts where cards span different numbers of columns and rows.

### 3.1 Grid Fundamentals

```css
/* CSS Grid basics */
.grid-container {
    display: grid;
    grid-template-columns: repeat(4, 1fr); /* 4 equal columns */
    gap: 1rem;                              /* Space between cells */
}

/* Item spanning multiple columns */
.wide-card {
    grid-column: span 2; /* Takes 2 of 4 columns */
}

/* Item spanning multiple rows */
.tall-card {
    grid-row: span 2;
}
```

**Tailwind equivalent:**
```jsx
<div className="grid grid-cols-4 gap-4">
    <div className="col-span-2">Wide card (2 of 4 columns)</div>
    <div className="col-span-1 row-span-2">Tall card</div>
    <div className="col-span-1">Normal card</div>
</div>
```

### 3.2 Responsive Bento Grid

```jsx
// Responsive: 1 col mobile, 2 col tablet, 4 col desktop
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    {/* Stats row - 4 equal cards */}
    <StatCard title="Total" value={complaints.length} />
    <StatCard title="Pending" value={pendingCount} />
    <StatCard title="Resolved" value={resolvedCount} />
    <StatCard title="High Priority" value={highPriorityCount} />

    {/* Wide complaint list - spans 3 columns */}
    <div className="lg:col-span-3">
        <ComplaintList complaints={complaints} />
    </div>

    {/* Sidebar stats - 1 column */}
    <div className="lg:col-span-1">
        <CategoryBreakdown complaints={complaints} />
    </div>
</div>
```

---

## 4. Building the Stat Card Component

```jsx
// frontend/src/components/StatCard.jsx

function StatCard({ title, value, trend, color = "accent" }) {
    const colorMap = {
        accent: "text-blue-400 bg-blue-500/10 border-blue-500/20",
        success: "text-green-400 bg-green-500/10 border-green-500/20",
        warning: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
        danger: "text-red-400 bg-red-500/10 border-red-500/20",
    };

    return (
        <div className="bg-surface border border-border rounded-xl p-5 flex flex-col gap-2">
            <span className="text-text-muted text-sm font-medium">{title}</span>
            <div className="flex items-end justify-between">
                <span className="text-3xl font-bold text-text-primary">{value}</span>
                {trend && (
                    <span className={`text-xs px-2 py-1 rounded-full border ${colorMap[color]}`}>
                        {trend}
                    </span>
                )}
            </div>
        </div>
    );
}

export default StatCard;
```

**Why `bg-blue-500/10`?** The `/10` is Tailwind's opacity modifier. `bg-blue-500/10` = blue background at 10% opacity. Used for subtle tinted backgrounds without covering the card background color.

---

## 5. Building the Complaint Card Component

```jsx
// frontend/src/components/ComplaintCard.jsx
import { motion } from 'framer-motion';

// Category to icon mapping — add new categories here
const CATEGORY_ICONS = {
    water: "💧",
    electricity: "⚡",
    cleaning: "🧹",
    noise: "🔊",
    maintenance: "🔧",
    security: "🔒",
    other: "❗",
};

// Status to visual style mapping
const STATUS_STYLES = {
    pending: {
        bg: "bg-yellow-500/10",
        text: "text-yellow-400",
        border: "border-yellow-500/20",
        label: "Pending",
    },
    in_progress: {
        bg: "bg-blue-500/10",
        text: "text-blue-400",
        border: "border-blue-500/20",
        label: "In Progress",
    },
    resolved: {
        bg: "bg-green-500/10",
        text: "text-green-400",
        border: "border-green-500/20",
        label: "Resolved",
    },
};

const PRIORITY_STYLES = {
    high: "bg-red-500/10 text-red-400 border-red-500/20",
    medium: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    low: "bg-gray-500/10 text-gray-400 border-gray-500/20",
};

function ComplaintCard({ complaint, onUpdate }) {
    const { id, category, priority, status, description, flat_number, created_at } = complaint;

    const statusStyle = STATUS_STYLES[status] || STATUS_STYLES.pending;
    const icon = CATEGORY_ICONS[category] || "❗";

    const handleStatusChange = (e) => {
        onUpdate({ ...complaint, status: e.target.value });
    };

    const formatDate = (dateStr) => {
        if (!dateStr) return "Unknown date";
        return new Date(dateStr).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        });
    };

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.2 }}
            className="bg-surface border border-border rounded-xl p-4 hover:border-border/80 transition-colors"
        >
            {/* Header: Category icon + Status badge + Priority */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                    <span className="text-xl">{icon}</span>
                    <span className="text-text-primary font-medium capitalize">{category}</span>
                </div>
                <div className="flex items-center gap-2">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${PRIORITY_STYLES[priority]}`}>
                        {priority}
                    </span>
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${statusStyle.bg} ${statusStyle.text} ${statusStyle.border}`}>
                        {statusStyle.label}
                    </span>
                </div>
            </div>

            {/* Description */}
            <p className="text-text-secondary text-sm leading-relaxed line-clamp-2 mb-3">
                {description}
            </p>

            {/* Footer: Flat number + Date + Status update */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    {flat_number && (
                        <span className="text-xs text-text-muted">Flat {flat_number}</span>
                    )}
                    <span className="text-xs text-text-muted">{formatDate(created_at)}</span>
                </div>

                <select
                    value={status}
                    onChange={handleStatusChange}
                    className="text-xs bg-surface border border-border text-text-secondary rounded-md px-2 py-1 cursor-pointer hover:border-accent/50 focus:outline-none focus:border-accent"
                >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="resolved">Resolved</option>
                </select>
            </div>
        </motion.div>
    );
}

export default ComplaintCard;
```

**`line-clamp-2` explained:** Limits text to 2 lines with an ellipsis. Requires Tailwind v3.3+ which includes it natively.

---

## 6. Framer Motion — Animations That Feel Professional

### 6.1 Basic Animation Pattern

```jsx
import { motion } from 'framer-motion';

<motion.div
    initial={{ opacity: 0, y: 20 }}     // Starting state
    animate={{ opacity: 1, y: 0 }}      // Target state
    exit={{ opacity: 0, y: -20 }}       // When unmounting
    transition={{ duration: 0.3 }}
>
    Content
</motion.div>
```

### 6.2 Page Transition Pattern

```jsx
// Wrap every view in motion.div with a key
<motion.div
    key={currentView}
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
    className="flex-1 overflow-y-auto p-6"
>
    {/* Current view content */}
</motion.div>
```

When `key` changes, React unmounts the old component and mounts a new one, triggering the `initial` animation.

### 6.3 List Animations with AnimatePresence

```jsx
import { motion, AnimatePresence } from 'framer-motion';

<AnimatePresence>
    {complaints.map(c => (
        <motion.div
            key={c.id}
            layout
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
        >
            <ComplaintCard complaint={c} />
        </motion.div>
    ))}
</AnimatePresence>
```

**`layout` prop:** When one item is removed, remaining items animate into their new positions instead of jumping.

---

## 7. The Backend Failure Handling Pattern

### 7.1 Three-State Loading Pattern

```jsx
function App() {
    const [complaints, setComplaints] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    async function loadComplaints() {
        try {
            setLoading(true);
            setError(null);
            const data = await fetchComplaints();
            setComplaints(data);
        } catch (err) {
            setError("Cannot connect to backend. Ensure the server is running on port 8000.");
            console.error("Backend unreachable:", err.message);
            // Do NOT reset complaints array — preserve last known good data
        } finally {
            setLoading(false);  // Always runs — even on error
        }
    }

    // Loading: show skeleton
    if (loading && complaints.length === 0) {
        return <LoadingScreen />;
    }

    return (
        <div>
            {/* Error banner — non-blocking, shows above dashboard */}
            {error && (
                <div className="bg-red-500/10 border border-red-500 text-red-400 p-3 rounded-lg mb-4">
                    {error}
                </div>
            )}
            <BentoDashboard complaints={complaints} />
        </div>
    );
}
```

### 7.2 Why `finally` Is Critical

```javascript
async function loadComplaints() {
    try {
        setLoading(true);
        const data = await fetchComplaints();
        setComplaints(data);
    } catch (err) {
        setError("Failed to load");
        // Without finally:
        // setLoading stays true forever when there's an error!
        // The spinner never stops.
    } finally {
        // This ALWAYS runs — even when catch block throws
        setLoading(false);
    }
}
```

---

## 8. The BentoDashboard Component

```jsx
// frontend/src/components/BentoDashboard.jsx
import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function BentoDashboard({ complaints, appointments, onComplaintUpdate }) {
    // useMemo prevents recomputing stats on every render
    const stats = useMemo(() => ({
        total: complaints.length,
        pending: complaints.filter(c => c.status === "pending").length,
        resolved: complaints.filter(c => c.status === "resolved").length,
        highPriority: complaints.filter(c => c.priority === "high").length,
    }), [complaints]);

    const sortedComplaints = useMemo(() =>
        [...complaints].sort((a, b) =>
            new Date(b.created_at) - new Date(a.created_at)
        ),
        [complaints]
    );

    return (
        <div className="space-y-6">
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard title="Total" value={stats.total} />
                <StatCard title="Pending" value={stats.pending} color="warning" />
                <StatCard title="Resolved" value={stats.resolved} color="success" />
                <StatCard title="High Priority" value={stats.highPriority} color="danger" />
            </div>

            <div className="space-y-3">
                <h2 className="text-text-primary text-lg font-semibold">Recent Complaints</h2>

                {complaints.length === 0 ? (
                    <div className="bg-surface border border-border rounded-xl p-8 text-center">
                        <p className="text-text-muted">No complaints yet.</p>
                    </div>
                ) : (
                    <AnimatePresence>
                        {sortedComplaints.map(complaint => (
                            <ComplaintCard
                                key={complaint.id}
                                complaint={complaint}
                                onUpdate={onComplaintUpdate}
                            />
                        ))}
                    </AnimatePresence>
                )}
            </div>
        </div>
    );
}

export default BentoDashboard;
```

**`useMemo` explained:**
- Caches the result of a computation between renders
- Only recomputes when the dependency array (`[complaints]`) changes
- Use for: filtering/sorting large arrays, derived stats
- Do NOT use for simple string concatenation — overhead is not worth it

---

## 9. Sidebar Navigation

```jsx
const NAV_ITEMS = [
    { id: "dashboard", label: "Dashboard", icon: "🏠" },
    { id: "calendar", label: "Calendar", icon: "📅" },
    { id: "properties", label: "Properties", icon: "🏢" },
    { id: "tenants", label: "Tenants", icon: "👥" },
    { id: "settings", label: "Settings", icon: "⚙️" },
    { id: "workflow", label: "SMS Workflow", icon: "💬" },
];

function Sidebar({ currentView, onNavigate }) {
    return (
        <div className="w-56 bg-surface border-r border-border flex flex-col h-full flex-shrink-0">
            <div className="p-6 border-b border-border">
                <h1 className="text-text-primary font-bold text-lg">TenantOS</h1>
            </div>

            <nav className="flex-1 p-4 space-y-1">
                {NAV_ITEMS.map(item => (
                    <button
                        key={item.id}
                        onClick={() => onNavigate(item.id)}
                        className={`
                            w-full flex items-center gap-3 px-3 py-2 rounded-lg
                            text-sm transition-colors duration-150
                            ${currentView === item.id
                                ? "bg-accent/10 text-accent border border-accent/20"
                                : "text-text-secondary hover:bg-surface-elevated hover:text-text-primary"
                            }
                        `}
                    >
                        <span>{item.icon}</span>
                        <span>{item.label}</span>
                    </button>
                ))}
            </nav>
        </div>
    );
}
```

---

## 10. Errors You Will Encounter

### Error 1: Framer Motion not installed

**Exact error:**
```
Cannot find module 'framer-motion'
```

**Fix:**
```bash
cd frontend
npm install framer-motion
```

### Error 2: Tailwind custom classes not applying

**Symptom:** `bg-surface` has no effect; background is transparent.

**Root cause A:** `content` in `tailwind.config.js` does not cover all files:
```javascript
// WRONG
content: ["./src/*.jsx"]  // Only root files

// CORRECT
content: ["./src/**/*.{js,jsx,ts,tsx}"]
```

**Root cause B:** The custom color definition is wrong:
```javascript
// CORRECT definition
colors: {
    surface: "#141414",       // Used as: bg-surface
    "text-muted": "#6b7280",  // Used as: text-text-muted
}
```

**Root cause C:** `tailwind.config.js` has a syntax error. Run `npm run dev` and check for config parse errors.

### Error 3: `useMemo` stats are stale

**Symptom:** Resolved count shows old number after status update.

**Root cause:** State was mutated directly (same array reference).

```jsx
// WRONG: Mutates in place — useMemo doesn't see a change
complaints.push(newComplaint);
setComplaints(complaints);

// CORRECT: New array reference triggers useMemo recompute
setComplaints(prev => [...prev, newComplaint]);
```

### Error 4: `line-clamp-2` not working

**Tailwind v3.3+:** Built-in, no plugin needed.

**Older Tailwind:** Install the plugin:
```bash
npm install @tailwindcss/line-clamp
# tailwind.config.js
plugins: [require('@tailwindcss/line-clamp')]
```

---

## 11. Anti-Patterns to Avoid

| Anti-pattern | Correct Approach |
|---|---|
| Magic hex values in JSX | Define semantic tokens in `tailwind.config.js` |
| Inline `style={{}}` for layout | Use Tailwind utility classes |
| Computing stats without `useMemo` | Wrap in `useMemo([complaints])` |
| Animating lists without `AnimatePresence` | Wrap animated list in `AnimatePresence` |
| Resetting complaint array on refresh error | Keep old data, show error banner only |

---

## 12. Session Completion Checklist

- [ ] `tailwind.config.js` defines all design tokens (background, surface, border, text-primary, text-secondary, text-muted, accent)
- [ ] `content` array covers `./src/**/*.{js,jsx,ts,tsx}`
- [ ] Framer Motion installed (`npm install framer-motion`)
- [ ] `StatCard` accepts `title`, `value`, `color` props
- [ ] `ComplaintCard` displays: icon, category, priority badge, status badge, description (clamped to 2 lines), flat number, formatted date
- [ ] Status `select` in card calls `onUpdate` with spread complaint object and new status
- [ ] `BentoDashboard` uses `useMemo` for all computed stats
- [ ] `AnimatePresence` wraps the complaint list for exit animations
- [ ] `motion.div` with `layout` prop on each card
- [ ] Page transitions use `motion.div` with `key={currentView}`
- [ ] Sidebar highlights active view with distinct accent styling
- [ ] `finally` block always resets loading state
- [ ] Error state shown as banner, not full-page replacement
- [ ] No hardcoded hex values in JSX components
