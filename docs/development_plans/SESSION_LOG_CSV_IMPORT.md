# Session Log — CSV Import Feature: Implementation & Testing

> **Date:** 2026-04-26  
> **Scope:** Implement CSV bulk-import for Properties and Tenants, then run a full manual test suite against the live backend.

---

## 1. What Was Already Built (Pre-Session)

Before this session started, the plan file `PLAN_CSV_IMPORT.md` existed. On inspection, **all four implementation layers were already complete** (likely written in a prior session):

| Layer | File | Status |
|-------|------|--------|
| Backend route | `backend/app/routes/import_routes.py` | ✅ Done |
| Backend registration | `backend/app/main.py` | ✅ Done |
| Frontend API service | `frontend/src/services/apiService.js` | ✅ Done |
| Frontend modal | `frontend/src/components/CsvImportModal.jsx` | ✅ Done |
| Properties page wiring | `frontend/src/components/PropertiesPage.jsx` | ✅ Done |
| Tenants page wiring | `frontend/src/components/TenantManagement.jsx` | ✅ Done |

The task for this session was therefore: **run the manual curl/programmatic tests** to verify every feature and edge case works as specified.

---

## 2. What the Feature Does (Architecture Summary)

### Data hierarchy
```
PropertyGroup (properties_list)
  └── Building (buildings)
        └── Flat (flats)
              └── Tenant (tenants)
```

### Endpoints
- `POST /import/properties` — accepts a CSV, creates PropertyGroups + Buildings + Flats in one shot, deduplicating properties and buildings by name.
- `POST /import/tenants` — accepts a CSV, looks up existing flats by `flat_number`, creates Tenants and bidirectionally links them; optionally creates a rent record.

### Key behaviour rules
- Never crash the whole import on one bad row — collect errors, continue, return full summary.
- Duplicate flat_number on properties import → `skipped` list (not error).
- Already-occupied flat on tenant import → `skipped` list (not error, existing tenant preserved).
- File > 5 MB or > 1000 rows → rejected before processing.
- Missing required columns → rejected immediately with a clear message.

### Bug discovered during testing
`properties_list` has an RLS (Row-Level Security) policy that requires `manager_id = auth.uid()`. The import route was inserting without setting `manager_id`, so every row failed with a Supabase `42501` RLS error. **Fix:** add `"manager_id": user["sub"]` to the `properties_list` INSERT payload.  
See §5.5 for full diagnosis.

---

## 3. Test Infrastructure Setup

### Goal
Run 25 test cases programmatically against the live FastAPI backend, covering happy paths and every edge case from the spec.

### Approach
Write a self-contained Python test script (`test_import.py`) that:
1. Creates a temporary Supabase user via the admin API.
2. Inserts a subscription row so the `require_active_subscription` guard passes.
3. Signs in as that user to get a JWT access token.
4. Runs all tests using `requests` + `io.BytesIO` (no temp files on disk).
5. Cleans up the test user and all associated data.

### Why not use curl directly?
- We needed a valid Supabase JWT, which requires signing in programmatically.
- The test user setup/teardown logic is too complex to do in a shell script.
- Python lets us build the assertions inline and report pass/fail clearly.

---

## 4. Step-by-Step: Getting the Backend Running

### 4.1 Check if backend was running
```bash
curl -s http://localhost:8000/
# Exit code 7 = "Failed to connect to host" → backend not running
```

### 4.2 Find the venv
```bash
ls "C:\Users\BIT\Coding\Tenant_management_MVP\backend"
# Found: venv/
ls "C:\Users\BIT\Coding\Tenant_management_MVP\backend\venv\Scripts"
# Found: python.exe, pip.exe — but pip.exe was broken (exit code 1)
```

**Issue:** `pip.exe` in the venv failed silently. Used `python.exe -m pip` instead.

### 4.3 Install missing packages (one by one, as errors surfaced)

Each package below was discovered missing only when the backend crashed on startup with a `ModuleNotFoundError`. The fix each time was the same: install the missing package and restart.

| Import error | Package installed | Command |
|---|---|---|
| `No module named 'uvicorn'` | uvicorn | `python.exe -m pip install uvicorn` |
| `No module named 'twilio'` | twilio | `python.exe -m pip install twilio` |
| `No module named 'openai'` | openai, groq | `python.exe -m pip install openai groq` |
| (All at once) | fastapi, python-multipart, supabase, PyJWT, requests, python-dotenv | `python.exe -m pip install fastapi python-multipart supabase PyJWT requests python-dotenv` |
| (All at once) | sendgrid, stripe, vapi-server-sdk, python-jose | `python.exe -m pip install sendgrid stripe vapi-server-sdk python-jose` |

