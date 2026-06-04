# CSV Import Test Plan — Full Edge Case Coverage
**Date:** 2026-06-04  
**Endpoints:** `POST /import/analyze` + `POST /import/properties` + `POST /import/tenants`

---

## Setup

```bash
BASE="https://tenant-management-mvp.onrender.com"
TOKEN="eyJhbGciOiJFUzI1NiIsImtpZCI6IjE3ODIzMTZkLTllY2MtNDgxZC1iNDc2LTk2NzA3M2JlM2Q4OSIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJodHRwczovL25mZ254bmRrdGVjcWVsZWFiYmlwLnN1cGFiYXNlLmNvL2F1dGgvdjEiLCJzdWIiOiIyOGM0M2M3Ny04YzljLTQ5NmYtOGQxZS0zOWZmYTlkNjE5ZTMiLCJhdWQiOiJhdXRoZW50aWNhdGVkIiwiZXhwIjoxNzgwNTcxMjU3LCJpYXQiOjE3ODA1Njc2NTcsImVtYWlsIjoibGVhZHBpcGVjcm1AZ21haWwuY29tIiwicGhvbmUiOiIiLCJhcHBfbWV0YWRhdGEiOnsicHJvdmlkZXIiOiJnb29nbGUiLCJwcm92aWRlcnMiOlsiZ29vZ2xlIl19LCJ1c2VyX21ldGFkYXRhIjp7ImF2YXRhcl91cmwiOiJodHRwczovL2xoMy5nb29nbGV1c2VyY29udGVudC5jb20vYS9BQ2c4b2NKS0I4OVRNMVQyR1hKc1FoU2RfQi13MXozOXl2dFZTOTQyaXFQQTcwTmpXR0tNNlE9czk2LWMiLCJlbWFpbCI6ImxlYWRwaXBlY3JtQGdtYWlsLmNvbSIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJmdWxsX25hbWUiOiJMZWFkcGlwZSIsImlzcyI6Imh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbSIsIm5hbWUiOiJMZWFkcGlwZSIsInBob25lX3ZlcmlmaWVkIjpmYWxzZSwicGljdHVyZSI6Imh0dHBzOi8vbGgzLmdvb2dsZXVzZXJjb250ZW50LmNvbS9hL0FDZzhvY0pLQjg5VE0xVDJHWEpzUWhTZF9CLXcxejM5eXZ0VlM5NDJpcVBBNzBOaldHS002UT1zOTYtYyIsInByb3ZpZGVyX2lkIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIiwic3ViIjoiMTAxOTUwMzczMjAwOTQwOTU1OTMzIn0sInJvbGUiOiJhdXRoZW50aWNhdGVkIiwiYWFsIjoiYWFsMSIsImFtciI6W3sibWV0aG9kIjoib2F1dGgiLCJ0aW1lc3RhbXAiOjE3ODA0MjI2OTR9XSwic2Vzc2lvbl9pZCI6ImY5MTVmNzAzLTJjZmEtNDFjNS1hODYzLTQ2ZDI5M2Y1N2M4YyIsImlzX2Fub255bW91cyI6ZmFsc2V9.myyUmeXEewMutyBmiIvXvL-cDNaTRxIlS1TeibkfAzS6bE-s7D7ntD6nTSaEFa2iOPpU3KFFVjB68MzqDVwhvA"
AUTH="Authorization: Bearer $TOKEN"
```

---

## Schema Reference

### Properties import required columns
`property_name`, `building_name`, `flat_number`

### Properties import optional columns
`property_address` (or `address`), `floor_number`, `bedrooms`, `bathrooms`, `street_address`, `city`, `state`, `country`

### Tenants import required columns
`name`, `phone`, `flat_number`

### Tenants import optional columns
`email`, `lease_start_date`, `lease_end_date`, `rent_amount`, `rent_status`, `manager_notes`

