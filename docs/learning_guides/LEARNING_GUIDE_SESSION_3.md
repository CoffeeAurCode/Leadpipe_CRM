# Learning Guide Session 3: React Frontend Foundation — Components, State, API Integration, and the Dashboard

**Role:** Senior Staff Engineer Mentorship
**Objective:** Build the manager dashboard frontend from scratch with React, Vite, and Tailwind. Understand every concept you use: component architecture, state management, async API calls, the useEffect trap, and how to structure a real frontend project.

---

## 1. What Was Built in This Session

| Deliverable | File | Purpose |
|---|---|---|
| Vite + React project | `frontend/` | Build tooling and dev server |
| Root component | `frontend/src/App.jsx` | Complaint state, API calls, layout |
| Dashboard component | `frontend/src/components/BentoDashboard.jsx` | Displays complaint cards |
| API service layer | `frontend/src/services/apiService.js` | All HTTP calls in one place |
| Complaint card | `frontend/src/components/ComplaintCard.jsx` | Individual complaint display |
| Status update | `frontend/src/App.jsx handleComplaintUpdate` | PATCH to backend on status change |

---

## 2. Why Vite, Not Create React App

Create React App (CRA) is slow. Vite is the modern standard.

| Feature | CRA | Vite |
|---|---|---|
| Dev server start | 15-30 seconds | Under 1 second |
| Hot reload | Slow (webpack) | Instant (native ESM) |
| Build speed | Minutes | Seconds |
| Configuration | Complex | Simple |
| Maintained? | Deprecated | Actively maintained |

```bash
# Start a new project
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm run dev
```

**Project structure Vite creates:**
```
frontend/
├── public/           # Static assets served as-is
├── src/
│   ├── App.jsx       # Root component
│   ├── main.jsx      # React DOM mount point
│   └── index.css     # Global styles
├── index.html        # Single HTML page (SPA entry)
├── vite.config.js    # Build configuration
└── package.json
```

---

## 3. JavaScript Fundamentals You Must Know for React

React is JavaScript. If you do not understand these JS features, you will not understand why React components work the way they do.

### 3.1 Arrow Functions and `this`

```javascript
// Traditional function — 'this' depends on HOW it's called
function greet() {
    console.log(this.name); // 'this' is unpredictable in callbacks
}

// Arrow function — 'this' is inherited from surrounding scope
const greet = () => {
    console.log(this.name); // 'this' is always the enclosing scope
}

// Why it matters in React event handlers:
// This BREAKS because 'this' is undefined inside the callback
class BadComponent extends React.Component {
    handleClick() {
        console.log(this.state); // undefined — 'this' is lost
    }
    render() {
        return <button onClick={this.handleClick}>Click</button>; // broken
    }
}

// This WORKS in functional components (no 'this' at all)
function GoodComponent() {
    const [count, setCount] = useState(0);
    const handleClick = () => {
        setCount(count + 1); // arrow function, no 'this' problem
    };
    return <button onClick={handleClick}>Click ({count})</button>;
}
```

### 3.2 Destructuring — Used Constantly in React

```javascript
// Object destructuring
const user = { name: "Alice", role: "manager", age: 30 };
const { name, role } = user; // name = "Alice", role = "manager"

// Array destructuring (useState returns an array)
const [count, setCount] = useState(0);
// count = 0, setCount = the setter function

// Destructuring in function parameters (how React props work)
function ComplaintCard({ id, status, description }) {
    // id, status, description come from the props object
    return <div>{description}</div>;
}

// Without destructuring (verbose)
function ComplaintCard(props) {
    return <div>{props.description}</div>;
}
```

### 3.3 Spread Operator — Immutable State Updates

```javascript
// Merging objects (creates a NEW object, does not mutate)
const original = { name: "Alice", role: "user" };
const updated = { ...original, role: "admin" };
// original unchanged, updated has role: "admin"

// Critical React pattern: updating a complaint in an array
const complaints = [
    { id: 1, status: "pending" },
    { id: 2, status: "resolved" }
];

// Update complaint id=1 to "resolved" without mutating
const updated = complaints.map(c =>
    c.id === 1 ? { ...c, status: "resolved" } : c
);
```

### 3.4 Array Methods — The React Toolkit

