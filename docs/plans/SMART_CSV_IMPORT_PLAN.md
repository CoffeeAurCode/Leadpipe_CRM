# Smart CSV Import — Implementation Plan

## Problem

The current CSV import requires exact column headers (`property_name`, `flat_number`, `name`, etc.). Any file with different naming conventions (e.g. "Unit No", "Tenant Name", "Block") fails immediately with "Missing required columns". There is no recovery path — the user must manually reformat their spreadsheet to match the template.

## Proposed Solution

A two-phase AI-assisted import flow:

1. **Detection** — Auto-detect if the uploaded file's columns match the expected schema.
2. **AI Mapping** — If they don't match, send headers + sample rows to OpenAI (`gpt-4o-mini`) and get back a semantic column mapping (e.g. `"Tenant Name" → "name"`, `"Unit No" → "flat_number"`).
3. **Confirmation UI** — Show the user the proposed mapping in an editable table so they can verify or override it.
4. **Import** — Send the confirmed mapping alongside the file; backend applies it before processing rows.

---

## Architecture

### New Backend Endpoint

```
POST /import/analyze
```

**Input:** `multipart/form-data`
- `file`: the CSV file
- `import_type`: `"properties"` | `"tenants"`

**What it does:**
1. Parse the CSV (reuse `_parse_csv`)
2. Check if all required columns already match → if yes, return `{"needs_mapping": false}`
3. If not, call OpenAI with:
   - The actual column headers from the file
   - First 3 rows of data as examples
   - The list of required + optional target columns + their descriptions
4. OpenAI returns a JSON mapping: `{"original_col": "target_col_or_null", ...}`
5. Return the mapping + a preview of the first 3 rows after mapping is applied

**Response shape:**
```json
{
  "needs_mapping": true,
  "mapping": {
    "Tenant Name": "name",
    "Mobile": "phone",
    "Unit No": "flat_number",
    "Monthly Rent": "rent_amount",
    "Extra Column": null
  },
  "unmapped_required": [],
  "preview": {
    "headers": ["name", "phone", "flat_number"],
    "rows": [["Rahul", "+919876543210", "A-101"]]
  }
}
```

If `unmapped_required` is non-empty, the user must manually assign those columns — the import button stays disabled.

---

### Modified Import Endpoints

Both `POST /import/properties` and `POST /import/tenants` gain an optional form field:

```
column_mapping: str  # JSON string, e.g. '{"Tenant Name": "name", "Unit No": "flat_number"}'
```

Backend helper `_apply_mapping(rows, mapping)` renames keys before processing. If `column_mapping` is absent, existing behavior is unchanged — no regression.

---

### New Helper: `_map_columns_with_ai`

```python
# backend/app/routes/import_routes.py

async def _map_columns_with_ai(
    headers: list[str],
    sample_rows: list[dict],
    import_type: str,   # "properties" | "tenants"
) -> dict[str, str | None]:
    ...
```

Calls `openai.chat.completions.create` with `gpt-4o-mini`. The prompt gives OpenAI:
- The target schema (required + optional columns with descriptions)
- The actual headers from the uploaded file
- 3 sample data rows for context
- Strict instruction to return only valid JSON, no commentary

The response is parsed with `json.loads`. If parsing fails, fall back to empty mapping (user must map manually).

---

### Frontend Changes — `CsvImportModal.jsx`

**New state:**
```js
const [mappingStep, setMappingStep] = useState(false);  // show mapping UI?
const [mapping, setMapping] = useState(null);            // {original: target}
const [analyzing, setAnalyzing] = useState(false);
const [unmappedRequired, setUnmappedRequired] = useState([]);
```

**Flow change after file upload:**

```
Upload file
  → Parse preview (existing)
  → Click "Import N rows"
      → Call POST /import/analyze
          → If needs_mapping: false → proceed directly to import (existing flow)
          → If needs_mapping: true  → show ColumnMappingStep UI
              → User reviews/edits mapping
              → Click "Confirm & Import"
                  → Call import endpoint with column_mapping JSON
```

**New sub-component: `ColumnMappingStep`**

A table with three columns:
| Your Column | Maps To | Status |
|---|---|---|
| "Tenant Name" | `name` ✓ | AI suggested |
| "Mobile" | `phone` ✓ | AI suggested |
| "Unit No" | `flat_number` ✓ | AI suggested |
| "Extra Notes" | *(ignore)* | — |

Each "Maps To" cell is a `<select>` dropdown populated with all valid target columns + "ignore". Required columns that are unmapped show a red indicator and block the import button.

---

### `apiService.js` — New Functions

```js
analyzeImportFile(file, importType)   // POST /import/analyze
importPropertiesWithMapping(file, mapping)  // POST /import/properties (with column_mapping)
importTenantsWithMapping(file, mapping)     // POST /import/tenants (with column_mapping)
```

These follow the existing auth token pattern used in the modal's `handleImport`.

---

## File Changes Summary