### Limits
- Max rows: **1,000**
- Max file size: **5 MB**
- Supported formats: `.csv` (UTF-8, UTF-8 BOM) and `.xlsx`

---

## Test File Creation

Create all test CSV files below before running the tests. You can create them in a `test_csvs/` directory.

---

### `test_csvs/prop_happy.csv` — valid properties, all columns
```
property_name,building_name,flat_number,property_address,floor_number,bedrooms,bathrooms
CSV Test Prop,CSV Test Block A,CSV-A101,100 Test Ave Montreal QC,1,1,1
CSV Test Prop,CSV Test Block A,CSV-A102,100 Test Ave Montreal QC,2,2,1
CSV Test Prop,CSV Test Block B,CSV-B101,100 Test Ave Montreal QC,1,3,2
```

### `test_csvs/prop_required_only.csv` — required columns only, no optional
```
property_name,building_name,flat_number
CSV ReqOnly Prop,CSV ReqOnly Block,CSV-R101
CSV ReqOnly Prop,CSV ReqOnly Block,CSV-R102
```

### `test_csvs/prop_two_groups.csv` — two property groups in one file
```
property_name,building_name,flat_number,bedrooms,bathrooms
CSV Group Alpha,Alpha Tower,CSV-GA01,1,1
CSV Group Alpha,Alpha Tower,CSV-GA02,2,1
CSV Group Beta,Beta Lodge,CSV-GB01,3,2
CSV Group Beta,Beta Annex,CSV-GB02,1,1
```

### `test_csvs/prop_missing_required.csv` — flat_number missing from header
```
property_name,building_name,bedrooms,bathrooms
Missing Col Prop,Missing Col Block,2,1
```

### `test_csvs/prop_empty_required_value.csv` — flat_number column present but blank in one row
```
property_name,building_name,flat_number,bedrooms
Row Error Prop,Row Error Block,,2
Row Error Prop,Row Error Block,CSV-VALID01,2
```

### `test_csvs/prop_duplicate_flat_in_csv.csv` — same flat number twice in the file
```
property_name,building_name,flat_number,bedrooms
Dup Flat Prop,Dup Block,CSV-DUP01,1
Dup Flat Prop,Dup Block,CSV-DUP01,2
```

### `test_csvs/prop_existing_flat.csv` — flat number that already exists in DB
```
property_name,building_name,flat_number,bedrooms
Clearview Heights TEST,Maple Tower,TST01,1
```
> `TST01` already exists from seed. Should be skipped, not error.

### `test_csvs/prop_numeric_text.csv` — bedrooms/bathrooms as text/float
```
property_name,building_name,flat_number,floor_number,bedrooms,bathrooms
Numeric Test Prop,Numeric Block,CSV-NUM01,one,two point five,1.5
```

### `test_csvs/prop_mixed_case_headers.csv` — uppercase/camelCase column headers (triggers AI mapping)
```
Property_Name,Building_Name,Flat_Number,Bedrooms,Bathrooms
Mixed Case Prop,Mixed Block,CSV-MC01,2,1
```

### `test_csvs/prop_whitespace_values.csv` — leading/trailing spaces in values
```
property_name,building_name,flat_number,bedrooms,bathrooms
  Whitespace Prop  ,  WS Block  ,  CSV-WS01  ,  2  ,  1  
```

### `test_csvs/prop_bom.csv` — UTF-8 BOM (Excel often saves with BOM)
Create by saving with Excel or by running:
```bash
printf '\xef\xbb\xbfproperty_name,building_name,flat_number\nBOM Test Prop,BOM Block,CSV-BOM01\n' > test_csvs/prop_bom.csv
```

### `test_csvs/prop_empty.csv` — empty file (header only or completely empty)
```
property_name,building_name,flat_number
```

