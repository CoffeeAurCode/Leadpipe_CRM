# Fix Plan: appointments.manager_id + Freeform Agent Greeting

**Date:** 2026-06-03  
**Trigger:** Test call for complaint #66 — appointment creation failed with PGRST204.  
**Log line:** `[!] Appointment creation failed: {'message': "Could not find the 'manager_id' column of 'appointments' in the schema cache", 'code': 'PGRST204'}`

---

## Root Cause Analysis

### Bug 1 — `appointments.manager_id` column does not exist

PGRST204 is PostgREST's "column not found in schema cache" error. The column was never added to the `appointments` table in any migration. The voice webhook code now correctly passes `manager_id` in the insert payload (fixed in Phase 1), but the DB column doesn't exist, so every voice-created appointment fails silently and no appointment is saved.

Migration `020_appointments_callback_type.sql` adds `type` and `tenant_phone` — it must also add `manager_id`.

### Bug 2 — FK constraints are missing across `manager_id` columns

Several `manager_id` / `assigned_manager_id` columns exist without FK constraints:

| Table | Column | Current state |
|---|---|---|
| `appointments` | `manager_id` | **column missing entirely** |
| `twilio_number_pool` | `assigned_manager_id` | column exists (migration 015), no FK |
| `manager_vapi_config` | `manager_id` | column exists (migration 015), no FK |

`complaints.manager_id`, `lease_leads.manager_id`, `notifications.manager_id` already reference `auth.users(id)` — this is the correct pattern for all tables.

Without FK constraints, PostgREST cannot infer the relationship, and future schema introspection / tooling is blind to these links.

### Bug 3 — Agent greeting is over-scripted

The current `first_message` is 50+ words, bilingual, and introduces the full purpose of the call before the caller says anything. This prevents the agent from adapting to context clues in the caller's opening words. A caller who immediately says "It's urgent, my pipe burst!" gets a long pre-planned greeting instead of an empathetic response.

The `[Language Policy — STRICT]` section mandates a bilingual opener on every call ("the opening greeting is the only bilingual utterance"). This forces Alex to say both languages regardless of what it can infer from the caller's number/region, and it forces the first turn to be long and rigid.

---

## Fix A — DB Migration `021_appointments_manager_id_fk.sql`

**This must be run BEFORE re-testing.** Migration 020 should be run first (adds `type` and `tenant_phone`), then this one.

```sql
-- ── 1. Add manager_id to appointments ────────────────────────────────────────
-- This is the root cause of PGRST204. The column was missing entirely.
ALTER TABLE appointments
  ADD COLUMN IF NOT EXISTS manager_id UUID REFERENCES auth.users(id);

CREATE INDEX IF NOT EXISTS idx_appointments_manager
  ON appointments(manager_id);

-- ── 2. Backfill existing appointments from their linked complaint ─────────────
-- Appointments created before this migration have no manager_id.
-- The linked complaint does have manager_id — use it.
UPDATE appointments a
SET    manager_id = c.manager_id
FROM   complaints c
WHERE  a.complaint_uuid = c.uuid
  AND  a.manager_id IS NULL
  AND  c.manager_id IS NOT NULL;

-- Fallback: any appointment still NULL (no linked complaint) — pull from
-- manager_profiles (single-manager MVP has exactly one real manager).
UPDATE appointments
SET    manager_id = (
    SELECT user_id FROM manager_profiles
    ORDER  BY created_at
    LIMIT  1
)
WHERE  manager_id IS NULL;

-- ── 3. RLS: manager sees only their own appointments ─────────────────────────
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'appointments'
          AND policyname = 'manager sees own appointments'
    ) THEN
        CREATE POLICY "manager sees own appointments"
            ON appointments FOR ALL
            USING (manager_id = auth.uid());
    END IF;
END $$;

-- ── 4. Add FK on twilio_number_pool.assigned_manager_id ──────────────────────
-- Column exists since migration 015 but has no FK constraint.
-- auth.users is the authoritative user table.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE  constraint_name = 'fk_pool_assigned_manager'
          AND  table_name      = 'twilio_number_pool'
    ) THEN
        ALTER TABLE twilio_number_pool
            ADD CONSTRAINT fk_pool_assigned_manager
            FOREIGN KEY (assigned_manager_id)
            REFERENCES auth.users(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- ── 5. Add FK on manager_vapi_config.manager_id ───────────────────────────────
-- Column exists since migration 015 but has no FK constraint.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE  constraint_name = 'fk_vapi_config_manager'
          AND  table_name      = 'manager_vapi_config'
    ) THEN
        ALTER TABLE manager_vapi_config
            ADD CONSTRAINT fk_vapi_config_manager
            FOREIGN KEY (manager_id)
            REFERENCES auth.users(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ── 6. Verify ─────────────────────────────────────────────────────────────────
-- SELECT
--   (SELECT COUNT(*) FROM appointments WHERE manager_id IS NULL)      AS appts_still_null,
--   (SELECT COUNT(*) FROM appointments WHERE manager_id IS NOT NULL)  AS appts_backfilled;
--
-- Expected: appts_still_null = 0 (or only rows with no linked complaint)
```

