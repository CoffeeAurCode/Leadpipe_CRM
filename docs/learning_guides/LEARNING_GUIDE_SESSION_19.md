# Learning Guide — Session 19: Debugging a Third-Party Library & Multi-User State

> **Prerequisite:** Session 18 (Code Splitting, Lazy Loading, Vite)
>
> **Goal:** By the end of this guide you will be able to:
> 1. Debug any third-party library by reading its compiled source — not just its docs
> 2. Understand how `react-joyride` v3 works, what changed from v2, and why controlled mode exists
> 3. Design a multi-page guided tour from scratch
> 4. Isolate user state in localStorage so two users on the same browser never collide
> 5. Apply a systematic debugging method that senior engineers use daily

---

## Table of Contents
1. [What We Built This Session](#1-what-we-built-this-session)
2. [The Core Skill: Reading Library Source Code](#2-the-core-skill-reading-library-source-code)
3. [How react-joyride Works](#3-how-react-joyride-works)
4. [Breaking Change: v2 → v3 API](#4-breaking-change-v2--v3-api)
5. [Controlled vs Uncontrolled Mode](#5-controlled-vs-uncontrolled-mode)
6. [Building the Multi-Page Tour Controller](#6-building-the-multi-page-tour-controller)
7. [The Nested Scroll Container Trap](#7-the-nested-scroll-container-trap)
8. [TARGET_NOT_FOUND and Retry Logic](#8-target_not_found-and-retry-logic)
9. [Multi-User localStorage Isolation](#9-multi-user-localstorage-isolation)
10. [The Debugging Process — Step by Step](#10-the-debugging-process--step-by-step)
11. [Errors We Hit and How We Diagnosed Them](#11-errors-we-hit-and-how-we-diagnosed-them)
12. [Commands Used to Diagnose](#12-commands-used-to-diagnose)
13. [Mental Models to Carry Forward](#13-mental-models-to-carry-forward)
14. [Resources](#14-resources)

---

## 1. What We Built This Session

The CRM now has a full guided walkthrough system:

```
Onboarding Checklist (hub page)
    ↓ user clicks "Start Full Tour"
react-joyride overlay appears
    → Step 1:  Sidebar navigation         (dashboard page)
    → Step 2:  KPI cards                  (dashboard page)
    → Step 3:  Trends chart               (dashboard page)
    → Step 4:  Category charts            (dashboard page)
    → Step 5:  View switcher              (properties page) ← auto-navigates
    → Step 6:  Property list              (properties page)
    → Step 7:  FAB buttons                (properties page)
    → Step 8:  Tenant filters             (tenants page)    ← auto-navigates
    → Step 9:  Tenant table               (tenants page)
    → Step 10: Quick filters              (complaints page) ← auto-navigates
    → Step 11: Complaint cards            (complaints page)
    → Step 12: Calendar header            (calendar page)   ← auto-navigates
    → Step 13: Calendar grid              (calendar page)
    → Step 14: SMS composer               (workflow page)   ← auto-navigates
    → Step 15: Recipient selector         (workflow page)
    ↓ tour finishes
Checklist marks all sections complete, navigates back to onboarding hub
```

Each section completion is persisted to:
- Browser `localStorage` (instant, scoped per user ID)
- Supabase `manager_profiles.tour_completed` (synced when 100% complete)

---

## 2. The Core Skill: Reading Library Source Code

This session's most important lesson is not about tours. It's about **how to debug when the library's documentation lies to you** — or more accurately, when the docs describe an older version.

### Why docs go stale

Library authors update code faster than they update docs. When a library releases a major version, the behaviour changes but blog posts, Stack Overflow answers, and even the README often still describe the old API.

In this session, every suggested fix was wrong because it was based on react-joyride **v2** documentation, but the project had react-joyride **v3** installed.

### The diagnostic command that cracked it

```bash
# 1. Check what version is actually installed
grep "react-joyride" frontend/package.json
# → "react-joyride": "^3.0.0"

# 2. Go look at the compiled source of that exact version
grep -n "callback\|onEvent" \
  frontend/node_modules/react-joyride/dist/index.cjs | head -20
```

Output:
```
1555:  const { debug, initialStepIndex, onEvent, run, stepIndex, steps } = mergedProps;
1570:  const emitEvent = useEventEmitter(onEvent, controls, store);
```

The string `"callback"` returned **zero results** from the entire dist file. Every blog post, every AI assistant, every Stack Overflow answer said to use `callback={...}`. The actual v3 source used `onEvent={...}`. The prop had been renamed in v3.

**Rule:** When a library prop silently does nothing, search the compiled dist for the prop name. If zero results → the prop does not exist in this version.

### How to read a compiled dist file

Compiled JS is minified and hard to read, but `grep` is your friend:

```bash
# Find all exported names
grep -n "exports\." node_modules/some-lib/dist/index.cjs | head -30

# Find where a prop is destructured (tells you the real prop names)
grep -n "const {" node_modules/some-lib/dist/index.cjs | head -20

# Find every event emitted
grep -n "emitEvent\|emit(" node_modules/some-lib/dist/index.cjs
```

The compiled source is the ground truth. Docs can be wrong. The compiled file cannot lie.

---

## 3. How react-joyride Works

### What it does

react-joyride puts a dark overlay over your entire page, cuts a "spotlight" hole around a specific DOM element, and floats a tooltip next to it. When the user clicks Next, it moves the spotlight to the next element.

### The three core pieces

```
┌─────────────────────────────────────────────────────┐
│  Your App                                           │
│  ┌─────────────────────────────────────────────┐   │
│  │  Dark overlay (rgba black)                  │   │
│  │        ┌──────────────────┐                │   │
│  │        │  SPOTLIGHT HOLE  │  ← [data-tour] │   │
│  │        │  (your element   │    element is   │   │
│  │        │   is visible)    │    highlighted  │   │
│  │        └──────────────────┘                │   │
│  │                                            │   │
│  │   ┌──────────────────────────┐             │   │
│  │   │  Tooltip (your custom    │             │   │
│  │   │  component or default)   │             │   │
│  │   │  [Back] [Skip] [Next →]  │             │   │
│  │   └──────────────────────────┘             │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### How Joyride finds elements

Every step has a `target` property — a CSS selector string:

```js
{
  target: '[data-tour="kpi-cards"]',
  title: 'Key Metrics',
  content: 'These cards show your most important numbers...',
}
```

When it is time to show this step, Joyride runs:
```js
document.querySelector('[data-tour="kpi-cards"]')
```

If found → calculates its bounding box → draws the spotlight there.
If not found → fires `TARGET_NOT_FOUND` event.

This means **your HTML elements need `data-tour` attributes** wherever you want spotlights:

```jsx
// In BentoDashboard.jsx
<div data-tour="kpi-cards" className="grid grid-cols-4 gap-4">
  <KPICard ... />
  <KPICard ... />
</div>
```

The attribute name is arbitrary — `data-tour` is just a convention. You could use `data-step` or `data-walkthrough`. The selector in the step definition must match.

---

## 4. Breaking Change: v2 → v3 API

This is the single most important fact in this session:

| What               | react-joyride v2       | react-joyride v3       |
|--------------------|------------------------|------------------------|
| Event callback prop | `callback={fn}`       | `onEvent={fn}`         |
| Event data shape   | `{ type, action, index, status }` | same + `error` field |
| Options prop       | `options={{ ... }}`   | direct props only      |
| Error events       | none                   | `EVENTS.ERROR` added   |
| Step after hook    | none                   | `EVENTS.STEP_AFTER_HOOK` added |

**Why this matters:** If you use `callback={handleCallback}`, react-joyride v3 silently ignores it. The library still works — the overlay shows, the spotlight renders, the user can click Next. But your callback is never called. This means:

- `setStepIndex` is never called → tour never advances (controlled mode)
- Checklist items are never marked complete
- Navigate-between-pages logic never fires

The symptom is: tour shows step 1, user clicks Next, nothing happens. Tour looks frozen.

**How to check your version quickly:**

```bash
cat frontend/package.json | grep react-joyride
# "react-joyride": "^3.0.0"

# Double-check what's actually installed (^ allows minor/patch upgrades)
cat frontend/node_modules/react-joyride/package.json | grep '"version"'
# "version": "3.0.0"
```

---

## 5. Controlled vs Uncontrolled Mode

This is a React pattern that appears constantly — not just in Joyride. Understanding it deeply will help you work with every third-party UI component.

### Uncontrolled mode (library owns state)

```jsx
// Library manages which step it's on internally
<Joyride
  steps={steps}
  run={true}
/>
```

The library tracks `currentStep` internally. You have no idea which step the user is on unless you listen to events. The library decides when to advance.

**Analogy:** An uncontrolled `<input>` in React — the DOM owns the value, you read it with `ref.current.value`.

### Controlled mode (you own state)

```jsx
// YOU manage which step the library shows
const [stepIndex, setStepIndex] = useState(0);

<Joyride
  steps={steps}
  run={run}
  stepIndex={stepIndex}     ← you hand the step down
  onEvent={handleCallback}  ← library tells you what happened
/>

function handleCallback({ type, index }) {
  if (type === EVENTS.STEP_AFTER) {
    setStepIndex(index + 1); // you decide to advance
  }
}
```

**Analogy:** A controlled `<input value={text} onChange={setField}>` — React owns the value.

### Why you NEED controlled mode for a multi-page tour

In this project the tour spans 6 different pages (dashboard, properties, tenants, complaints, calendar, workflow). When the user clicks Next on the last dashboard step, the app must:

1. Navigate to the Properties page (`onNavigate('properties')`)
2. Wait ~1200ms for the page to mount and render
3. THEN tell Joyride to advance to step 5

In uncontrolled mode, Joyride would immediately advance to step 5 before the Properties page exists in the DOM → `TARGET_NOT_FOUND`.

In controlled mode, you control the timing:
```js
// In handleCallback
setRun(false);               // pause Joyride
onNavigate('properties');    // trigger page change
setTimeout(() => {
  setStepIndex(nextIndex);   // now advance
  setRun(true);              // resume
}, 1200);                    // after DOM settles
```

---

## 6. Building the Multi-Page Tour Controller

The `OnboardingTour.jsx` component is the brain. Here is the architecture:

### Step definitions (onboardingTours.js)

```js
export const ALL_STEPS = [
  // Each step has a section field linking it to a page
  { target: '[data-tour="sidebar-nav"]', section: 'dashboard', ... },
  { target: '[data-tour="kpi-cards"]',   section: 'dashboard', ... },
  { target: '[data-tour="view-switcher"]', section: 'properties', ... },
  // ...
];

export const SECTION_VIEW = {
  dashboard:  'dashboard',
  properties: 'properties',
  // maps section name → view name used by onNavigate()
};

export const SECTION_CHECKLIST_IDS = {
  dashboard: ['dashboard-tour'],
  properties: ['properties-tour'],
  // maps section → checklist item IDs to mark complete
};
```

The `section` field on each step is how the controller knows "this step belongs to the dashboard page."

### The callback logic (the heart of the controller)

```js
const handleCallback = useCallback((data) => {
  const { action, index, status, type } = data;

  // ── 1. Tour finished or skipped globally ──
  if (status === STATUS.FINISHED || status === STATUS.SKIPPED) {
    setRun(false);
    markAllSectionsComplete();
    onNavigate('onboarding');
    return;
  }

  // ── 2. User clicked X to close ──
  if (action === ACTIONS.CLOSE) {
    setRun(false);
    markVisitedSectionsComplete(index);
    return;
  }

  // ── 3. Target element not found in DOM ──
  if (type === EVENTS.TARGET_NOT_FOUND) {
    retryCountRef.current += 1;
    if (retryCountRef.current <= 5) {
      // Retry same step after 800ms (element might still be loading)
      setRun(false);
      timerRef.current = setTimeout(() => setRun(true), 800);
      return;
    }
    // After 5 retries (~4 seconds), give up and advance
    retryCountRef.current = 0;
    // falls through to step advancement below
  }

  // ── 4. Normal step completion — advance ──
  if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
    retryCountRef.current = 0;
    const nextIndex = index + (action === ACTIONS.PREV ? -1 : 1);

    // End of tour reached
    if (nextIndex >= ALL_STEPS.length) {
      setRun(false);
      markAllSectionsComplete();
      onNavigate('onboarding');
      return;
    }

    const goingToNewPage = ALL_STEPS[nextIndex].section !== ALL_STEPS[index].section;

    if (goingToNewPage) {
      // Mark current section complete, navigate, then resume
      markComplete(SECTION_CHECKLIST_IDS[ALL_STEPS[index].section]);
      setRun(false);
      onNavigate(SECTION_VIEW[ALL_STEPS[nextIndex].section]);
      timerRef.current = setTimeout(() => {
        setStepIndex(nextIndex);
        setRun(true);
      }, 1200);
    } else {
      // Same page — just advance
      setStepIndex(nextIndex);
    }
  }
}, [markComplete, onNavigate]);
```

### The bug this logic fixed: the end-of-array trap

Before this fix, the code had:
```js
if (nextIndex >= ALL_STEPS.length) return; // ← just returned!
```

On the last step, clicking Next calculated `nextIndex = 15` (out of 15 steps). The check fired and returned immediately — without ever calling `setRun(false)`. The dark overlay stayed permanently. The tour was technically still "running" but had no more steps to render, so no tooltip appeared. The user saw a frozen dark screen with no way to escape except refreshing.

**The fix:** Replace the bare `return` with proper cleanup:
```js
if (nextIndex >= ALL_STEPS.length) {
  setRun(false);          // kill the overlay
  markAllComplete();      // check off all items
  onNavigate('onboarding');
  return;
}
```

**Lesson:** Any time you have a boundary check that exits early, ask yourself: "Is the system left in a clean state?" If you were running something, stop it. Never leave a loading spinner or an overlay active when you bail out.

---

## 7. The Nested Scroll Container Trap

### The layout structure

```
<div class="flex h-screen overflow-hidden">     ← OUTER: fixed viewport, no scroll
  <Sidebar />
  <div class="flex-1 flex flex-col overflow-hidden">
    <TopBar />
    <motion.div class="flex-1 overflow-y-auto"> ← INNER: this one scrolls
      {/* page content */}
    </motion.div>
  </div>
</div>
```

The page has two containers. The outer is `overflow-hidden` (nothing scrolls on the root). The inner is `overflow-y-auto` (this is the actual scrollable area).

### Why this breaks Joyride's auto-scroll

Joyride's built-in scroll tries to do:
```js
window.scrollTo({ top: elementY, behavior: 'smooth' });
// or
document.documentElement.scrollTop = elementY;
```

But `document.documentElement.scrollTop` is always 0 — the page root does not scroll. The inner div scrolls. Joyride has no way to know which div is the real scrollable container. So it attempts to scroll the wrong element, silently fails, and positions the spotlight where the element would be if it were on screen — which is off the bottom edge of the monitor.

### The fix: move the target to always-visible elements

The `sms-recipients` step originally targeted a massive table div at the very bottom of the SMS Workflow page — always off-screen on first load. The fix was to move `data-tour="sms-recipients"` from the table wrapper to its toolbar div (the search bar + filter row), which is always in the visible viewport:

```jsx
// BEFORE — targets the full table (off-screen)
<div data-tour="sms-recipients" className="bg-card ...">
  <div className="flex items-center justify-between ...">  ← toolbar
    ...search, filter...
  </div>
  <table>...</table>
</div>

// AFTER — targets just the toolbar (always visible)
<div className="bg-card ...">
  <div data-tour="sms-recipients"                         ← moved here
       className="flex items-center justify-between ...">
    ...search, filter...
  </div>
  <table>...</table>
</div>
```

**General rule:** When you have a nested scroll container layout (`overflow-hidden` outer + `overflow-y-auto` inner), always place tour targets on elements that are guaranteed to be visible without scrolling. Joyride cannot reliably scroll your inner container.

---

## 8. TARGET_NOT_FOUND and Retry Logic

### When does TARGET_NOT_FOUND fire?

Joyride runs `document.querySelector(step.target)` when it is time to render a step. If the element is not in the DOM at that exact millisecond, it fires `TARGET_NOT_FOUND`.

Common causes:
1. **Page still loading** — lazy-loaded component (via `React.lazy`) hasn't finished downloading
2. **Data gate** — component only renders when data arrives (`loading && data.length === 0 ? <Spinner> : <RealContent>`)
3. **Animation mid-flight** — framer-motion element is between states
4. **Wrong page** — accidentally navigated away before Joyride queried the DOM

### The original (broken) behavior

```js
// Old code treated TARGET_NOT_FOUND exactly like STEP_AFTER
if (type === EVENTS.STEP_AFTER || type === EVENTS.TARGET_NOT_FOUND) {
  setStepIndex(index + 1); // ← skip immediately
}
```

If `kpi-cards` wasn't found yet (data still loading), it would advance to `trends-charts`. If that wasn't found either, it advanced to `category-charts`. All four dashboard steps skipped in milliseconds — a "cascade."

### The fixed behavior: retry with a limit

```js
if (type === EVENTS.TARGET_NOT_FOUND) {
  retryCountRef.current += 1;

  if (retryCountRef.current <= 5) {
    // Pause, give the DOM time to settle, then try again
    setRun(false);
    timerRef.current = setTimeout(() => setRun(true), 800);
    return;
  }

  // After 5 attempts (~4 seconds total), give up and advance
  retryCountRef.current = 0;
  // falls through to advance logic
}
```

**Why a limit?** Without the limit of 5, if an element genuinely does not exist (broken import, wrong `data-tour` spelling), the tour loops forever — overlay flickering on and off, never progressing.

**Why `retryCountRef` instead of state?**
```js
const retryCountRef = useRef(0);
```
State updates cause re-renders. A re-render while Joyride is mid-lifecycle can confuse it. A ref (`useRef`) stores a mutable value that does not trigger re-renders — perfect for a counter used inside a callback.

**Why `setRun(false)` → delay → `setRun(true)` instead of just waiting?**
In react-joyride controlled mode, you cannot tell Joyride "re-query the DOM for the same step." The only way to force it to re-query is to briefly stop and restart. Setting `run=false` resets Joyride's lifecycle, and `run=true` restarts it at whatever `stepIndex` currently is.

---

## 9. Multi-User localStorage Isolation

### The bug

`localStorage` in a browser is shared across all users who use the same physical browser. When user A completed the tour, the app saved:

```
localStorage["crm-onboarding-checklist"] = '{"dashboard-tour":true,"properties-tour":true,...}'
```

When user B logged in on the same machine, the app read `localStorage["crm-onboarding-checklist"]` and found all 15 items complete — immediately skipping the checklist and silently marking user B's Supabase profile as `tour_completed: true`.

### Why this is a classic mistake

`localStorage` is scoped to the **origin** (domain + port), not the **user**. Every user who opens your app on the same browser shares the same `localStorage` namespace. This is fine for truly global settings (theme, language) but is wrong for per-user data (progress, preferences, drafts).

### The fix: user-scoped keys

```js
// BEFORE — shared key
const STORAGE_KEY = 'crm-onboarding-checklist';
localStorage.setItem(STORAGE_KEY, JSON.stringify(checked));

// AFTER — keyed by user ID
const getStorageKey = (userId) => `crm-onboarding-checklist-${userId}`;
localStorage.setItem(getStorageKey(user.id), JSON.stringify(checked));
```

Now user A's data lives at `crm-onboarding-checklist-abc123` and user B's lives at `crm-onboarding-checklist-def456`. They never collide.

### The guard for missing user ID

```js
function loadChecked(userId) {
  if (!userId) return {};   // ← guard: no user = no data
  const raw = localStorage.getItem(getStorageKey(userId));
  return raw ? JSON.parse(raw) : {};
}
```

If somehow `user` is null (auth still loading), the function returns an empty object instead of crashing or reading the wrong key.

### Same fix applied in App.jsx

The `currentView` initializer also read localStorage to decide whether to skip to the dashboard:

```js
// BEFORE (in App.jsx)
const checked = localStorage.getItem('crm-onboarding-checklist');

// AFTER — guarded + scoped
if (!user) return 'onboarding';
const checked = localStorage.getItem(`crm-onboarding-checklist-${user.id}`);
```

Without `if (!user) return 'onboarding'`, the initializer would try to read a key with `undefined` in it (`crm-onboarding-checklist-undefined`), never find data, and always default to the onboarding page — a subtler bug.

---

## 10. The Debugging Process — Step by Step

Here is the exact methodology used to crack each bug in this session:

### Step 1: Reproduce the symptom precisely

Don't say "it doesn't work." Say exactly:
- "After clicking Next on step 1, the tooltip disappears and the overlay stays dark permanently"
- "After clicking Next on step 1, nothing happens at all — overlay stays, tooltip stays, no movement"

These two descriptions point to completely different root causes.

### Step 2: Ask "whose code is running and whose isn't?"

For the frozen tour, the question was: "Is Joyride advancing internally and our code not responding, or is nothing advancing at all?"

To test this, add a `console.log` in the callback:
```js
const handleCallback = useCallback((data) => {
  console.log('[Tour callback]', data.type, data.index, data.action);
  // ...
```

If the log never fires after clicking Next → the callback is not connected.
If the log fires but `setStepIndex` is not called → there's a logic bug.
If the log fires and `setStepIndex` is called but Joyride doesn't advance → controlled mode issue.

In this session: no log fired. Callback was not connected. Prop name was wrong.

### Step 3: Verify the prop name exists in the installed version

```bash
# Version check
grep "react-joyride" frontend/package.json
cat frontend/node_modules/react-joyride/package.json | grep '"version"'

# Prop existence check
grep -n "callback" frontend/node_modules/react-joyride/dist/index.cjs | head -5
# → zero results = prop does not exist
grep -n "onEvent" frontend/node_modules/react-joyride/dist/index.cjs | head -5
# → results found = correct prop name
```

### Step 4: Fix one thing at a time

Every broken system has multiple problems. Fix them in order from most fundamental to least:

1. First: Is the callback connected at all? (→ `onEvent` fix)
2. Then: Does the end-of-array case crash? (→ boundary fix)
3. Then: Does TARGET_NOT_FOUND cause cascade skipping? (→ retry logic)
4. Then: Is the final step spotlight off-screen? (→ move `data-tour` attribute)
5. Then: Do users share localStorage? (→ key scoping fix)

If you try to fix all five at once, you cannot tell which fix resolved which symptom.

### Step 5: Test the fix against the original symptom

After each fix, reproduce the original test case. Don't just assume it works.

---

## 11. Errors We Hit and How We Diagnosed Them

### Error 1: Tour appears then immediately shows dark frozen screen

**Symptom:** Tour shows step 1 tooltip. User clicks Next. Overlay stays dark. No tooltip for step 2. App is unresponsive.

**Wrong diagnoses considered:**
- framer-motion causing 0px dimensions on KPI cards *(incorrect — wrapper div has no animation)*
- React 18 batching causing race condition *(incorrect — kpi-cards is always in DOM when BentoDashboard renders)*
- React Strict Mode double-firing callbacks *(incorrect — Strict Mode doubles effects, not event handler invocations)*

**Actual root cause:** `callback` prop does not exist in react-joyride v3. Event handler was never called. `setStepIndex` was never updated. Tour stuck at step 0 in controlled mode.

**Diagnosed by:**
```bash
grep -n '"callback"\|callback:' \
  frontend/node_modules/react-joyride/dist/index.cjs
# → zero results
```

**Fixed by:** Renaming prop from `callback={handleCallback}` to `onEvent={handleCallback}`

---

### Error 2: Tour jumps directly to SMS Workflow, skipping everything else

**Symptom:** Start tour from checklist. Step 1 (sidebar) appears. Click Next. Tour jumps to step 14 (SMS composer), skipping Properties, Tenants, Complaints, Calendar entirely.

**Root cause:** `TARGET_NOT_FOUND` was handled identically to `STEP_AFTER` — it advanced the step index. With framer-motion animations still mid-flight when the tour tried to render step 2, `TARGET_NOT_FOUND` fired for kpi-cards, then trends-charts, then category-charts, cascading forward until reaching the SMS page.

**Fixed by:** Separating `TARGET_NOT_FOUND` handling — retry the same step up to 5 times instead of advancing.

---

### Error 3: Last step leaves permanent dark overlay

**Symptom:** Complete all 15 steps. After the final "Next" click, tooltip disappears but dark overlay stays forever. Must refresh to escape. Checklist never marks SMS Workflow complete.

**Root cause:**
```js
// When nextIndex = 15 (one past the last step at index 14):
if (nextIndex >= ALL_STEPS.length) return; // ← returned without setRun(false)
```

`run` was still `true`. Joyride was technically still running with no more steps to render. The overlay (rendered by Joyride) stayed visible. No tooltip appeared because there was no step to render.

**Fixed by:**
```js
if (nextIndex >= ALL_STEPS.length) {
  setRun(false);
  markAllComplete();
  onNavigate('onboarding');
  return;
}
```

---

### Error 4: New manager sees completed checklist on first login

**Symptom:** Create a new manager account on the same browser that another manager used. New manager lands directly on the Dashboard, with all 15 checklist items pre-checked.

**Root cause:** Both managers shared the same `localStorage` key (`crm-onboarding-checklist`). The new manager's session read the old manager's completion data. The context then synced this false completion to Supabase, permanently corrupting the new manager's profile.

**Fixed by:** Scoping localStorage key to user ID: `crm-onboarding-checklist-${user.id}`

---

### Error 5: SMS Workflow step shows dark screen with spotlight off-screen

**Symptom:** Tour reaches step 15 (SMS recipients). Dark overlay appears. No tooltip visible anywhere. User cannot interact. Refreshing to escape means step 15 is never marked complete.

**Root cause:** The nested scroll layout (`overflow-hidden` outer + `overflow-y-auto` inner). The `data-tour="sms-recipients"` attribute was on a table div at the very bottom of the page. Joyride calculated the table's position correctly but couldn't scroll the inner container to bring it into view. Spotlight was drawn ~2000px below the visible area.

**Diagnosed by:** Understanding that `window.scrollY` is always 0 in this layout. The scroll position lives on an inner div, not the document root.

**Fixed by:** Moving `data-tour="sms-recipients"` from the table wrapper to the toolbar div (search bar + filters), which is always in the visible viewport.

---

## 12. Commands Used to Diagnose

```bash
# Check installed library version
grep "react-joyride" frontend/package.json
cat frontend/node_modules/react-joyride/package.json | grep '"version"'

# Check if a prop name exists in the installed dist
grep -n "callback" frontend/node_modules/react-joyride/dist/index.cjs | head -10

# Find which prop react-joyride v3 actually uses for events
grep -n "onEvent" frontend/node_modules/react-joyride/dist/index.cjs | head -10

# Find all exported constants (STATUS, EVENTS, ACTIONS values)
grep -n "STEP_AFTER\|TARGET_NOT_FOUND\|FINISHED" \
  frontend/node_modules/react-joyride/dist/index.cjs | head -20

# Find where a prop is destructured (confirms the real prop names)
grep -n "mergedProps\|const {" \
  frontend/node_modules/react-joyride/dist/index.cjs | grep "onEvent\|run\|stepIndex"

# Confirm localStorage key naming in context
grep -rn "crm-onboarding" frontend/src/

# Find all data-tour attributes across the codebase
grep -rn 'data-tour=' frontend/src/components/

# Find all step targets in tour config
grep -n "target:" frontend/src/config/onboardingTours.js
```

---

## 13. Mental Models to Carry Forward

### "The installed version is the truth"

npm's semver ranges (`^3.0.0`) mean "3.0.0 or higher minor/patch." What's actually in `node_modules` may differ from what you specified. Always verify with `cat node_modules/library/package.json | grep version`. Then read the dist, not the docs.

### "When a prop silently does nothing, grep the dist"

If you pass a prop and the component seems to ignore it completely, there are three possibilities:
1. The prop name changed (version mismatch — most common)
2. The prop is ignored under certain conditions
3. There's a JS error earlier that prevents that code path from running

Grep the dist for the prop name. Zero results = renamed or removed.

### "State in a callback needs useRef, not useState"

Anything you want to track inside an event callback that should NOT cause re-renders belongs in a `useRef`:

```js
const retryCountRef = useRef(0);   // ← won't cause re-renders when updated
const [retryCount, setRetryCount] = useState(0); // ← every increment re-renders
```

Re-renders during Joyride's lifecycle can confuse its positioning engine. Keep callback-internal counters in refs.

### "Every early return must leave the system in a clean state"

If a function sets state X to `true` and then an early return fires before setting it back to `false`, X is permanently `true`. Always audit every `return` path:
- Is `run` still `true` when it should be `false`?
- Is a timer still pending that will fire unexpectedly?
- Is a loading state stuck?

### "localStorage is per-origin, not per-user"

Use user-scoped keys for any data that differs between users. Use unscoped keys only for device-wide preferences (theme, language, zoom level).

```
Good unscoped keys:   'theme', 'locale', 'sidebar-collapsed'
Bad unscoped keys:    'onboarding-progress', 'draft-message', 'last-viewed-tenant'
```

### "Move tour targets to always-visible elements"

In apps with inner scroll containers (`overflow-y-auto` divs), Joyride cannot reliably scroll to off-screen elements. Always attach `data-tour` to elements that are visible when the page first loads — the header, the toolbar, the first visible card. Not the bottom of a long list.

---

## 14. Resources

### react-joyride v3
- **Official docs (v3):** https://docs.react-joyride.com
  *(always check the version selector in the top-right — make sure it matches your installed version)*
- **Migration guide v2 → v3:** https://github.com/gilbarbara/react-joyride/blob/main/CHANGELOG.md
- **Controlled mode example:** https://docs.react-joyride.com/controlled

### React patterns used
- **useRef vs useState:** https://react.dev/reference/react/useRef#storing-information-between-re-renders
- **Controlled vs uncontrolled components:** https://react.dev/learn/sharing-state-between-components#controlled-and-uncontrolled-components
- **useCallback:** https://react.dev/reference/react/useCallback

### localStorage
- **MDN Web Storage API:** https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API
- **Storage scope (origin-level):** https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage#description

### Debugging tools
- **Chrome DevTools Application tab** → Storage → Local Storage: inspect/edit/delete localStorage keys in real time
- **Chrome DevTools Console:** `localStorage.getItem('crm-onboarding-checklist-YOUR_USER_ID')` to inspect values
- **Chrome DevTools Console:** `localStorage.clear()` to wipe all keys and test fresh-user experience

### Reading compiled JS
- **Understanding minified output:** https://developer.chrome.com/docs/devtools/javascript/source-maps
- **ripgrep (fast grep for codebases):** https://github.com/BurntSushi/ripgrep — the tool used for all `grep -n` commands above

---

## Quick Reference Card

```
react-joyride v3 cheatsheet
────────────────────────────────────────────────
Correct event prop:     onEvent={handleCallback}   ← NOT callback
Controlled mode props:  run={bool} stepIndex={num}
Step advance:           setStepIndex(index + 1) inside onEvent handler
Pause tour:             setRun(false)
Resume tour:            setRun(true)
Target attribute:       data-tour="my-element"
Step config:            { target: '[data-tour="my-element"]', section: 'page' }

Events to handle
────────────────────────────────────────────────
EVENTS.STEP_AFTER       user clicked Next/Back   → advance stepIndex
EVENTS.TARGET_NOT_FOUND element not in DOM       → retry or skip
EVENTS.ERROR            internal error           → retry or skip
STATUS.FINISHED         tour completed           → setRun(false), cleanup
STATUS.SKIPPED          user skipped tour        → setRun(false), partial cleanup
ACTIONS.CLOSE           user clicked X           → setRun(false), partial cleanup

localStorage key rule
────────────────────────────────────────────────
Per-user data:    `my-key-${user.id}`
Device-wide data: `my-key`

Nested scroll layout rule
────────────────────────────────────────────────
If layout has overflow-hidden outer + overflow-y-auto inner:
  → data-tour must target always-visible elements (headers, toolbars)
  → Never target elements below the fold
```