```javascript
const complaints = [
    { id: 1, category: "water", status: "pending" },
    { id: 2, category: "electricity", status: "resolved" },
    { id: 3, category: "water", status: "pending" }
];

// MAP: Transform each element into JSX
const cards = complaints.map(c => <ComplaintCard key={c.id} {...c} />);

// FILTER: Show only pending
const pending = complaints.filter(c => c.status === "pending");

// FIND: Get specific complaint
const specific = complaints.find(c => c.id === 2);

// REDUCE: Count by category
const counts = complaints.reduce((acc, c) => {
    acc[c.category] = (acc[c.category] || 0) + 1;
    return acc;
}, {});
// { water: 2, electricity: 1 }
```

### 3.5 Async/Await — How Every API Call Works

```javascript
// The wrong way (callback hell)
fetch('/api/complaints')
    .then(response => response.json())
    .then(data => {
        fetch(`/api/tenants/${data[0].tenant_id}`)
            .then(r => r.json())
            .then(tenant => console.log(tenant));
    });

// The right way (async/await)
async function loadComplaintWithTenant(complaintId) {
    try {
        const response = await fetch(`/api/complaints/${complaintId}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const complaint = await response.json();

        const tenantResponse = await fetch(`/api/tenants/${complaint.tenant_id}`);
        const tenant = await tenantResponse.json();

        return { complaint, tenant };
    } catch (error) {
        console.error("Failed to load:", error.message);
        throw error; // Let caller handle it
    }
}
```

---

## 4. React Core Concepts

### 4.1 Components — Functions That Return JSX

```jsx
// Component = function that returns JSX
// JSX looks like HTML but compiles to JavaScript
function ComplaintCard({ id, category, status, description }) {
    return (
        <div className="card">
            <h3>{category}</h3>
            <p>{description}</p>
            <span className={`status-${status}`}>{status}</span>
        </div>
    );
}

// JSX rules:
// 1. One root element (or use <>...</> fragment)
// 2. className not class (class is a JS keyword)
// 3. Expressions in {} — any valid JavaScript
// 4. Self-closing tags must have / (<br /> not <br>)
// 5. CamelCase event handlers (onClick not onclick)
```

### 4.2 State — Data That Triggers Re-renders

```jsx
import { useState } from 'react';

function StatusToggle({ initialStatus }) {
    // State: [currentValue, setterFunction]
    const [status, setStatus] = useState(initialStatus);

    const toggleStatus = () => {
        // WRONG: Direct mutation does NOT trigger re-render
        // status = "resolved"; // This does nothing visible

        // CORRECT: Use setter function
        setStatus(status === "pending" ? "resolved" : "pending");
        // React detects the new value and re-renders the component
    };

    return (
        <div>
            <p>Status: {status}</p>
            <button onClick={toggleStatus}>Toggle</button>
        </div>
    );
}
```

**Why does mutation not work?**
React uses a virtual DOM diff algorithm. It only re-renders when state variables change to new references. If you mutate an object directly, the reference stays the same and React does not see a change.

```javascript
// WRONG: Same array reference, React skips re-render
const complaints = [...prev];
complaints.push(newItem); // mutates existing array
setComplaints(complaints); // same reference!

// CORRECT: New array reference, React re-renders
setComplaints(prev => [...prev, newItem]); // spread creates new array
```

### 4.3 useEffect — Side Effects and the Dependency Array

`useEffect` runs code AFTER the component renders. Use it for: API calls, event listeners, timers.

```jsx
import { useState, useEffect } from 'react';

function App() {
    const [complaints, setComplaints] = useState([]);
    const [filter, setFilter] = useState("all");

    // Pattern 1: Run once on mount (empty dependency array)
    useEffect(() => {
        loadComplaints();
    }, []); // ← empty array = run once when component mounts

    // Pattern 2: Run when filter changes
    useEffect(() => {
        loadComplaints(filter);
    }, [filter]); // ← run whenever 'filter' changes

    // Pattern 3: Cleanup (removing event listeners)
    useEffect(() => {
        const handler = () => loadComplaints();
        window.addEventListener('refresh-data', handler);

        // Cleanup function: runs when component unmounts
        return () => {
            window.removeEventListener('refresh-data', handler);
        };
    }, []);

    async function loadComplaints(statusFilter = "all") {
        const data = await fetchComplaints();
        const filtered = statusFilter === "all"
            ? data
            : data.filter(c => c.status === statusFilter);
        setComplaints(filtered);
    }

    return <div>{complaints.map(c => <ComplaintCard key={c.id} {...c} />)}</div>;
}
```

**The useEffect trap — async function inside useEffect:**

```jsx
// WRONG: useEffect callback cannot be async directly
useEffect(async () => {
    const data = await fetchComplaints(); // React ignores the returned Promise
    setComplaints(data);
}, []);

