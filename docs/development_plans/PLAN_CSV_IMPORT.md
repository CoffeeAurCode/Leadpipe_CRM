# Plan: CSV Import 
> Status: Ready to implement  
> Date: 2026-04-23



## CSV Import Feature

### Goal
Let managers bulk-import their data from any existing CRM by uploading CSVs.
Two import types: **Properties** (full hierarchy) and **Tenants**.

### Data Hierarchy
```
PropertyGroup (properties_list)
  └── Building (buildings)
        └── Flat (flats)
              └── Tenant (tenants)
```

---

### CSV Formats

#### Properties CSV (creates PropertyGroup + Building + Flat in one shot)
One row per flat. Property + Building names are repeated on each row (deduplicated on import).

```
property_name, property_address, building_name, flat_number, floor_number, bedrooms, bathrooms
Sunrise Towers, 12 MG Road, Block A, A-101, 1, 2, 1
Sunrise Towers, 12 MG Road, Block A, A-102, 1, 3, 2
Sunrise Towers, 12 MG Road, Block B, B-201, 2, 2, 1
```

Required columns: `property_name`, `building_name`, `flat_number`  
Optional columns: `property_address`, `floor_number`, `bedrooms`, `bathrooms`

#### Tenants CSV (links to existing flats by flat_number)
```
name, phone, email, flat_number, lease_start_date, lease_end_date, rent_amount, rent_status, manager_notes
Rahul Sharma, +919876543210, rahul@gmail.com, A-101, 2024-01-01, 2025-01-01, 15000, On-time,
Priya Patel, +919988776655, priya@gmail.com, B-201, 2024-06-01, 2025-06-01, 18000, Upcoming, Pets allowed
```

Required columns: `name`, `phone`, `flat_number`  
Optional columns: `email`, `lease_start_date`, `lease_end_date`, `rent_amount`, `rent_status`, `manager_notes`

---

### Backend Implementation

**New file:** `backend/app/routes/import_routes.py`

#### `POST /import/properties`
1. Parse CSV (use Python's built-in `csv` module — no new dependency)
2. Validate required columns exist
3. Deduplicate property groups by `property_name` (case-insensitive) — create once, reuse UUID
4. Deduplicate buildings by `(property_id, building_name)` — create once, reuse integer ID
5. For each flat row: check if `flat_number` already exists — skip with error entry if duplicate
6. Insert flat linked to building
7. Return summary: `{ created: { properties, buildings, flats }, skipped: [...], errors: [...] }`

#### `POST /import/tenants`
1. Parse CSV
2. Validate required columns exist
3. For each row:
   a. Look up flat by `flat_number` (ilike, case-insensitive)
   b. If flat not found → log error, skip
   c. If flat already has a tenant → log skip (don't overwrite)
   d. Create tenant with all provided fields
   e. Bidirectionally link: `tenant.flat_uuid = flat.uuid`, `flat.tenant_uuid = tenant.uuid`, `flat.occupied = True`
   f. If `rent_amount` provided → insert a row into `rents` table (`is_active=True`)
4. Return summary: `{ created, skipped, errors }`

**Register in `main.py`:**
```python
from app.routes import import_routes
app.include_router(import_routes.router)
```

---

### Frontend Implementation

#### New component: `CsvImportModal.jsx`

**Location:** `frontend/src/components/CsvImportModal.jsx`

**Layout:**
```
┌─────────────────────────────────────────┐
│  Import from CSV                     X  │
│                                         │
│  [Properties] [Tenants]   ← tabs        │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │  Drop CSV file here or Browse     │  │
│  └───────────────────────────────────┘  │
│                                         │
│  Preview (first 3 rows):               │
│  ┌──────────┬──────────┬────────────┐   │
│  │ col1     │ col2     │ col3       │   │
│  │ val1     │ val2     │ val3       │   │
│  └──────────┴──────────┴────────────┘   │
│                                         │
│  Download Template ↓                    │
│                                         │
│  [Cancel]          [Import X rows →]   │
└─────────────────────────────────────────┘
```

After import, show result panel:
```
✓ 3 properties created
✓ 5 buildings created  
✓ 24 flats created
⚠ 2 rows skipped (flat already exists): A-101, B-301
✗ 1 error: Row 7 — missing flat_number
```

#### Template download (client-side, no backend needed)
Generate a `.csv` download from a hardcoded header string using the Blob API.

#### Wire into existing pages
- `PropertiesPage.jsx` — add "Import CSV" button in the top action bar (next to "Add Property")
- `TenantManagement.jsx` — add "Import CSV" button in the tenant list header

#### `apiService.js` additions
```js
importPropertiesCsv(file)  // POST /import/properties  multipart/form-data
importTenantsCsv(file)     // POST /import/tenants     multipart/form-data
```

---

### Implementation Order

1. **Backend first:**
   - [ ] `backend/app/routes/import_routes.py` — both endpoints
   - [ ] Register in `main.py`
   - [ ] Manual test with curl

2. **Frontend:**
   - [ ] `apiService.js` — add two import methods
   - [ ] `CsvImportModal.jsx` — file upload, preview, template download, result display
   - [ ] Wire import button into `PropertiesPage.jsx`
   - [ ] Wire import button into `TenantManagement.jsx`

3. **Auth fix (no code changes required, config only):**
   - [ ] Follow diagnostic checklist above
   - [ ] Add `vercel.json` if on Vercel

---

### Error Handling Rules

- **Never crash the whole import on a single bad row** — collect errors, continue, return full summary
- **Duplicate detection:** by flat_number (properties import) and by flat_number lookup (tenant import)
- **Flat already occupied:** skip tenant, log as skipped (not error) — preserve existing data
- **File too large:** reject if > 5MB or > 1000 rows before processing
- **Missing required columns:** reject immediately with clear message listing which columns are missing

---

### Testing the Import Manually

Once built, test with curl:

```bash
# Test properties import
curl -X POST http://localhost:8000/import/properties \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@test_properties.csv"

# Test tenants import
curl -X POST http://localhost:8000/import/tenants \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@test_tenants.csv"
```

Sample `test_properties.csv`:
```
property_name,property_address,building_name,flat_number,floor_number,bedrooms,bathrooms
Test Society,123 Main St,Block A,A-101,1,2,1
Test Society,123 Main St,Block A,A-102,1,3,2
Test Society,123 Main St,Block B,B-201,2,2,1
```

Sample `test_tenants.csv`:
```
name,phone,email,flat_number,lease_start_date,lease_end_date,rent_amount,rent_status
Rahul Sharma,+919876543210,rahul@test.com,A-101,2024-01-01,2025-01-01,15000,On-time
Priya Patel,+919988776655,,A-102,2024-06-01,2025-06-01,18000,Upcoming
```
