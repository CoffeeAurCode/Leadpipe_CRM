# CSV Import Guide

Use CSV import to bulk-load your entire property and tenant database in one shot — ideal for migrating from a spreadsheet or another CRM.

---

## Where to find it

The import button lives inside the **Properties** page. Click **Import CSV** (or the upload icon) to open the import modal. Two tabs are available: **Properties** and **Tenants**.

---

## Import Type 1 — Properties

### What it creates

One row per unit (flat). The backend automatically:

- Creates the **PropertyGroup** if it doesn't exist (matched by name, case-insensitive)
- Creates the **Building** inside that group if it doesn't exist
- Creates the **Flat** with the given number

Duplicate detection is in-memory within the upload and also checked against the live database, so re-uploading the same file is safe — existing rows are skipped.

### Required columns

| Column | Description |
|---|---|
| `property_name` | Top-level property group name (e.g. `Sunrise Towers`) |
| `building_name` | Building name inside the property (e.g. `Block A`) |
| `flat_number` | Unit identifier — stored in UPPER CASE (e.g. `A-101`) |

### Optional columns

| Column | Description |
|---|---|
| `property_address` or `address` | Street address attached to the property group |
| `floor_number` | Integer floor number |
| `bedrooms` | Integer count |
| `bathrooms` | Integer count |

### Sample CSV

```
property_name,property_address,building_name,flat_number,floor_number,bedrooms,bathrooms
Sunrise Towers,12 MG Road,Block A,A-101,1,2,1
Sunrise Towers,12 MG Road,Block A,A-102,1,3,2
Sunrise Towers,12 MG Road,Block B,B-201,2,2,1
```

### What gets skipped

A flat is skipped (not errored) when a flat with the same `flat_number` already exists in the database.

### What gets errored

A row is errored when:
- Any required column value is missing
- An unexpected exception occurs during DB insert (e.g. constraint violation)

---

## Import Type 2 — Tenants

### What it creates

One row per tenant. The backend:

- Looks up the flat by `flat_number` (case-insensitive)
- Creates the **Tenant** record and links it to the flat
- Optionally creates an active **Rent** record if `rent_amount` is provided

### Prerequisite

The flats must already exist — either created manually or via the Properties import above. The tenant import does NOT create flats.

### Required columns

| Column | Description |
|---|---|
| `name` | Tenant full name |
| `phone` | Phone number (E.164 recommended, e.g. `+919876543210`) |
| `flat_number` | Must match an existing flat (case-insensitive) |

### Optional columns

| Column | Description |
|---|---|
| `email` | Tenant email address |
| `lease_start_date` | ISO date, e.g. `2024-01-01` |
| `lease_end_date` | ISO date, e.g. `2025-01-01` |
| `rent_amount` | Monthly rent in INR (creates an active rent record) |
| `rent_status` | `On-time` / `Upcoming` / `Overdue` / `At Risk` |
| `manager_notes` | Free-text notes |

### Sample CSV

```
name,phone,email,flat_number,lease_start_date,lease_end_date,rent_amount,rent_status,manager_notes
Rahul Sharma,+919876543210,rahul@gmail.com,A-101,2024-01-01,2025-01-01,15000,On-time,
Priya Patel,+919988776655,priya@gmail.com,B-201,2024-06-01,2025-06-01,18000,Upcoming,Pets allowed
```

### What gets skipped

A row is skipped (not errored) when the flat is already occupied (has an existing tenant linked).

### What gets errored

A row is errored when:
- Any required column value is missing
- The flat number is not found in the database
- An unexpected exception occurs during insert

---

## Limits

| Limit | Value |
|---|---|
| Max file size | 5 MB |
| Max rows per file | 1 000 rows |
| File format | `.csv` (UTF-8 or UTF-8 with BOM) |

---

## Step-by-step walkthrough

1. **Download the template** — click "Download Template" in the modal footer to get a pre-formatted CSV with the correct column headers and sample rows.

2. **Fill in your data** — open the template in Excel, Google Sheets, or any text editor. Add one row per unit (Properties) or one row per tenant (Tenants).

3. **Upload** — drag the CSV into the drop zone or click "browse" to select the file. A preview of the first 3 rows appears so you can verify the column mapping before committing.

4. **Import** — click "Import N rows". The backend processes rows sequentially and returns a results panel showing:
   - How many records were **created**
   - Which rows were **skipped** (and why)
   - Which rows had **errors** (and why)

5. **Review results** — fix any errored rows in your spreadsheet and re-upload. Rows that already exist are skipped harmlessly, so it's safe to re-upload the full file.

---

## Recommended order for a fresh setup

1. Import **Properties** first — this creates your PropertyGroups, Buildings, and Flats.
2. Import **Tenants** second — flat numbers from step 1 must exist before tenants can be linked.

---

## Common gotchas

| Problem | Fix |
|---|---|
| "Missing required columns" error | Make sure the column headers match exactly (case-insensitive). Check for trailing spaces. |
| Flat not found for tenant import | Run the Properties import first, or create the flat manually. |
| Already occupied flat skipped | The flat already has a tenant. Remove or unassign the existing tenant first. |
| Unicode / special characters breaking the CSV | Save the file as "UTF-8" (not "UTF-16") from Excel. |
| Numbers parsed incorrectly (bedrooms, bathrooms) | Ensure there are no decimal places or currency symbols — use plain integers. |
