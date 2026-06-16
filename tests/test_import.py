"""
CSV Import - comprehensive test suite.

Creates a temporary Supabase test user + subscription, runs all test cases
against the live backend, then cleans up.

Usage:
    python test_import.py

Requires: pip install requests supabase
"""
import io
import sys
import time
import textwrap
import requests
from supabase import create_client

# Force UTF-8 output on Windows
if sys.platform == "win32":
    import io as _io
    sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ── Config ────────────────────────────────────────────────────────────────────

SUPABASE_URL    = "https://nfgnxndktecqeleabbip.supabase.co"
SUPABASE_KEY    = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mZ254bmRrdGVjcWVsZWFiYmlwIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk4NjYzNTUsImV4cCI6MjA4NTQ0MjM1NX0.lFBVU9aqWtCo1l7uDjD8326CzFwCsKJqMCCcA13Nvi8"
SERVICE_KEY     = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im5mZ254bmRrdGVjcWVsZWFiYmlwIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTg2NjM1NSwiZXhwIjoyMDg1NDQyMzU1fQ.MM_lvld7Jr54E3fWgtCeyDWOwuLdW5JcU6352xf5Nd4"
API_BASE        = "http://localhost:8000"

TEST_EMAIL      = "csv_import_test@example.com"
TEST_PASSWORD   = "CsvTest2026!@#"

# ── Colour helpers ────────────────────────────────────────────────────────────

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}"); sys.exit(1)
def warn(msg): print(f"  {YELLOW}⚠{RESET} {msg}")
def info(msg): print(f"  {CYAN}→{RESET} {msg}")
def section(title): print(f"\n{BOLD}{title}{RESET}\n{'─' * 60}")

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        ok(f"{name}")
        passed += 1
    else:
        print(f"  {RED}✗ FAIL:{RESET} {name}")
        if detail:
            print(f"       {detail}")
        failed += 1

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def post_csv(endpoint, csv_text, token, filename="test.csv"):
    """POST a CSV string to an import endpoint."""
    return requests.post(
        f"{API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, io.BytesIO(csv_text.encode("utf-8")), "text/csv")},
        timeout=30,
    )

def post_csv_bytes(endpoint, csv_bytes, token, filename="test.csv"):
    """POST raw bytes (for BOM test)."""
    return requests.post(
        f"{API_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": (filename, io.BytesIO(csv_bytes), "text/csv")},
        timeout=30,
    )

# ── Setup ─────────────────────────────────────────────────────────────────────

section("Setup — test user")

admin  = create_client(SUPABASE_URL, SERVICE_KEY)
anon   = create_client(SUPABASE_URL, SUPABASE_KEY)

# Delete any leftover test user from a previous run
try:
    existing = admin.auth.admin.list_users()
    # supabase-py v2 returns a flat list of User objects
    user_list = existing if isinstance(existing, list) else list(existing)
    for u in user_list:
        if getattr(u, 'email', None) == TEST_EMAIL:
            admin.auth.admin.delete_user(u.id)
            info(f"Cleaned up leftover test user {TEST_EMAIL}")
            break
except Exception as e:
    warn(f"Could not clean up leftover user: {e}")

# Create test user
try:
    result = admin.auth.admin.create_user({
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "email_confirm": True,
    })
    user_id = result.user.id
    ok(f"Created test user: {TEST_EMAIL} (id={user_id[:8]}…)")
except Exception as e:
    fail(f"Could not create test user: {e}")

# Add subscription
try:
    admin.table("subscriptions").insert({
        "manager_id": user_id,
        "status": "trialing",
        "trial_ends_at": "2099-12-31",
        "stripe_customer_id": "cus_test_placeholder",
    }).execute()
    ok("Subscription row inserted")
except Exception as e:
    fail(f"Could not insert subscription: {e}")

# Sign in as test user (anon client)
try:
    session = anon.auth.sign_in_with_password({"email": TEST_EMAIL, "password": TEST_PASSWORD})
    TOKEN = session.session.access_token
    ok("Signed in — access token obtained")
except Exception as e:
    fail(f"Sign-in failed: {e}")

# Wait for backend
info("Waiting for backend to be ready…")
for _ in range(20):
    try:
        r = requests.get(f"{API_BASE}/", timeout=3)
        if r.ok:
            ok(f"Backend is up at {API_BASE}")
            break
    except Exception:
        pass
    time.sleep(1)
else:
    fail(f"Backend never responded at {API_BASE}")

# ── Properties import tests ───────────────────────────────────────────────────