**Run order:**
1. `020_appointments_callback_type.sql` — adds `type`, `tenant_phone`
2. `021_appointments_manager_id_fk.sql` — adds `manager_id` + FKs

After running 021, PostgREST will pick up the new column at the next schema reload (Supabase does this automatically, or trigger it in Dashboard → Settings → API → Reload schema).

---

## Fix B — Code: update `020` to also cover `manager_id`

**File:** `backend/migrations/020_appointments_callback_type.sql`

The existing 020 only adds `type` and `tenant_phone`. To keep migrations atomic, leave 020 as-is and use 021 for `manager_id`. No code changes needed — the voice webhook already sends `manager_id` in the payload (added in the callback scheduling implementation).

---

## Fix C — Agent greeting: remove scripted opener, let Alex lead naturally

**File:** `backend/app/services/vapi_agent_config.py`

### C.1 — `build_complaint_config()` — shorten `first_message`

**Current (after last update):**
```python
"first_message": "Hi, thanks for calling — I'm Alex, here to help log your complaint and schedule a callback from your property manager. What's your flat number? / Bonjour, merci d'appeler — je suis Alex, ici pour enregistrer votre demande et planifier un rappel de votre gestionnaire. Quel est votre numéro d'appartement?",
```

**New:**
```python
"first_message": "Hi, this is Alex — how can I help you today?",
```

Why: A short, open-ended opener lets the caller lead. If they immediately say "my pipe burst", Alex hears the emergency and responds to it. If they say "bonjour", Alex switches to French. A scripted paragraph forces Alex to finish the script before it can listen.

The flat-number collection is handled naturally in the system prompt flow — Alex will ask for it once the caller's intent is clear.

### C.2 — `COMPLAINT_SYSTEM_PROMPT` — loosen the language opening rule

**Current:**
```
[Language Policy — STRICT]
The opening greeting is the only bilingual utterance in the call. Its purpose is to
announce that both languages are supported. After that point, the call is monolingual.
```

**New:**
```
[Language Policy]
Detect the caller's language from their first words and lock to it for the entire call.
- Caller speaks English → respond in ENGLISH ONLY for all remaining turns
- Caller speaks French  → respond in FRENCH ONLY for all remaining turns
- Language unclear after 2 exchanges → ask "English or French? / Anglais ou français?" then lock

Do NOT mix languages in the same sentence. Do NOT append translations.
You may briefly offer both languages once ("English or French?") if the caller's language
is genuinely ambiguous — but do not force a bilingual greeting on every call.
```

Why: Mandating a bilingual opener means Alex always speaks both languages even when the caller's language is obvious (e.g. caller says "hello" — English is clear). Removing the mandate lets Alex be natural and reduces the length of the first turn, which matters for perceived responsiveness.

### C.3 — Keep everything else in the system prompt unchanged

The verification flow, callback scheduling flow, tool invocation rules, and tool data language rules are all correct and should not be touched. Only the greeting rigidity is relaxed.

---

## Implementation Order

| Step | Action | Where |
|---|---|---|
| 1 | Run `020_appointments_callback_type.sql` in Supabase | Supabase SQL Editor |
| 2 | Run `021_appointments_manager_id_fk.sql` in Supabase | Supabase SQL Editor |
| 3 | Verify: existing appointment rows now have `manager_id` set | Supabase Table Editor |
| 4 | Apply Fix C to `vapi_agent_config.py` | Local code |
| 5 | Run `python backend/scripts/update_shared_agents.py` | Terminal |
| 6 | Make a test call — confirm: appointment created, calendar shows it, notification appears | Live test |

---

## What the After State Looks Like

- Voice call creates complaint → complaint has `manager_id` → appointment insert includes `manager_id` (code already does this) → `appointments.manager_id` column now exists → insert succeeds → RLS passes → frontend GET returns the row → calendar shows the callback event
- Agent greets with "Hi, this is Alex — how can I help you today?" → caller responds naturally → Alex adapts
- Bell notification fires (also inserted by same webhook) → manager sees teal badge within 30 seconds
