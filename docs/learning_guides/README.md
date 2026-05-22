# Learning Guides — Reading Order

This directory contains 22 session guides + one staff-engineer synthesis document, written across the full build of the Tenant Management MVP. Each guide was written immediately after the session — bugs, decisions, and wrong turns included.

---

## How to Read This

**If you are joining the project mid-stream (most common):**  
Start with `STAFF_ENGINEER_LEARNING_GUIDE.md` to understand the system end-to-end, then jump to the session where the feature you're working on was first built. The table below maps features to sessions.

**If you are learning from scratch:**  
Read all 22 sessions in order. Each session assumes the previous ones.

**If you want the debugging wisdom without reading everything:**  
Read Part 3 of `STAFF_ENGINEER_LEARNING_GUIDE.md` (Sections 17–32). It synthesizes the top lessons from all 22 sessions into one reference.

---

## The Staff Engineer Guide (Read This First)

| File | What it covers |
|------|---------------|
| `STAFF_ENGINEER_LEARNING_GUIDE.md` | Full system architecture, data flow, anti-patterns, debugging playbook, scaling analysis. **Part 3** (added after Session 22) contains the accumulated wisdom: four bug categories, three-layer status rule, all-code-paths mental model, RLS audit queries, VAPI patterns, and 10 senior dev principles. |

---

## Session Map — In Order

### Track 1 — Foundation (Sessions 1–7)
*Read these if you are new to FastAPI, React, or Supabase.*

| Session | Topic | Key concepts |
|---------|-------|-------------|
| Session 1 | Project Foundation — FastAPI, Pydantic, Rule-Based NLP | `BaseModel`, FastAPI router pattern, Pydantic V2 validators, complaint extraction logic |
| Session 2 | Webhooks & VAPI Integration | Webhook vs REST, event payload parsing, the 307 redirect trap, idempotency |
| Session 3 | React Frontend Foundation | Component architecture, `useState`, `useEffect`, async API calls, `apiService.js` pattern |
| Session 4 | Premium Dark Dashboard | Design systems, component reuse, graceful error handling in the UI |
| Session 5 | Tailwind CSS Design System | Migration from custom CSS, utility classes, design tokens |
| Session 6 | Production Deployment | Render (backend), Netlify (frontend), environment variables, CORS |
| Session 7 | Critical Missing Skills | Git workflow, `.env` files, debugging curl, reading error messages |

---

### Track 2 — Core Product Features (Sessions 8–15)
*Read these to understand the data model and main CRUD patterns.*

| Session | Topic | Key concepts |
|---------|-------|-------------|
| Session 8 | Calendar & Appointment Scheduling | Date/time serialization, calendar UI, interactive forms |
| Session 9 | Appointment Edit & Delete | PATCH patterns, optimistic UI, status transitions |
| Session 10 | UUID Migration & VAPI Voice Lookup | UUID vs int IDs, VAPI tool endpoint design, tenant phone lookup |
| Session 11 | Debugging — Timezone & Calendar Bugs | IST timezone, `parseISO` vs space separator, systematic debugging |
| Session 12 | Production Debugging & Feature Dev | Reading 500 errors, Supabase SDK query patterns, `.maybe_single()` |
| Session 13 | File Uploads & Multipart Forms | `UploadFile`, Supabase Storage, service role key for storage |
| Session 14 | Relational Hierarchies & N+1 Prevention | PropertyGroup→Building→Flat→Tenant hierarchy, batch lookups, N+1 query problem |
| Session 15 | VAPI Tool Endpoints & SMS Notifications | VAPI `apiRequest` tools, FastAPI `BackgroundTasks`, Twilio SMS |

---

### Track 3 — AI & Advanced Patterns (Sessions 16–19)
*Read these to understand the chatbot, LLM tool calling, and performance optimization.*

| Session | Topic | Key concepts |
|---------|-------|-------------|
| Session 16 | AI Chatbot — Auditing Plans & Tool Calling | Pre-mortem auditing, Groq LLM tool calling, plan-to-code translation, 5-category audit framework |
| Session 17 | Full-Stack Feature Engineering | react-markdown, three-layer status rule, all-code-paths mental model, notification coverage, stacked modals |
| Session 18 | Frontend & Backend Performance | Code splitting, lazy loading, Vite manual chunks, Supabase client singleton, N+1 diagnosis, DB indexes |
| Session 19 | Debugging Third-Party Libraries | Reading compiled dist files, react-joyride v2→v3 breaking change, controlled vs uncontrolled components, multi-user localStorage isolation |

---

### Track 4 — Multi-Tenancy & Scale (Sessions 20–22)
*Read these to understand auth, RLS, leasing agents, and integration testing.*

