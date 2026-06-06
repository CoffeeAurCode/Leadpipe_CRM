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

## Hard Rules (non-negotiable)

- **No `/api` prefix** on any backend route — routes are registered without it in `main.py`
- **All frontend HTTP calls go through `apiService.js`** — never inline `fetch` in a component
- **Never use SQLAlchemy models** in new code — use the Supabase Python SDK directly
- **DB dependency injection**: user routes use `get_authenticated_db` (RLS-enforced); webhooks/admin use `get_service_db`
- **VAPI endpoints always return HTTP 200** — never raise HTTP errors from `/flats/verify-phone`, `/voice/webhook`, etc.
- **Pydantic V2** — use `model_validator` / `field_validator`, not `@validator`
- **Groq model**: `llama-3.3-70b-versatile` — `llama-3.1-70b-versatile` is decommissioned
- **Date format**: `YYYY-MM-DDTHH:MM:SS` (T separator) for `parseISO` compatibility; store as IST

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