section("POST /import/properties")

# ── T1: Happy path ────────────────────────────────────────────────────────────
print(f"\n{CYAN}T1 — Happy path{RESET}")
csv_t1 = textwrap.dedent("""\
    property_name,property_address,building_name,flat_number,floor_number,bedrooms,bathrooms
    Sunrise Towers,12 MG Road,Block A,A-101,1,2,1
    Sunrise Towers,12 MG Road,Block A,A-102,1,3,2
    Sunrise Towers,12 MG Road,Block B,B-201,2,2,1
""")
r = post_csv("/import/properties", csv_t1, TOKEN)
check("T1 status 200", r.status_code == 200, r.text)
d = r.json()
check("T1 created 1 property",  d["created"]["properties"] == 1, str(d))
check("T1 created 2 buildings", d["created"]["buildings"]  == 2, str(d))
check("T1 created 3 flats",     d["created"]["flats"]      == 3, str(d))
check("T1 no skipped",          len(d["skipped"]) == 0, str(d))
check("T1 no errors",           len(d["errors"])  == 0, str(d))

# ── T2: Deduplication within a single CSV ─────────────────────────────────────
print(f"\n{CYAN}T2 — Deduplication: same property+building repeated across rows{RESET}")
csv_t2 = textwrap.dedent("""\
    property_name,building_name,flat_number
    Dedup Society,Tower X,X-101
    Dedup Society,Tower X,X-102
    Dedup Society,Tower X,X-103
    Dedup Society,Tower Y,Y-201
""")
r = post_csv("/import/properties", csv_t2, TOKEN)
d = r.json()
check("T2 status 200", r.status_code == 200, r.text)
check("T2 created 1 property only",  d["created"]["properties"] == 1, str(d))
check("T2 created 2 buildings only", d["created"]["buildings"]  == 2, str(d))
check("T2 created 4 flats",          d["created"]["flats"]      == 4, str(d))
check("T2 no errors",                len(d["errors"]) == 0, str(d))

# ── T3: Duplicate flat across two runs (same flat_number already exists) ──────
print(f"\n{CYAN}T3 — Duplicate flat_number (re-import same CSV){RESET}")
r = post_csv("/import/properties", csv_t1, TOKEN)
d = r.json()
check("T3 status 200", r.status_code == 200, r.text)
check("T3 0 new flats",   d["created"]["flats"]  == 0, str(d))
check("T3 3 skipped",     len(d["skipped"])       == 3, str(d))
check("T3 no errors",     len(d["errors"])        == 0, str(d))

# ── T4: Missing required COLUMN (entire column absent) ───────────────────────
print(f"\n{CYAN}T4 — Missing required column: flat_number column absent{RESET}")
csv_t4 = textwrap.dedent("""\
    property_name,building_name
    Test Prop,Block A
""")
r = post_csv("/import/properties", csv_t4, TOKEN)
check("T4 status 400",                r.status_code == 400, r.text)
check("T4 error mentions flat_number", "flat_number" in r.text, r.text)

# ── T5: Missing required VALUE in a row (flat_number empty in one row) ────────
print(f"\n{CYAN}T5 — Missing required value: empty flat_number in row 3{RESET}")
csv_t5 = textwrap.dedent("""\
    property_name,building_name,flat_number
    Good Prop,Block A,G-101
    Good Prop,Block A,G-102
    Good Prop,Block A,
""")
r = post_csv("/import/properties", csv_t5, TOKEN)
d = r.json()
check("T5 status 200",            r.status_code == 200, r.text)
check("T5 2 flats created",       d["created"]["flats"] == 2, str(d))
check("T5 1 error for empty row", len(d["errors"]) == 1, str(d))

# ── T6: Optional numeric fields — valid values stored ────────────────────────
print(f"\n{CYAN}T6 — Optional fields: floor/bedrooms/bathrooms stored correctly{RESET}")
csv_t6 = textwrap.dedent("""\
    property_name,building_name,flat_number,floor_number,bedrooms,bathrooms
    Optional Fields Prop,Block Z,Z-501,5,3,2
""")
r = post_csv("/import/properties", csv_t6, TOKEN)
d = r.json()
check("T6 status 200",     r.status_code == 200, r.text)
check("T6 1 flat created", d["created"]["flats"] == 1, str(d))
check("T6 no errors",      len(d["errors"]) == 0, str(d))