// CORRECT: Define async function inside, call it immediately
useEffect(() => {
    async function load() {
        const data = await fetchComplaints();
        setComplaints(data);
    }
    load(); // Call the async function
}, []);

// ALSO CORRECT: Extract to named function (used in App.jsx)
async function loadComplaints() {
    const data = await fetchComplaints();
    setComplaints(data);
}

useEffect(() => {
    loadComplaints();
}, []);
```

### 4.4 Props — Passing Data Down

```jsx
// Parent passes data as props
function App() {
    const [complaints, setComplaints] = useState([]);

    const handleUpdate = async (updatedComplaint) => {
        await updateComplaint(updatedComplaint.id, { status: updatedComplaint.status });
        setComplaints(prev => prev.map(c =>
            c.id === updatedComplaint.id ? updatedComplaint : c
        ));
    };

    return (
        <BentoDashboard
            complaints={complaints}
            onComplaintUpdate={handleUpdate}
        />
    );
}

// Child receives props (destructured)
function BentoDashboard({ complaints, onComplaintUpdate }) {
    return (
        <div>
            {complaints.map(c => (
                <ComplaintCard
                    key={c.id}
                    complaint={c}
                    onUpdate={onComplaintUpdate}
                />
            ))}
        </div>
    );
}
```

**Rules about props:**
- Props flow DOWN (parent to child). Never up.
- Props are read-only inside the child.
- To "pass data up," pass a callback function as a prop.
- The `key` prop is required when rendering lists. Use unique IDs, never array index.

---

## 5. API Service Layer — Never Call fetch() Directly in Components

**Why a service layer?**
If every component calls `fetch("/api/complaints")` directly, and the API URL changes, you update 20 files. If the API layer is centralized, you update one file.

**File: `frontend/src/services/apiService.js`**

```javascript
// All API configuration in one place
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Fetch all complaints with error handling.
 * Always returns an array (never throws to the caller).
 */
export async function fetchComplaints() {
    const response = await fetch(`${API_BASE_URL}/complaints`);
    if (!response.ok) {
        throw new Error(`Failed to fetch complaints: HTTP ${response.status}`);
    }
    return response.json();
}

/**
 * Update a complaint by ID (PATCH — partial update).
 * Only sends the fields that changed.
 */
export async function updateComplaint(id, updates) {
    const response = await fetch(`${API_BASE_URL}/complaints/${id}`, {
        method: "PATCH",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(updates),
    });

    if (!response.ok) {
        const errorBody = await response.text();
        throw new Error(`Failed to update complaint ${id}: ${response.status} — ${errorBody}`);
    }

    return response.json();
}

/**
 * Fetch appointments within a date range.
 */
export async function fetchAppointments(startDate, endDate) {
    const params = new URLSearchParams({ start: startDate, end: endDate });
    const response = await fetch(`${API_BASE_URL}/appointments?${params}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch appointments: HTTP ${response.status}`);
    }
    return response.json();
}
```

**`import.meta.env.VITE_API_URL` explained:**
- In Vite, environment variables prefixed with `VITE_` are embedded into the build
- `import.meta.env` is how Vite exposes them (not `process.env` which is Node.js)
- Create `frontend/.env.local` for local development:
  ```
  VITE_API_URL=http://localhost:8000
  ```
- The fallback `|| "http://localhost:8000"` prevents undefined errors when `.env.local` is missing

---

## 6. The App Component — State Management at the Top

The `App.jsx` pattern in this project is "lift state up": all shared state lives at the top, gets passed down via props.

```jsx
// frontend/src/App.jsx
import { useState, useEffect } from 'react';
import { fetchComplaints, updateComplaint, fetchAppointments } from './services/apiService';
import BentoDashboard from './components/BentoDashboard';
import { format, subDays, addDays } from 'date-fns';

