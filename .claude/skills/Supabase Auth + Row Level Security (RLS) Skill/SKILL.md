---
name: supabase-auth-rls
description: >
  Add Supabase Auth and Row Level Security (RLS) to convert a single-user app into a multi-user app.
  Use this skill whenever the user wants to: add authentication to an existing app, add login/signup,
  convert a single-user product to multi-user, add Supabase Auth, add RLS policies, secure database
  tables per user, add email/password auth, add OAuth/social login with Supabase, protect routes,
  add user sessions, make an app multi-tenant, add "user_id" columns, or anything involving
  Supabase auth.uid(), auth.jwt(), row level security policies, or the @supabase/ssr package.
  Also trigger when the user says things like "add auth", "add login", "make it multi-user",
  "add user accounts", "secure my tables", "add RLS", or "protect my data per user".
---

# Supabase Auth + Row Level Security (RLS) Skill

This skill converts a single-user application into a secure multi-user application using Supabase Auth for authentication and Postgres Row Level Security for per-user data isolation.

## Overview

The transformation has 4 phases:

1. **Audit** — Understand the existing app (framework, database schema, Supabase usage)
2. **Database** — Add `user_id` columns, enable RLS, write policies, create profiles table + trigger
3. **Auth** — Install packages, create Supabase clients, build login/signup UI, protect routes
4. **Migrate** — Wire existing queries to respect the authenticated user

Read `references/database-patterns.md` before starting Phase 2.
Read the framework-specific reference before starting Phase 3:
- Next.js (App Router) → `references/nextjs-auth.md`
- React (Vite / CRA) → `references/react-auth.md`
- Other frameworks → adapt the React patterns; the Supabase client code is identical.

---

## Phase 1: Audit the existing app

Before writing any code, answer these questions by reading the codebase:

1. **Framework**: Next.js (App Router or Pages Router)? React + Vite? React Native? Something else?
2. **Is Supabase already in use?** Look for `@supabase/supabase-js` in package.json or any `createClient` calls. Note the existing client setup.
3. **Database schema**: List every table in use. For each table, note whether it already has a `user_id` column. Check if RLS is already enabled.
4. **Data access layer**: Where are Supabase queries made? (Server components, API routes, client components, a dedicated `lib/` file?) List the files.
5. **Existing auth**: Is there any auth at all? (Even a simple password gate or environment variable check.)
6. **Environment variables**: Check `.env` / `.env.local` for `SUPABASE_URL`, `SUPABASE_ANON_KEY`, or `NEXT_PUBLIC_SUPABASE_URL` etc.

Present your findings to the user before proceeding. Confirm the plan.

---

## Phase 2: Database changes

Read `references/database-patterns.md` now for the full SQL patterns.

### 2.1 Create a profiles table

Every multi-user app needs a public profiles table that mirrors `auth.users`:

```sql
create table if not exists public.profiles (
  id uuid not null references auth.users on delete cascade,
  email text,
  full_name text,
  avatar_url text,
  created_at timestamptz default now(),
  primary key (id)
);

alter table public.profiles enable row level security;

create policy "Users can view their own profile"
  on public.profiles for select
  to authenticated
  using ((select auth.uid()) = id);

create policy "Users can update their own profile"
  on public.profiles for update
  to authenticated
  using ((select auth.uid()) = id)
  with check ((select auth.uid()) = id);
```

### 2.2 Create a trigger to auto-populate profiles on signup

```sql
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

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

### 2.3 Add user_id to existing tables

For each table that stores user-specific data:

```sql
-- Add user_id column if it doesn't exist
alter table <table_name>
  add column if not exists user_id uuid references auth.users on delete cascade;

-- Create index for RLS performance (critical!)
create index if not exists idx_<table_name>_user_id
  on <table_name> using btree (user_id);
```

If the table already has data from the single-user era, you'll need a migration strategy. Ask the user:
- Option A: Assign all existing rows to the first user who signs up
- Option B: Create a migration script that assigns rows to a specific user ID
- Option C: Delete existing data and start fresh

### 2.4 Enable RLS and create policies for every table

For each user-data table, enable RLS and create the four standard CRUD policies:

```sql
alter table <table_name> enable row level security;