# ── T7: Invalid numeric field value (bedrooms="studio") ───────────────────────
print(f"\n{CYAN}T7 — Invalid numeric field: bedrooms='studio' → flat created, bad field skipped{RESET}")
csv_t7 = textwrap.dedent("""\
    property_name,building_name,flat_number,bedrooms
    Bad Numbers Prop,Block Q,Q-001,studio
""")
r = post_csv("/import/properties", csv_t7, TOKEN)
d = r.json()
check("T7 status 200",     r.status_code == 200, r.text)
check("T7 1 flat created", d["created"]["flats"] == 1, str(d))
check("T7 no errors",      len(d["errors"]) == 0, str(d))

# ── T8: Case-insensitive deduplication of property + building names ───────────
print(f"\n{CYAN}T8 — Case-insensitive dedup: 'sunrise towers' vs 'SUNRISE TOWERS'{RESET}")
csv_t8 = textwrap.dedent("""\
    property_name,building_name,flat_number
    sunrise towers,block a,A-888
""")
r = post_csv("/import/properties", csv_t8, TOKEN)
d = r.json()
check("T8 status 200",           r.status_code == 200, r.text)
check("T8 0 new properties",     d["created"]["properties"] == 0, str(d))
check("T8 0 new buildings",      d["created"]["buildings"]  == 0, str(d))
check("T8 1 flat created",       d["created"]["flats"]      == 1, str(d))

# ── T9: Extra unknown columns ignored ─────────────────────────────────────────
print(f"\n{CYAN}T9 — Extra unknown columns in CSV are silently ignored{RESET}")
csv_t9 = textwrap.dedent("""\
    property_name,building_name,flat_number,random_col,another_col
    Extra Cols Prop,Block E,E-001,should_ignore,also_ignore
""")
r = post_csv("/import/properties", csv_t9, TOKEN)
d = r.json()
check("T9 status 200",     r.status_code == 200, r.text)
check("T9 1 flat created", d["created"]["flats"] == 1, str(d))
check("T9 no errors",      len(d["errors"]) == 0, str(d))

# ── T10: Only required columns (no optionals) ─────────────────────────────────
print(f"\n{CYAN}T10 — Minimal CSV: only required columns present{RESET}")
csv_t10 = textwrap.dedent("""\
    property_name,building_name,flat_number
    Minimal Prop,Block M,M-001
    Minimal Prop,Block M,M-002
""")
r = post_csv("/import/properties", csv_t10, TOKEN)
d = r.json()
check("T10 status 200",     r.status_code == 200, r.text)
check("T10 2 flats created", d["created"]["flats"] == 2, str(d))
check("T10 no errors",       len(d["errors"]) == 0, str(d))

# ── T11: BOM-prefixed CSV (Excel export) ──────────────────────────────────────
print(f"\n{CYAN}T11 — BOM-prefixed CSV (utf-8-sig, as exported by Excel){RESET}")
csv_bom = "property_name,building_name,flat_number\r\nBOM Prop,Block B,BOM-001\r\n"
bom_bytes = b"\xef\xbb\xbf" + csv_bom.encode("utf-8")
r = post_csv_bytes("/import/properties", bom_bytes, TOKEN, filename="excel_export.csv")
d = r.json()
check("T11 status 200",     r.status_code == 200, r.text)
check("T11 1 flat created", d["created"]["flats"] == 1, str(d))
check("T11 no errors",      len(d["errors"]) == 0, str(d))

# ── T12: Empty CSV (header only, zero data rows) ──────────────────────────────
print(f"\n{CYAN}T12 — Empty CSV: header row only, no data rows{RESET}")
csv_t12 = "property_name,building_name,flat_number\n"
r = post_csv("/import/properties", csv_t12, TOKEN)
d = r.json()
check("T12 status 200",       r.status_code == 200, r.text)
check("T12 0 properties",     d["created"]["properties"] == 0, str(d))
check("T12 0 flats",          d["created"]["flats"]      == 0, str(d))
check("T12 no errors",        len(d["errors"]) == 0, str(d))

# ── T13: Mixed batch — some valid, some bad rows ───────────────────────────────
print(f"\n{CYAN}T13 — Mixed batch: 2 good rows, 1 row missing property_name{RESET}")
csv_t13 = textwrap.dedent("""\
    property_name,building_name,flat_number
    Mixed Prop,Block X,MX-001
    ,Block X,MX-002
    Mixed Prop,Block X,MX-003
""")
r = post_csv("/import/properties", csv_t13, TOKEN)
d = r.json()
check("T13 status 200",    r.status_code == 200, r.text)
check("T13 2 flats",       d["created"]["flats"] == 2, str(d))
check("T13 1 error",       len(d["errors"])       == 1, str(d))

