Goal: I want to LEARN to build this from scratch without AI assistance.
Build the full project AND produce structured learning material as SELF-CONTAINED
HTML FILES that teach me every concept, every line of code, every design decision,
and every tool used — so I can recreate it myself.

The learning material must be in HTML format (not markdown, i have made some md file learning material(in here C:\Users\BIT\Coding\Tenant_management_MVP\docs\learning_guides)) so I can open each
module directly in a browser with beautiful formatting, syntax highlighting,
navigation, and interactivity — no build tools or servers required.
PHASE 1 — PLAN (do this first, stop and wait for my approval)

MODULE BREAKDOWN
   Split the project into multiple self-contained modules. For each module:
   - Module number and name
   - Which source files it covers
   - What the learner will be able to do after completing it
   - What concepts it teaches
   Keep modules detailed enough that a learner on completing knows everything to make the project from scratch.
FINAL FILE STRUCTURE
   Full directory tree with a one-line comment on every file.
KEY DESIGN DECISIONS TABLE
   | Decision | Why | What you would do differently without this constraint |
   Include at least: data flow between components, error handling strategy,
   configuration approach, and extensibility points.
OPEN QUESTIONS FOR THE USER
   List any choices the user should make before building starts
   (UI type, external services, target OS, etc.)

After writing PLAN.md, stop. Do not write any code yet.
Ask me: "Review PLAN.md and reply 'approved' when ready to build."
PHASE 2 — BUILD (only after I say "approved")
Learning material folder: learning_material/
  ┌──────────────────────────────────────────────────────────────────────────┐
  │  ALL LEARNING MODULES MUST BE SELF-CONTAINED HTML FILES                │
  │  Each file works by simply opening it in any modern browser.           │
  │  No build step. No server. No external CSS/JS CDN required.           │
  │  Everything is embedded inline.                                        │
  └──────────────────────────────────────────────────────────────────────────┘

  Create one HTML file per module: module_00_name.html, module_01_name.html, …
  Also create an index.html that serves as the learning hub / dashboard.

  ──────────────────────────────────────────────────────────────────────────
  HTML DESIGN SPECIFICATION FOR EVERY MODULE FILE
  ──────────────────────────────────────────────────────────────────────────

  Each HTML file must include these embedded features (all CSS and JS inline):

  VISUAL DESIGN:
    - Clean, modern design with a professional color palette
    - Dark mode / light mode toggle (persisted in localStorage)
    - Responsive layout that works on desktop, tablet, and mobile
    - Maximum content width of 800px, centered, with comfortable padding
    - Professional typography using system font stack:
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                     'Helvetica Neue', Arial, sans-serif;
    - Monospace font for code:
        font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas,
                     'Courier New', monospace;

  CODE BLOCKS:
    - Syntax highlighting using embedded CSS classes (no external library needed)
    - At minimum, highlight: keywords, strings, comments, functions, numbers
    - Use a color scheme inspired by VS Code / One Dark (for dark mode)
      and GitHub (for light mode)
    - "Copy" button on every code block that copies to clipboard
    - Language label in the top-right corner of each code block
    - Line numbers on code blocks longer than 5 lines
    - Distinct visual styling for inline code vs block code

  NAVIGATION:
    - Fixed sidebar (collapsible on mobile) with table of contents
      generated from all <h2> headings in the page
    - "Previous Module" / "Next Module" navigation buttons at top and bottom
    - Breadcrumb trail: Home > Module 3 > Section Name
    - Smooth scroll-to-section when clicking TOC links
    - Active section highlighting in sidebar as user scrolls
    - "Back to top" floating button

  INTERACTIVITY:
    - Collapsible/expandable sections for "Concept Deep-Dives" and "Exercises"
      (click to expand, default collapsed for exercises, expanded for content)
    - Checkbox-based progress tracking for each section
      (persisted in localStorage per module)
    - Progress bar at the top showing % of sections completed
    - Estimated reading time displayed at the top

  PRINT SUPPORT:
    - @media print stylesheet that:
      * Removes navigation, toggles, and interactive elements
      * Uses black text on white background
      * Expands all collapsed sections
      * Adds page break hints before <h2> elements

  ──────────────────────────────────────────────────────────────────────────
  CONTENT SPECIFICATION FOR EVERY MODULE HTML FILE
  ──────────────────────────────────────────────────────────────────────────

  Each module file MUST contain ALL of these sections (as HTML content):

  HEADER AREA:
    - Module number and title (e.g. "Module 03 — Tool Registry")
    - Estimated time to complete
    - List of source files this module covers (as links if viewing locally)
    - Prerequisites: which modules must be completed first
    - Progress bar (auto-calculated from section checkboxes)

  SECTION 1: What You Are Building
    One paragraph. What does this module produce and why does it matter
    in the overall project? Include a simple diagram or visual if helpful
    (use ASCII art or inline SVG).

  SECTION 2: Concept Deep-Dives (collapsible sub-sections)
    For every non-trivial concept used in this module:
      - Name the concept and give a one-sentence definition
      - Show a MINIMAL standalone code example (NOT from the project)
        that demonstrates the concept in isolation
      - Show how the project uses this concept (quote the actual project code)
      - Explain what would break if this concept were removed or done naively
      - "Try it yourself" — a tiny hands-on exercise for just this concept
    Do not assume knowledge. Explain decorators, async, closures, generics,
    middleware, hooks, etc. from first principles if the project uses them.

  SECTION 3: Reading the Source File(s) — Line-by-Line Walkthrough
    Walk through the ACTUAL source file(s) for this module, section by section.
    For each logical section of the code:
      - Quote the exact code in a syntax-highlighted block
      - Below the code block, explain EVERY non-obvious line:
        * What it does
        * Why it's written this way (not just what)
        * What would happen if you changed or removed it
      - Highlight design patterns used and name them
        (e.g. "This is the Strategy pattern — here's why it's used here")
      - Call out any "magic" — configuration values, special syntax,
        framework conventions that wouldn't be obvious to a newcomer
    The walkthrough must cover 100% of the source code — no lines skipped.

  SECTION 4: Why This Design (Alternatives & Trade-offs)
    For each major design decision in this module:
      - What the decision was
      - What alternatives were considered (list at least 2)
      - A comparison table: | Approach | Pros | Cons |
      - When you would make a different choice
      - What would need to change in the code to switch approaches

  SECTION 5: How It Connects (Data Flow)
    - Show how this module connects to modules before and after it
    - What data flows IN to this module (type, shape, source)
    - What data flows OUT of this module (type, shape, destination)
    - Use an ASCII or inline SVG diagram showing the flow

  SECTION 6: Running & Testing
    - Exact shell command to run just this module's code in isolation
    - Exact command to run just this module's tests
    - Expected output (show what success looks like)
    - Explain what each test is checking and why that test matters
    - Common failure modes and how to debug them

  SECTION 7: Checkpoint ✓
    One small runnable snippet (REPL session, shell command, or browser action)
    that proves this module works correctly in isolation.
    Include the expected output. Should take < 30 seconds to run.
    Style this as a highlighted "success" card in the HTML.

  SECTION 8: Exercises (3 minimum, in collapsible cards)
    Three exercises, ordered easy → hard, each in its own expandable card:
      1. EASY — A modification that requires understanding ONE concept from this module
      2. MEDIUM — A small extension that adds new behaviour
      3. HARD — A challenge that requires combining TWO or more concepts
    Each exercise must include:
      - Clear problem statement
      - Hints (in a collapsible sub-section)
      - Success condition ("you know you got it right when ___")
      - Solution (in a deeply nested collapsible section — hidden by default)

  SECTION 9: Glossary
    A styled table of every technical term introduced in this module:
    | Term | Definition | First used in |

  SECTION 10: Resources
    For EVERY library, tool, or concept used in this module, list:
      - Official documentation link (as a clickable <a> tag)
      - Best practical tutorial / guide (not the official docs)
      - If it is a CS concept: a plain-English explanation link
    Minimum 5 resources per module. Style as a card grid.

  SECTION 11: What's Next
    One sentence linking to the next module file. Preview what they'll learn.
    Include a "Mark Module Complete" button that updates localStorage and
    the progress on the index page.

  ──────────────────────────────────────────────────────────────────────────
  INDEX.HTML — LEARNING HUB / DASHBOARD
  ──────────────────────────────────────────────────────────────────────────

  Create a learning_material/index.html that serves as the main entry point:

  DESIGN:
    - Professional dashboard layout with the same dark/light mode toggle
    - Project title and one-paragraph description at the top
    - Overall progress bar (reads module completion from localStorage)

  CONTENT:
    - Architecture diagram (ASCII or inline SVG) showing all components
    - Module cards in a grid layout, each showing:
        * Module number and name
        * Estimated time
        * Key concepts taught (as tags/badges)
        * Completion status (checkbox + visual indicator)
        * Link to the module HTML file
    - Technology stack section with logos/icons for each technology
    - Prerequisites checklist with links to download/sign up
    - "Quick Start" section: numbered steps to get the project running
    - File map table: | File | Module # | What it contains |
    - End-to-end walkthrough: a concrete example showing the full system
      working from input to output (use the sample files in examples/)
    - "How to Extend" section with 5+ extension ideas, each as a card:
        * What it adds
        * Difficulty level (tag)
        * Which files to change
        * New concepts to learn (with resource links)
    - Troubleshooting table:
        | Symptom | Most likely cause | Fix |
        At least 8 rows covering common failure modes
    - Learning roadmap: 3 follow-on projects ordered by difficulty
    - "Before You Start" resources table:
        | Technology | What to learn | Resource link | Time needed |