function App() {
    // State lifted to top level — all components that need this data get it as props
    const [complaints, setComplaints] = useState([]);
    const [appointments, setAppointments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentView, setCurrentView] = useState('dashboard');

    // Load on mount
    useEffect(() => {
        loadComplaints();
        loadAppointments();
    }, []);

    // Listen for refresh events from child components (custom event pattern)
    useEffect(() => {
        window.addEventListener('refresh-data', loadComplaints);
        return () => window.removeEventListener('refresh-data', loadComplaints);
    }, []);

    async function loadComplaints() {
        try {
            setLoading(true);
            const data = await fetchComplaints();
            setComplaints(data);
            setError(null);
        } catch (err) {
            setError('Failed to load complaints. Is the backend running?');
            console.error(err);
        } finally {
            setLoading(false);  // Always runs, even on error
        }
    }

    async function loadAppointments() {
        try {
            const start = format(subDays(new Date(), 90), 'yyyy-MM-dd');
            const end = format(addDays(new Date(), 30), 'yyyy-MM-dd');
            const data = await fetchAppointments(start, end);
            setAppointments(data);
        } catch (err) {
            console.error('Failed to load appointments:', err);
            // Don't set error state — appointments are secondary
        }
    }

    // Optimistic update pattern: update local state immediately after API success
    const handleComplaintUpdate = async (updatedComplaint) => {
        const original = complaints.find(c => c.id === updatedComplaint.id);
        if (!original) return;

        // Build a minimal diff — only send what changed
        const updates = {};
        if (updatedComplaint.status !== original.status) {
            updates.status = updatedComplaint.status;
        }
        if (Object.keys(updates).length === 0) return;

        try {
            const serverResult = await updateComplaint(updatedComplaint.id, updates);
            // Update local state with SERVER response (not the local optimistic value)
            setComplaints(prev => prev.map(c =>
                c.id === serverResult.id ? serverResult : c
            ));
        } catch (error) {
            console.error('Failed to update:', error);
            alert('Failed to update complaint. Please try again.');
        }
    };

    return (
        <div className="flex h-screen bg-background overflow-hidden">
            {/* Sidebar, TopBar, etc. */}
            <BentoDashboard
                complaints={complaints}
                appointments={appointments}
                onComplaintUpdate={handleComplaintUpdate}
            />
        </div>
    );
}

export default App;
```

---

## 7. Component Architecture Principles

### 7.1 Single Responsibility — Each Component Does One Thing

```
App.jsx
├── Sidebar.jsx          ← Navigation only
├── TopBar.jsx           ← Header only
└── BentoDashboard.jsx   ← Complaint list + summary stats
    └── ComplaintCard.jsx ← Single complaint display + status update
```

If a component is longer than 200 lines, ask: "Is this doing two things?" Extract one of them.

### 7.2 Controlled vs Uncontrolled Inputs

```jsx
// UNCONTROLLED: React doesn't know the value (use for simple, isolated forms)
<input defaultValue="initial" ref={inputRef} />

// CONTROLLED: React owns the value (use whenever you need the value in state)
const [status, setStatus] = useState("pending");
<select value={status} onChange={e => setStatus(e.target.value)}>
    <option value="pending">Pending</option>
    <option value="resolved">Resolved</option>
</select>
```

For this project, always use controlled inputs. They make validation and form submission straightforward.

### 7.3 The Key Prop — React's Identity System

```jsx
// WRONG: Using array index as key
{complaints.map((c, index) => (
    <ComplaintCard key={index} {...c} />
))}
// If the array reorders, React gets confused about which component is which

// CORRECT: Use the database ID (stable, unique)
{complaints.map(c => (
    <ComplaintCard key={c.id} {...c} />
))}
```

React uses `key` to match virtual DOM elements between renders. Changing keys causes React to unmount and remount components (losing local state, triggering animations).

---

## 8. Tailwind CSS Crash Course for This Project

Tailwind is a utility-first CSS framework. Instead of writing CSS files, you apply classes directly in JSX.

### 8.1 Core Concepts

```jsx
// Traditional CSS approach
.card {
    display: flex;
    padding: 16px;
    background-color: #1a1a1a;
    border-radius: 8px;
}

// Tailwind approach (same result)
<div className="flex p-4 bg-gray-900 rounded-lg">
```

### 8.2 Classes You Will Use Daily

```jsx
// Layout
<div className="flex">          {/* display: flex */}
<div className="flex-col">     {/* flex-direction: column */}
<div className="items-center"> {/* align-items: center */}
<div className="justify-between"> {/* justify-content: space-between */}
<div className="grid grid-cols-3"> {/* CSS Grid, 3 columns */}
<div className="gap-4">        {/* gap: 1rem */}

// Sizing
<div className="w-full">       {/* width: 100% */}
<div className="h-screen">     {/* height: 100vh */}
<div className="max-w-7xl">    {/* max-width: 80rem */}
<div className="p-4">          {/* padding: 1rem (all sides) */}
<div className="px-6 py-3">    {/* padding: 0.75rem 1.5rem */}
<div className="m-auto">       {/* margin: auto */}