### `test_csvs/prop_1001_rows.csv` — 1001 data rows (exceeds MAX_ROWS=1000)
```bash
python3 -c "
import csv, sys
w = csv.writer(sys.stdout)
w.writerow(['property_name','building_name','flat_number'])
for i in range(1001):
    w.writerow(['Big Import Prop','Big Block',f'BIG-{i:04d}'])
" > test_csvs/prop_1001_rows.csv
```

### `test_csvs/prop_alias_address.csv` — uses legacy `address` column instead of `property_address`
```
property_name,building_name,flat_number,address
Alias Prop,Alias Block,CSV-ALIAS01,999 Legacy St Montreal
```

### `test_csvs/tenant_happy.csv` — valid tenants, all columns
```
name,phone,flat_number,email,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes
CSV Tenant One,+15145551001,CSV-A101,one@test.com,2026-01-01,2026-12-31,1500,On-time,Test notes
CSV Tenant Two,+15145551002,CSV-A102,two@test.com,2026-03-01,2027-02-28,1800,Upcoming,Second tenant
```
> Requires `CSV-A101` and `CSV-A102` to exist (create via `prop_happy.csv` first).

### `test_csvs/tenant_required_only.csv` — required columns only
```
name,phone,flat_number
Minimal Tenant,+15145551010,CSV-R101
```

### `test_csvs/tenant_flat_not_found.csv` — flat number does not exist in DB
```
name,phone,flat_number
Ghost Tenant,+15145559001,DOESNOTEXIST-999
```

### `test_csvs/tenant_occupied_flat.csv` — flat already has a tenant
```
name,phone,flat_number
Second Person,+15145559002,CSV-A101
```
> `CSV-A101` will be occupied after `tenant_happy.csv` import.

### `test_csvs/tenant_invalid_rent_amount.csv` — rent_amount is non-numeric text
```
name,phone,flat_number,rent_amount
Bad Rent Tenant,+15145559003,CSV-B101,not-a-number
```

### `test_csvs/tenant_zero_rent.csv` — rent_amount = 0 (treated as falsy → no rent record)
```
name,phone,flat_number,rent_amount
Zero Rent Tenant,+15145559004,CSV-R102,0
```

### `test_csvs/tenant_invalid_rent_status.csv` — rent_status is not one of the 4 valid values
```
name,phone,flat_number,rent_status
Invalid Status Tenant,+15145559005,CSV-GB01,Banana
```

### `test_csvs/tenant_all_rent_statuses.csv` — one row per valid rent_status
```
name,phone,flat_number,rent_amount,rent_status
Status On-time,+15145559010,CSV-GA01,1000,On-time
Status Upcoming,+15145559011,CSV-GA02,1100,Upcoming
Status Overdue,+15145559012,CSV-GB01,1200,Overdue
Status At Risk,+15145559013,CSV-GB02,1300,At Risk
```

### `test_csvs/tenant_missing_required.csv` — missing phone column
```
name,flat_number,email
No Phone Tenant,CSV-A101,nophone@test.com
```

### `test_csvs/tenant_empty_required_value.csv` — phone is blank in one row
```
name,phone,flat_number
Good Tenant,+15145559020,CSV-R101
Bad Tenant,,CSV-R102
```

### `test_csvs/tenant_mixed_case_headers.csv` — column names with wrong case (triggers AI mapping)
```
Name,Phone,Flat_Number
Case Tenant,+15145559030,CSV-A101
```

### `test_csvs/tenant_all_optional.csv` — all optional fields present
```
name,phone,flat_number,email,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes
Full Optional,+15145559040,CSV-R101,full@test.com,2026-01-01,2026-12-31,1450,On-time,Has dog. Pays early.
```

---

## Part A — Properties CSV Tests

### CP01 — Analyze valid file (POST /import/analyze)
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** `{"needs_mapping":false,"row_count":3}`.

