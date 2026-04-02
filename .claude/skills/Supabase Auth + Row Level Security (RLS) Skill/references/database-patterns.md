# Database Patterns for Supabase Auth + RLS

This reference covers all SQL patterns needed to convert a single-user database to multi-user with RLS.

## Table of Contents

1. [Profiles table and trigger](#profiles-table-and-trigger)
2. [Adding user_id to existing tables](#adding-user_id-to-existing-tables)
3. [Standard CRUD RLS policies](#standard-crud-rls-policies)
4. [Shared / public data policies](#shared--public-data-policies)
5. [Admin access patterns](#admin-access-patterns)
6. [Migration strategies for existing data](#migration-strategies-for-existing-data)
7. [Performance optimization](#performance-optimization)
8. [Supabase SQL migration file conventions](#supabase-sql-migration-file-conventions)

---

## Profiles table and trigger

The `auth.users` table is managed by Supabase and not exposed via the API. Create a `public.profiles` table to store user-facing data. Reference `auth.users` with `on delete cascade` so that deleting a user cleans up their profile.

```sql
-- Create profiles table
create table if not exists public.profiles (
  id uuid not null references auth.users on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (id)
);

alter table public.profiles enable row level security;

-- Policies for profiles
create policy "Users can view their own profile"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

create policy "Users can update their own profile"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);

-- Trigger to auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (id, email, full_name, avatar_url)
  values (
    new.id,
    new.email,
    new.raw_user_meta_data ->> 'full_name',
    new.raw_user_meta_data ->> 'avatar_url'
  );
  return new;
end;
$$;

-- Drop existing trigger if any, then create
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

**Why `security definer set search_path = ''`**: The trigger function runs as the function owner (superuser), which can insert into `public.profiles` even though RLS is enabled. Setting `search_path = ''` prevents search-path-based attacks.

---

## Adding user_id to existing tables

For every table that stores per-user data, add a `user_id` column:

```sql
-- Add user_id column
alter table <table_name>
  add column if not exists user_id uuid references auth.users on delete cascade;

-- CRITICAL: Add index for RLS performance
create index if not exists idx_<table_name>_user_id
  on <table_name> using btree (user_id);
```

If the table uses a UUID primary key that already matches user IDs (like profiles), you may not need a separate `user_id` — just use the primary key in RLS policies.

For tables with **foreign key relationships**, add `user_id` to child tables too. Example:

```sql
-- Parent: projects (has user_id)
-- Child: tasks (belongs to a project)
-- Add user_id to tasks as well for direct RLS filtering
alter table tasks
  add column if not exists user_id uuid references auth.users on delete cascade;

create index if not exists idx_tasks_user_id
  on tasks using btree (user_id);
```

Alternatively, you can write a policy on `tasks` that joins to `projects`:

```sql
create policy "tasks_select_via_project"
  on tasks for select
  to authenticated
  using (
    exists (
      select 1 from projects
      where projects.id = tasks.project_id
      and projects.user_id = (select auth.uid())
    )
  );
```

The direct `user_id` approach is simpler and faster. The join approach avoids data duplication but is slower on large tables.

---

## Standard CRUD RLS policies

Apply this template to every user-scoped table:

```sql
-- Enable RLS (does nothing if already enabled)
alter table <table_name> enable row level security;

-- SELECT: users see only their own rows
create policy "<table_name>_select_own"
  on <table_name> for select
  to authenticated
  using ((select auth.uid()) = user_id);

-- INSERT: users can only insert rows with their own user_id
create policy "<table_name>_insert_own"
  on <table_name> for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

-- UPDATE: users can only update their own rows, cannot reassign to another user
create policy "<table_name>_update_own"
  on <table_name> for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

-- DELETE: users can only delete their own rows
create policy "<table_name>_delete_own"
  on <table_name> for delete
  to authenticated
  using ((select auth.uid()) = user_id);
```

**Key points:**
- Always use `(select auth.uid())` (with the select wrapper) for performance.
- The `to authenticated` clause means only logged-in users match these policies. Unauthenticated requests via the `anon` key will see nothing.
- UPDATE policies need both `using` (which rows can be targeted) and `with check` (what the new row must look like). Both check `user_id` to prevent a user from reassigning their row to another user.

---

## Shared / public data policies

For reference tables or content that should be readable by everyone:

```sql
alter table <table_name> enable row level security;

-- Anyone (logged in or not) can read
create policy "<table_name>_select_public"
  on <table_name> for select
  to authenticated, anon
  using (true);

-- Only admins can write (use service role key server-side)
-- No INSERT/UPDATE/DELETE policies = no writes via API
```

For data that is publicly readable but user-writable (e.g., blog posts):

```sql
-- Anyone can read
create policy "posts_select_public"
  on posts for select
  to authenticated, anon
  using (true);

-- Only the author can insert/update/delete
create policy "posts_insert_own"
  on posts for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

create policy "posts_update_own"
  on posts for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "posts_delete_own"
  on posts for delete
  to authenticated
  using ((select auth.uid()) = user_id);
```

---

## Admin access patterns

For admin operations, you have two options:

### Option A: Service role key (simplest)

Use the service role key server-side. It bypasses RLS entirely. Never expose it to the browser.

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseAdmin = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!
)

// This bypasses all RLS
const { data } = await supabaseAdmin.from('users_data').select('*')
```

### Option B: app_metadata-based admin role

Store admin status in `raw_app_meta_data` (users cannot modify this):

```sql
-- Set a user as admin (run in SQL editor or via service role)
update auth.users
set raw_app_meta_data = raw_app_meta_data || '{"role": "admin"}'::jsonb
where id = '<user-uuid>';
```

Then create policies that check for the admin role:

```sql
create policy "admins_can_read_all"
  on <table_name> for select
  to authenticated
  using (
    (select auth.uid()) = user_id
    or
    (select auth.jwt() -> 'app_metadata' ->> 'role') = 'admin'
  );
```

---

## Migration strategies for existing data

When converting from single-user to multi-user, existing rows won't have a `user_id`. Three strategies:

### Strategy A: Assign to first signup

Create a migration function that runs once:

```sql
-- After the first user signs up, run this to claim existing data:
update <table_name> set user_id = '<first-user-uuid>' where user_id is null;
```

You can automate this by checking in the `handle_new_user` trigger whether any unclaimed rows exist.

### Strategy B: Assign via migration script

```sql
-- Explicitly assign all orphaned rows to a specific user
update todos set user_id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' where user_id is null;
update projects set user_id = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' where user_id is null;
```

### Strategy C: Make user_id NOT NULL after migration

After migrating existing data, enforce the constraint:

```sql
-- Only do this AFTER all existing rows have a user_id
alter table <table_name> alter column user_id set not null;
```

---

## Performance optimization

### Always index user_id columns

```sql
create index if not exists idx_<table_name>_user_id
  on <table_name> using btree (user_id);
```

### Always wrap auth functions in (select ...)

```sql
-- SLOW: auth.uid() called per-row
using (auth.uid() = user_id)

-- FAST: auth.uid() called once, cached per-statement
using ((select auth.uid()) = user_id)
```

### Avoid complex joins in policies when possible

If a policy requires joining multiple tables, consider denormalizing `user_id` onto the child table for simpler, faster policies.

### Test with realistic data volumes

RLS overhead is negligible on small tables but can become significant with millions of rows. Use `EXPLAIN ANALYZE` to check query plans:

```sql
-- Run as the authenticated role to see RLS in action
set role authenticated;
set request.jwt.claims to '{"sub": "<user-uuid>"}';
explain analyze select * from <table_name>;
reset role;
```

---

## Supabase SQL migration file conventions

If the project uses Supabase CLI migrations (check for a `supabase/` directory):

- Place migration files in `supabase/migrations/`
- Name format: `YYYYMMDDHHMMSS_description.sql` (e.g., `20240101000000_add_auth_and_rls.sql`)
- Run with `supabase db push` (remote) or `supabase migration up` (local)

If the project does NOT use Supabase CLI:
- Provide the SQL as a single script the user can run in the Supabase Dashboard SQL Editor
- Save it as something like `migrations/001_add_auth_rls.sql` in the project root