**Root cause:** The `requirements.txt` lists all packages, but none were installed in the venv. The venv was created but `pip install -r requirements.txt` was never run. Packages were installed on-demand as crashes revealed them.

### 4.4 Start the backend

```bash
# On Windows, Start-Process launches it as a detached process:
Start-Process -FilePath "venv\Scripts\python.exe" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
  -WorkingDirectory "backend\" `
  -WindowStyle Normal
```

**Verify:**
```bash
curl -s http://localhost:8000/
# → {"status":"Backend running"}
```

**Important: After changing backend code, the process must be killed and restarted.** Killing all Python processes:
```powershell
Get-Process | Where-Object { $_.ProcessName -like "python*" } | ForEach-Object { Stop-Process -Id $_.Id -Force }
```

---

## 5. Issues Faced During Testing & How Each Was Solved

### 5.1 UnicodeEncodeError on Windows terminal

**Symptom:**
```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 29-88
```

**Cause:** The test script used Unicode box-drawing characters (`─`, `✓`, `✗`, `⚠`, `→`) which the Windows `cp1252` console can't encode.

**Fix:** Force UTF-8 on stdout at the top of the script:
```python
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
```

---

### 5.2 Subscriptions table requires `stripe_customer_id` (NOT NULL)

**Symptom:**
```
null value in column "stripe_customer_id" of relation "subscriptions" violates not-null constraint
```

**Cause:** The subscriptions table has a `NOT NULL` constraint on `stripe_customer_id`. The test script was only inserting `manager_id`, `status`, and `trial_ends_at`.

**Fix:** Add a placeholder value:
```python
admin.table("subscriptions").insert({
    "manager_id": user_id,
    "status": "trialing",
    "trial_ends_at": "2099-12-31",
    "stripe_customer_id": "cus_test_placeholder",   # ← added
}).execute()
```

---

### 5.3 "A user with this email address has already been registered"

**Symptom:** On the second run, the test script couldn't create the test user because the previous run failed mid-way and left the user in Supabase.

**Cause:** The cleanup at the end of the script ran `admin.auth.admin.delete_user(user_id)` — but if the previous run crashed before cleanup, the user persisted.

**Fix — Part 1:** Delete manually before re-running:
```python
# Manual cleanup (run once to clear the stuck user)
admin.auth.admin.delete_user("bb4d7214-...")
```

But this also failed: **"Database error deleting user"** — because the user had rows in other tables (FK constraints).

**Fix — Part 2:** Clean up dependent data first, then delete the user:
```python
# In the cleanup section of the test script:
for tbl, col in [
    ("subscriptions",    "manager_id"),
    ("manager_profiles", "user_id"),
    ("properties_list",  "manager_id"),
]:
    admin.table(tbl).delete().eq(col, user_id).execute()

admin.auth.admin.delete_user(user_id)
```

**Fix — Part 3:** The auto-cleanup loop at the start of the script was using the wrong iteration pattern for `list_users()`. Fixed to:
```python
existing = admin.auth.admin.list_users()
user_list = existing if isinstance(existing, list) else list(existing)
for u in user_list:
    if getattr(u, "email", None) == TEST_EMAIL:
        # clean up dependent tables, then:
        admin.auth.admin.delete_user(u.id)
        break
