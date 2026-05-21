# Session Handoff — Voice Agent Test Run

**Session date:** 2026-05-21  
**Next action:** Fix 3 code bugs, then re-run scripts to confirm full green

---

## What Was Done This Session

### 1. Read & understood the test plan
`docs/development_plans/TEST_PLAN_VOICE_AGENTS.md` — full Phase A–E breakdown.

### 2. Started the backend
```bash
cd backend && ./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 3. Ran Phase A — Complaint endpoints
```bash
BASE_URL=http://localhost:8000 FLAT_NUMBER=TEST_2_UNIT TENANT_PHONE=+919998064026 \
bash backend/scripts/test_complaint_endpoints.sh
```
Result: **14 pass / 4 fail**

### 4. Ran Phase B + C — Lease endpoints + Manager CRUD
```bash
BASE_URL=http://localhost:8000 JWT=<testmanager1 token> \
FLAT_UUID=bd23f621-f1ef-427b-8fd7-3c3eb5c7cebf QUERY_TERM=TEST_2_UNIT \
bash backend/scripts/test_leasing_endpoints.sh
```
JWT was obtained via:
```bash
curl -s -X POST "https://nfgnxndktecqeleabbip.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: <SUPABASE_KEY from backend/.env>" \
  -H "Content-Type: application/json" \
  -d '{"email":"testmanager1@gmail.com","password":"testmanager"}'
```
Result: **23 pass / 3 fail / 5 skip**

### 5. Fixed Bug #4 in test script
File: `backend/scripts/test_leasing_endpoints.sh` (~line 96)  
Added `EXISTING_LISTING_UUID="${EXISTING_LISTING_UUID:-}"` after B1 block.  
This was crashing the script at B9 when no listing existed.

### 6. Created full test report
`docs/development_plans/TEST_REPORT_VOICE_AGENTS.md` — complete pass/fail/skip table for all phases run, root-cause analysis for every failure, and a re-run checklist.

---

## What Is Left To Do

### Code Bugs (must fix before re-running)

#### Bug #1 — `verify_phone` uses wrong DB client (CRITICAL)
**File:** `backend/app/routes/flats.py`, line 55  
**Fix:** Change `Depends(get_db)` → `Depends(get_service_db)`  
**Impact:** A1 fails (flat lookup returns empty due to RLS blocking VAPI calls with no JWT). All verify-phone happy-path tests fail until this is fixed.

```python
# Line 55 — change:
async def verify_phone(..., db: Client = Depends(get_db)):
# to:
async def verify_phone(..., db: Client = Depends(get_service_db)):
```

#### Bug #2 — `voice_webhook` uses wrong DB client (CRITICAL)
**File:** `backend/app/routes/voice.py`, line 20  
**Fix:** Change `Depends(get_db)` → `Depends(get_service_db)`  
**Impact:** A6/A8 fail — call_log INSERT is blocked by RLS (`new row violates row-level security policy for table "call_logs"`). Complaint creation never works via webhook until fixed.

```python
# Line 20 — change:
async def voice_webhook(request: Request, background_tasks: BackgroundTasks, db: Client = Depends(get_db)):
# to:
async def voice_webhook(request: Request, background_tasks: BackgroundTasks, db: Client = Depends(get_service_db)):
```

#### Bug #3 — Unicode `✓` crashes webhook on Windows (HIGH)
**File:** `backend/app/routes/voice.py`, line 164  
**Fix:** Replace `✓` with plain ASCII (e.g. `[OK]` or `v`)  
**Impact:** A7 complaint creation silently fails — the print statement raises `UnicodeEncodeError` (cp1252 codec) before the DB write completes, falling into the outer except and returning `{"status":"error"}`.

```python
# Line 164 — change:
print(f"  ✓ User confirmed complaint via submit_complaint")
# to:
print(f"  [OK] User confirmed complaint via submit_complaint")
```
Search the rest of `voice.py` for any other Unicode characters in print statements and replace them too.

---

### Data Setup (needed for full B + C coverage)

#### Missing: lease listing for TEST_2_UNIT
- B1 (`find-listing`) returns `found=false` because no `lease_listings` row exists for this flat.
- B4 (`search`) returns `count=0`.
- B9 (qualified lead with listing_uuid) is skipped entirely.
- **Fix:** Create a listing via the app UI or run C3 with the correct account (see below).

#### Phase C needs the right auth account
- `testmanager1@gmail.com` has zero property groups and zero flats — C3 (create listing) gets 404 "Flat not found" because RLS blocks access to `TEST_2_UNIT` (owned by `curiosus.steel@gmail.com`).
- C4/C5/C6/C9/C10 are all skipped as a cascade.
- **Fix:** Get a JWT for `curiosus.steel@gmail.com` and re-run leasing script with that token.

---

### Re-run Commands (after fixes)

```bash
# Phase A — expect 18/18
BASE_URL=http://localhost:8000 FLAT_NUMBER=TEST_2_UNIT TENANT_PHONE=+919998064026 \
bash backend/scripts/test_complaint_endpoints.sh

# Get JWT for main account
curl -s -X POST "https://nfgnxndktecqeleabbip.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mZ254bmRrdGVjcWVsZWFiYmlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjYzNTUsImV4cCI6MjA4NTQ0MjM1NX0.lFBVU9aqWtCo1l7uDjD8326CzFwCsKJqMCCcA13Nvi8" \
  -H "Content-Type: application/json" \
  -d '{"email":"curiosus.steel@gmail.com","password":"<YOUR_PASSWORD>"}'

# Phase B + C — expect all pass
BASE_URL=http://localhost:8000 JWT=<main account token> \
FLAT_UUID=bd23f621-f1ef-427b-8fd7-3c3eb5c7cebf QUERY_TERM=TEST_2_UNIT \
bash backend/scripts/test_leasing_endpoints.sh
```

---

### Remaining Phases (manual — not automated)

| Phase | What it is | How to run |
|-------|-----------|------------|
| D1 | Check `vapi_provisioning_status` in Supabase | Run SQL in Supabase dashboard: `SELECT id, name, vapi_provisioning_status FROM properties_list;` |
| D2 | New property group triggers VAPI provisioning | Create PG via app UI, wait 10s, check DB |
| D3 | Retry provisioning endpoint | `POST /property-groups/<PG_ID>/provision-voice` with JWT |
| E1–E13 | Manual voice calls | Call `+19734904520` (complaint) or `+15183189117` (lease). Do after all code bugs fixed. |

---

## Key Reference

| Item | Value |
|------|-------|
| Test flat | `TEST_2_UNIT` — uuid `bd23f621-f1ef-427b-8fd7-3c3eb5c7cebf` |
| Tenant phone | `+919998064026` |
| Supabase URL | `https://nfgnxndktecqeleabbip.supabase.co` |
| Supabase anon key | In `backend/.env` → `SUPABASE_KEY` |
| Test report | `docs/development_plans/TEST_REPORT_VOICE_AGENTS.md` |
| Complaint script | `backend/scripts/test_complaint_endpoints.sh` |
| Leasing script | `backend/scripts/test_leasing_endpoints.sh` |
| Backend start cmd | `cd backend && ./venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` |