### CP02 — Import valid properties (POST /import/properties)
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{"created":3,"skipped":[],"errors":[]}
```
New property group "CSV Test Prop", 2 buildings ("CSV Test Block A", "CSV Test Block B"), 3 flats.

**Verify in Supabase:**
```sql
SELECT flat_number, bedrooms, bathrooms FROM flats WHERE flat_number LIKE 'CSV-%' ORDER BY flat_number;
```

### CP03 — Import required columns only
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_required_only.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":2,"skipped":[],"errors":[]}`. Optional fields are null/default.

**Verify:** `bedrooms`, `bathrooms`, `floor_number` are null in DB.

### CP04 — Import two property groups in one file
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_two_groups.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":4,"skipped":[],"errors":[]}`. Two separate property groups created.

**Verify:**
```sql
SELECT name FROM properties_list WHERE name LIKE 'CSV Group%';
-- Should return: CSV Group Alpha, CSV Group Beta
```

### CP05 — Re-import same file → all skipped (idempotent)
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":0,"skipped":["Row 2: flat CSV-A101 already exists","Row 3: flat CSV-A102 already exists","Row 4: flat CSV-B101 already exists"],"errors":[]}`.
- Property group and buildings are reused (not duplicated)
- Flats with matching flat_number are skipped, not errored

### CP06 — Missing required column → 400 at endpoint level
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_missing_required.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Missing required columns: flat_number"`. File is rejected before any rows are processed.

### CP07 — Analyze missing-required file → needs_mapping + unmapped_required
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_missing_required.csv;type=text/csv" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** `{"needs_mapping":true,"unmapped_required":["flat_number"],"mapping":{...}}` (AI fails to map `flat_number` from the available headers).

### CP08 — Empty required value → row error, other rows succeed
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_empty_required_value.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{"created":1,"skipped":[],"errors":["Row 2: missing required value (property_name, building_name or flat_number)"]}
```
Row 2 (blank flat_number) is an error; Row 3 (`CSV-VALID01`) succeeds.

### CP09 — Duplicate flat number in same CSV
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_duplicate_flat_in_csv.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** First row creates `CSV-DUP01`. Second row is skipped (already exists after first insert). Result: `{"created":1,"skipped":["Row 3: flat CSV-DUP01 already exists"],"errors":[]}`.

**Edge case:** The ilike check runs before each insert, so the second row catches the first row's DB insert.

### CP10 — Existing flat (from seed) → skipped, not error
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_existing_flat.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":0,"skipped":["Row 2: flat TST01 already exists"],"errors":[]}`.
Building "Maple Tower" in "Clearview Heights TEST" is reused (not duplicated). Property group is reused.

**Verify:** No second "Clearview Heights TEST" row in `properties_list`:
```sql
SELECT count(*) FROM properties_list WHERE name = 'Clearview Heights TEST';
-- Must return 1, not 2
```

### CP11 — Numeric fields as text → skipped gracefully
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_numeric_text.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** Flat `CSV-NUM01` created. `bedrooms` and `bathrooms` stored as null (non-integer strings silently skipped — `int(val)` fails → field not set). `floor_number` from "one" → null.

**Verify:** `SELECT bedrooms, bathrooms, floor_number FROM flats WHERE flat_number = 'CSV-NUM01';` → all null.

### CP12 — Mixed-case column headers → analyze triggers AI mapping
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_mixed_case_headers.csv;type=text/csv" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** `{"needs_mapping":true,"mapping":{"Property_Name":"property_name","Building_Name":"building_name","Flat_Number":"flat_number","Bedrooms":"bedrooms","Bathrooms":"bathrooms"}}`.