// Typography
<p className="text-sm">        {/* font-size: 0.875rem */}
<p className="text-xl font-bold"> {/* large + bold */}
<p className="text-gray-400">  {/* color: gray #9ca3af */}
<p className="truncate">       {/* overflow ellipsis */}

// Colors (dark theme pattern)
<div className="bg-gray-900 text-white border border-gray-700">

// Responsive
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
// 1 column on mobile, 2 on medium screens, 3 on large screens

// Hover and focus states
<button className="hover:bg-blue-600 focus:outline-none focus:ring-2">

// Conditional classes (using template literals or clsx)
<span className={`px-2 py-1 rounded ${
    status === "pending" ? "bg-yellow-500" : "bg-green-500"
}`}>
```

### 8.3 Dark Theme Pattern (This Project's Design)

This project uses a custom dark theme defined in `tailwind.config.js`:

```javascript
// tailwind.config.js
export default {
    theme: {
        extend: {
            colors: {
                background: "#0a0a0a",   // Page background
                surface: "#141414",      // Card background
                border: "#2a2a2a",       // Subtle borders
                muted: "#6b7280",        // Secondary text
            }
        }
    }
}
```

Usage:
```jsx
<div className="bg-background text-white">
    <div className="bg-surface border border-border rounded-lg p-4">
        <p className="text-muted-foreground text-sm">Created 2 hours ago</p>
    </div>
</div>
```

---

## 9. Errors You Will Encounter

### Error 1: CORS error when frontend calls backend

**Exact console error:**
```
Access to fetch at 'http://localhost:8000/complaints' from origin 'http://localhost:5173'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present.
```

**Root cause:** The browser blocks cross-origin requests unless the server explicitly allows them.

**Fix in FastAPI (`backend/app/main.py`):**
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why Vite uses port 5173:** Vite defaults to 5173 (not 3000 like CRA). Always confirm the port before setting CORS.

---

### Error 2: `TypeError: Cannot read properties of undefined (reading 'map')`

**Exact error:**
```
TypeError: Cannot read properties of undefined (reading 'map')
```

**Root cause:** Rendering `complaints.map(...)` before `complaints` is populated from the API.

**Before (broken):**
```jsx
const [complaints, setComplaints] = useState(); // undefined by default!
return <div>{complaints.map(c => <Card key={c.id} {...c} />)}</div>; // crash
```

**After (fixed):**
```jsx
const [complaints, setComplaints] = useState([]); // empty array, not undefined
return <div>{complaints.map(c => <Card key={c.id} {...c} />)}</div>; // safe
```

Always initialize array state with `[]` and object state with `{}`.

---

### Error 3: Infinite loop with useEffect

**Symptom:** Browser tab freezes. Network tab shows thousands of identical API requests.

**Root cause:** State set inside useEffect triggers re-render, which triggers useEffect again.

```jsx
// WRONG: This creates an infinite loop
useEffect(() => {
    setComplaints(prev => [...prev]); // setComplaints triggers re-render
    // Re-render triggers useEffect again (no dependency array = runs every render)
    // → infinite loop
});

// CORRECT: Specify what to watch
useEffect(() => {
    loadComplaints();
}, []); // Only run once on mount
```

**Rule:** If a `useEffect` has no dependency array, it runs after EVERY render. Almost always wrong.

---

### Error 4: Stale state in event handlers

**Symptom:** Status update shows old value even after clicking.

```jsx
// WRONG: Captures 'complaints' at time of creation
const handleDelete = () => {
    const updated = complaints.filter(c => c.id !== deleteId);
    setComplaints(updated); // 'complaints' might be stale
};

// CORRECT: Use functional update with current state
const handleDelete = () => {
    setComplaints(prev => prev.filter(c => c.id !== deleteId));
    // 'prev' is always the most recent state
};
```

Use the functional form of state setters (`setX(prev => ...)`) whenever the new state depends on the old state.

---

### Error 5: `Warning: Each child in a list should have a unique "key" prop`

**Console warning:**
```
Warning: Each child in a list should have a unique "key" prop.
```

**Root cause:** Rendering a list without `key`, or using array index as `key`.

```jsx
// WRONG
{complaints.map(c => <Card {...c} />)} // no key

// WRONG
{complaints.map((c, i) => <Card key={i} {...c} />)} // index as key