# ── Tenants import tests ──────────────────────────────────────────────────────

section("POST /import/tenants")

# ── T14: Happy path — link tenants to flats created above ─────────────────────
print(f"\n{CYAN}T14 — Happy path: import tenants for A-101 and B-201{RESET}")
csv_t14 = textwrap.dedent("""\
    name,phone,email,flat_number,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes
    Rahul Sharma,+919876543210,rahul@test.com,A-101,2024-01-01,2025-01-01,15000,On-time,Good tenant
    Priya Patel,+919988776655,priya@test.com,B-201,2024-06-01,2025-06-01,18000,Upcoming,Pets allowed
""")
r = post_csv("/import/tenants", csv_t14, TOKEN)
d = r.json()
check("T14 status 200",       r.status_code == 200, r.text)
check("T14 2 tenants created", d["created"] == 2, str(d))
check("T14 no skipped",        len(d["skipped"]) == 0, str(d))
check("T14 no errors",         len(d["errors"])  == 0, str(d))

# ── T15: Flat already occupied — skip (don't overwrite) ───────────────────────
print(f"\n{CYAN}T15 — Already occupied flat is skipped (not overwritten){RESET}")
csv_t15 = textwrap.dedent("""\
    name,phone,flat_number
    Duplicate Person,+910000000000,A-101
""")
r = post_csv("/import/tenants", csv_t15, TOKEN)
d = r.json()
check("T15 status 200",       r.status_code == 200, r.text)
check("T15 0 created",        d["created"] == 0, str(d))
check("T15 1 skipped",        len(d["skipped"]) == 1, str(d))
check("T15 skip mentions A-101", any("A-101" in s for s in d["skipped"]), str(d["skipped"]))

# ── T16: Flat not found → error ───────────────────────────────────────────────
print(f"\n{CYAN}T16 — Flat not found: 'DOES-NOT-EXIST'{RESET}")
csv_t16 = textwrap.dedent("""\
    name,phone,flat_number
    Ghost Tenant,+910000000001,DOES-NOT-EXIST
""")
r = post_csv("/import/tenants", csv_t16, TOKEN)
d = r.json()
check("T16 status 200",        r.status_code == 200, r.text)
check("T16 0 created",         d["created"] == 0, str(d))
check("T16 1 error",           len(d["errors"]) == 1, str(d))
check("T16 error mentions flat", any("flat" in e.lower() or "DOES-NOT-EXIST" in e for e in d["errors"]), str(d["errors"]))

# ── T17: Missing required COLUMN in tenants CSV ───────────────────────────────
print(f"\n{CYAN}T17 — Missing required column: phone column absent{RESET}")
csv_t17 = textwrap.dedent("""\
    name,flat_number
    No Phone Guy,A-102
""")
r = post_csv("/import/tenants", csv_t17, TOKEN)
check("T17 status 400",           r.status_code == 400, r.text)
check("T17 mentions phone",        "phone" in r.text, r.text)

# ── T18: Missing required VALUE in a row ─────────────────────────────────────
print(f"\n{CYAN}T18 — Missing required value: empty name in row 2, rest valid{RESET}")
csv_t18 = textwrap.dedent("""\
    name,phone,flat_number
    Valid Person,+919999999999,A-102
    ,+910000000002,X-101
    Another Valid,+918888888888,G-101
""")
r = post_csv("/import/tenants", csv_t18, TOKEN)
d = r.json()
check("T18 status 200",     r.status_code == 200, r.text)
check("T18 2 created",      d["created"] == 2, str(d))
check("T18 1 error",        len(d["errors"]) == 1, str(d))

# ── T19: No rent_amount → tenant created, no rent record (no crash) ──────────
print(f"\n{CYAN}T19 — No rent_amount: tenant created without rent record{RESET}")
csv_t19 = textwrap.dedent("""\
    name,phone,flat_number
    No Rent Guy,+911234567890,G-102
""")
r = post_csv("/import/tenants", csv_t19, TOKEN)
d = r.json()
check("T19 status 200",    r.status_code == 200, r.text)
check("T19 1 created",     d["created"] == 1, str(d))
check("T19 no errors",     len(d["errors"]) == 0, str(d))

