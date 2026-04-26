"""
CSV Import API routes — bulk-import properties and tenants from CSV files.
No new dependencies: uses Python's built-in csv module.
"""
import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from supabase import Client

from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription

router = APIRouter(prefix="/import", tags=["Import"])

MAX_ROWS = 1000
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB

PROPERTIES_REQUIRED = {"property_name", "building_name", "flat_number"}
TENANTS_REQUIRED = {"name", "phone", "flat_number"}


def _parse_csv(content: bytes) -> tuple[list[dict], set[str]]:
    """Decode bytes → DictReader with lowercased, stripped keys."""
    text = content.decode("utf-8-sig")  # handle Excel BOM
    reader = csv.DictReader(io.StringIO(text))
    # Access fieldnames first so header is parsed even on empty CSVs
    raw_fields = reader.fieldnames or []
    fieldnames = {f.strip().lower() for f in raw_fields}
    rows = [
        {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        for row in reader
    ]
    return rows, fieldnames


# ── POST /import/properties ───────────────────────────────────────────────────

@router.post("/properties")
async def import_properties(
    file: UploadFile = File(...),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """
    Bulk-import PropertyGroup → Building → Flat hierarchy from a CSV.

    Required columns: property_name, building_name, flat_number
    Optional columns: property_address, floor_number, bedrooms, bathrooms

    PropertyGroups and Buildings are deduplicated within the import (and
    against existing DB rows).  Flats that already exist are skipped.
    """
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        rows, fieldnames = _parse_csv(content)
    except Exception as exc:
        raise HTTPException(400, f"Invalid CSV: {exc}")

    missing = PROPERTIES_REQUIRED - fieldnames
    if missing:
        raise HTTPException(400, f"Missing required columns: {', '.join(sorted(missing))}")

    if len(rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS})")

    created_properties = 0
    created_buildings = 0
    created_flats = 0
    skipped: list[str] = []
    errors: list[str] = []

    # In-memory caches to avoid redundant DB lookups within the same upload
    property_cache: dict[str, str] = {}       # name.lower() → uuid
    building_cache: dict[tuple, int] = {}     # (property_uuid, name.lower()) → int id

    for i, row in enumerate(rows, start=2):   # row 1 = header
        try:
            prop_name    = row.get("property_name", "")
            building_name = row.get("building_name", "")
            flat_number  = row.get("flat_number", "")
            prop_address = row.get("property_address", "") or row.get("address", "")

            if not prop_name or not building_name or not flat_number:
                errors.append(f"Row {i}: missing required value (property_name, building_name or flat_number)")
                continue

            # ── 1. Get or create PropertyGroup ────────────────────────────────
            prop_key = prop_name.lower()
            if prop_key not in property_cache:
                existing = (
                    db.table("properties_list")
                    .select("id")
                    .ilike("name", prop_name)
                    .execute()
                )
                if existing.data:
                    property_cache[prop_key] = existing.data[0]["id"]
                else:
                    payload: dict = {
                        "name": prop_name,
                        "manager_id": user["sub"],  # required by RLS policy
                    }
                    if prop_address:
                        payload["address"] = prop_address
                    created = db.table("properties_list").insert(payload).execute()
                    property_cache[prop_key] = created.data[0]["id"]
                    created_properties += 1

            property_uuid = property_cache[prop_key]

            # ── 2. Get or create Building ─────────────────────────────────────
            b_key = (property_uuid, building_name.lower())
            if b_key not in building_cache:
                existing = (
                    db.table("buildings")
                    .select("id")
                    .eq("property_id", property_uuid)
                    .ilike("name", building_name)
                    .execute()
                )
                if existing.data:
                    building_cache[b_key] = existing.data[0]["id"]
                else:
                    created = db.table("buildings").insert(
                        {"property_id": property_uuid, "name": building_name}
                    ).execute()
                    building_cache[b_key] = created.data[0]["id"]
                    created_buildings += 1

            building_id = building_cache[b_key]

            # ── 3. Skip if flat already exists ────────────────────────────────
            existing_flat = (
                db.table("flats")
                .select("uuid")
                .ilike("flat_number", flat_number)
                .execute()
            )
            if existing_flat.data:
                skipped.append(f"Row {i}: flat {flat_number} already exists")
                continue

            # ── 4. Create Flat ────────────────────────────────────────────────
            flat_payload: dict = {
                "building_id": building_id,
                "flat_number": flat_number.upper(),
            }
            for field, col in (("floor_number", "floor_number"), ("bedrooms", "bedrooms"), ("bathrooms", "bathrooms")):
                raw = row.get(field, "")
                if raw:
                    try:
                        flat_payload[col] = int(raw)
                    except ValueError:
                        pass

            db.table("flats").insert(flat_payload).execute()
            created_flats += 1

        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    return {
        "created": {
            "properties": created_properties,
            "buildings":  created_buildings,
            "flats":      created_flats,
        },
        "skipped": skipped,
        "errors":  errors,
    }


# ── POST /import/tenants ──────────────────────────────────────────────────────

@router.post("/tenants")
async def import_tenants(
    file: UploadFile = File(...),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    """
    Bulk-import Tenants from a CSV and link them to existing flats.

    Required columns: name, phone, flat_number
    Optional columns: email, lease_start_date, lease_end_date,
                      rent_amount, rent_status, manager_notes

    Already-occupied flats are skipped (not overwritten).
    If rent_amount is provided an active rent record is created.
    """
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        rows, fieldnames = _parse_csv(content)
    except Exception as exc:
        raise HTTPException(400, f"Invalid CSV: {exc}")

    missing = TENANTS_REQUIRED - fieldnames
    if missing:
        raise HTTPException(400, f"Missing required columns: {', '.join(sorted(missing))}")

    if len(rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS})")

    created_tenants = 0
    skipped: list[str] = []
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        try:
            name        = row.get("name", "")
            phone       = row.get("phone", "")
            flat_number = row.get("flat_number", "")

            if not name or not phone or not flat_number:
                errors.append(f"Row {i}: missing required value (name, phone or flat_number)")
                continue

            # ── 1. Find flat ──────────────────────────────────────────────────
            flat_resp = (
                db.table("flats")
                .select("uuid, tenant_uuid")
                .ilike("flat_number", flat_number)
                .execute()
            )
            if not flat_resp.data:
                errors.append(f"Row {i}: flat '{flat_number}' not found")
                continue

            flat = flat_resp.data[0]
            flat_uuid = flat["uuid"]

            if flat.get("tenant_uuid"):
                skipped.append(f"Row {i}: flat {flat_number} is already occupied")
                continue

            # ── 2. Build tenant payload ───────────────────────────────────────
            tenant_payload: dict = {"name": name, "phone": phone, "flat_uuid": flat_uuid}
            for field in ("email", "lease_start_date", "lease_end_date", "rent_status", "manager_notes"):
                val = row.get(field, "")
                if val:
                    tenant_payload[field] = val

            # ── 3. Create tenant ──────────────────────────────────────────────
            t_resp = db.table("tenants").insert(tenant_payload).execute()
            if not t_resp.data:
                errors.append(f"Row {i}: failed to create tenant record")
                continue

            tenant_uuid = t_resp.data[0]["uuid"]

            # ── 4. Bidirectionally link flat ──────────────────────────────────
            db.table("flats").update({
                "tenant_uuid": tenant_uuid,
                "occupied": True,
            }).eq("uuid", flat_uuid).execute()

            # ── 5. Create rent record if amount provided ───────────────────────
            rent_raw = row.get("rent_amount", "")
            if rent_raw:
                try:
                    monthly_rent = float(rent_raw)
                    effective_from = row.get("lease_start_date", "") or str(date.today())
                    db.table("rents").insert({
                        "flat_uuid":     flat_uuid,
                        "monthly_rent":  monthly_rent,
                        "effective_from": effective_from,
                        "is_active":     True,
                    }).execute()
                except (ValueError, TypeError):
                    pass  # bad rent amount — skip silently

            created_tenants += 1

        except Exception as exc:
            errors.append(f"Row {i}: {exc}")

    return {
        "created": created_tenants,
        "skipped": skipped,
        "errors":  errors,
    }