// CORRECT
{complaints.map(c => <Card key={c.id} {...c} />)} // stable unique ID
```

---

### Error 6: `fetch` returns `ok: false` but no exception is thrown

**Symptom:** 404 or 500 from backend but no error in the catch block.

**Root cause:** `fetch()` only throws on network failures (DNS, connection refused). HTTP error codes like `404` or `500` return a resolved promise with `response.ok === false`.

```javascript
// WRONG: 404 silently returns undefined
async function fetchComplaint(id) {
    const response = await fetch(`/api/complaints/${id}`);
    return response.json(); // Returns {"detail": "Not found"} — looks like success!
}

// CORRECT: Check response.ok explicitly
async function fetchComplaint(id) {
    const response = await fetch(`/api/complaints/${id}`);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    return response.json();
}
```

---

## 10. The Custom Event Pattern for Cross-Component Refresh

When a child component (e.g., a modal) creates a new complaint, the parent `App.jsx` needs to know about it so it can reload the list. Without passing callbacks through many layers of components, you can use browser custom events.

**Child component (inside a modal):**
```javascript
async function handleSaveComplaint() {
    await createComplaint(formData);
    // Broadcast event — any listener in the app will receive it
    window.dispatchEvent(new Event('refresh-data'));
    closeModal();
}
```

**App.jsx (listener):**
```javascript
useEffect(() => {
    const refresh = () => loadComplaints();
    window.addEventListener('refresh-data', refresh);
    return () => window.removeEventListener('refresh-data', refresh);
}, []);
```

**When to use this pattern:** When the component that triggers a change is too deeply nested to receive a callback prop without prop-drilling through many intermediaries.

**When NOT to use this:** This is a light alternative to a state management library. For large apps, use React Context or Zustand instead.

---

## 11. Anti-Patterns to Avoid

**Anti-pattern 1: Calling fetch directly in component body (not in useEffect)**
```jsx
// WRONG: Runs on every render, creates infinite loop
function Dashboard() {
    const [data, setData] = useState([]);
    fetch('/api/complaints').then(r => r.json()).then(setData); // Runs every render!
    return <div>{data.length} complaints</div>;
}

// CORRECT: Wrapped in useEffect
function Dashboard() {
    const [data, setData] = useState([]);
    useEffect(() => {
        fetch('/api/complaints').then(r => r.json()).then(setData);
    }, []); // Run once
    return <div>{data.length} complaints</div>;
}
```

**Anti-pattern 2: Mutating state directly**
```jsx
// WRONG: Does not trigger re-render
const addComplaint = (complaint) => {
    complaints.push(complaint); // Mutates in place
    setComplaints(complaints);  // Same reference — React ignores it
};

// CORRECT: Create new array
const addComplaint = (complaint) => {
    setComplaints(prev => [...prev, complaint]); // New array reference
};
```

**Anti-pattern 3: Hardcoding the API URL**
```javascript
// WRONG: Must change this in every file when backend URL changes
const response = await fetch("http://localhost:8000/complaints");

// CORRECT: Single point of configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const response = await fetch(`${API_BASE_URL}/complaints`);
```

---

## 12. Session Completion Checklist

- [ ] Vite + React project created with `npm create vite@latest frontend -- --template react`
- [ ] `npm install` run, `npm run dev` starts without errors
- [ ] Tailwind CSS installed and configured (`npm install -D tailwindcss postcss autoprefixer`)
- [ ] `tailwind.config.js` includes `content: ["./src/**/*.{js,jsx}"]`
- [ ] `API_BASE_URL` uses `import.meta.env.VITE_API_URL` with fallback to localhost
- [ ] All fetch calls in `apiService.js`, not directly in components
- [ ] Every fetch call checks `response.ok` and throws on error
- [ ] All array state initialized with `[]` (not undefined)
- [ ] All useEffect calls have a dependency array (even if empty)
- [ ] No async functions passed directly as useEffect callback
- [ ] All list renders use `key={item.id}` (not index)
- [ ] State updates that depend on previous state use functional form `setX(prev => ...)`
- [ ] FastAPI backend has CORSMiddleware allowing `http://localhost:5173`
- [ ] Component tree: App (state) → BentoDashboard → ComplaintCard (display only)
- [ ] Custom event listener cleaned up in useEffect return function
- [ ] Status update sends only changed fields (not entire complaint object)
- [ ] Loading state prevents rendering empty data
- [ ] Error state shows user-friendly message (not raw exception)
