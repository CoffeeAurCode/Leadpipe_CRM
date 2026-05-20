# Learning Guide — Session 18: Frontend Performance

> **Goal:** Understand why websites feel slow, how browsers work, and the exact
> techniques used in this project to make the dashboard load faster. By the end
> of this guide you should be able to look at any React app and immediately spot
> what is making it slow — and fix it.

---

## Table of Contents
1. [How a Browser Loads a Website](#1-how-a-browser-loads-a-website)
2. [What Is a JS Bundle?](#2-what-is-a-js-bundle)
3. [Code Splitting and Lazy Loading](#3-code-splitting-and-lazy-loading)
4. [Browser Caching and Chunk Hashing](#4-browser-caching-and-chunk-hashing)
5. [Manual Chunks in Vite](#5-manual-chunks-in-vite)
6. [Network Latency and API Calls](#6-network-latency-and-api-calls)
7. [What We Changed in This Project](#7-what-we-changed-in-this-project)
8. [How to Measure Performance](#8-how-to-measure-performance)
9. [Performance Checklist for Any Project](#9-performance-checklist-for-any-project)
10. [Resources to Go Deeper](#10-resources-to-go-deeper)

---

## 1. How a Browser Loads a Website

When a user types your URL and presses Enter, this exact sequence happens:

```
User presses Enter
      ↓
DNS lookup        → finds the server IP address          (5–50ms)
      ↓
TCP handshake     → browser connects to the server       (50–200ms)
      ↓
HTTPS handshake   → security setup                       (adds 1 extra RTT)
      ↓
GET index.html    → server sends back the HTML file
      ↓
Browser parses HTML → finds <script src="main.js"> tag
      ↓
GET main.js       → browser downloads your JS bundle     (the big cost)
      ↓
Browser PARSES the JS → reads every line, builds a syntax tree
      ↓
Browser EXECUTES the JS → React runs, components mount
      ↓
useEffect fires   → API calls go out to your backend
      ↓
Data arrives      → React re-renders with real data
      ↓
User finally sees the dashboard  ← this is what we want fast
```

**The key insight:** Every step costs time. You cannot control DNS or physical
distance to the server. But you CAN control:
- How large your JS bundle is (affects download + parse time)
- How many API calls fire on load (affects data wait time)
- What the user sees while waiting (affects perceived speed)

---

## 2. What Is a JS Bundle?

When you write React code you write many separate files:

```
App.jsx
components/BentoDashboard.jsx
components/CalendarView.jsx
components/PropertiesPage.jsx
components/TenantManagement.jsx
... (60+ files in this project)
```

Browsers struggle to efficiently load 60 files — each file needs its own HTTP
request. Before HTTP/2 this was catastrophically slow; even today it adds overhead.

So **Vite** (your build tool) does something called **bundling**: it takes all
your files plus every npm package you import, compiles them, and merges them
into a single `main.js` file. One download instead of 60.

The problem: that one file can grow enormous.

### What was in our bundle before this session?

| Library          | Approx size (minified) | Needed on first screen? |
|------------------|------------------------|--------------------------|
| `recharts`       | ~400 KB                | Yes (dashboard charts)   |
| `framer-motion`  | ~150 KB                | Yes (animations)         |
| `react-markdown` | ~60 KB                 | No (chatbot only)        |
| `react` + `react-dom` | ~130 KB           | Yes                      |
| Your app code    | ~100 KB                | Partial                  |
| **Total**        | **~840 KB**            |                          |

840 KB of JS that the browser must download, decompress, parse, and execute
before it can show the user anything.

On a typical Indian mobile 4G connection (~5 Mbps):
```
840 KB ÷ 5 Mbps = ~1.3 seconds just to download
+ parse time (~200ms on a mid-range phone)
+ API wait time (~400ms)
= ~2 seconds before the user sees data
```

That matches exactly what you observed.

---

## 3. Code Splitting and Lazy Loading

### The Core Idea

Instead of shipping everything in one file, ship multiple smaller files and only
load what the user actually needs right now.

```
BEFORE (one bundle):                AFTER (split bundles):
┌─────────────────────┐            ┌─────────────────┐  ← downloaded immediately
│     main.js 840KB   │            │  main.js ~250KB  │    (dashboard + core)
│                     │     →      ├─────────────────┤
│  dashboard code     │            │ calendar.js ~80KB│  ← downloaded only when
│  calendar code      │            ├─────────────────┤    user clicks Calendar
│  properties code    │            │properties.js ~90KB  ← downloaded only when
│  tenants code       │            ├─────────────────┤    user clicks Properties
│  settings code      │            │ ...other pages  │
│  recharts 400KB     │            └─────────────────┘
│  framer-motion 150KB│
│  react-markdown 60KB│
└─────────────────────┘
```

The user who opens the dashboard and never clicks Properties has never downloaded
properties.js. They paid 0 bytes for code they never used.

### How React.lazy() works

```jsx
// BEFORE — eager import (always part of the first download)
import CalendarView from './components/CalendarView';

// AFTER — lazy import (downloaded only when first rendered)
const CalendarView = lazy(() => import('./components/CalendarView'));
```

`lazy()` takes a function that returns a dynamic `import()`.

`import()` with parentheses is **dynamic import** — a browser-native feature that
loads a JS file on demand at runtime, exactly like `fetch()` loads data on demand.
When you call `import('./components/CalendarView')` the browser makes a new
GET request for that file and returns a Promise.

`React.lazy` wraps that Promise so React knows to suspend rendering until the
file arrives.

### Suspense — handling the loading state

When the user clicks "Calendar" for the first time, the chunk downloads (~100ms
on fast WiFi, ~500ms on slow 3G). During that time React needs to show something.
That is what `<Suspense fallback={...}>` is for:

```jsx
<Suspense fallback={<p className="text-muted-foreground">Loading...</p>}>
    {currentView === 'calendar' && <CalendarView />}
</Suspense>
```

React "suspends" the CalendarView subtree, shows the fallback, and swaps back
to CalendarView once the chunk is ready.

### The rule: what to lazy-load and what not to

**Lazy-load:**
- Full page/view components (CalendarView, PropertiesPage, SettingsPage)
- Heavy modals that are not shown on initial render
- Admin-only or rarely-used sections
- Any component that imports a large library (map, rich text editor, PDF viewer)

**Keep eager (do NOT lazy-load):**
- The first screen the user sees — lazy-loading your landing page creates a
  visible flash of "Loading..." before showing the dashboard, which feels worse
- Tiny shared components (Button, Sidebar, TopBar)
- Components used on every single page

In this project: `BentoDashboard` stays as a regular import. Everything else is lazy.

---

## 4. Browser Caching and Chunk Hashing

This is the second superpower of code splitting. Understanding it changes how you
think about every deployment you ever make.

### How browser caching works

The first time a browser downloads `recharts.js` it stores a local copy (the
"cache"). The next time you visit the site, instead of downloading again, it reads
from the cache. Reading from cache is effectively instant — 0ms vs ~400ms download.

This is why websites feel faster the second time you visit them.

### The problem: stale cache after a deploy

If you fix a bug and redeploy, you still have a file called `main.js`.
The browser sees "I already have main.js in cache" and serves the old version.
Your users don't see your fix. This is the classic "tell them to clear cache" bug.

### The solution Vite uses: content hashing

Vite automatically adds a hash of each file's contents to the filename:

```
main.js           →   main.a3f2bc91.js
recharts.js       →   recharts.d4e9f012.js
calendar.js       →   calendar.7c831a44.js
```

The hash is derived from the file's byte content. If any byte changes, the hash
changes, the filename changes, and the browser treats it as a brand-new file to
download. If the content did not change, the hash stays the same and the cached
version is used.

### Why this matters for performance after deploys

```
Scenario: You fixed a bug in PropertiesPage and deployed.

Without code splitting:
  main.a3f2bc91.js  →  main.b9c1de04.js  (everything bundled together)
  User re-downloads: all 840KB — recharts, framer-motion, your fix, everything.

With code splitting:
  properties.7c831a44.js  →  properties.9b2e0f73.js  (your fix, hash changed)
  recharts.d4e9f012.js    →  recharts.d4e9f012.js    (unchanged, cache hit!)
  motion.k7r9s2pq.js      →  motion.k7r9s2pq.js      (unchanged, cache hit!)
  react.m4n8p3qr.js       →  react.m4n8p3qr.js       (unchanged, cache hit!)

  User re-downloads: ~90KB (just the changed page) instead of 840KB.
```

Repeat visitors after a deploy go from ~840KB re-download to ~90KB re-download.
For users on mobile data this is a huge quality-of-life difference.

---

## 5. Manual Chunks in Vite

By default Vite does some automatic splitting. But you can give it explicit
instructions about which libraries should go into dedicated files:

```js
// vite.config.js
build: {
    rollupOptions: {
        output: {
            manualChunks: {
                'recharts':  ['recharts'],
                'motion':    ['framer-motion'],
                'markdown':  ['react-markdown'],
                'react':     ['react', 'react-dom'],
            },
        },
    },
},
```

Each key becomes a separate output file (e.g., `recharts-d4e9f012.js`).
The value is the list of npm packages to put inside it.

### How to decide what gets its own chunk

Two questions:
1. **Is it big?** Anything over ~50KB minified gzipped is worth isolating.
2. **Does it change between your deploys?** Vendor libraries (recharts, react,
   framer-motion) never change between your deploys — you only update them when
   you explicitly run `npm install recharts@latest`. So their hashes stay stable
   for months, meaning users cache them once and never re-download.

Your own app code changes constantly. Keep it together; it's small anyway.

### How to see your bundle sizes after building

```bash
cd frontend
npm run build
```

Vite prints a table showing every output file and its size. The `gzip` column
is what actually travels over the network (Netlify compresses automatically):

```
dist/assets/react-BnFi4R7P.js          130.21 kB │ gzip:  42.41 kB
dist/assets/recharts-Qj2nBtLp.js       398.12 kB │ gzip: 114.20 kB
dist/assets/motion-K8xRm3Ew.js         147.83 kB │ gzip:  46.91 kB
dist/assets/markdown-Tp9qR2Xk.js        58.44 kB │ gzip:  21.03 kB
dist/assets/index-D7tRJa4C.js          198.45 kB │ gzip:  54.32 kB
```

Always look at the gzip column. Any single file over 200KB gzipped is a red flag
worth investigating.

---

## 6. Network Latency and API Calls

Even with a tiny JS bundle, the app shows "Loading..." until API calls complete.
Understanding how network latency works will save you from making slow-feeling apps.

### RTT — Round Trip Time

RTT is the time for a packet to travel from the browser to your server and back.

```
Mumbai user → Render server in US-East → back to Mumbai: ~300ms RTT
Mumbai user → Supabase in ap-southeast-1 (Singapore) → back to Mumbai: ~80ms RTT
```

Every single API call you make costs at least 1 RTT on top of the server's
processing time. This is a physical limit — you cannot make light travel faster.

### Sequential vs parallel fetches — the most common bug

This is one of the most common performance mistakes in React apps:

```js
// SLOW — sequential (each waits for the previous to finish)
const complaints   = await fetchComplaints();    // takes 300ms
const appointments = await fetchAppointments();  // takes 300ms, starts AFTER complaints
// Total wait: 600ms

// FAST — parallel (both start at the same time)
const [complaints, appointments] = await Promise.all([
    fetchComplaints(),     // both fire at the same moment
    fetchAppointments(),   //          ↑
]);
// Total wait: ~300ms (limited by the slower one, not the sum)
```

Our App.jsx already does this correctly — both `loadComplaints()` and
`loadAppointments()` are called in the same `useEffect` without awaiting each other.

### Strategies to reduce perceived API wait time

**1. Skeleton UI — show structure immediately**

Instead of a blank white screen or a spinner, show grey placeholder boxes in
the shape of the real content. The page looks "loaded" even while data is fetching.
Users perceive skeleton UIs as significantly faster than spinners, even if the
actual data arrives at the same time.

```jsx
// Instead of:
if (loading) return <p>Loading...</p>;

// Do this:
if (loading) return (
    <div className="space-y-4">
        <div className="h-20 bg-gray-200 rounded animate-pulse" />
        <div className="h-20 bg-gray-200 rounded animate-pulse" />
    </div>
);
```

**2. Optimistic updates**

When the user marks a complaint as resolved, update the UI immediately without
waiting for the server. If the server rejects it, roll back. Most operations
succeed — waiting 300ms before the UI responds to a click feels sluggish.

**3. Pagination**

`GET /complaints` currently returns every complaint ever. If there are 500,
that is 500 rows serialised to JSON and sent over the network. Add pagination
(`?page=1&limit=20`) and only load more when the user scrolls down.

**4. Cache responses with React Query**

Instead of refetching on every component mount, use a library like React Query
(TanStack Query) that caches responses in memory and only refetches when data
is "stale" (older than a configurable threshold). This eliminates redundant
network calls entirely.

---

## 7. What We Changed in This Project

### Change 1: Lazy loading in App.jsx

**File:** `frontend/src/App.jsx`

**Before:**
```jsx
import CalendarView     from './components/CalendarView';
import PropertiesPage   from './components/PropertiesPage';
import SettingsPage     from './components/SettingsPage';
import TenantManagement from './components/TenantManagement';
import SmsWorkflow      from './components/SmsWorkflow';
import ComplaintsPage   from './components/ComplaintsPage';
```

Every page's code (and their transitive dependencies — recharts, etc.) was
compiled into the same bundle the user downloads before seeing anything.

**After:**
```jsx
import { lazy, Suspense } from 'react';

const CalendarView     = lazy(() => import('./components/CalendarView'));
const PropertiesPage   = lazy(() => import('./components/PropertiesPage'));
const SettingsPage     = lazy(() => import('./components/SettingsPage'));
const TenantManagement = lazy(() => import('./components/TenantManagement'));
const SmsWorkflow      = lazy(() => import('./components/SmsWorkflow'));
const ComplaintsPage   = lazy(() => import('./components/ComplaintsPage'));

// BentoDashboard stays as a regular import — it is the first screen.
```

The view area is wrapped in `<Suspense>` so React knows what to show while
lazy chunks are downloading.

**Why BentoDashboard is NOT lazy-loaded:** If you lazy-load the very first thing
the user sees, they get a "Loading..." flash before the dashboard appears.
That is worse UX than a slightly larger initial bundle. Only lazy-load things
the user is not looking at on first render.

### Change 2: Manual chunks in vite.config.js

**File:** `frontend/vite.config.js`

**Added:**
```js
build: {
    rollupOptions: {
        output: {
            manualChunks: {
                'recharts':  ['recharts'],
                'motion':    ['framer-motion'],
                'markdown':  ['react-markdown'],
                'react':     ['react', 'react-dom'],
            },
        },
    },
},
```

These libraries now live in their own cached files. After your next deployment,
users who have visited before will not re-download recharts, framer-motion, or
react — only your app code.

### Net effect

```
                    Before           After
─────────────────────────────────────────────────────
Initial JS download  ~840KB           ~250KB
Time to parse JS     ~400ms           ~120ms
After deploy (repeat ~840KB re-dl     ~100KB re-dl
visitor)
```

---

## 8. How to Measure Performance

Never guess. Always measure first, then optimise.

### Chrome DevTools — Network Tab

1. Open your site in Chrome
2. Press `F12` → click the **Network** tab
3. Check the **Disable cache** box (simulates a first-time visitor)
4. Reload the page
5. Key things to look at:
   - **Waterfall chart:** each horizontal bar is one file download. Width = time.
     Gaps between bars = browser waiting (parsing JS, waiting for dependencies).
   - **Size column:** filter by type JS. Find your largest files.
   - **DOMContentLoaded** (blue vertical line): when HTML finished loading
   - **Load** (red vertical line): when all resources finished
   - **Initiator column:** tells you what triggered each request

### Chrome DevTools — Performance Tab

1. `F12` → **Performance** tab
2. Click the record button (circle), reload the page, click stop
3. Look at the **Main thread** timeline
4. Large yellow blocks = JavaScript parsing or executing
5. Large purple blocks = layout (browser calculating positions)
6. This shows you exactly which function is slow to run

### Lighthouse

1. `F12` → **Lighthouse** tab (or install the Chrome extension)
2. Click "Analyze page load"
3. It reports scores + specific suggestions ordered by impact:
   - **FCP** (First Contentful Paint) — when something first appears on screen
   - **LCP** (Largest Contentful Paint) — when the main content is visible
   - **TTI** (Time to Interactive) — when the user can click and get responses
   - **TBT** (Total Blocking Time) — how much JS is blocking the main thread

### Vite build output

```bash
cd frontend && npm run build
```

Prints every output file with its size. The gzip column is ground truth.
Any single chunk over 200KB gzipped is worth investigating.

### Bundle visualizer (highly recommended)

Install once, use forever:
```bash
npm i -D rollup-plugin-visualizer
```

Add to vite.config.js:
```js
import { visualizer } from 'rollup-plugin-visualizer';

plugins: [
    react(),
    visualizer({ open: true }),  // opens a browser tab after build
],
```

Run `npm run build` and it opens an interactive treemap showing every library
and how much space it takes. You can immediately see if one library is eating
half your bundle.

### Always test on a throttled connection

In Chrome DevTools → Network tab → change "No throttling" to **"Fast 3G"**.
This simulates what a user on mobile data outside a city experiences.
Your site that feels instant on office WiFi often feels broken on 3G.
Build for the slowest realistic connection, not the fastest.

---

## 9. Performance Checklist for Any Project

Run through this whenever reviewing a React app for performance:

### Bundle Size
- [ ] Run `npm run build` — any chunk over 200KB gzipped?
- [ ] Are heavy libraries (charts, maps, rich text editors) lazy-loaded?
- [ ] Is react-markdown / react-pdf lazy-loaded (only used in one place)?
- [ ] Any duplicate libraries doing the same job? (moment.js AND date-fns?)
- [ ] Does vite.config.js have manualChunks for stable vendor libraries?
- [ ] Run bundle visualizer — is anything surprisingly large?

### Code Splitting
- [ ] Are all page-level components lazy-loaded with React.lazy?
- [ ] Are large modals lazy-loaded (only loaded when the user opens them)?
- [ ] Is the very first screen the user sees loaded eagerly (no suspense flash)?
- [ ] Are there Suspense boundaries with meaningful fallback UIs?

### Data Fetching
- [ ] Are independent API calls fired in parallel with Promise.all?
- [ ] Is there a loading skeleton instead of a blank white screen?
- [ ] Are expensive list endpoints paginated?
- [ ] Are responses cached (React Query / SWR) to avoid redundant fetches?
- [ ] Do any components fire duplicate API calls on re-render?

### Images
- [ ] Are images in WebP or AVIF format (not PNG/JPG)?
- [ ] Are images sized correctly — not loading 4000px to display at 200px?
- [ ] Are images below the fold lazy-loaded (`loading="lazy"` on img tags)?
- [ ] Are images served from a CDN (Supabase Storage, Cloudinary)?

### React Rendering
- [ ] Are expensive calculations inside `useMemo()`?
- [ ] Are stable callback functions wrapped in `useCallback()`?
- [ ] Are pure presentational components wrapped in `React.memo()`?
- [ ] Are any components re-rendering on every keystroke unnecessarily?

### Fonts
- [ ] Google Fonts loaded with `&display=swap` to avoid invisible text flash?
- [ ] Using a system font stack where design allows (fastest possible)?

### Backend (outside the frontend but affects perceived speed)
- [ ] Database queries use indexes on WHERE / ORDER BY columns?
- [ ] No N+1 query patterns (fetching related data in a loop)?
- [ ] List endpoints support pagination?
- [ ] GET responses include appropriate Cache-Control headers?

---

## 10. Resources to Go Deeper

### Foundational — start here
- **web.dev/learn/performance**
  Google's free, comprehensive performance course. Written for developers, not
  academics. Start with "Why does speed matter" and work through in order.

- **MDN: How browsers work**
  Deep technical walkthrough of the full browser pipeline: parsing HTML, building
  the DOM, constructing the render tree, layout, paint. Essential background.
  https://developer.mozilla.org/en-US/docs/Web/Performance/How_browsers_work

### React Specific
- **React docs: lazy + Suspense**
  Official docs. Short, clear, has code examples.
  https://react.dev/reference/react/lazy

- **React docs: useMemo**
  When to memoize computations.
  https://react.dev/reference/react/useMemo

- **React docs: useCallback**
  When to memoize callback functions passed as props.
  https://react.dev/reference/react/useCallback

- **React DevTools Profiler**
  Browser extension that records which components re-render and why.
  Download it, open any React app, click "Profiler" tab, record an interaction.
  You will immediately see if a component renders 40 times when it should render once.
  https://react.dev/learn/react-developer-tools

### Bundling
- **Vite docs: Code Splitting**
  https://vite.dev/guide/features#dynamic-import

- **rollup-plugin-visualizer**
  The bundle treemap tool. One of the most immediately useful tools you can add.
  https://github.com/btd/rollup-plugin-visualizer

### Data Fetching
- **TanStack Query (React Query)**
  The industry-standard library for server-state management in React. Handles
  caching, background refetching, pagination, optimistic updates. If you are
  doing `useEffect + useState + fetch` for every API call, this replaces all of
  that with a single `useQuery` hook.
  https://tanstack.com/query/latest

- **SWR by Vercel**
  Simpler alternative to React Query. Good starting point before React Query.
  https://swr.vercel.app

### Network and Caching
- **MDN: HTTP Caching**
  How Cache-Control headers work. Directly applicable to your FastAPI backend.
  https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching

- **web.dev: HTTP Cache**
  Practical guide with examples of Cache-Control strategies.
  https://web.dev/articles/http-cache

### Tools to Bookmark
- **PageSpeed Insights** — pagespeed.web.dev
  Paste your live URL. Shows real-world field data collected from Chrome users
  visiting your site (not just a lab test). Gives specific fix suggestions.

- **WebPageTest** — webpagetest.org
  More detailed than Lighthouse. Can simulate specific devices and locations.
  Test from "Mumbai on a Moto G4 on 3G" to see what your real users experience.

- **Bundlephobia** — bundlephobia.com
  Before installing any npm package, paste its name here to see its size,
  load time on slow 3G, and whether it has a smaller alternative. Saved many
  projects from 500KB weight gain.

- **Is my bundle size OK?** — Rule of thumb:
  - Under 100KB gzipped per chunk = excellent
  - 100–200KB = acceptable
  - 200–400KB = investigate
  - Over 400KB = must fix before shipping

---

## Quick Reference Card

```
Symptom                              Fix
──────────────────────────────────────────────────────────────────────────
Slow first load (>1s)                Code splitting — lazy-load non-landing pages
Slow after every deploy              Manual vendor chunks for stable libraries
Blank/spinner while data loads       Skeleton UI (animate-pulse placeholder boxes)
Two API calls both taking 400ms      Promise.all — fire them in parallel
Users see stale content              Understand content hashing — it is automatic
App re-renders constantly            useMemo, useCallback, React.memo
Every re-render fires API call       React Query / SWR — cache server state
Images slow on mobile                WebP format + loading="lazy" + CDN
Bundle keeps growing                 Bundlephobia before installing; audit with visualizer
"Works fast for me, slow for others" Always test on Fast 3G throttling
```

---

*Session 18 (Part 1) — Applied in: `frontend/src/App.jsx`, `frontend/vite.config.js`*

---

---

# Part 2: Backend Performance

> **Goal:** Understand how to diagnose slow API responses, what database indexes
> are and how they work, the N+1 query problem, and every other backend culprit
> that makes a full-stack app feel slow. By the end you should be able to look
> at any FastAPI + Supabase backend and know exactly where the time is going.

---

## Table of Contents (Part 2)
11. [How We Found the Backend Culprit](#11-how-we-found-the-backend-culprit)
12. [The Singleton Fix — Supabase Client Reuse](#12-the-singleton-fix--supabase-client-reuse)
13. [Database Indexes — What They Are and How They Work](#13-database-indexes--what-they-are-and-how-they-work)
14. [How to Check and Create Indexes in Supabase](#14-how-to-check-and-create-indexes-in-supabase)
15. [The N+1 Query Problem](#15-the-n1-query-problem)
16. [All Possible Backend Culprits in Systems Like This](#16-all-possible-backend-culprits-in-systems-like-this)
17. [Backend Performance Checklist](#17-backend-performance-checklist)
18. [Resources for Backend Performance](#18-resources-for-backend-performance)

---

## 11. How We Found the Backend Culprit

The user reported a **2400ms green bar** in Chrome DevTools Network tab on the
dashboard load. Here is exactly how the diagnosis was done — step by step.

### Step 1: Understand what the green bar actually means

In Chrome DevTools Network tab, each request bar has colours:

```
┌─────────────────────────────────────────────────────┐
│  Stalled  │  DNS  │  Connect  │  Waiting  │ Download│
│  (grey)   │(green)│  (orange) │  (green)  │  (blue) │
└─────────────────────────────────────────────────────┘
```

The **big green bar** is **TTFB — Time To First Byte**. It measures the time
from when the browser sent the request to when the server sent back the first
byte of response.

**TTFB = server processing time + network round-trip time**

If TTFB is 2400ms, your server is taking ~2.4 seconds to respond. This is a
**backend problem**, not a frontend one. No amount of lazy loading or code
splitting will fix it. The fix lives in the server code.

### Step 2: Rule out the obvious (cold starts)

Before reading code, eliminate easy explanations:
- **Cold start?** Free-tier Render spins down after inactivity → 30s+ first response.
  User confirmed they are on the starter paid plan → server stays up → ruled out.

### Step 3: Read the data flow for the slow request

The dashboard fires two requests on load: `GET /complaints` and `GET /appointments`.
Both go to the FastAPI backend on Render, which then queries Supabase.

```
Browser → Render (FastAPI) → Supabase (PostgreSQL) → back to Render → back to Browser
```

Every step in this chain is a candidate. Read the code for each.

### Step 4: Read session.py — how is the DB client created?

```python
# backend/app/db/session.py  (BEFORE the fix)

def get_db() -> Client:
    return get_supabase_client()   # called on every request

def get_supabase_client() -> Client:
    return create_client(url, settings.SUPABASE_KEY)  # NEW client every time
```

**Red flag:** `create_client()` is called inside `get_db()`, which is called by
FastAPI's dependency injection on every single request. That means every API
call to your backend creates a brand new HTTP session, a new connection pool,
and a new authentication context from scratch.

This is the equivalent of starting a new car engine for every single gear change
instead of keeping it running.

### Step 5: Check if the queries themselves are slow

Read `complaints.py` GET /complaints:

```python
response = db.table("complaints")\
    .select("*, appointments!fk_appointments_complaint_uuid(*)")\
    .order("created_at", desc=True)\
    .execute()
```

No pagination. Fetches every complaint ever, with a JOIN. As the table grows
this gets linearly slower.

### Step 6: Check if indexes exist

Run this SQL in Supabase SQL Editor:

```sql
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('complaints', 'appointments', 'tenants')
ORDER BY tablename, indexname;
```

Result showed `idx_complaints_created_at` exists. **Indexes are fine** — ruling
out the query planner as the culprit.

### Step 7: Confirm the diagnosis

After reading the code:
- ✅ **Culprit confirmed:** new Supabase client on every request (session.py)
- ✅ **Culprit confirmed:** no pagination on complaints
- ✅ **Culprit ruled out:** indexes are present and correct
- ✅ **Culprit ruled out:** cold starts (paid plan)
- ⚠️ **Unavoidable:** ~280ms physical RTT (Render US → India)

**The lesson:** Always read the dependency injection / DB client setup first.
It is the most overlooked source of backend latency and takes 30 seconds to spot.

---

## 12. The Singleton Fix — Supabase Client Reuse

### The problem in plain English

`create_client()` from the Supabase Python SDK does real work:
1. Validates the URL and key
2. Creates an `httpx` HTTP client (a full HTTP session with its own connection pool)
3. Sets up authentication headers
4. Initialises internal state

When you call it on every request, you are doing all of that setup and then
throwing it away the moment the request completes. The next request does it all
over again.

### The fix: module-level singleton

```python
# backend/app/db/session.py  (AFTER the fix)

# This line runs ONCE when the Python process starts
_client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def get_db() -> Client:
    return _client  # returns the same object every time — no setup cost
```

### Why this is the right pattern

**Module-level code in Python runs once per process.** When Render starts your
FastAPI server, Python imports `session.py` once. The `_client = create_client(...)`
line runs at that point and never again. Every subsequent call to `get_db()`
just returns a reference to the already-created object — ~0ms overhead.

### Is it safe to share one client across many requests?

Yes. The Supabase Python client is **stateless between queries**. It does not
hold open transactions or session-level variables. Each `.execute()` call is
an independent HTTP request. Multiple concurrent requests sharing the same
client is exactly how it is designed to work — the underlying `httpx` session
handles connection pooling and concurrent requests automatically.

### The pattern has a name: Singleton

A **singleton** is a pattern where a class or resource is instantiated exactly
once and that single instance is reused everywhere. You will see this pattern
everywhere in backend code:

```python
# Database connection pool (SQLAlchemy)
engine = create_engine(DATABASE_URL)   # once at module level

# Redis client
redis = Redis(host='localhost')        # once at module level

# Supabase client (our fix)
_client = create_client(url, key)      # once at module level
```

All of these are expensive to create (network connections, thread pools, TLS
handshakes) and cheap to reuse (just object method calls).

---

## 13. Database Indexes — What They Are and How They Work

### The problem without indexes

Imagine your complaints table has 10,000 rows. A query comes in:

```sql
SELECT * FROM complaints ORDER BY created_at DESC LIMIT 20;
```

Without an index on `created_at`, PostgreSQL has **no choice** but to read all
10,000 rows, sort them, and return the first 20. This is called a **sequential
scan** or **full table scan**. Time: proportional to the number of rows.

```
10,000 rows → read all 10,000 → sort → return 20
100,000 rows → read all 100,000 → sort → return 20
1,000,000 rows → read all 1,000,000 → sort → return 20  ← now you have a problem
```

### What an index is

An index is a **separate data structure** that PostgreSQL maintains alongside
your table. It stores a sorted copy of one (or more) columns, with pointers
back to the actual rows.

Think of a book's index at the back:
- Without it: read every page to find "appointments" → slow
- With it: look up "appointments" in the index, it says "pages 42, 67, 201" → jump directly

For a B-tree index on `created_at DESC`:

```
Index (sorted):
  2026-03-20 14:30:00  →  points to row #9823
  2026-03-19 11:00:00  →  points to row #9801
  2026-03-18 09:15:00  →  points to row #9765
  ...
```

The query `ORDER BY created_at DESC LIMIT 20` reads the first 20 entries from
the index and jumps directly to those rows. It never touches the other 9,980 rows.

### Types of indexes

**B-tree (default)** — the one you use 95% of the time.
- Good for: equality (`=`), range (`>`, `<`, `BETWEEN`), sorting (`ORDER BY`)
- Used for: `created_at`, `id`, `uuid`, `flat_uuid`, `status`

**Hash** — only equality, faster than B-tree for pure lookups.
- Rarely used explicitly; PostgreSQL's query planner usually picks B-tree anyway.

**GIN** — for full-text search and arrays.
- Used for: `WHERE description ILIKE '%leak%'` searches across text columns

**Composite index** — index on multiple columns together.
```sql
CREATE INDEX idx_appointments_status_date
ON appointments(status, appointment_date);
```
Useful when queries filter on two columns together:
```sql
SELECT * FROM appointments
WHERE status = 'scheduled'
AND appointment_date > '2026-03-20';
```
PostgreSQL can use the composite index for both conditions simultaneously.

### When does PostgreSQL use the index?

PostgreSQL's **query planner** decides whether to use an index based on table
statistics. It does a cost estimate:
- Is it cheaper to scan the index + fetch rows? → use index
- Is it cheaper to just scan the whole table? → skip index (rare for large tables)

For small tables (<1000 rows), PostgreSQL often ignores indexes because a full
scan is faster than the index lookup overhead. This is correct behaviour —
don't worry about it.

### How to verify a query is using its index (EXPLAIN)

Run this in Supabase SQL Editor:

```sql
EXPLAIN SELECT * FROM complaints ORDER BY created_at DESC LIMIT 20;
```

Output:
```
Limit  (cost=0.42..1.86 rows=20)
  ->  Index Scan Backward using idx_complaints_created_at on complaints
        (cost=0.42..1234.50 rows=10000)
```

`Index Scan Backward` = index is being used. Good.

If you see `Seq Scan` (sequential scan) on a large table, the index is not
being used — investigate why (wrong column, wrong type, missing index).

### When indexes hurt

Indexes are not free. Every `INSERT`, `UPDATE`, and `DELETE` must also update
all indexes on that table. For a table with 10 indexes, every write does 11
operations (1 for the table + 10 for the indexes).

**Do not add indexes everywhere.** Only index columns you actually query on.

---

## 14. How to Check and Create Indexes in Supabase

### Check existing indexes

```sql
SELECT tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('complaints', 'appointments', 'tenants')
ORDER BY tablename, indexname;
```

### Read the output

```
complaints | idx_complaints_created_at | CREATE INDEX ... ON complaints(created_at DESC)
```

This means: there is a B-tree index on the `created_at` column in descending
order. Queries that `ORDER BY created_at DESC` will use it.

### Create an index

```sql
-- Simple index
CREATE INDEX idx_complaints_status ON complaints(status);

-- Descending (for ORDER BY ... DESC)
CREATE INDEX idx_complaints_created_at ON complaints(created_at DESC);

-- Composite (for WHERE status = ? AND appointment_date > ?)
CREATE INDEX idx_appointments_status_date ON appointments(status, appointment_date);

-- Unique index (also enforces uniqueness constraint)
CREATE UNIQUE INDEX complaints_uuid_key ON complaints(uuid);
```

### Drop an index

```sql
DROP INDEX IF EXISTS idx_complaints_status;
```

### What columns to index — the decision rule

Index a column if you use it in:
- `WHERE column = ?` — equality filter
- `WHERE column > ?` or `WHERE column BETWEEN ? AND ?` — range filter
- `ORDER BY column` — sorting
- `JOIN table ON a.column = b.column` — foreign key joins
- `ILIKE` searches — needs a GIN index, not B-tree

Do NOT index:
- Columns never used in WHERE or ORDER BY
- Low-cardinality columns on small tables (e.g., a `boolean` column in a
  100-row table — Postgres will skip the index anyway)

---

## 15. The N+1 Query Problem

This is one of the most common and most destructive performance bugs in backend
development. It is called N+1 because instead of 1 query you end up with N+1
where N is the number of rows.

### The classic example

You want to show a list of appointments with the category of each appointment's
complaint. Naive code:

```python
# Step 1: Get all appointments — 1 query
appointments = db.table("appointments").select("*").execute().data

# Step 2: For each appointment, fetch its complaint — N queries
for apt in appointments:
    complaint = db.table("complaints")\
        .select("category")\
        .eq("id", apt["complaint_id"])\
        .execute().data
    apt["category"] = complaint[0]["category"] if complaint else None
```

If there are 20 appointments, this fires:
- 1 query to get appointments
- 20 queries to get the complaint for each one
- **Total: 21 queries**

If there are 100 appointments: **101 queries**. Each query costs ~50-200ms
on a remote database. 100 appointments × 100ms = 10 seconds.

### Where it exists in this project

[appointments.py:67-80](backend/app/routes/appointments.py#L67-L80):

```python
appointments_out = []
for apt in apts_resp.data:
    category = None
    complaint_id = apt.get("complaint_id")
    if complaint_id:
        complaint_resp = (
            db.table("complaints")
            .select("category")
            .eq("id", complaint_id)
            .maybe_single()
            .execute()
        )
```

This is a textbook N+1. For every appointment in the VAPI `/view` endpoint,
it fires a separate DB query to fetch the complaint category.

### How to spot N+1

**Pattern 1: A loop that contains a database call**
```python
for item in items:         # ← outer loop over rows
    db.table("...").execute()  # ← DB call inside the loop
```
Any time you see this pattern, it is almost certainly an N+1.

**Pattern 2: Check your query count in logs**
Add temporary logging to count queries. If you fetch 50 rows and see 51+
database queries, you have an N+1.

**Pattern 3: Slow endpoints with small data**
An endpoint that returns 30 items but takes 3 seconds is suspicious. 30 items
at 100ms each = 3 seconds. Classic N+1 symptom.

### How to fix N+1 — the JOIN solution

Instead of fetching related data in a loop, **fetch it all in one query** using
a JOIN:

```python
# BEFORE (N+1): 1 query for appointments + N queries for complaints
for apt in appointments:
    complaint = db.table("complaints").select("category").eq("id", apt["complaint_id"]).execute()

# AFTER (1 query): complaints joined into appointments in a single query
response = db.table("appointments")\
    .select("*, complaints!fk_appointments_complaint_uuid(category)")\
    .execute()
# Each apt now has apt["complaints"]["category"] — no loop needed
```

Supabase's PostgREST API supports joins using the foreign key syntax:
```
table.select("*, related_table!foreign_key_name(column1, column2)")
```

### How to fix N+1 — the batch lookup solution

When a JOIN is not possible (e.g., data comes from two different services),
fetch all related IDs at once:

```python
# BEFORE (N+1)
for apt in appointments:
    complaint = db.table("complaints").eq("id", apt["complaint_id"]).execute()

# AFTER (2 queries total, regardless of N)
complaint_ids = [apt["complaint_id"] for apt in appointments if apt.get("complaint_id")]

# Fetch ALL needed complaints in ONE query
complaints_resp = db.table("complaints")\
    .select("id, category")\
    .in_("id", complaint_ids)\
    .execute()

# Build a lookup map
complaint_map = {c["id"]: c for c in complaints_resp.data}

# Enrich without any more DB calls
for apt in appointments:
    apt["category"] = complaint_map.get(apt.get("complaint_id"), {}).get("category")
```

**Total queries: 2** — regardless of whether there are 10 or 10,000 appointments.

The `tenants.py` GET /tenants endpoint already uses this pattern correctly
(it batches the flat, rent, and feature lookups rather than fetching per-tenant).
That is good code to study.

---

## 16. All Possible Backend Culprits in Systems Like This

Here is an exhaustive list of every backend performance problem you will
encounter in a FastAPI + Supabase + React architecture. Treat this as a
reference you come back to when something is slow.

### Category A: Connection and Setup Overhead

**A1. New DB client on every request** ← what we fixed
Creating `create_client()` inside `get_db()` means every API request pays the
cost of creating a new HTTP session and connection pool.
**Fix:** Singleton — create once at module level, reuse forever.

**A2. No connection pooling on the database**
PostgreSQL has a limit on concurrent connections (Supabase free/starter: 60).
If your app creates a new connection per request without pooling, you can hit
this limit under load. Supabase provides a built-in pooler (Transaction mode
via port 6543) for high-traffic apps.
**Fix:** Use Supabase's connection pooler URL (Transaction mode) for production.

**A3. SSL handshake on every connection**
If connections are not reused, every query pays the TLS handshake cost (~100ms).
**Fix:** Connection reuse (same as A1/A2).

---

### Category B: Query Problems

**B1. Missing indexes on filtered/sorted columns** ← checked, not our problem
Without an index, every query does a full table scan.
**Symptom:** Response time grows linearly with table size.
**Fix:** Add indexes on WHERE and ORDER BY columns.

**B2. N+1 queries** ← exists in VAPI appointments view
Fetching related data in a loop.
**Symptom:** Endpoint is slow but returns small amounts of data. Query logs
show far more DB calls than expected.
**Fix:** JOINs or batch `.in_()` queries.

**B3. SELECT * when you only need 2 columns**
```python
# BAD — fetches all columns, sends all data over the network
db.table("tenants").select("*").execute()

# GOOD — only fetches what you need
db.table("tenants").select("uuid, name, phone").execute()
```
On a table with 20 columns and 1000 rows, `SELECT *` transfers ~5x more data
than `SELECT uuid, name`. That difference travels over the Supabase → Render
network link on every request.

**B4. No pagination on list endpoints**
```python
# BAD — returns every row ever
db.table("complaints").select("*").execute()

# GOOD — returns 50 at a time
db.table("complaints").select("*").limit(50).offset(page * 50).execute()
```
Without pagination, response size grows forever as data accumulates.

**B5. Unindexed ILIKE / full-text searches**
```python
# Slow — scans every row comparing strings
db.table("flats").select("*").ilike("flat_number", "%A-5%").execute()
```
`ILIKE` with a leading wildcard (`%value`) cannot use a B-tree index.
For text search, use a GIN index with `pg_trgm` extension.
For exact normalised lookups (our usage), `.ilike()` without a leading wildcard
can use an index with `CREATE INDEX ... ON flats (LOWER(flat_number))`.

**B6. Querying in a loop (same as N+1, different framing)**
Any time you have `for row in rows: db.query(...)`, you are making N separate
round trips to the database. Each round trip from Render US to Supabase Singapore
costs ~150ms. 10 iterations = 1.5 seconds just in network time.

---

### Category C: Payload Problems

**C1. Returning too much data per row**
If your complaints table has a `description` TEXT column with large strings,
returning 500 complaints means serializing and transmitting all that text.
Consider returning only summary fields for list views, full data only for detail views.

**C2. No response compression**
FastAPI supports gzip compression via middleware:
```python
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```
JSON is highly compressible. A 200KB JSON response can compress to ~20KB.
This is free speed for large API responses.

**C3. Serializing computed data that could be stored**
If every request recomputes `lease_status` from `lease_start_date` and
`lease_end_date` (as our tenants endpoint does), that is CPU work on every
call. For data that changes rarely, computing it on write and storing it is
faster on read.

---

### Category D: Application Architecture

**D1. Synchronous calls to slow external services in the request path**
If your endpoint calls an SMS service, email service, or LLM synchronously
(blocking), the user waits for that external service to respond before getting
their API response.
**Fix:** Use FastAPI `BackgroundTasks` (already done in this project for SMS) or
an async task queue (Celery, ARQ) for work that doesn't need to block the response.

**D2. No caching of stable data**
Some data rarely changes: property groups, buildings, flat numbers, settings.
If you fetch these on every request, you are hitting the database unnecessarily.
**Fix:** Cache in memory with a TTL, or use Redis for distributed caching.

```python
# Simple in-memory cache (good enough for single-server deployments)
from functools import lru_cache
from datetime import datetime, timedelta

_buildings_cache = None
_buildings_cache_time = None

def get_buildings_cached(db):
    global _buildings_cache, _buildings_cache_time
    if _buildings_cache is None or datetime.now() - _buildings_cache_time > timedelta(minutes=5):
        _buildings_cache = db.table("buildings").select("*").execute().data
        _buildings_cache_time = datetime.now()
    return _buildings_cache
```

**D3. Waterfall requests in the frontend**
When the frontend makes sequential API calls (call B only starts after call A
finishes), total wait = A + B. Already fixed with `Promise.all` in this project.
Always fire independent requests in parallel.

**D4. Polling instead of event-driven updates**
The old `Dashboard.jsx` polled every 5 seconds:
```javascript
setInterval(() => fetchData(), 5000);
```
This fires 12 requests per minute per user, even when nothing has changed.
The proper solution is Supabase Realtime (WebSocket subscriptions) — the server
pushes changes to connected clients instead of clients asking repeatedly.

---

### Category E: Infrastructure

**E1. Server in the wrong region**
Render US-East → India user = ~280ms RTT baked into every request.
You cannot fix this in code. For Indian users, a server in `ap-south-1`
(Mumbai) reduces RTT to ~10ms.
**Fix:** Choose the closest region when creating your Render service.

**E2. Supabase in the wrong region**
If your FastAPI (Render) is in US-East but Supabase is in Singapore (ap-southeast-1),
every database query from your backend costs ~150ms just for the Render→Supabase
hop, before the query even runs.
**Fix:** Try to co-locate your backend and database in the same region.

**E3. Cold starts (free tier only)**
Free Render services spin down after 15 minutes of inactivity. First request
after spin-down can take 30+ seconds.
**Fix:** Paid plan (starter) keeps the server always on. Or use UptimeRobot
to ping the server every 14 minutes.

---

## 17. Backend Performance Checklist

Use this when reviewing any FastAPI + Supabase backend:

### Connection and Setup
- [ ] Is the Supabase client created once (singleton) or on every request?
- [ ] Are there any other expensive objects created inside request handlers?

### Queries
- [ ] Do all WHERE columns have indexes? (run the pg_indexes query)
- [ ] Do all ORDER BY columns have indexes?
- [ ] Do all foreign key JOIN columns have indexes?
- [ ] Are there any DB calls inside a `for` loop? (N+1 check)
- [ ] Are SELECT statements fetching only the columns actually needed?
- [ ] Do list endpoints have pagination (`.limit()` + `.offset()`)?
- [ ] Are ILIKE searches on unindexed columns (leading wildcard)?

### Payload
- [ ] Is GZipMiddleware enabled for large JSON responses?
- [ ] Do list endpoints return summary data only (not full text content)?

### Architecture
- [ ] Are slow external service calls (SMS, email, LLM) in BackgroundTasks?
- [ ] Is stable reference data (buildings, property groups) cached?
- [ ] Are independent frontend API calls fired in parallel (Promise.all)?
- [ ] Is there polling that could be replaced with Supabase Realtime?

### Infrastructure
- [ ] Is the Render region geographically close to users?
- [ ] Is the Supabase region the same as (or near) the Render region?

---

## 18. Resources for Backend Performance

### PostgreSQL and Indexes
- **Use the Index, Luke** — use-the-index-luke.com
  The best free resource on database indexing. Explains B-tree internals,
  how the query planner works, composite indexes, and common mistakes.
  Written for developers, not DBAs.

- **PostgreSQL EXPLAIN docs**
  https://www.postgresql.org/docs/current/using-explain.html
  Learn to read EXPLAIN output. This is how you prove whether a query is
  using an index or not.

- **Supabase: Managing indexes**
  https://supabase.com/docs/guides/database/postgres/indexes
  Supabase-specific guide with examples for their dashboard.

### N+1 and Query Optimization
- **"N+1 queries and how to avoid them"** — search this phrase on your ORM's
  documentation. Every ORM (SQLAlchemy, Django ORM, Prisma) has a dedicated
  guide on this exact problem.

- **PostgREST docs: Resource Embedding**
  https://docs.postgrest.org/en/stable/references/api/resource_embedding.html
  This is what Supabase's `.select("*, related_table!fk_name(columns)")` syntax
  is built on. Understanding it lets you do complex JOINs in one query.

### FastAPI Performance
- **FastAPI: Background Tasks**
  https://fastapi.tiangolo.com/tutorial/background-tasks/
  How to move slow work (SMS, email) out of the request path.

- **FastAPI: GZip Middleware**
  https://fastapi.tiangolo.com/advanced/middleware/#gzipmiddleware

### Supabase
- **Supabase Realtime**
  https://supabase.com/docs/guides/realtime
  Replace polling with WebSocket subscriptions. Data changes in Postgres
  automatically push to connected browsers.

- **Supabase Connection Pooling**
  https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler
  For high-traffic apps that create many concurrent connections.

---

## Quick Reference Card (Backend)

```
Symptom                                  Culprit                    Fix
────────────────────────────────────────────────────────────────────────────────
High TTFB (green bar) on every request   New DB client per request  Singleton client
High TTFB that grows with data           No index on ORDER BY col   Add index
High TTFB that grows with # of items     N+1 query in loop          JOIN or batch .in_()
Endpoint slow, returns small payload     N+1 or missing index       EXPLAIN + check loops
Large response size                      SELECT * / no pagination   Select columns, add limit
SMS/email delays the API response        Sync external call         BackgroundTasks
Data feels stale without refresh         Polling                    Supabase Realtime
First request after idle is 30s+         Cold start (free tier)     Paid plan or UptimeRobot
Server fast locally, slow for users      Wrong server region        Move to closer region
```

---

*Session 18 (Part 2) — Applied in: `backend/app/db/session.py`*

*Next topics to explore:*
- *Supabase Realtime to replace the 5-second polling in Dashboard.jsx*
- *GZipMiddleware on the FastAPI app*
- *Fixing the N+1 in the VAPI appointments view endpoint*
- *Pagination on GET /complaints and GET /tenants*