| File | Change |
|---|---|
| `backend/app/routes/import_routes.py` | Add `POST /import/analyze` endpoint, add `_map_columns_with_ai` helper, add `_apply_mapping` helper, add `column_mapping` param to both import endpoints |
| `backend/app/config.py` | Already has `OPEN_AI_API` — no change needed |
| `frontend/src/components/CsvImportModal.jsx` | Add mapping flow state, `ColumnMappingStep` sub-component, modify `handleImport` to call analyze first |
| `frontend/src/services/apiService.js` | Add `analyzeImportFile`, update import functions to pass `column_mapping` |

**No new files needed. No new dependencies** — `openai` package is already used by the chatbot.

---

## OpenAI Prompt Design (draft)

```
You are a data-mapping assistant. The user has uploaded a CSV for importing into a property management system.

Import type: {import_type}

TARGET SCHEMA — Required columns (must be present):
{required_columns_with_descriptions}

TARGET SCHEMA — Optional columns (map if you see them):
{optional_columns_with_descriptions}

ACTUAL CSV HEADERS from the uploaded file:
{headers}

SAMPLE DATA (first 3 rows):
{sample_rows_as_csv}

Task: Map each actual header to its best-matching target column name, or null if it doesn't match anything.
Return ONLY a valid JSON object. No commentary. Example:
{"Actual Header": "target_column", "Irrelevant Column": null}
```

---

## Edge Cases

| Case | Handling |
|---|---|
| All columns already match | Skip AI call entirely — analyze returns `needs_mapping: false`, import proceeds normally |
| OpenAI returns unparseable JSON | Fall back: show mapping UI with all columns set to "ignore" — user must map manually |
| OpenAI maps a required column incorrectly | User can override via dropdown in mapping UI |
| A required column has no plausible match in the file | `unmapped_required` non-empty — import button disabled with clear message |
| OpenAI API call fails (timeout, quota) | Return 200 with `needs_mapping: true, mapping: {}` — user maps manually |
| File has comma-only issues (semicolons, tabs) | Out of scope for this change — note for future: add delimiter sniffing |

---

## What Does NOT Change

- The existing import logic (row-by-row DB writes, skip/error semantics) is untouched
- The 5 MB / 1000 row limits remain
- Template download still works exactly as before
- Non-AI imports (files that already match the schema) get zero extra latency

---

## Decisions Made

| Question | Decision |
|---|---|
| File types | **CSV + Excel (.xlsx)** — requires `openpyxl` added to `requirements.txt` |
| AI model | **gpt-4o-mini** — same as the chatbot, sufficient for column mapping |
| Mapping review | **Always shown** — user always sees and confirms AI mapping before any DB writes |
| Value normalization | **Column mapping only** — AI only renames columns; existing validation handles values |

---

## How Existing Value Validation Works (no changes needed)

Once the column mapping is applied and rows have the correct key names, the existing import code already validates values before writing to the DB:

**Properties import:**
- `property_name`, `building_name`, `flat_number` — checked with `if not x` → row errored if empty
- `floor_number`, `bedrooms`, `bathrooms` — wrapped in `int(raw)` → silently skipped if not a valid integer (non-blocking)
- Duplicate flats — checked via DB lookup (`ilike`) → row skipped

**Tenants import:**
- `name`, `phone`, `flat_number` — checked with `if not x` → row errored if empty
- `flat_number` — must resolve to an existing flat in DB → row errored if not found
- `lease_start_date`, `lease_end_date` — stored as-is (strings); Supabase rejects non-date strings at DB level → row errored
- `rent_amount` — wrapped in `float(rent_raw)` → silently skipped if not numeric (rent record simply not created)
- `rent_status` — stored as-is; no enum validation currently (existing behavior)

**What this means for smart import:** The AI does not need to fix values. A user whose CSV has `"15,000"` for rent_amount will still see an import with rent silently skipped — same as today. We may want to add a warning in the mapping UI ("rent_amount should be a plain number, e.g. 15000") but that's cosmetic.

---

## Additional File Changes (updated)

| File | Change |
|---|---|
| `backend/app/routes/import_routes.py` | Add `POST /import/analyze`, `_map_columns_with_ai`, `_apply_mapping`, `_parse_xlsx`; add `column_mapping` param to both import endpoints |
| `backend/requirements.txt` | Add `openpyxl` |
| `backend/app/config.py` | Already has `OPEN_AI_API` — no change |
| `frontend/src/components/CsvImportModal.jsx` | Add mapping flow state, `ColumnMappingStep` sub-component, modify `handleImport` |
| `frontend/src/services/apiService.js` | Add `analyzeImportFile`, update import functions |

### Excel (.xlsx) support

**Backend:** New helper `_parse_xlsx(content: bytes) -> tuple[list[dict], set[str]]` using `openpyxl.load_workbook`. Reads the first sheet, treats row 1 as headers, returns the same `(rows, fieldnames)` tuple as `_parse_csv`. `import_routes.py` detects file type by `content_type` or filename extension and routes to the correct parser.

**Frontend:** `DropZone` `accept` attribute changed from `".csv"` to `".csv,.xlsx"`. Preview for Excel files: backend analyze endpoint returns the same preview shape, so the existing `PreviewTable` works unchanged. The "Download Template" still gives CSV — Excel template generation is out of scope.
