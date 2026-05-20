# Frontend Development Guide - Manager Dashboard

**Author's Note:** This guide explains the React frontend development for the Tenant Management Dashboard. It's written for someone with minimal frontend experience.

---

## Table of Contents
1. [What We Built](#what-we-built)
2. [Technology Stack Explained](#technology-stack-explained)
3. [Project Structure](#project-structure)
4. [Understanding React Basics](#understanding-react-basics)
5. [Component Breakdown](#component-breakdown)
6. [Data Flow & State Management](#data-flow--state-management)
7. [API Integration](#api-integration)
8. [Styling Approach](#styling-approach)
9. [How to Run & Deploy](#how-to-run--deploy)
10. [Common Issues & Solutions](#common-issues--solutions)

---

## What We Built

A **real-time manager dashboard** that displays tenant complaints with the following features:

✅ **Complaint Table** - Shows all complaints in a scrollable table  
✅ **Priority Colors** - Rows are colored based on urgency (red/yellow/blue)  
✅ **Editable Status** - Managers can update complaint status with a dropdown  
✅ **Phone Numbers** - Displays tenant phone numbers from call logs  
✅ **Auto-refresh** - Dashboard updates every 5 seconds automatically  
✅ **Modern UI** - Professional design with smooth animations  

---

## Technology Stack Explained

### What is React?

**React** is a JavaScript library for building user interfaces. Think of it like building with LEGO blocks:
- Each component is a reusable block (like Sidebar, Table, Button)
- You combine these blocks to build your app
- When data changes, React automatically updates the UI

**Why React?**
- Component-based: Reusable pieces of UI
- Fast: Only updates what changed, not the whole page
- Popular: Huge community, lots of resources

### What is Vite?

**Vite** is a build tool that:
- Bundles your code (combines multiple files into one)
- Provides a development server (runs your app locally)
- Hot Module Replacement (updates instantly when you save a file)

**Think of it as:** A super-fast compiler that turns your React code into something browsers understand.

### What is JSX?

JSX lets you write HTML-like code in JavaScript:

```javascript
// Regular JavaScript
const element = React.createElement('h1', {}, 'Hello');

// JSX (much easier!)
const element = <h1>Hello</h1>;
```

---

## Project Structure

```
frontend/
├── public/                     # Static files (never change)
├── src/                        # Source code (where you work)
│   ├── components/             # Reusable UI components
│   │   ├── Sidebar.jsx         # Left navigation menu
│   │   ├── Sidebar.css         # Sidebar styles
│   │   ├── Dashboard.jsx       # Main page container
│   │   ├── Dashboard.css       # Dashboard styles
│   │   ├── ComplaintTable.jsx  # Table component
│   │   ├── ComplaintTable.css  # Table styles
│   │   ├── StatusDropdown.jsx  # Status editor
│   │   └── StatusDropdown.css  # Dropdown styles
│   ├── services/               # Backend communication
│   │   └── api.js              # API functions
│   ├── App.jsx                 # Root component
│   ├── App.css                 # App-level styles
│   ├── main.jsx                # Entry point
│   └── index.css               # Global styles
├── index.html                  # HTML template
├── package.json                # Dependencies list
├── vite.config.js              # Vite configuration
└── README.md                   # Instructions
```

**Key Files:**

- **`main.jsx`** - Starting point, renders the app
- **`App.jsx`** - Main container, holds Sidebar + Dashboard
- **`Dashboard.jsx`** - Fetches data, manages state, contains table
- **`ComplaintTable.jsx`** - Displays complaints in table format
- **`api.js`** - Functions to talk to backend API

---

## Understanding React Basics

### 1. Components

A component is a function that returns JSX (HTML-like code):

```javascript
function Greeting() {
  return <h1>Hello, World!</h1>;
}
```

### 2. Props (Properties)

Props are like function arguments. They pass data from parent to child:

```javascript
// Parent component
<Greeting name="Alice" />

// Child component
function Greeting(props) {
  return <h1>Hello, {props.name}!</h1>;
}
// Output: Hello, Alice!
```

### 3. State

State is data that changes over time. When state changes, React re-renders:

```javascript
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0); // Initial value: 0
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>+1</button>
    </div>
  );
}
```

**How it works:**
1. `useState(0)` creates state variable `count` with initial value 0
2. `setCount` is the function to update `count`
3. When you click the button, `count` increases and UI updates

### 4. Effects (Side Effects)

`useEffect` runs code after render (like fetching data):

```javascript
import { useEffect } from 'react';

useEffect(() => {
  console.log('Component rendered!');
  
  // Cleanup function (optional)
  return () => {
    console.log('Component unmounted!');
  };
}, []); // Empty array = run once on mount
```

**Dependency array:**
- `[]` - Run once when component mounts
- `[count]` - Run when `count` changes
- No array - Run after every render

---

## Component Breakdown

### 1. App.jsx (Root Component)

**Purpose:** Container that holds the entire app layout.

**Code Explanation:**

```javascript
import Sidebar from './components/Sidebar';
import Dashboard from './components/Dashboard';
import './App.css';

function App() {
  return (
    <div className="app-container">
      <Sidebar />      {/* Left side */}
      <Dashboard />    {/* Right side */}
    </div>
  );
}
```

**Layout:**
```
┌────────────────────────────────┐
│ Sidebar │      Dashboard       │
│         │                      │
│Profile  │   Complaint Table    │
│Dashboard│                      │
│Logout   │                      │
└────────────────────────────────┘
```

---

### 2. Sidebar.jsx (Navigation Menu)

**Purpose:** Shows navigation links and branding.

**Key Features:**
- M-TENANT logo
- Navigation items (Profile, Dashboard, Logout)
- 24/7 Service badge
- Illustrated person working

**Props:** None (static component)

**Styling:**
- Blue gradient background (`#4F46E5` → `#3730A3`)
- Active state for Dashboard item (white background)
- Hover effects on nav items

---

### 3. Dashboard.jsx (Main Container)

**Purpose:** Manages data fetching, state, and auto-refresh.

**State Variables:**

```javascript
const [complaints, setComplaints] = useState([]);    // List of complaints
const [callLogs, setCallLogs] = useState([]);        // List of call logs
const [loading, setLoading] = useState(true);        // Loading state
const [error, setError] = useState(null);            // Error message
const [updatingIds, setUpdatingIds] = useState([]);  // IDs being updated
```

**Data Fetching:**

```javascript
const fetchData = async () => {
  try {
    const [complaintsData, callLogsData] = await Promise.all([
      api.fetchComplaints(),
      api.fetchCallLogs()
    ]);
    setComplaints(complaintsData);
    setCallLogs(callLogsData);
  } catch (err) {
    setError('Failed to load complaints');
  }
};
```

**Explanation:**
- `Promise.all` - Fetch both APIs at the same time (faster!)
- `await` - Wait for API response before continuing
- `try/catch` - Handle errors gracefully

**Auto-refresh (Polling):**

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    fetchData(); // Fetch every 5 seconds
  }, 5000);
  
  return () => clearInterval(interval); // Cleanup on unmount
}, []);
```

**How it works:**
1. `setInterval` creates a timer that runs `fetchData()` every 5000ms
2. Timer keeps running until component unmounts
3. `clearInterval` stops the timer when component is destroyed

**Status Update Handler:**

```javascript
const handleStatusUpdate = async (complaintId, newStatus) => {
  setUpdatingIds(prev => [...prev, complaintId]); // Mark as updating
  
  try {
    const updated = await api.updateComplaintStatus(complaintId, newStatus);
    
    // Update local state immediately (optimistic update)
    setComplaints(prev =>
      prev.map(complaint =>
        complaint.id === complaintId
          ? { ...complaint, status: updated.status }
          : complaint
      )
    );
  } catch (err) {
    alert('Failed to update status');
  } finally {
    setUpdatingIds(prev => prev.filter(id => id !== complaintId)); // Remove from updating
  }
};
```

**Explanation:**
- **Optimistic Update:** Update UI immediately, don't wait for server
- **Array.map():** Transform array by updating one item
- **Spread operator (`...`):** Copy object and change one property

---

### 4. ComplaintTable.jsx (Data Display)

**Purpose:** Display complaints in a table with priority colors.

**Props Received:**

```javascript
{
  complaints: [],       // Array of complaint objects
  callLogs: [],         // Array of call log objects
  onStatusUpdate: fn,   // Function to call when status changes
  updatingIds: []       // IDs currently being updated
}
```

**Phone Number Mapping:**

```javascript
const phoneMap = {};
callLogs.forEach(log => {
  if (log.complaint_id && log.phone_number) {
    phoneMap[log.complaint_id] = log.phone_number;
  }
});
```

**Creates:**
```javascript
phoneMap = {
  1: "+91-9876543210",
  2: "+91-8765432109",
  // complaint_id: phone_number
}
```

**Priority Color Function:**

```javascript
const getPriorityClass = (priority) => {
  switch (priority?.toLowerCase()) {
    case 'high':   return 'priority-high';    // Red
    case 'medium': return 'priority-medium';  // Yellow
    case 'low':    return 'priority-low';     // Blue
    default:       return '';
  }
};
```

**Table Rendering:**

```javascript
{complaints.map((complaint, index) => (
  <tr key={complaint.id} className={getPriorityClass(complaint.priority)}>
    <td>{index + 1}</td>
    <td>{complaint.flat_number || 'N/A'}</td>
    <td>{phoneMap[complaint.id] || 'N/A'}</td>
    <td>{complaint.description}</td>
    <td>
      <StatusDropdown
        currentStatus={complaint.status}
        complaintId={complaint.id}
        onStatusChange={onStatusUpdate}
        isUpdating={updatingIds.includes(complaint.id)}
      />
    </td>
  </tr>
))}
```

**Explanation:**
- `map()` - Loop through array and create elements
- `key={complaint.id}` - Unique identifier (React requirement)
- `||` - Logical OR (if left is empty, use right)

---

### 5. StatusDropdown.jsx (Interactive Control)

**Purpose:** Let managers change complaint status.

**Props:**

```javascript
{
  currentStatus: "pending",  // Current status value
  complaintId: 5,            // Complaint ID
  onStatusChange: fn,        // Function to call on change
  isUpdating: false          // Is this complaint updating?
}
```

**Status Options:**

```javascript
const statuses = ['pending', 'in-progress', 'resolved', 'closed'];
```

**Handle Change:**

```javascript
const handleChange = async (e) => {
  const newStatus = e.target.value;
  if (newStatus !== currentStatus) {
    await onStatusChange(complaintId, newStatus);
  }
};
```

**Conditional Rendering:**

```javascript
{isUpdating ? (
  <div>Updating...</div>
) : (
  <select value={currentStatus} onChange={handleChange}>
    {statuses.map(status => (
      <option key={status} value={status}>{status}</option>
    ))}
  </select>
)}
```

**Checkmark Icon:**

```javascript
{getStatusIcon(currentStatus) && (
  <span className="status-icon">✓</span>
)}
```

Shows checkmark only for `resolved` or `closed` statuses.

---

## Data Flow & State Management

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         App.jsx                             │
│                 (No state, just layout)                     │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
   ┌─────────▼─────────┐          ┌──────────▼──────────┐
   │   Sidebar.jsx     │          │   Dashboard.jsx     │
   │   (No state)      │          │   (Has ALL state)   │
   └───────────────────┘          └──────────┬──────────┘
                                             │
                              ┌──────────────┼──────────────┐
                              │              │              │
                    State: complaints    callLogs    updatingIds
                              │              │              │
                              └──────────────┼──────────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │ ComplaintTable    │
                                   │ (Receives props)  │
                                   └─────────┬─────────┘
                                             │
                                   ┌─────────▼─────────┐
                                   │ StatusDropdown    │
                                   │ (Receives props)  │
                                   └───────────────────┘
```

### State Lifting

**Why Dashboard has all the state:**
- Needs to fetch data from API
- Needs to pass data to child components
- Needs to handle updates from child components

**Alternative (bad approach):**
- Each component fetches its own data → Multiple API calls
- Can't share data between components
- Hard to keep data in sync

---

## API Integration

### api.js - Service Layer

**Why separate file?**
- Centralized API logic
- Reusable functions
- Easy to change backend URL

**Base URL:**

```javascript
const BASE_URL = 'http://localhost:8000';
```

**Fetch Complaints:**

```javascript
async fetchComplaints() {
  try {
    const response = await fetch(`${BASE_URL}/complaints`);
    if (!response.ok) throw new Error('HTTP error');
    return await response.json();
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}
```

**Breakdown:**
1. `fetch()` - Make HTTP request
2. `await` - Wait for response
3. `.ok` - Check if status code is 200-299
4. `.json()` - Parse response as JSON
5. `throw error` - Pass error to caller (Dashboard will catch it)

**Update Status:**

```javascript
async updateComplaintStatus(complaintId, status) {
  const response = await fetch(`${BASE_URL}/complaints/${complaintId}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ status }),
  });
  return await response.json();
}
```

**HTTP Methods:**
- `GET` - Fetch data (read-only)
- `POST` - Create new resource
- `PATCH` - Update existing resource (partial update)
- `DELETE` - Remove resource

**Headers:**
- Tell server what format you're sending (`application/json`)

**Body:**
- The data you're sending (must be stringified)

---

## Styling Approach

### CSS Methodology

We use **Component-scoped CSS**:
- Each component has its own CSS file
- Class names are specific to that component
- Global styles in `index.css`

### Example: Priority Colors

```css
/* ComplaintTable.css */

.priority-high {
  background: linear-gradient(135deg, #FCA5A5 0%, #EF4444 100%);
  color: white;
}

.priority-medium {
  background: linear-gradient(135deg, #FDE047 0%, #FACC15 100%);
  color: #1F2937;
}

.priority-low {
  background: linear-gradient(135deg, #93C5FD 0%, #60A5FA 100%);
  color: #1F2937;
}
```

**CSS Concepts Used:**

**Gradients:**
```css
background: linear-gradient(135deg, color1, color2);
/*                          angle   start   end   */
```

**Flexbox (Layout):**
```css
.app-container {
  display: flex;           /* Use flexbox layout */
  min-height: 100vh;       /* Full viewport height */
}
```

**Transitions (Animations):**
```css
.nav-item {
  transition: all 0.3s ease;  /* Smooth animation */
}

.nav-item:hover {
  transform: translateX(4px);  /* Move 4px right */
  background: rgba(255, 255, 255, 0.1);
}
```

**Custom Scrollbar:**
```css
.table-container::-webkit-scrollbar {
  width: 8px;
}

.table-container::-webkit-scrollbar-thumb {
  background: #9CA3AF;
  border-radius: 4px;
}
```

---

## How to Run & Deploy

### Development (Local)

**1. Install Dependencies:**
```bash
cd frontend
npm install
```

**What it does:** Downloads all packages listed in `package.json`

**2. Start Dev Server:**
```bash
npm run dev
```

**What happens:**
- Vite starts development server on port 5173
- Opens in browser automatically
- Hot reload: Changes appear instantly

**3. Start Backend:**
```bash
cd backend
uvicorn app.main:app --reload
```

### Production Build

```bash
npm run build
```

**Output:** `dist/` folder with optimized files

**To preview:**
```bash
npm run preview
```

### Deployment Options

**Frontend:**
- Vercel (easiest for React)
- Netlify
- GitHub Pages
- AWS S3 + CloudFront

**Backend:**
- Render
- Railway
- Heroku
- AWS EC2

---

## Common Issues & Solutions

### Issue 1: "npm: command not found"

**Cause:** Node.js not installed or not in PATH

**Solution:**
```bash
# Check if installed
node --version
npm --version

# If not found, add to PATH (Windows)
$env:Path += ";C:\Program Files\nodejs"

# Or install Node.js from nodejs.org
```

---

### Issue 2: CORS Error

**Error:**
```
Access to fetch at 'http://localhost:8000/complaints' from origin
'http://localhost:5173' has been blocked by CORS policy
```

**Cause:** Backend not allowing frontend origin

**Solution:** Add CORS middleware in `backend/app/main.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

### Issue 3: Blank Page (White Screen)

**Causes & Solutions:**

1. **Check browser console** (F12 → Console tab)
   - Look for error messages

2. **Check if backend is running**
   ```bash
   curl http://localhost:8000/complaints
   ```

3. **Check network tab** (F12 → Network tab)
   - Are API calls failing?
   - What's the status code?

4. **Check React DevTools**
   - Install React DevTools extension
   - Inspect component tree

---

### Issue 4: "Cannot find module" Error

**Error:**
```
Error: Cannot find module './components/Dashboard'
```

**Causes:**
- Typo in filename
- File in wrong location
- Case sensitivity (Linux/Mac)

**Solution:**
- Check exact filename: `Dashboard.jsx` not `dashboard.jsx`
- Check import path: `./components/Dashboard` not `./Components/Dashboard`

---

### Issue 5: State Not Updating

**Problem:** You change state but UI doesn't update

**Common Mistakes:**

```javascript
// ❌ WRONG - Mutating state directly
complaints.push(newComplaint);

// ✅ CORRECT - Create new array
setComplaints([...complaints, newComplaint]);
```

**Why:** React only re-renders when state reference changes. Mutating the array keeps same reference.

---

## Advanced Concepts (For Future Learning)

### 1. React Router
Add multiple pages (Dashboard, Settings, Profile):
```bash
npm install react-router-dom
```

### 2. State Management Libraries
For complex apps with lots of state:
- **Redux** - Most popular, steep learning curve
- **Zustand** - Simpler alternative
- **Context API** - Built into React

### 3. API Libraries
Better than `fetch`:
- **Axios** - More features, easier error handling
- **React Query** - Caching, auto-refetch, loading states

### 4. UI Component Libraries
Pre-built components:
- **Material-UI** - Google Material Design
- **Chakra UI** - Modern, accessible
- **Ant Design** - Enterprise-grade

### 5. TypeScript
Add type safety:
```typescript
interface Complaint {
  id: number;
  description: string;
  status: 'pending' | 'in-progress' | 'resolved' | 'closed';
}
```

---

## Quick Reference

### React Hooks Cheat Sheet

```javascript
// State
const [value, setValue] = useState(initialValue);

// Effect (runs after render)
useEffect(() => {
  // code
}, [dependencies]);

// Ref (persist value across renders)
const ref = useRef(initialValue);

// Callback (memoized function)
const fn = useCallback(() => {
  // code
}, [dependencies]);

// Memo (memoized value)
const value = useMemo(() => {
  return expensiveCalculation();
}, [dependencies]);
```

### Common Array Methods

```javascript
// Map (transform array)
const doubled = [1, 2, 3].map(x => x * 2); // [2, 4, 6]

// Filter (keep matching items)
const evens = [1, 2, 3, 4].filter(x => x % 2 === 0); // [2, 4]

// Find (first matching item)
const found = [{id: 1}, {id: 2}].find(x => x.id === 2); // {id: 2}

// Some (any match?)
const hasEven = [1, 2, 3].some(x => x % 2 === 0); // true

// Every (all match?)
const allEven = [2, 4, 6].every(x => x % 2 === 0); // true
```

### Async/Await Pattern

```javascript
// Promise chain (old way)
fetch(url)
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(err => console.error(err));

// Async/Await (modern way)
try {
  const res = await fetch(url);
  const data = await res.json();
  console.log(data);
} catch (err) {
  console.error(err);
}
```

---

## Resources for Learning More

### Official Docs
- React: https://react.dev/
- Vite: https://vitejs.dev/
- MDN Web Docs: https://developer.mozilla.org/

### Interactive Tutorials
- React Tutorial: https://react.dev/learn
- JavaScript.info: https://javascript.info/
- FreeCodeCamp: https://www.freecodecamp.org/

### YouTube Channels
- Traversy Media
- Fireship
- Web Dev Simplified
- Codevolution

---

## Summary

**What You Built:**
- A full-stack React application with real-time features
- Component-based architecture
- RESTful API integration
- Modern, responsive UI

**Key Takeaways:**
1. **React = Components** - Small, reusable pieces
2. **Props = Data Down** - Parent passes data to children
3. **State = Data Up** - Children trigger parent's functions
4. **Effects = Side Effects** - Fetching data, timers, subscriptions
5. **JSX = HTML in JS** - Easier than creating elements manually

**You Now Know:**
- How to structure a React project
- How to manage state and props
- How to make API calls
- How to style components
- How to debug common issues

---

**Congratulations!** You've built a production-ready React dashboard. Keep experimenting and building! 🚀
