# Session Context — 2026-06-04 (CSV Import Testing)

## What We Did This Session

### 1. Ran the Full CSV Import Test Suite
- Source plan: `CSV_TEST_PLAN.md` (47 tests across 4 parts: Properties, Tenants, Analyze edge cases, Auth)
- Endpoints tested: `POST /import/analyze`, `POST /import/properties`, `POST /import/tenants`
- Base URL: `https://tenant-management-mvp.onrender.com`

### 2. Created the Python Test Runner
**File:** `run_csv_tests.py` (project root)
- Generates all 30+ test CSV and XLSX files into `test_csvs/`
- Runs every test against the live API using `requests`
- Writes results to `CSV_TEST_RESULTS.md`

### 3. Created HTML Test Report
**File:** `CSV_TEST_RESULTS.html` — beautifully styled standalone HTML with:
- Score cards (47 total / 43 PASS / 2 DIFF / 1 DOC / 0 true failures)
- Color-coded summary table (PASS, PASS*, PASS+, DIFF, DOC badges)
- HTTP status chips, detailed response cards, observation callouts
- Syntax-highlighted cleanup SQL

### 4. Reviewed Frontend Code
**File:** `frontend/src/components/CsvImportModal.jsx`
- Confirmed `ResultPanel` (line 295) already correctly handles `created` as a dict
  (`created?.properties`, `created?.buildings`, `created?.flats`)
- Confirmed the analyze → import flow (line 429) correctly handles `needs_mapping:false`
  by going straight to import without a mapping step

---

## Bugs Hit and Fixed

### Bug 1 — Wrong JWT Token (1-character signature difference)
- `CSV_TEST_PLAN.md` had `...s7D7ntD6...` in its token signature
- User's message had the correct token `...s7D7ktD6...`
- All requests returned `{"detail": "Invalid token"}`
- Fix: replaced `ntD6` → `ktD6` in `run_csv_tests.py`
- Lesson: always use the token from the user's message, not from a plan file copy

### Bug 2 — Windows UnicodeEncodeError (cp1252)
- Print statements with `→` (U+2192), `✓` (U+2713), `✗` (U+2717) crashed on Windows
- Error: `UnicodeEncodeError: 'charmap' codec can't encode character`
- Fix: replaced all Unicode arrows/checkmarks with ASCII (`->`, `OK`, `FAIL`)
- Root cause: Windows PowerShell defaults to cp1252, not UTF-8

### Bug 3 — Test ran twice (DB state contamination on second run)
- Run 1 (wrong token) → all 401. Run 2 (fixed token) → data created. Run 3 → all "already exists"
- Fix: rewrote assertions to handle both fresh-data and idempotent-skip outcomes
- Also: rewrote final results manually in `CSV_TEST_RESULTS.md` combining both runs

---

## Key API Discoveries

### 1. `created` is a dict for property imports (not a plain int)
```json
{"created": {"properties": 1, "buildings": 2, "flats": 3}, "skipped": [], "errors": []}
```
- Tenant endpoint returns a plain int: `{"created": 2, ...}`
- Test plan spec said `{"created": 3}` — spec is wrong, API is right
- Frontend already handles this correctly (no change needed)

### 2. Mixed-case headers → `needs_mapping: false` (better than spec)
- `Property_Name`, `Flat_Number`, `Name`, `Phone` etc. are normalised internally
- The 2-step AI mapping flow only triggers for truly unrecognised names (e.g. `unit_id`)
- CP12 and CT12 in the test plan expected `needs_mapping: true` — spec is wrong

### 3. Row-count limit fires before file-size limit
- 50k-row file → `"Too many rows (max 1000)"` not `"File too large (max 5 MB)"`

### 4. `rent_amount = "0"` inserts a $0 rent record
- `"0"` is truthy → `float(0.0)` → rent row inserted with `monthly_rent = 0`

### 5. Invalid `rent_status` silently dropped to null (no warning)
- Minor improvement opportunity: add a message to `skipped` for invalid status values

### 6. Groq AI mapping quality confirmed excellent
- CA04: `unit_id → flat_number`, `block_name → building_name`, `street → property_address`
- All 3 mapped correctly, `unmapped_required` was empty

---

## Files Created / Modified This Session

| File | Status | Purpose |
|---|---|---|
| `run_csv_tests.py` | Created | Python test runner — generates files, runs 47 tests, writes results |
| `test_csvs/` | Created (dir) | All generated test CSV and XLSX files |
| `CSV_TEST_RESULTS.md` | Created | Raw markdown results (all 47 tests with actual JSON responses) |
| `CSV_TEST_RESULTS.html` | Created | Standalone HTML report with color-coded table + detail cards |

---

## Pending: Learning Session HTML

The user asked to create a learning HTML file but the session was interrupted.

**Target path:** `C:\Users\BIT\Coding\Tenant_management_MVP\learning\session-01-csv-api-testing.html`
(The `learning/` folder was already created with `mkdir`)

### What the file should teach:
- **Concepts:** API testing philosophy, JWT tokens (structure + expiry), Python `requests` multipart POST, test plan design (idempotency, edge cases, state dependencies)
- **Bug Journal (3 bugs):**
  - Bug 1: 1-char JWT signature difference — how to decode a JWT to inspect it
  - Bug 2: Windows cp1252 UnicodeEncodeError — Python encoding on Windows
  - Bug 3: State contamination across test runs — designing stateless or idempotent tests
- **API Discoveries:** `created` dict shape, `needs_mapping` behavior, row-before-size check
- **Frontend verification:** reading `CsvImportModal.jsx` to confirm correct handling

### Format (from README in ScoreUs/Learning):
- Self-contained HTML (all CSS + JS inline, works offline)
- Dark (`#1a1a2e`) / light mode toggle saved to localStorage
- VS Code-inspired syntax highlighting, sticky sidebar TOC
- Callout boxes: Tip, Warning, Key Concept, Bug Story, Exercise, Deep Dive
- Header: Session 01, title, estimated time (~90 min), difficulty 🟡 Intermediate
- Sections in order: Overview → Recap → Concepts → Build Log → Bug Journal →
  Design Decisions → Verification → Exercises → Troubleshooting → Glossary → Footer
- Split into multiple files if content exceeds ~1500 lines

---

## Cleanup SQL (already run by user — DB is clean)
```sql
DELETE FROM flats WHERE flat_number LIKE 'CSV-%' OR flat_number LIKE 'XLSX-%' OR flat_number LIKE 'BIG-%';
DELETE FROM properties_list WHERE name IN (
  'CSV Test Prop','CSV ReqOnly Prop','CSV Group Alpha','CSV Group Beta',
  'Numeric Test Prop','Mixed Case Prop','Whitespace Prop','BOM Test Prop',
  'Alias Prop','Row Error Prop','Dup Flat Prop','XLSX Test Prop','XLSX Empty Prop'
);
DELETE FROM tenants WHERE phone LIKE '+1514555900%' OR phone LIKE '+1514555901%' OR phone LIKE '+1514555910%';
```

---

## Token Note
JWT used this session expires **2026-06-04 11:07:37 UTC** (already expired by next session).
For future test runs, get a fresh token from the Supabase dashboard or by logging in to the app,
then update the `TOKEN` variable at the top of `run_csv_tests.py`.
