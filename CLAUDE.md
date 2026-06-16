# Claude Code Instructions — Tenant Management MVP

## Start every session by reading this file first:
**`CODEBASE_CONTEXT.md`** — full product overview, DB schema, all routes, all components, architectural rules, integrations, and patterns. Read it before touching any code so you never need to re-explore the codebase from scratch.CODEBASE_CONTEXT.md should be update regularly.

## Keeping CODEBASE_CONTEXT.md up to date (mandatory):
At the end of **every session** where you make code changes that affect any of the following, update the relevant section(s) of `CODEBASE_CONTEXT.md` before finishing:
- Database schema changes (new tables, new columns, new constraints, migrations)
- New or modified backend routes (method, path, behavior, VAPI contract)
- New or modified frontend components, modals, or pages
- Changes to integration behavior (VAPI agent config, Stripe, Twilio, SendGrid)
- Changes to key architectural rules (auth patterns, DB client usage, error handling)
- New environment variables or config settings

**How to update:** Edit only the specific section(s) that changed — do not rewrite the whole file. Keep the same table/bullet format. Add the change inline where it logically belongs rather than appending to the bottom.

---

## File Organization (mandatory)

**The repo root is reserved.** The only files that belong at the root are the canonical entry docs (`CLAUDE.md`, `CODEBASE_CONTEXT.md`, `README.md`) and config (`.gitignore`, etc.). **Never create a new file in the repo root** — put it in the folder for its kind, so any human or agent can find it by looking in one predictable place.

| Content type | Folder | Example |
|---|---|---|
| Plans, specs, implementation / improvement docs | `docs/development_plans/` | `PLAN_quebec_sizing_and_address_autofill.md` |
| Bug investigations & fix records | `docs/diagnoses/` | `VOICE_AGENT_BUG_DIAGNOSIS.md` |
| Test plans, reports, logs | `docs/testing/` | `LEAD_AGENT_TEST_REPORT.md` |
| Session context / handoff notes | `docs/sessions/` | `SESSION_HANDOFF.md` |
| Voice-agent prompt / flow / script definitions | `docs/agent/` | `SYSTEM_PROMPT.md` |
| Misc reference (env var lists, requirements, snapshots) | `docs/reference/` | `RENDER_ENV_VARS.md` |
| Seed SQL + seed data CSVs (kept together) | `scripts/seeds/` | `seed_listings.sql` |
| One-off data-fix / backfill SQL | `scripts/backfills/` | `backfill_call_logs_manager_id.sql` |
| Numbered schema / RLS migration SQL | `scripts/` (project) · `backend/migrations/` (app) | `02_rls_policies.sql` |
| Manual / integration test runner scripts | `tests/` | `run_api_tests.py` |
| CSV / XLSX test fixtures | `test_csvs/` | `prop_happy.csv` |
| Python deploy / admin scripts | `backend/scripts/` | `update_lease_agents.py` |
| E2E (Playwright) tests | `e2e/` | `tests/a-auto-delist.spec.ts` |

**Naming rules (so names stay unique and searchable):**
- Give every file a **descriptive, unique** name that states its subsystem and topic. Prefix with the subsystem when relevant: `lease_agent_`, `complaint_`, `csv_import_`, `voice_agent_`.
- **Banned generic stems** — never name a file `PLAN.md`, `FIX.md`, `FIX_PLAN.md`, `changes.md`, `notes.md`, `WORKSHEET.md`, or anything that collides on a common word. They are unsearchable and clash across topics.
- For dated artifacts (diagnoses, test reports, session notes), append an ISO date: `lease_agent_diagnosis_2026-06-14.md`.
- Before creating a doc, check the target folder for an existing file on the same topic and **update it instead** of adding a near-duplicate.

---

## Hard Rules (non-negotiable)

- **No `/api` prefix** on any backend route — routes are registered without it in `main.py`
- **All frontend HTTP calls go through `apiService.js`** — never inline `fetch` in a component
- **Never use SQLAlchemy models** in new code — use the Supabase Python SDK directly
- **DB dependency injection**: user routes use `get_authenticated_db` (RLS-enforced); webhooks/admin use `get_service_db`
- **VAPI endpoints always return HTTP 200** — never raise HTTP errors from `/flats/verify-phone`, `/voice/webhook`, etc.
- **Pydantic V2** — use `model_validator` / `field_validator`, not `@validator`
- **Groq model**: `llama-3.3-70b-versatile` — `llama-3.1-70b-versatile` is decommissioned
- **Date format**: `YYYY-MM-DDTHH:MM:SS` (T separator) for `parseISO` compatibility; store as IST
- **Never create files in the repo root** — every new doc/script/data file goes in its folder with a unique, descriptive name (see [File Organization](#file-organization-mandatory))

## Code Style

- No comments unless the WHY is non-obvious
- No docstrings
- No backwards-compat shims for removed code
- Short, direct responses — no trailing summaries
- Functional React components only

## Project Stack Quick Reference

| Layer | Tech |
|---|---|
| Backend | FastAPI + Supabase Python SDK + Pydantic V2 |
| Frontend | React 18 + Vite + TailwindCSS + Framer Motion |
| DB | Supabase PostgreSQL |
| AI Chatbot | OpenAI gpt-4o-mini |
| AI Extraction | Groq llama-3.3-70b-versatile |
| Voice | VAPI.ai |
| SMS | Twilio |
| Email | SendGrid |
| Payments | Stripe |