```

---

### 5.4 `pip.exe` silently fails (exit code 1)

**Symptom:** Running `venv\Scripts\pip.exe install uvicorn` returned exit code 1 with no output.

**Cause:** Unknown — possibly a broken pip wrapper script in this particular venv on Python 3.13.

**Fix:** Use `python.exe -m pip install ...` instead of calling `pip.exe` directly. This always worked.

---

### 5.5 RLS Policy Violation — the main bug  ⚠️

**Symptom (first ~40 tests all failed):**
```json
{
  "errors": [
    "Row 2: {'message': 'new row violates row-level security policy for table \"properties_list\"', 'code': '42501'}"
  ]
}
```
All properties import tests failed; all tenant tests cascaded to fail because no flats were ever created.

**Diagnosis:**

Step 1 — Confirm the table has `manager_id`:
```python
db.table("properties_list").select("*").limit(1).execute()
# → cols: ['id', 'name', 'description', 'address', 'image_url', 'property_type_id', 'created_at', 'manager_id']
```

Step 2 — Confirm inserting WITH `manager_id` explicitly works:
```python
anon.postgrest.auth(token)
anon.table("properties_list").insert({"name": "Test", "manager_id": uid}).execute()
# → success ✓
```

Step 3 — Confirm inserting WITHOUT `manager_id` fails:
```python
anon.table("properties_list").insert({"name": "Test"}).execute()
# → 42501 RLS error ✗
```

**Root cause:** Supabase RLS `WITH CHECK` policy for `properties_list` requires `manager_id = auth.uid()`. The table does NOT have a database-level `DEFAULT auth.uid()` on the column (even though the normal `property_groups` route works for the real user, probably because that user was created via the normal signup trigger which sets things up differently).

**Why the existing `property_groups` route works for the real user but the import route didn't for the test user:** The real user went through the Supabase signup flow which triggers internal setup; the test user was created via admin API. Either way, the import route was missing `manager_id` — it just happened to not be caught before.

**Fix in `import_routes.py`:**
```python
# Before (broken):
payload: dict = {"name": prop_name}