### CP13 — Import with AI-suggested mapping (2-step flow)
```bash
# Step 1: analyze
MAPPING=$(curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_mixed_case_headers.csv;type=text/csv" \
  -F "import_type=properties" | python -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('mapping',{})))")

echo "Mapping: $MAPPING"

# Step 2: import with mapping
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_mixed_case_headers.csv;type=text/csv" \
  -F "column_mapping=$MAPPING" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. `CSV-MC01` created correctly.

### CP14 — Whitespace trimming in values
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_whitespace_values.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. Values trimmed by `_parse_csv`. Flat stored as `CSV-WS01` (uppercase, no spaces).

**Verify:** `SELECT flat_number FROM flats WHERE flat_number = 'CSV-WS01';`

### CP15 — UTF-8 BOM file
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_bom.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. BOM stripped by `content.decode("utf-8-sig")`.

### CP16 — Empty file (header only)
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_empty.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":0,"skipped":[],"errors":[]}`. No rows to process — not an error.

### CP17 — Too many rows (>1000) → 400
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_1001_rows.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Too many rows (max 1000)"`. File rejected before any rows are inserted.

### CP18 — File too large (>5 MB) → 400
```bash
# Create a 6MB file
python3 -c "
print('property_name,building_name,flat_number')
for i in range(50000):
    print(f'Big Prop,Big Block {i},BIG-{i:05d}')
" > test_csvs/prop_toolarge.csv

curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_toolarge.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"File too large (max 5 MB)"`.

### CP19 — Wrong file type (plain text with .txt extension)
```bash
cp test_csvs/prop_happy.csv test_csvs/prop_happy.txt
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.txt;type=text/plain" \
  | python -m json.tool
```
**Expected:** File extension is neither `.csv` nor `.xlsx` → `_detect_and_parse` falls through to `_parse_csv` (default). If headers match → imports. Document actual behavior.

### CP20 — XLSX format (POST /import/properties)
Create `test_csvs/prop_happy.xlsx` with Excel or Python:
```python
# run: python3 create_test_xlsx.py
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(["property_name","building_name","flat_number","bedrooms","bathrooms"])
ws.append(["XLSX Test Prop","XLSX Block","XLSX-X01",2,1])
ws.append(["XLSX Test Prop","XLSX Block","XLSX-X02",1,1])
wb.save("test_csvs/prop_happy.xlsx")
```
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  | python -m json.tool
```
**Expected:** `{"created":2,"skipped":[],"errors":[]}`.

### CP21 — XLSX with empty rows (Excel often has trailing blank rows)
```python
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(["property_name","building_name","flat_number"])
ws.append(["XLSX Empty Prop","XLSX Empty Block","XLSX-E01"])
ws.append([None, None, None])  # blank row
ws.append([None, None, None])  # another blank row
wb.save("test_csvs/prop_xlsx_empty_rows.xlsx")
```
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_xlsx_empty_rows.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. Blank rows filtered by `if any(row_dict.values())`.

### CP22 — Legacy `address` column alias
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_alias_address.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. `address` column picked up as `prop_address` via `row.get("property_address","") or row.get("address","")`.

### CP23 — Invalid JSON column_mapping → 400
```bash
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  -F 'column_mapping=not-valid-json' \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Invalid column_mapping JSON"`.

---

## Part B — Tenants CSV Tests

> **Prerequisite for all tenant tests:** The flat numbers referenced must already exist in the DB.
> Run `CP02` (prop_happy.csv import) and `CP04` (prop_two_groups.csv) before these tests.

### CT01 — Analyze valid tenants file (POST /import/analyze)
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/tenant_happy.csv;type=text/csv" \
  -F "import_type=tenants" | python -m json.tool
```
**Expected:** `{"needs_mapping":false,"row_count":2}`.

### CT02 — Import valid tenants — all columns
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_happy.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":2,"skipped":[],"errors":[]}`.

**Verify:**
```sql
SELECT t.name, t.phone, t.email, t.rent_status, f.flat_number, r.monthly_rent
FROM tenants t
JOIN flats f ON f.uuid = t.flat_uuid
LEFT JOIN rents r ON r.flat_uuid = f.uuid AND r.is_active = true
WHERE t.name LIKE 'CSV Tenant%';
```
Both tenants created. `flats.tenant_uuid` set. `flats.occupied = true`. `rents` rows inserted with correct amounts.

