# Leads Disappearing — Debug Plan

## Where Leads Can Silently Disappear

```
Browser           →  authFetch /leasing/leads
  ↓
Promise.all       →  if ANY of 4 requests throws, catch() runs, setLeads([]) never called
  ↓
GET /leasing/leads →  require_active_subscription → user["sub"] from JWT
  ↓
DB query          →  WHERE manager_id = user["sub"]
  ↓
lease_leads rows  →  manager_id was backfilled from auth.users LIMIT 1
```

**Most probable break:** UUID mismatch. Migration 012 used `SELECT id FROM auth.users LIMIT 1`
without `ORDER BY` or `WHERE email`. If multiple rows exist in `auth.users` (test accounts,
anonymous sessions, etc.), the backfill may have used the wrong UUID — not the one in the JWT `sub`.

---

## Step 1 — Confirm UUID mismatch

Run in Supabase SQL Editor:

```sql
SELECT
    u.id           AS auth_uuid,
    u.email,
    COUNT(ll.id)   AS leads_with_this_id
FROM auth.users u
LEFT JOIN lease_leads ll ON ll.manager_id = u.id
GROUP BY u.id, u.email
ORDER BY u.created_at;
```

If `curiosus.steel@gmail.com` shows `leads_with_this_id = 0`, the backfill picked a different user. Go to Step 2.

---

## Step 2 — Fix the UUID (if Step 1 confirms mismatch)

**Root cause confirmed:** Migration 012 used `SELECT id FROM auth.users LIMIT 1` without
`ORDER BY`, which picked `mock-manager@yourdomain.com` — the first row postgres returned.
All 17 leads were backfilled to that UUID. The real owner account is `leadpipecrm@gmail.com`.

```sql
-- Fix leads
UPDATE lease_leads
SET manager_id = (SELECT id FROM auth.users WHERE email = 'leadpipecrm@gmail.com')
WHERE true;

-- Fix properties_list (same root cause)
UPDATE properties_list
SET manager_id = (SELECT id FROM auth.users WHERE email = 'leadpipecrm@gmail.com')
WHERE manager_id IS NULL
   OR manager_id != (SELECT id FROM auth.users WHERE email = 'leadpipecrm@gmail.com');
```

Verify:

```sql
SELECT COUNT(*) FROM lease_leads
WHERE manager_id = (SELECT id FROM auth.users WHERE email = 'leadpipecrm@gmail.com');
-- Should return 17
```

---

## Step 3 — Check browser console

Open DevTools → Console → click Refresh on Leasing tab. Look for:

- `Leasing load error` — one of the 4 parallel requests threw
- Any red HTTP errors

`Promise.all` in `load()` means if any of these fails, **all** state updates are skipped:
1. `getListings`
2. `getLeaseLeads`
3. `getLeasingMetrics`
4. `fetchPropertyGroups`

---

## Step 4 — Check network tab

DevTools → Network → Refresh → find `/leasing/leads`:

| Status | Meaning |
|---|---|
| `200` with `[]` | UUID mismatch — Step 2 fixes it |
| `200` with rows | Frontend filter hiding them — check `listingFilter` / `statusFilter` dropdowns |
| `500` | Response validation error — check Render logs for the field name |
| `403` | Subscription gate failing |
| Request never appears | One of the other 3 parallel calls threw first |

---

## Step 5 — Confirm Render is on the right commit

Render dashboard → your service → Deploys.

Active deploy should be commit `30cf8129` ("streamline lead retrieval… filtering by manager_id").

If still on `b428ef51` (old fallback code), trigger a manual redeploy.

---

## Resolution Checklist

- [ ] Step 1: Run UUID audit SQL
- [ ] Step 2: Fix UUID if mismatched, verify count = 17
- [ ] Step 3: No `Leasing load error` in console
- [ ] Step 4: `/leasing/leads` returns 200 with rows
- [ ] Step 5: Render is on commit `30cf8129`