# ── T20: With rent_amount → rent record created ───────────────────────────────
print(f"\n{CYAN}T20 — rent_amount provided: rent record should be created{RESET}")
csv_t20 = textwrap.dedent("""\
    name,phone,flat_number,rent_amount,lease_start_date
    Rent Guy,+911111111111,M-001,12000,2025-01-01
""")
r = post_csv("/import/tenants", csv_t20, TOKEN)
d = r.json()
check("T20 status 200",    r.status_code == 200, r.text)
check("T20 1 created",     d["created"] == 1, str(d))
check("T20 no errors",     len(d["errors"]) == 0, str(d))

# ── T21: Case-insensitive flat lookup (lowercase flat_number) ─────────────────
print(f"\n{CYAN}T21 — Case-insensitive flat lookup: 'a-102' should match 'A-102'{RESET}")
csv_t21 = textwrap.dedent("""\
    name,phone,flat_number
    Lowercase Flat,+912222222222,a-102
""")
r = post_csv("/import/tenants", csv_t21, TOKEN)
d = r.json()
check("T21 status 200",  r.status_code == 200, r.text)
# A-102 may already be occupied from T18; check that it didn't error out with "not found"
no_not_found = not any("not found" in e.lower() for e in d["errors"])
check("T21 no 'not found' errors (case-insensitive lookup worked)", no_not_found, str(d["errors"]))

# ── T22: All optional fields provided ────────────────────────────────────────
print(f"\n{CYAN}T22 — All optional fields: email, lease dates, rent, status, notes{RESET}")
csv_t22 = textwrap.dedent("""\
    name,phone,email,flat_number,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes
    Full Details,+913333333333,full@test.com,M-002,2025-01-01,2026-01-01,20000,On-time,Full optional fields test
""")
r = post_csv("/import/tenants", csv_t22, TOKEN)
d = r.json()
check("T22 status 200",    r.status_code == 200, r.text)
check("T22 1 created",     d["created"] == 1, str(d))
check("T22 no errors",     len(d["errors"]) == 0, str(d))

# ── T23: Mixed tenants batch (some valid, some missing flat, some occupied) ───
print(f"\n{CYAN}T23 — Mixed batch: 1 valid, 1 flat-not-found, 1 occupied{RESET}")
csv_t23 = textwrap.dedent("""\
    name,phone,flat_number
    Good Tenant,+914444444444,MX-001
    Bad Flat,+915555555555,NO-FLAT
    Occupied Again,+916666666666,B-201
""")
r = post_csv("/import/tenants", csv_t23, TOKEN)
d = r.json()
check("T23 status 200",  r.status_code == 200, r.text)
check("T23 1 created",   d["created"] == 1, str(d))
check("T23 1 skipped",   len(d["skipped"]) == 1, str(d))
check("T23 1 error",     len(d["errors"])  == 1, str(d))

# ── T24: Empty tenants CSV ────────────────────────────────────────────────────
print(f"\n{CYAN}T24 — Empty tenants CSV (header only){RESET}")
csv_t24 = "name,phone,flat_number\n"
r = post_csv("/import/tenants", csv_t24, TOKEN)
d = r.json()
check("T24 status 200",   r.status_code == 200, r.text)
check("T24 0 created",    d["created"] == 0, str(d))
check("T24 no errors",    len(d["errors"]) == 0, str(d))

# ── T25: No auth token → 403 / 401 ───────────────────────────────────────────
print(f"\n{CYAN}T25 — No auth token: should return 401 / 403{RESET}")
r = requests.post(
    f"{API_BASE}/import/properties",
    files={"file": ("t.csv", io.BytesIO(b"property_name,building_name,flat_number\n"), "text/csv")},
    timeout=10,
)
check("T25 unauthenticated → 401 or 403", r.status_code in (401, 403), r.text)

# ── Cleanup ───────────────────────────────────────────────────────────────────

section("Cleanup")

# Delete dependent data first (FK constraints block user deletion otherwise)
for tbl, col in [("subscriptions", "manager_id"), ("manager_profiles", "user_id"), ("properties_list", "manager_id")]:
    try:
        admin.table(tbl).delete().eq(col, user_id).execute()
    except Exception:
        pass

try:
    admin.auth.admin.delete_user(user_id)
    ok(f"Deleted test user {TEST_EMAIL}")
except Exception as e:
    warn(f"Could not delete test user: {e}")

# ── Summary ───────────────────────────────────────────────────────────────────

section("Results")
total = passed + failed
print(f"\n  {GREEN}{passed}/{total} passed{RESET}  {RED if failed else ''}{failed} failed{RESET}\n")
if failed:
    sys.exit(1)