-- SELECT: users see only their own rows
create policy "<table_name>_select_own"
  on <table_name> for select
  to authenticated
  using ((select auth.uid()) = user_id);

-- INSERT: users can only insert rows tagged with their own ID
create policy "<table_name>_insert_own"
  on <table_name> for insert
  to authenticated
  with check ((select auth.uid()) = user_id);

-- UPDATE: users can only update their own rows
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

**Performance note**: Always wrap `auth.uid()` in a `(select ...)` subquery in policies. This lets Postgres cache the result per-statement instead of evaluating it per-row, which is dramatically faster on large tables.

### 2.5 Handle shared / public data tables

Not all tables are user-scoped. For tables that should be readable by everyone (e.g. a `categories` table), use:

```sql
alter table <table_name> enable row level security;

create policy "<table_name>_select_all"
  on <table_name> for select
  to authenticated, anon
  using (true);
```

For admin-only write access, either use the service role key server-side, or create an `is_admin` check in `app_metadata`.

---

## Phase 3: Auth implementation

Choose the correct reference file for the framework:

- **Next.js App Router** → Read `references/nextjs-auth.md` — uses `@supabase/ssr` with cookie-based sessions
- **React (Vite/CRA)** → Read `references/react-auth.md` — uses `@supabase/supabase-js` with token-based sessions
- **Other** → Adapt the React patterns

### General principles (all frameworks)

1. **Install packages**: `@supabase/supabase-js` is always needed. For SSR frameworks, also install `@supabase/ssr`.
2. **Environment variables**: The app needs `SUPABASE_URL` (or `NEXT_PUBLIC_SUPABASE_URL`) and `SUPABASE_ANON_KEY` (or `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
3. **Client creation**: Create a shared utility that initializes the Supabase client. Never create multiple client instances in the same request context.
4. **Auth UI**: Build (or use) login and signup forms. Supabase provides `@supabase/auth-ui-react` for drop-in forms, or you can build custom forms using `supabase.auth.signUp()`, `supabase.auth.signInWithPassword()`, and `supabase.auth.signInWithOAuth()`.
5. **Session management**: Listen for auth state changes with `supabase.auth.onAuthStateChange()` on the client side.
6. **Route protection**: Redirect unauthenticated users away from protected pages.
7. **Sign out**: Provide a sign-out button that calls `supabase.auth.signOut()`.

### Wiring queries to include user_id

After auth is set up, update all INSERT queries to include the authenticated user's ID:

```typescript
const { data: { user } } = await supabase.auth.getUser();

const { error } = await supabase
  .from('todos')
  .insert({ title: 'New todo', user_id: user.id });
```

For SELECT/UPDATE/DELETE, RLS handles filtering automatically — you don't need to add `.eq('user_id', user.id)` to every query because the RLS policy does it. However, including it can be a good defense-in-depth practice and helps with query planning.

---

## Phase 4: Testing checklist

After implementation, verify:

- [ ] Unauthenticated users are redirected to login
- [ ] New users can sign up and a profile row is created automatically
- [ ] Logged-in users can only see their own data
- [ ] Inserting data automatically tags it with the user's ID
- [ ] Users cannot see, edit, or delete other users' data
- [ ] Sign out works and clears the session
- [ ] The app works correctly in incognito/private browsing
- [ ] Existing data (if any) was migrated correctly

---

## Common pitfalls

1. **Forgetting to enable RLS on a table** — Data is exposed to everyone via the API. Always enable RLS on every table in the `public` schema.
2. **Not wrapping `auth.uid()` in `(select ...)`** — Causes massive performance degradation on large tables.
3. **Using `raw_user_meta_data` in RLS policies** — Users can modify this themselves via `supabase.auth.update()`. Use `raw_app_meta_data` for authorization data.
4. **Creating the Supabase client multiple times** — Especially in Next.js server components. Use utility functions that create one client per request.
5. **Not handling the auth callback route** — For email confirmation and OAuth redirects, you need a `/auth/callback` route that exchanges the code for a session.
6. **RLS blocking your own server-side admin operations** — Use the service role key (never exposed to the browser) for admin operations that need to bypass RLS.
7. **Forgetting indexes on `user_id` columns** — RLS policies that filter by `user_id` need a btree index for acceptable performance.