STEP D — Master worksheet: WORKSHEET.md
  Still create a WORKSHEET.md as a quick-reference text file that contains:
    1. Project summary (3–5 sentences)
    2. Link to learning_material/index.html as the main learning entry point
    3. Complete file map table
    4. Quick setup instructions
    5. All environment variables documented
  This file exists for quick reference in a code editor — the real learning
  content lives in the HTML files.

────────────────────────────────────────────────────────────────────────────────
HTML TEMPLATE REFERENCE
────────────────────────────────────────────────────────────────────────────────

Here is the skeleton structure every module HTML file should follow.
Adapt and expand this — do not use it as-is with empty sections.

<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Module XX — Module Name | Project Name</title>
  <style>
    /* ── CSS Reset ── */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    /* ── CSS Custom Properties (Theme Tokens) ── */
    :root {
      --bg-primary: #1a1b26;
      --bg-secondary: #24283b;
      --bg-tertiary: #2f3348;
      --text-primary: #c0caf5;
      --text-secondary: #a9b1d6;
      --text-muted: #565f89;
      --accent: #7aa2f7;
      --accent-hover: #89b4fa;
      --success: #9ece6a;
      --warning: #e0af68;
      --error: #f7768e;
      --border: #3b4261;
      --code-bg: #1e2030;
      --shadow: 0 4px 6px rgba(0,0,0,0.3);
      --radius: 8px;
      --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      --font-mono: 'SF Mono', 'Fira Code', 'Cascadia Code', Consolas, monospace;
    }

    [data-theme="light"] {
      --bg-primary: #ffffff;
      --bg-secondary: #f6f8fa;
      --bg-tertiary: #e8ecf1;
      --text-primary: #24292f;
      --text-secondary: #57606a;
      --text-muted: #8b949e;
      --accent: #0969da;
      --accent-hover: #0550ae;
      --success: #1a7f37;
      --warning: #9a6700;
      --error: #cf222e;
      --border: #d0d7de;
      --code-bg: #f6f8fa;
      --shadow: 0 4px 6px rgba(0,0,0,0.08);
    }

    /* ── Base Styles ── */
    body {
      font-family: var(--font-sans);
      background: var(--bg-primary);
      color: var(--text-primary);
      line-height: 1.7;
      transition: background 0.3s, color 0.3s;
    }

    /* ── Layout ── */
    .container { max-width: 860px; margin: 0 auto; padding: 2rem; }

    /* ── Sidebar ── */
    .sidebar {
      position: fixed; top: 0; left: 0; width: 280px; height: 100vh;
      background: var(--bg-secondary); border-right: 1px solid var(--border);
      overflow-y: auto; padding: 1.5rem; z-index: 100;
      transform: translateX(0); transition: transform 0.3s;
    }
    .sidebar.collapsed { transform: translateX(-100%); }
    .sidebar a { color: var(--text-secondary); text-decoration: none; display: block;
                 padding: 0.3rem 0; font-size: 0.9rem; }
    .sidebar a:hover, .sidebar a.active { color: var(--accent); }
    .main-content { margin-left: 280px; }

    @media (max-width: 768px) {
      .sidebar { transform: translateX(-100%); }
      .sidebar.open { transform: translateX(0); }
      .main-content { margin-left: 0; }
    }

    /* ── Typography ── */
    h1 { font-size: 2rem; margin-bottom: 0.5rem; color: var(--accent); }
    h2 { font-size: 1.5rem; margin: 2rem 0 1rem; padding-top: 1rem;
         border-top: 1px solid var(--border); }
    h3 { font-size: 1.2rem; margin: 1.5rem 0 0.75rem; }
    p { margin-bottom: 1rem; }
    a { color: var(--accent); }

    /* ── Code Blocks ── */
    pre {
      background: var(--code-bg); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 1rem; overflow-x: auto;
      position: relative; margin: 1rem 0;
    }
    code { font-family: var(--font-mono); font-size: 0.9rem; }
    pre code { display: block; line-height: 1.6; }
    :not(pre) > code {
      background: var(--code-bg); padding: 0.15rem 0.4rem;
      border-radius: 4px; font-size: 0.85em;
    }

    /* Syntax highlighting classes */
    .kw { color: #bb9af7; }     /* keyword */
    .str { color: #9ece6a; }    /* string */
    .cm { color: #565f89; font-style: italic; }  /* comment */
    .fn { color: #7aa2f7; }     /* function */
    .num { color: #ff9e64; }    /* number */
    .op { color: #89ddff; }     /* operator */
    .dec { color: #e0af68; }    /* decorator / annotation */
    .typ { color: #2ac3de; }    /* type */

    [data-theme="light"] .kw { color: #cf222e; }
    [data-theme="light"] .str { color: #0a3069; }
    [data-theme="light"] .cm { color: #8b949e; }
    [data-theme="light"] .fn { color: #8250df; }
    [data-theme="light"] .num { color: #0550ae; }
    [data-theme="light"] .dec { color: #953800; }
    [data-theme="light"] .typ { color: #0550ae; }

    /* Copy button */
    .copy-btn {
      position: absolute; top: 0.5rem; right: 0.5rem;
      background: var(--bg-tertiary); border: 1px solid var(--border);
      color: var(--text-muted); padding: 0.25rem 0.5rem; border-radius: 4px;
      cursor: pointer; font-size: 0.75rem;
    }
    .copy-btn:hover { color: var(--accent); border-color: var(--accent); }

    /* Language label */
    .lang-label {
      position: absolute; top: 0.5rem; right: 4rem;
      color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase;
    }

    /* ── Collapsible Sections ── */
    details {
      background: var(--bg-secondary); border: 1px solid var(--border);
      border-radius: var(--radius); margin: 1rem 0; padding: 1rem;
    }
    summary {
      cursor: pointer; font-weight: 600; color: var(--accent);
      padding: 0.25rem 0; user-select: none;
    }
    details[open] summary { margin-bottom: 0.75rem; }

    /* ── Cards ── */
    .card {
      background: var(--bg-secondary); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 1.25rem; margin: 1rem 0;
      box-shadow: var(--shadow);
    }
    .card-success { border-left: 4px solid var(--success); }
    .card-warning { border-left: 4px solid var(--warning); }
    .card-info { border-left: 4px solid var(--accent); }

    /* ── Progress Bar ── */
    .progress-bar {
      width: 100%; height: 8px; background: var(--bg-tertiary);
      border-radius: 4px; overflow: hidden; margin: 0.5rem 0;
    }
    .progress-fill {
      height: 100%; background: linear-gradient(90deg, var(--accent), var(--success));
      border-radius: 4px; transition: width 0.5s;
    }

    /* ── Tables ── */
    table {
      width: 100%; border-collapse: collapse; margin: 1rem 0;
      font-size: 0.9rem;
    }
    th, td {
      text-align: left; padding: 0.75rem; border: 1px solid var(--border);
    }
    th { background: var(--bg-tertiary); font-weight: 600; }
    tr:nth-child(even) { background: var(--bg-secondary); }

    /* ── Badges / Tags ── */
    .badge {
      display: inline-block; padding: 0.15rem 0.5rem; border-radius: 12px;
      font-size: 0.75rem; font-weight: 600; margin: 0.15rem;
    }
    .badge-easy { background: #9ece6a22; color: var(--success); border: 1px solid var(--success); }
    .badge-medium { background: #e0af6822; color: var(--warning); border: 1px solid var(--warning); }
    .badge-hard { background: #f7768e22; color: var(--error); border: 1px solid var(--error); }

    /* ── Navigation ── */
    .nav-buttons {
      display: flex; justify-content: space-between; margin: 2rem 0;
      gap: 1rem; flex-wrap: wrap;
    }
    .nav-btn {
      display: inline-block; padding: 0.75rem 1.5rem;
      background: var(--bg-secondary); border: 1px solid var(--border);
      border-radius: var(--radius); color: var(--accent);
      text-decoration: none; font-weight: 500;
      transition: all 0.2s;
    }
    .nav-btn:hover { background: var(--accent); color: var(--bg-primary); }

    /* ── Breadcrumbs ── */
    .breadcrumbs {
      font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1rem;
    }
    .breadcrumbs a { color: var(--text-secondary); }

    /* ── Theme Toggle ── */
    .theme-toggle {
      position: fixed; top: 1rem; right: 1rem; z-index: 200;
      background: var(--bg-secondary); border: 1px solid var(--border);
      border-radius: 50%; width: 40px; height: 40px; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      font-size: 1.2rem; transition: all 0.3s;
    }
    .theme-toggle:hover { border-color: var(--accent); }

    /* ── Back to Top ── */
    .back-to-top {
      position: fixed; bottom: 2rem; right: 2rem; z-index: 200;
      background: var(--accent); color: var(--bg-primary);
      border: none; border-radius: 50%; width: 44px; height: 44px;
      cursor: pointer; font-size: 1.2rem; box-shadow: var(--shadow);
      opacity: 0; transition: opacity 0.3s;
    }
    .back-to-top.visible { opacity: 1; }

    /* ── Checkbox Progress ── */
    .section-check {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;
    }
    .section-check input[type="checkbox"] {
      width: 18px; height: 18px; accent-color: var(--accent);
    }

    /* ── Print Styles ── */
    @media print {
      .sidebar, .theme-toggle, .back-to-top, .copy-btn, .nav-buttons,
      .section-check input, .progress-bar { display: none !important; }
      .main-content { margin-left: 0 !important; }
      body { color: #000; background: #fff; }
      pre { border: 1px solid #ccc; }
      details { display: block; }
      details > * { display: block; }
      h2 { page-break-before: always; }
      a { color: #000; text-decoration: underline; }
    }
  </style>
</head>
<body>
  <!-- Sidebar / TOC -->
  <nav class="sidebar" id="sidebar">
    <h3>Contents</h3>
    <!-- Auto-generated from h2 headings via JS -->
    <div id="toc"></div>
  </nav>

  <!-- Theme Toggle -->
  <button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">🌙</button>

  <!-- Back to Top -->
  <button class="back-to-top" id="backToTop" aria-label="Back to top">↑</button>

  <!-- Main Content -->
  <div class="main-content">
    <div class="container">

      <!-- Breadcrumbs -->
      <div class="breadcrumbs">
        <a href="index.html">Home</a> › <strong>Module XX — Name</strong>
      </div>

      <!-- Header -->
      <h1>Module XX — Module Name</h1>
      <p style="color: var(--text-muted);">⏱ Estimated time: XX minutes &nbsp;|&nbsp; 📁 Files: <code>filename.py</code></p>
      <p style="color: var(--text-muted);">Prerequisites: Module XX</p>
      <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>

      <!-- Nav -->
      <div class="nav-buttons">
        <a href="module_XX_prev.html" class="nav-btn">← Previous: Module Name</a>
        <a href="module_XX_next.html" class="nav-btn">Next: Module Name →</a>
      </div>

      <!-- SECTIONS GO HERE — see content specification above -->

      <!-- Bottom Nav -->
      <div class="nav-buttons">
        <a href="module_XX_prev.html" class="nav-btn">← Previous: Module Name</a>
        <a href="module_XX_next.html" class="nav-btn">Next: Module Name →</a>
      </div>

    </div>
  </div>

  <script>
    // ── Theme Toggle ──
    const html = document.documentElement;
    const toggle = document.getElementById('themeToggle');
    const saved = localStorage.getItem('theme') || 'dark';
    html.setAttribute('data-theme', saved);
    toggle.textContent = saved === 'dark' ? '☀️' : '🌙';
    toggle.addEventListener('click', () => {
      const next = html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', next);
      localStorage.setItem('theme', next);
      toggle.textContent = next === 'dark' ? '☀️' : '🌙';
    });

    // ── Build TOC from h2 ──
    const toc = document.getElementById('toc');
    document.querySelectorAll('h2').forEach((h, i) => {
      if (!h.id) h.id = 'section-' + i;
      const a = document.createElement('a');
      a.href = '#' + h.id;
      a.textContent = h.textContent;
      toc.appendChild(a);
    });

    // ── Active section highlighting ──
    const tocLinks = toc.querySelectorAll('a');
    const observer = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          tocLinks.forEach(l => l.classList.remove('active'));
          const active = toc.querySelector(`a[href="#${e.target.id}"]`);
          if (active) active.classList.add('active');
        }
      });
    }, { rootMargin: '-20% 0px -60% 0px' });
    document.querySelectorAll('h2').forEach(h => observer.observe(h));

    // ── Copy buttons ──
    document.querySelectorAll('pre').forEach(pre => {
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'Copy';
      btn.addEventListener('click', () => {
        navigator.clipboard.writeText(pre.querySelector('code').textContent);
        btn.textContent = '✓ Copied';
        setTimeout(() => btn.textContent = 'Copy', 2000);
      });
      pre.appendChild(btn);
    });

    // ── Back to top ──
    const topBtn = document.getElementById('backToTop');
    window.addEventListener('scroll', () => {
      topBtn.classList.toggle('visible', window.scrollY > 400);
    });
    topBtn.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

    // ── Section checkbox progress ──
    const MODULE_KEY = 'module_XX_progress';  // Change XX per module
    const checks = document.querySelectorAll('.section-check input[type="checkbox"]');
    const progressFill = document.getElementById('progressFill');
    const savedProgress = JSON.parse(localStorage.getItem(MODULE_KEY) || '{}');

    checks.forEach(cb => {
      if (savedProgress[cb.id]) cb.checked = true;
      cb.addEventListener('change', () => {
        savedProgress[cb.id] = cb.checked;
        localStorage.setItem(MODULE_KEY, JSON.stringify(savedProgress));
        updateProgress();
      });
    });

    function updateProgress() {
      const total = checks.length;
      const done = [...checks].filter(c => c.checked).length;
      progressFill.style.width = total ? (done/total*100) + '%' : '0%';
    }
    updateProgress();

    // ── Sidebar toggle (mobile) ──
    const sidebar = document.getElementById('sidebar');
    document.addEventListener('click', e => {
      if (window.innerWidth <= 768) {
        if (e.target.closest('.sidebar')) return;
        sidebar.classList.remove('open');
      }
    });
  </script>
</body>
</html>

QUALITY RULES (apply to everything)
Learning material quality:
  - Never say "as you can see" or "simply" — explain as if talking to an intelligent peer
    who is new to this specific technology
  - Every code snippet in the HTML must be runnable as written
  - All resource links must be to official docs, well-known tutorials, or reputable references
  - Exercises must have a clear success condition (the learner knows when they got it right)
  - Code in HTML files must use the syntax highlighting CSS classes defined above
    (wrap keywords in <span class="kw">, strings in <span class="str">, etc.)

HTML quality:
  - Valid HTML5 — every file must pass basic validation
  - Every interactive element must have aria labels for accessibility
  - All CSS and JS must be inline (no external dependencies)
  - Files must work when opened directly from the filesystem (file:// protocol)
  - Files must look professional on first open — no unstyled flash
  - Responsive design must work on screens from 320px to 2560px wide

Linking rules:
  - Every module HTML file must link to its source file(s) at the top
  - index.html must link to every module HTML file
  - Every module must have working Previous/Next navigation
  - WORKSHEET.md must link to learning_material/index.html