### CT03 — Import required columns only
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_required_only.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. `email`, `lease_start_date`, etc. are null. No rent record created.

### CT04 — Flat not found → row error, continues
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_flat_not_found.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{"created":0,"skipped":[],"errors":["Row 2: flat 'DOESNOTEXIST-999' not found"]}
```

### CT05 — Occupied flat → row skipped (not an error)
```bash
# CSV-A101 is occupied after CT02
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_occupied_flat.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{"created":0,"skipped":["Row 2: flat CSV-A101 is already occupied"],"errors":[]}
```

### CT06 — Invalid rent_amount (non-numeric) → tenant created, rent skipped
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_invalid_rent_amount.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{
  "created": 1,
  "skipped": ["Row 2 (Bad Rent Tenant): rent_amount 'not-a-number' is not a valid number — tenant imported without a rent record"],
  "errors": []
}
```
Tenant is created. Flat is occupied. No `rents` row inserted.

**Verify:**
```sql
SELECT t.name, t.uuid FROM tenants WHERE phone = '+15145559003';
-- Tenant exists
SELECT * FROM rents WHERE flat_uuid = (SELECT uuid FROM flats WHERE flat_number = 'CSV-B101');
-- No rent record
```

### CT07 — Zero rent_amount → no rent record (0 is falsy in Python)
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_zero_rent.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. Tenant created. No rent record (rent_amount_raw `"0"` → `float("0") = 0.0` which is falsy → `if rent_amount_raw:` is false for empty string but `"0"` is truthy — actually `float("0") = 0` is a valid number, so a rent record with $0 IS inserted).

**Actual behavior check:** `rent_amount_raw = "0"` → `if rent_amount_raw:` → True (non-empty string) → `float("0") = 0.0` → inserts rent record with `monthly_rent=0`. Verify:
```sql
SELECT monthly_rent FROM rents WHERE flat_uuid = (SELECT uuid FROM flats WHERE flat_number = 'CSV-R102');
-- Expected: 0.00
```

### CT08 — Invalid rent_status → tenant created without rent_status field
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_invalid_rent_status.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. Tenant created but `rent_status` is null (invalid value silently dropped, not errored).

**Verify:**
```sql
SELECT rent_status FROM tenants WHERE phone = '+15145559005';
-- Expected: null or default value
```

### CT09 — All four valid rent_status values
```bash
# First ensure the target flats exist (CSV-GA01, CSV-GA02, CSV-GB01, CSV-GB02)
# They were created by CP04 (prop_two_groups.csv)

curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_all_rent_statuses.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":4,"skipped":[],"errors":[]}`. All four statuses stored correctly.

**Verify:**
```sql
SELECT name, rent_status FROM tenants WHERE phone LIKE '+1514555901%' ORDER BY phone;
-- Expected: On-time, Upcoming, Overdue, At Risk
```

### CT10 — Missing required column `phone` → 400
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_missing_required.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Missing required columns: phone"`.

### CT11 — Empty required value in row → row error, other rows succeed
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_empty_required_value.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:**
```json
{"created":1,"skipped":[],"errors":["Row 3: missing required value (name, phone or flat_number)"]}
```
Row 2 (Good Tenant with valid phone) succeeds. Row 3 (blank phone) is an error.

### CT12 — Mixed-case column headers → analyze triggers AI mapping
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/tenant_mixed_case_headers.csv;type=text/csv" \
  -F "import_type=tenants" | python -m json.tool
