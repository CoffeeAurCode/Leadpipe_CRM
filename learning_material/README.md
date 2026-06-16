We just finished a build session. Create a new file in the learning_material/ folder
as a SELF-CONTAINED HTML FILE. The file should be named
session-0X-<phase-or-topic-slug>.html where X is the next session number.
**if the file is too big then make it into multiple files of html, just connect them and don't cheap out quality and depth of material**
The HTML file IS the lesson — all explanation, code, visuals, and exercises
are inside it. The learner opens it in a browser and reads it like a
textbook chapter.

Cover EVERYTHING we did in this session — every concept, every file, every
command, every bug we hit and how we fixed it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HTML FILE REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. SELF-CONTAINED: Single .html file. ALL CSS in a <style> block, ALL JS
   in a <script> block. No external dependencies. Works offline forever.

2. VISUAL DESIGN — make it beautiful and professional:
   - Dark/light mode toggle (saved to localStorage)
   - Color palette: dark charcoal (#1a1a2e) background, soft code colors
     in a VS Code–inspired syntax theme; clean white for light mode
   - Typography: system font stack or embed Inter via Google Fonts <link>
   - Code blocks: styled <pre><code> with line numbers, VS Code colors,
     copy-to-clipboard button
   - Sticky sidebar table-of-contents with smooth scroll
   - Collapsible sections for long code blocks (<details><summary>)
   - Callout boxes with distinct styling for:
       💡 Tip  |  ⚠️ Warning  |  🔑 Key Concept  |
       🐛 Bug Story  |  🧪 Exercise  |  📖 Deep Dive
   - Progress bar or module indicator at the top
   - Print-friendly @media print styles
   - Fully responsive — works on mobile, tablet, desktop

3. NAVIGATION:
   - Header: Session number, title, estimated time, difficulty level
   - Footer: ← Previous Session | Index | Next Session →
   - Sidebar: clickable table of contents for all sections

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CONTENT STRUCTURE (use this exact order)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### A. Header Bar
   - Session number & title (e.g. "Session 15 — Webhook Integration")
   - Estimated reading/build time
   - Difficulty: 🟢 Beginner / 🟡 Intermediate / 🔴 Advanced
   - Prerequisites: "Requires: Sessions 01–14"

### B. Session Overview
   - What we built in this session (with screenshot/mockup if visual)
   - Why it matters for CRM specifically
   - Learning objectives: "By the end you will be able to…"

### C. Recap Bridge
   - 2–3 paragraph recap of where we left off in the previous session
   - What is already built and working
   - Makes this session readable as a standalone document

### D. Concepts Introduced This Session
   For EACH new concept, create a dedicated subsection with:

   1. **Plain-English Explanation** — No jargon first. Explain like I'm
      smart but have never seen this before.
   2. **Why We Need It** — Specifically for CRM. Not abstract theory.
   3. **How It Works** — With a helpful analogy.
      (e.g. "Middleware is like airport security — every request passes
      through it before reaching the gate.")
   4. **Jargon Decoder** — Every acronym/shortform/technical term gets
      explained in brackets on FIRST use.
      Example: "ESM (ECMAScript Modules — the modern JavaScript system
      for sharing code between files)"
   5. **Annotated Code Snippet** — EVERY line gets a comment explaining
      what it does and WHY. The reader should understand the code purely
      from the comments.
   6. **📖 Resources** — For each concept:
      - Official documentation link
      - One beginner-friendly tutorial or video
      - One advanced deep-dive resource

### E. Step-by-Step Build Log
   Document EVERY action taken in this session. For each step:

   - **Step Number & Title** (e.g. "Step 3 — Create the database schema")
   - **The exact command** (in a styled terminal block) OR
     **the exact file** to create/edit (with full path shown)
   - **Full file contents** with EVERY line commented
   - **Why this step happens NOW** — not earlier, not later
   - **What would break if we skipped it**
   - **Expected output** — what the terminal or browser should show

### F. 🐛 Bug Journal (CRITICAL — include for every bug encountered)
   For EVERY bug, error, or unexpected behavior we hit during the session,
   create a dedicated "Bug Story" subsection. Each bug story must include:

   1. **🚨 The Symptom** — What we saw go wrong. Exact error message,
      exact log output, exact browser behavior. Copy-paste the real error.
   2. **🔍 The Diagnosis** — How we figured out what was wrong.
      Walk through the EXACT debugging steps:
      - What logs did we check? What did they say?
      - What did we Google or search for?
      - What hypotheses did we form and test?
      - What commands did we run to narrow it down?
      - What red herrings did we encounter?
   3. **🧠 The Root Cause** — WHY it happened. Not just "this line was
      wrong" but the underlying reason:
      - Was it a misunderstanding of how an API works?
      - Was it a config mismatch between environments?
      - Was it a race condition, a typo, a missing dependency?
      - What concept does the learner need to understand to prevent
        this class of bug in the future?
   4. **🔧 The Fix** — The exact code change, shown as before/after.
      EVERY changed line gets a comment explaining why this fixes it.
   5. **🛡️ The Lesson** — What general principle or debugging technique
      does this bug teach? How would a developer spot this faster next
      time? Are there tools, linter rules, or patterns that prevent it?

   If NO bugs were encountered in the session, include a short section
   titled "🐛 Bug Journal — Clean Session" explaining that no bugs were
   hit and why (e.g. "We were adding new code rather than modifying
   existing code, so there were fewer integration points to fail").

### G. Design Decisions Table
   A styled HTML table:
   | Decision | Alternatives Considered | Why We Chose This | Trade-offs |

### H. Verification Checklist
   - Exact commands to run (with expected output)
   - Browser URLs to visit (with expected behavior)
   - ✅ "It works if…" / ❌ "Something's wrong if…" diagnostic guide

### I. Exercises
   2–3 hands-on exercises ranked by difficulty:
   - 🟢 **Practice**: Reinforce what we just built
   - 🟡 **Stretch**: Extend the feature
   - 🔴 **Challenge**: Push beyond the lesson
   Each with hints in a collapsible <details> block.

### J. Troubleshooting / Common Errors
   A styled FAQ covering errors that are LIKELY at this stage:
   - "Error: MODULE_NOT_FOUND" → cause and fix
   - "Page shows blank white screen" → cause and fix
   - etc.

### K. What's Next
   One paragraph bridging to the next session — what we'll build next
   and what concepts will be introduced.

### L. Glossary
   Alphabetical list of every new term introduced in THIS session.
   Styled as a two-column table: Term | Definition

### M. Footer
   - "Session X — CRM Learning Series"
   - Navigation: ← Previous Session | Index | Next Session →
   - Timestamp of when the session file was generated

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 TEACHING RULES (apply to every session)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. AUDIENCE: Someone who has read all previous session files but is not
   a developer. They can follow instructions but need every concept
   explained.

2. DEPTH: Teach at the level of a senior developer mentoring a junior.
   Never say "as you know" — assume nothing is known. But never talk down.

3. JARGON RULE: Every shortform or technical term gets explained in
   brackets the FIRST time it appears in each session. After that, use
   freely.

4. CODE COMMENTS: EVERY code block must have a comment on EVERY
   non-obvious line. The reader should be able to rebuild the entire
   project just from reading these sessions.

5. DESIGN REASONING: For every architectural choice, explain WHY.
   Don't just say "create this file" — say why this file exists, what
   responsibility it owns, and how it fits into the bigger picture.

6. TOOL EXPLANATION: When we use any tool (npm, git, docker, psql, etc.),
   explain what it is, why we use it, and what command flags mean.
   Example: "npm install -D means install as a devDependency — a package
   needed only during development, not shipped to users."

7. BUG TRANSPARENCY: NEVER skip bugs. Every error, crash, wrong output,
   or unexpected behavior that happened during the session MUST be
   documented with the full Bug Story format (Section F). These are
   the most valuable learning moments.

8. NO MAGIC: Never handwave. If something is complex, break it into
   smaller pieces. If a concept requires a prerequisite, teach the
   prerequisite first or link to the session that covered it.

9. REAL-WORLD CONTEXT: Relate concepts to how they're used in production.
   (e.g. "In production apps like Slack, this same pattern handles
   millions of WebSocket connections.")

10. CONTINUITY: Start with a recap bridge so the file works as a
    standalone document.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 HTML DESIGN REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use this CSS color system (or close to it) for consistency across all
sessions:

  --bg-dark: #1a1a2e;
  --bg-dark-card: #16213e;
  --bg-dark-code: #0f0f23;
  --text-dark: #e0e0e0;
  --accent: #6c63ff;
  --accent-hover: #5a52d5;
  --success: #4ade80;
  --warning: #fbbf24;
  --danger: #f87171;
  --bug: #f472b6;

Code syntax colors (dark mode):
  --code-keyword: #c678dd;
  --code-string: #98c379;
  --code-comment: #5c6370;
  --code-function: #61afef;
  --code-number: #d19a66;
  --code-operator: #56b6c2;

Ensure light mode inverts these appropriately.
after you have 3+ HTML session files create a master index.
Create an index.html file in the learning/ folder that serves as the
homepage for all learning sessions. It should:

1. Use the same visual design as the session HTML files (dark/light
   toggle, same fonts, same colors).
2. Hero section: "CRM Learning Series" with subtitle and
   total session count.
3. Display all sessions as styled cards in a responsive grid. Each card:
   - Session number and title
   - Key concepts (as colored tag badges)
   - Difficulty level indicator
   - Estimated time
   - Completion checkbox (saved to localStorage)
   - "Contains Bug Stories" badge if the session has bug sections
4. Overall progress bar based on checked sessions.
5. Link each card to the corresponding session file.
6. Search/filter bar to find sessions by concept or keyword.
7. Fully responsive (mobile, tablet, desktop).
8. Self-contained — no external dependencies.
````

---

### Follow-up prompt: Generate an index page

> Paste this after you have 3+ HTML session files to create a master index.

````
Create an index.html file in the learning/ folder that serves as the
homepage for all learning sessions. It should:

1. Use the same visual design as the session HTML files (dark/light
   toggle, same fonts, same colors).
2. Hero section: "CRM Learning Series" with subtitle and
   total session count.
3. Display all sessions as styled cards in a responsive grid. Each card:
   - Session number and title
   - Key concepts (as colored tag badges)
   - Difficulty level indicator
   - Estimated time
   - Completion checkbox (saved to localStorage)
   - "Contains Bug Stories" badge if the session has bug sections
4. Overall progress bar based on checked sessions.
5. Link each card to the corresponding session file.
6. Search/filter bar to find sessions by concept or keyword.
7. Fully responsive (mobile, tablet, desktop).
8. Self-contained — no external dependencies.