# After (fixed):
payload: dict = {
    "name": prop_name,
    "manager_id": user["sub"],  # required by RLS policy
}
```

`user["sub"]` is the authenticated user's UUID, available from the `require_active_subscription` dependency which already validates the JWT and returns the payload.

**After the fix:** All 82 assertions passed.

---

## 6. The 25 Test Cases

### Properties Import (`POST /import/properties`)

| ID | Scenario | What it verifies |
|----|----------|-----------------|
| T1 | Happy path | 3 rows → 1 property, 2 buildings, 3 flats created; 0 skipped, 0 errors |
| T2 | Dedup within a CSV | Same property + building repeated on 4 rows → only 1 property, 2 buildings created |
| T3 | Re-import same CSV | All 3 flats already exist → 0 created, 3 skipped, 0 errors |
| T4 | Missing required **column** (`flat_number` absent) | Returns HTTP 400 with error message naming the missing column |
| T5 | Missing required **value** (empty `flat_number` in row 3) | 2 flats created, 1 error for the bad row |
| T6 | Optional numeric fields | `floor_number`, `bedrooms`, `bathrooms` all stored correctly |
| T7 | Invalid numeric value (`bedrooms="studio"`) | Flat created successfully; bad field silently dropped (no crash) |
| T8 | Case-insensitive dedup | `"sunrise towers"` matches existing `"Sunrise Towers"` → 0 new properties |
| T9 | Extra unknown columns | Columns not in the schema are silently ignored |
| T10 | Minimal CSV (required columns only) | Works without any optional columns present |
| T11 | BOM-prefixed CSV (Excel utf-8-sig export) | `\xef\xbb\xbf` BOM stripped, import succeeds normally |
| T12 | Empty CSV (header row only) | Returns 200 with all counts = 0, no errors |
| T13 | Mixed batch (2 valid + 1 missing `property_name`) | 2 flats created, 1 error; processing continues past the bad row |

### Tenants Import (`POST /import/tenants`)

| ID | Scenario | What it verifies |
|----|----------|-----------------|
| T14 | Happy path | 2 tenants linked to existing flats, optional fields stored |
| T15 | Already-occupied flat | Tenant not overwritten; row in `skipped` list (not `errors`) |
| T16 | Flat not found | Row logged to `errors` list; processing continues |
| T17 | Missing required **column** (`phone` absent) | Returns HTTP 400 with error message naming the missing column |
| T18 | Missing required **value** (empty `name` in row 2) | 2 created, 1 error; other rows succeed |
| T19 | No `rent_amount` | Tenant created without a rent record; no crash |
| T20 | `rent_amount` provided | Tenant created AND a `rents` table row is inserted with `is_active=True` |
| T21 | Case-insensitive flat lookup | `"a-102"` in CSV matches flat stored as `"A-102"` |
| T22 | All optional fields | `email`, `lease_start_date`, `lease_end_date`, `rent_status`, `manager_notes` all stored |
| T23 | Mixed batch | 1 valid + 1 flat-not-found + 1 occupied → 1 created, 1 skipped, 1 error |
| T24 | Empty tenants CSV | Returns 200 with `created=0`, no errors |
| T25 | No auth token | Returns 401 or 403 (not 200) |

### Final result
```
82/82 passed   0 failed
```

---

## 7. What the Test Script Does (Full Flow)

```
test_import.py
│
├── Setup
│   ├── Scan list_users() → delete leftover csv_import_test@example.com if found
│   │   (delete dependent rows in subscriptions, manager_profiles, properties_list first)
│   ├── admin.auth.admin.create_user() → new user with email_confirm=True
│   ├── admin.table("subscriptions").insert() → gives user an active subscription
│   ├── anon.auth.sign_in_with_password() → get access token (JWT)
│   └── Poll GET / → wait for backend to be ready
│
├── T1–T13  POST /import/properties
│   └── Each test: post_csv(endpoint, csv_string, token) → assert status + counts
│
├── T14–T24  POST /import/tenants
│   └── Tests depend on flats created in T1–T13 (same test user's data)
│
├── T25  Auth check (no token → 401/403)
│
└── Cleanup
    ├── delete from subscriptions where manager_id = user_id
    ├── delete from manager_profiles where user_id = user_id
    ├── delete from properties_list where manager_id = user_id
    └── admin.auth.admin.delete_user(user_id)
```

### Helper functions
```python
post_csv(endpoint, csv_text, token)        # POST a CSV string
post_csv_bytes(endpoint, csv_bytes, token) # POST raw bytes (for BOM test)
check(name, condition, detail)             # assertion that increments pass/fail count
```

---

## 8. Key Commands Reference

### Start backend (after installing deps)
```powershell
Start-Process `
  -FilePath "backend\venv\Scripts\python.exe" `
  -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" `
  -WorkingDirectory "backend\" `
  -WindowStyle Normal
```

### Kill all Python processes (to reload backend after code changes)
```powershell
Get-Process | Where-Object { $_.ProcessName -like "python*" } | ForEach-Object { Stop-Process -Id $_.Id -Force }
```

### Check backend is alive
```bash
curl -s http://localhost:8000/
# → {"status":"Backend running"}
```

### Install missing venv packages
```bash
# Always use python.exe -m pip, NOT pip.exe directly (broken on this machine)
backend/venv/Scripts/python.exe -m pip install <package>
```

### Run the test suite
```bash
cd "C:\Users\BIT\Coding\Tenant_management_MVP"
backend/venv/Scripts/python.exe test_import.py
```

### Manual cleanup of stuck test user (if test_import.py crashes before cleanup)
```python
from supabase import create_client
admin = create_client(SUPABASE_URL, SERVICE_KEY)
uid = "the-user-uuid-here"

for tbl, col in [
    ("subscriptions",    "manager_id"),
    ("manager_profiles", "user_id"),
    ("properties_list",  "manager_id"),
]:
    admin.table(tbl).delete().eq(col, uid).execute()

admin.auth.admin.delete_user(uid)
```

---

## 9. Files Changed / Created This Session

| File | Change |
|------|--------|
| `backend/app/routes/import_routes.py` | **Bug fix:** added `"manager_id": user["sub"]` to `properties_list` INSERT payload |
| `test_import.py` | **New:** self-contained test suite (25 test cases, creates/destroys a temp Supabase user) |
| `SESSION_LOG_CSV_IMPORT.md` | **New:** this file |

---

## 10. Lessons / Gotchas for Future Sessions

1. **`pip.exe` is broken in this venv** — always use `python.exe -m pip install`.

2. **Always install all `requirements.txt` deps when setting up the venv for the first time:**
   ```bash
   python.exe -m pip install -r requirements.txt
   ```

3. **RLS INSERT policies in Supabase don't auto-set `manager_id`** — any route that inserts into `properties_list` must explicitly set `"manager_id": user["sub"]`. The `buildings`, `flats`, and `tenants` tables do NOT have a `manager_id` column, so only `properties_list` needs this.

4. **Deleting a Supabase auth user fails if FK-linked rows exist** — always delete dependent table rows first, then delete the user.

5. **Windows console encoding** — any Python script printing Unicode must either set UTF-8 stdout or use ASCII-only output characters.

6. **Backend restart after code changes** — `Start-Process` on Windows launches a truly separate process. To reload code, kill all Python processes and restart. Just re-running the start command will fail with "port already in use".

7. **Admin-created test users vs. normal signup** — users created via `admin.auth.admin.create_user()` bypass the signup trigger that sets up `manager_id` defaults. Always test auth-gated features with a full token obtained from `sign_in_with_password()`, not via a manually crafted JWT.
