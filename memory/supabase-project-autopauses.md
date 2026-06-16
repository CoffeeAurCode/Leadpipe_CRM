---
name: supabase-project-autopauses
description: The Supabase DB pauses on idle and times out via MCP; run SQL in the dashboard editor
metadata:
  type: reference
---

Supabase project `bpvzfboslevifpnsezts` (the CRM database) is on a tier that **auto-pauses when idle**. It frequently reports `status: INACTIVE` to the MCP Supabase tools, and `execute_sql` calls **time out** ("Connection terminated due to connection timeout") even while the live app is serving traffic — because the running app reaches Postgres through the PostgREST REST path, which is separate from the MCP's direct SQL connection.

**How to apply:** Don't rely on the Supabase MCP `execute_sql` for this project. Give the user SQL to run in the **Supabase dashboard SQL editor** (which wakes the project), and ask them to paste results back. Migrations and verification queries go through the editor, not tooling.