| Session | Topic | Key concepts |
|---------|-------|-------------|
| Session 20 | Google OAuth / PKCE | `flowType: 'pkce'`, `detectSessionInUrl`, callback page, cross-domain token handoff |
| Session 21 | Feature Roadmap Execution + RLS Audit | Feature-first exploration methodology, FastAPI route ordering trap, bidirectional FK updates, Python dict join for aggregation, RLS audit SQL queries, Google OAuth deployment debugging |
| Session 22 | Two Voice Agents + Image Upload + Testing | Spec-to-code translation, `UploadFile`, Supabase Storage, `BackgroundTasks`, `StreamingResponse`, dual DB clients, JSONB, partial indexes, `WITH CHECK` vs `USING`, bash integration test scripts, four bug categories |

---

## Quick Reference — "Where Is X Covered?"

| Topic | Session(s) |
|-------|-----------|
| FastAPI basics (routes, Pydantic, Depends) | 1, 13 |
| Webhook design (idempotency, always-200) | 2, 15, 22 |
| React state, useEffect, apiService.js | 3 |
| Tailwind CSS | 4, 5 |
| Production deployment (Render, Netlify, env vars) | 6, 21 appendix |
| Database schema (full hierarchy) | 14, `STAFF_ENGINEER_LEARNING_GUIDE` |
| UUID vs int IDs | 10, 17 Section 19 |
| Calendar & date/time bugs (IST, parseISO, T separator) | 8, 11, 17 Section 16 |
| File upload + Supabase Storage | 13, 22 |
| VAPI endpoints (verify-phone, voice webhook) | 2, 10, 15, 22 |
| N+1 query problem | 14, 18 |
| AI chatbot (OpenAI tool calling) | 16, 17 |
| Groq LLM (complaint extraction) | 1, 16 |
| Supabase RLS — what it is, how to debug it | 17, 21, 22 |
| DB client: anon vs service role | 13, 17, 21, 22 |
| FastAPI route ordering trap | 21 |
| Bidirectional FK updates (flat ↔ tenant) | 21 |
| Google OAuth PKCE flow | 20, 21 appendix |
| Frontend performance (code splitting, lazy loading) | 18 |
| Backend performance (singleton client, indexes) | 18 |
| Third-party library debugging (grep the dist) | 19 |
| react-joyride onboarding tour | 19 |
| localStorage per-user scoping | 19 |
| Leasing agent + lead pipeline | 22 |
| VAPI auto-provisioning (BackgroundTasks) | 22 |
| CSV / XLSX import with AI column mapping | `PLAN_CSV_IMPORT.md` + `SESSION_LOG_CSV_IMPORT.md` |
| Stripe subscription gate | `CODEBASE_CONTEXT.md` Section 13 |
| Integration test scripts (bash + curl + jq) | 22 |
| Senior dev debugging methodology | 17 Section 18, `STAFF_ENGINEER_LEARNING_GUIDE` Part 3 |

---

## Recommended Reading Paths

### "I'm a new intern starting on this project"
1. `STAFF_ENGINEER_LEARNING_GUIDE.md` — Parts 1 and 2 (architecture overview)
2. `CODEBASE_CONTEXT.md` (in repo root — full route and schema reference)
3. Sessions 1 → 7 (foundation)
4. Sessions 14, 16, 17 (data model, AI chatbot, advanced patterns)
5. `STAFF_ENGINEER_LEARNING_GUIDE.md` — Part 3 (accumulated debugging wisdom)
6. Any remaining sessions that cover features you'll be working on

### "I know web dev but I'm new to this stack (FastAPI + Supabase + VAPI)"
1. `STAFF_ENGINEER_LEARNING_GUIDE.md`
2. Sessions 2, 10, 14, 15 (Supabase SDK, VAPI, hierarchical data)
3. Sessions 16, 22 (AI chatbot, leasing agent)
4. Session 21 (RLS, bidirectional FK, feature roadmap execution)

### "I need to debug something right now"
1. `STAFF_ENGINEER_LEARNING_GUIDE.md` Part 3 — Section 30 (systematic debugging method) and Section 31 (silent failures)
2. Session 17 — Section 9 (bug catalogue from real bugs)
3. Session 18 — Part 1 (frontend) and Part 2 (backend) for performance issues
4. Session 21 — Section 5 (diagnosis commands reference)
5. Session 22 — Appendix (common bugs in this codebase)

### "I'm working on a VAPI / voice feature"
1. Sessions 2, 10, 15 (VAPI fundamentals)
2. Session 22 — Parts 2 and 3 (two-agent system, VAPI tool endpoints, `get_service_db` requirement)
3. `STAFF_ENGINEER_LEARNING_GUIDE.md` Part 3 — Section 26 (VAPI critical patterns)

### "I'm working on the AI chatbot"
1. Session 16 — Parts 2 and 3 (Groq tool calling)
2. Session 17 — Section 7 (chatbot tool design patterns)
3. `STAFF_ENGINEER_LEARNING_GUIDE.md` Part 3 — Sections 19–20 (three-layer rule, all-code-paths)

---

## A Note on Guide Quality

The guides get significantly richer from Session 14 onward. Sessions 1–7 are shorter and more tutorial-style. Sessions 16–22 are long, deep, and include the kind of "why" reasoning that separates senior developers from juniors. If you only have time to read a few, prioritize 17, 18, 21, and 22 — plus Part 3 of the Staff Engineer Guide.