```
**Expected:** `{"needs_mapping":true,"mapping":{"Name":"name","Phone":"phone","Flat_Number":"flat_number"}}`.

### CT13 — Import tenants with AI mapping (2-step)
```bash
TMAPPING=$(curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/tenant_mixed_case_headers.csv;type=text/csv" \
  -F "import_type=tenants" | python -c "import sys,json; print(json.dumps(json.load(sys.stdin).get('mapping',{})))")

curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_mixed_case_headers.csv;type=text/csv" \
  -F "column_mapping=$TMAPPING" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}` (or skipped if CSV-A101 is already occupied).

### CT14 — All optional fields present
```bash
# Re-use CSV-R101 if it was cleaned up after CT03
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_all_optional.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. All fields persisted.

**Verify:**
```sql
SELECT name, phone, email, lease_start_date, lease_end_date, manager_notes, rent_status
FROM tenants WHERE phone = '+15145559040';
```

### CT15 — Tenant file > 1000 rows → 400
```bash
python3 -c "
print('name,phone,flat_number')
for i in range(1001):
    print(f'Tenant {i},+15145{i:06d},CSV-A101')
" > test_csvs/tenant_1001.csv

curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_1001.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Too many rows (max 1000)"`.

### CT16 — Tenant file too large → 400
```bash
python3 -c "
print('name,phone,flat_number,manager_notes')
for i in range(10000):
    print(f'Tenant {i},+15145{i:06d},CSV-A101,' + 'x'*500)
" > test_csvs/tenant_toolarge.csv

curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_toolarge.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"File too large (max 5 MB)"`.

### CT17 — Tenant XLSX import
```python
# create_tenant_xlsx.py
import openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.append(["name","phone","flat_number","email","rent_amount","rent_status"])
ws.append(["XLSX Tenant","+ 15145551099","CSV-R102","xlsx@test.com",1600,"On-time"])
wb.save("test_csvs/tenant_happy.xlsx")
```
```bash
curl -s -X POST "$BASE/import/tenants" -H "$AUTH" \
  -F "file=@test_csvs/tenant_happy.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" \
  | python -m json.tool
```
**Expected:** `{"created":1,"skipped":[],"errors":[]}`. Tenant created. Phone stored as-is (backend doesn't normalize during import — verify stored value).

---

## Part C — Analyze Endpoint Edge Cases

### CA01 — analyze with wrong import_type → 400
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  -F "import_type=buildings" | python -m json.tool
```
**Expected:** HTTP 400 — `"import_type must be 'properties' or 'tenants'"`.

### CA02 — analyze with no file → 422
```bash
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** HTTP 422 (missing required form field `file`).

### CA03 — analyze a completely garbage binary file → 400
```bash
printf '\x00\x01\x02\x03\xff\xfe' > test_csvs/garbage.bin
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/garbage.bin;type=application/octet-stream" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** HTTP 400 — `"Cannot parse file: ..."`.

### CA04 — analyze → needs_mapping:true → confirm all required columns eventually resolve
If AI mapping cannot find a match for a required column, `unmapped_required` lists it.
```bash
# File with completely unrelated headers
printf 'unit_id,block_name,street\nU001,Block Z,100 Main St\n' > test_csvs/prop_weird_headers.csv
curl -s -X POST "$BASE/import/analyze" -H "$AUTH" \
  -F "file=@test_csvs/prop_weird_headers.csv;type=text/csv" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:**
- `needs_mapping: true`
- `mapping` has AI's best guesses: `{"unit_id":"flat_number","block_name":"building_name","street":"property_address"}` (or similar)
- If AI can guess all 3 required fields → `unmapped_required: []`
- If not → lists what it couldn't map

### CA05 — Import with mapping that nulls a required field → 400
```bash
# Provide mapping that maps flat_number to null (drop it)
curl -s -X POST "$BASE/import/properties" -H "$AUTH" \
  -F "file=@test_csvs/prop_mixed_case_headers.csv;type=text/csv" \
  -F 'column_mapping={"Property_Name":"property_name","Building_Name":"building_name","Flat_Number":null,"Bedrooms":"bedrooms"}' \
  | python -m json.tool
```
**Expected:** HTTP 400 — `"Missing required columns: flat_number"` (null-mapped columns are dropped by `_apply_mapping`).

---

## Part D — Authorization Tests on Import Routes

### CD01 — Import without token → 401
```bash
curl -s -X POST "$BASE/import/properties" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  | python -m json.tool
```
**Expected:** HTTP 401.

### CD02 — Analyze without token → 401
```bash
curl -s -X POST "$BASE/import/analyze" \
  -F "file=@test_csvs/prop_happy.csv;type=text/csv" \
  -F "import_type=properties" | python -m json.tool
```
**Expected:** HTTP 401.

---

## Cleanup

After all tests, remove test data:

```sql
-- Remove test flats and cascade
DELETE FROM flats WHERE flat_number LIKE 'CSV-%' OR flat_number LIKE 'XLSX-%' OR flat_number LIKE 'BIG-%';

-- Remove test property groups (cascade: buildings → flats → tenants → rents)
DELETE FROM properties_list WHERE name IN (
  'CSV Test Prop','CSV ReqOnly Prop','CSV Group Alpha','CSV Group Beta',
  'Numeric Test Prop','Mixed Case Prop','Whitespace Prop','BOM Test Prop',
  'Alias Prop','Row Error Prop','Dup Flat Prop','XLSX Test Prop','XLSX Empty Prop'
);

-- Remove test tenants orphaned from flat deletion
DELETE FROM tenants WHERE phone LIKE '+1514555900%' OR phone LIKE '+1514555901%' OR phone LIKE '+1514555910%';

-- Verify cleanup
SELECT count(*) FROM flats WHERE flat_number LIKE 'CSV-%';
SELECT count(*) FROM properties_list WHERE name LIKE 'CSV %';
```

---

## Quick Checklist

| Test | Description | Pass | Fail | Notes |
|---|---|---|---|---|
| CP01 | Analyze valid → needs_mapping:false | | | |
| CP02 | Import valid properties | | | |
| CP03 | Import required columns only | | | |
| CP04 | Two property groups in one file | | | |
| CP05 | Re-import same file → all skipped | | | |
| CP06 | Missing required column → 400 | | | |
| CP08 | Empty required value → row error | | | |
| CP09 | Duplicate flat in same CSV | | | |
| CP10 | Existing flat from seed → skipped | | | |
| CP11 | Non-numeric bedrooms → null | | | |
| CP12 | Mixed-case headers → needs_mapping:true | | | |
| CP13 | AI mapping 2-step import | | | |
| CP14 | Whitespace trimming | | | |
| CP15 | UTF-8 BOM | | | |
| CP16 | Empty file (header only) | | | |
| CP17 | >1000 rows → 400 | | | |
| CP18 | >5MB file → 400 | | | |
| CP20 | XLSX format | | | |
| CP21 | XLSX with blank rows | | | |
| CP22 | `address` column alias | | | |
| CP23 | Invalid column_mapping JSON → 400 | | | |
| CT02 | Import valid tenants all columns | | | |
| CT03 | Import required columns only | | | |
| CT04 | Flat not found → row error | | | |
| CT05 | Occupied flat → row skipped | | | |
| CT06 | Invalid rent_amount → tenant created, rent skipped | | | |
| CT07 | Zero rent_amount → $0 rent record inserted | | | |
| CT08 | Invalid rent_status → tenant created, status null | | | |
| CT09 | All 4 valid rent_status values | | | |
| CT10 | Missing required column → 400 | | | |
| CT11 | Empty required value in row → row error | | | |
| CT13 | Tenant AI mapping 2-step | | | |
| CT14 | All optional fields | | | |
| CT15 | >1000 rows → 400 | | | |
| CT17 | Tenant XLSX import | | | |
| CA01 | Wrong import_type → 400 | | | |
| CA03 | Garbage binary file → 400 | | | |
| CA05 | Mapping nulls required field → 400 | | | |
| CD01 | Import no token → 401 | | | |
