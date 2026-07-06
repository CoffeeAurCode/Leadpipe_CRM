import csv
import io
import json
import os
import re
from datetime import date

import openpyxl
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from groq import AsyncGroq
from openai import AsyncOpenAI
from supabase import Client

from app.config import settings
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.core.db_errors import clean_db_error
from app.core.phone import normalize_phone_e164

router = APIRouter(prefix="/import", tags=["Import"])

MAX_ROWS = 1000
MAX_FILE_BYTES = 5 * 1024 * 1024

# Only flat_number is mandatory. A row WITH a building_name creates a unit inside a
# property/building; a row WITHOUT a building_name creates a STANDALONE unit
# (building_id NULL) owned directly by the importing manager.
PROPERTIES_REQUIRED = {"flat_number"}
PROPERTIES_OPTIONAL = {
    "property_name", "building_name", "property_address", "address",
    "street_address", "address_line", "city", "state", "country",
    "floor_number", "bedrooms", "bathrooms", "living_rooms", "kitchen",
    "tenant_name", "tenant_phone", "rent_amount", "lease_start_date",
}
TENANTS_REQUIRED = {"name", "phone", "flat_number"}
TENANTS_OPTIONAL = {"email", "lease_start_date", "lease_end_date", "rent_amount", "rent_status", "manager_notes"}

_SCHEMA = {
    "properties": {
        "required": {
            "flat_number": "Unit identifier — letters and numbers only (e.g. A101)",
        },
        "optional": {
            "property_name": "Top-level property group name — LEAVE BLANK for standalone units (bungalow/house)",
            "building_name": "Building inside the property — LEAVE BLANK for standalone units",
            "property_address": "Street address of the property",
            "floor_number": "Integer floor number",
            "bedrooms": "Number of bedrooms (integer)",
            "bathrooms": "Number of bathrooms (integer)",
            "living_rooms": "Number of living rooms (integer)",
            "kitchen": "Number of kitchens (integer)",
            "tenant_name": "Tenant full name — fill to mark the unit occupied, leave blank for vacant",
            "tenant_phone": "Tenant phone — required alongside tenant_name to create the tenant",
            "rent_amount": "Monthly rent as a plain number (only used when a tenant is given)",
        },
    },
    "tenants": {
        "required": {
            "name": "Tenant full name",
            "phone": "Phone number (e.g. +919876543210)",
            "flat_number": "Flat/unit number the tenant lives in — letters and numbers only (e.g. A101)",
        },
        "optional": {
            "email": "Tenant email address",
            "lease_start_date": "Lease start date ISO format (2024-01-01)",
            "lease_end_date": "Lease end date ISO format (2025-01-01)",
            "rent_amount": "Monthly rent as a plain number (e.g. 15000)",
            "rent_status": "On-time / Upcoming / Overdue / At Risk",
            "manager_notes": "Free-text notes",
        },
    },
}


_INVALID_FLAT_RE = re.compile(r'[^A-Za-z0-9]')


def _strip_flat_number(s: str) -> str:
    return _INVALID_FLAT_RE.sub('', s)


def _find_invalid_flat_numbers(rows: list[dict]) -> list[dict]:
    seen: dict[str, str] = {}
    for row in rows:
        orig = row.get("flat_number", "")
        if orig and _INVALID_FLAT_RE.search(orig) and orig not in seen:
            seen[orig] = _strip_flat_number(orig)
    return [{"original": k, "sanitized": v} for k, v in seen.items()]


def _flat_attrs_from_row(row: dict) -> dict:
    """Pull the optional unit attributes (numbers + structured address) out of a CSV row."""
    payload: dict = {}
    for field in ("floor_number", "bedrooms", "bathrooms", "living_rooms", "kitchen"):
        raw = row.get(field, "")
        if raw:
            try:
                payload[field] = int(raw)
            except ValueError:
                pass
    for field in ("street_address", "address_line", "city", "state", "country"):
        val = row.get(field, "")
        if val:
            payload[field] = val
    return payload


def _maybe_create_tenant_and_rent(db, row: dict, flat: dict, skipped: list, errors: list, i: int) -> None:
    """If the row carries tenant_name + tenant_phone, create the tenant, mark the unit
    occupied, and (optionally) add an active rent record. Blank tenant cols => vacant unit."""
    name = row.get("tenant_name", "").strip()
    phone = row.get("tenant_phone", "").strip()
    if not (name and phone):
        return  # vacant — nothing to do
    normalized_phone = normalize_phone_e164(phone)
    if not normalized_phone:
        errors.append(
            f"Row {i}: unit created but tenant_phone '{phone}' is not a valid phone number "
            f"(include country code, e.g. +15145550130) — tenant not created"
        )
        return
    flat_uuid = flat["uuid"]
    try:
        t = db.table("tenants").insert({"name": name, "phone": normalized_phone, "flat_uuid": flat_uuid}).execute()
        if not t.data:
            errors.append(f"Row {i}: unit created but tenant could not be added")
            return
        db.table("flats").update({"tenant_uuid": t.data[0]["uuid"], "occupied": True}).eq("uuid", flat_uuid).execute()
    except Exception as exc:
        errors.append(f"Row {i}: unit created but tenant failed — {clean_db_error(exc)}")
        return
    rent_raw = row.get("rent_amount", "").strip()
    if rent_raw:
        try:
            db.table("rents").insert({
                "flat_uuid": flat_uuid,
                "monthly_rent": float(rent_raw),
                "effective_from": row.get("lease_start_date", "") or str(date.today()),
                "is_active": True,
            }).execute()
        except (ValueError, TypeError):
            skipped.append(f"Row {i} ({name}): rent_amount '{rent_raw}' is not a number — tenant added without rent")


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_csv(content: bytes) -> tuple[list[dict], set[str]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    raw_fields = reader.fieldnames or []
    fieldnames = {f.strip().lower() for f in raw_fields}
    rows = [
        {k.strip().lower(): (v or "").strip() for k, v in row.items()}
        for row in reader
    ]
    return rows, fieldnames


def _parse_xlsx(content: bytes) -> tuple[list[dict], set[str]]:
    wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    first_row = next(rows_iter, None)
    if first_row is None:
        return [], set()
    raw_headers = [str(h).strip() if h is not None else "" for h in first_row]
    fieldnames = {h.lower() for h in raw_headers if h}
    rows = []
    for excel_row in rows_iter:
        row_dict = {
            h.strip().lower(): (str(v).strip() if v is not None else "")
            for h, v in zip(raw_headers, excel_row)
            if h.strip()
        }
        if any(row_dict.values()):
            rows.append(row_dict)
    return rows, fieldnames


def _detect_and_parse(content: bytes, filename: str) -> tuple[list[dict], set[str]]:
    if filename.lower().endswith(".xlsx"):
        return _parse_xlsx(content)
    return _parse_csv(content)


# ── Mapping helpers ───────────────────────────────────────────────────────────

def _apply_mapping(rows: list[dict], mapping: dict) -> list[dict]:
    result = []
    for row in rows:
        new_row = {}
        for orig_key, val in row.items():
            target = mapping.get(orig_key)
            if target:
                new_row[target] = val
        result.append(new_row)
    return result


async def _map_columns_with_ai(
    headers: list[str],
    sample_rows: list[dict],
    import_type: str,
) -> dict:
    schema = _SCHEMA[import_type]
    all_targets = set(schema["required"]) | set(schema["optional"])

    req_lines = "\n".join(f"  - {k}: {v}" for k, v in schema["required"].items())
    opt_lines = "\n".join(f"  - {k}: {v}" for k, v in schema["optional"].items())
    sample_text = "\n".join(
        "  " + ", ".join(f"{k}={v!r}" for k, v in row.items())
        for row in sample_rows[:3]
    )

    prompt = (
        f"You are a data-mapping assistant for a property management system.\n\n"
        f"Import type: {import_type}\n\n"
        f"REQUIRED TARGET COLUMNS:\n{req_lines}\n\n"
        f"OPTIONAL TARGET COLUMNS:\n{opt_lines}\n\n"
        f"ACTUAL HEADERS from uploaded file: {headers}\n\n"
        f"SAMPLE DATA (first rows):\n{sample_text}\n\n"
        f"Map each actual header to its best-matching target column, or null if irrelevant.\n"
        f"Return ONLY valid JSON. Example: {{\"Tenant Name\": \"name\", \"Mobile\": \"phone\", \"Extra\": null}}"
    )

    async def _call_openai():
        client = AsyncOpenAI(api_key=settings.OPEN_AI_API)
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(r.choices[0].message.content)

    async def _call_groq():
        client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
        r = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        return json.loads(r.choices[0].message.content)

    raw_mapping = None
    for attempt in (_call_openai, _call_groq):
        try:
            raw_mapping = await attempt()
            break
        except Exception:
            continue

    if raw_mapping is None:
        return {h: None for h in headers}

    sanitized: dict = {}
    for orig, target in raw_mapping.items():
        sanitized[orig] = target if (target and target in all_targets) else None
    for h in headers:
        if h not in sanitized:
            sanitized[h] = None
    return sanitized


# ── POST /import/analyze ──────────────────────────────────────────────────────

@router.post("/analyze")
async def analyze_import(
    file: UploadFile = File(...),
    import_type: str = Form(...),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    if import_type not in ("properties", "tenants"):
        raise HTTPException(400, "import_type must be 'properties' or 'tenants'")

    try:
        rows, fieldnames = _detect_and_parse(content, file.filename or "")
    except Exception as exc:
        raise HTTPException(400, f"Cannot parse file: {exc}")

    required = PROPERTIES_REQUIRED if import_type == "properties" else TENANTS_REQUIRED
    missing = required - fieldnames

    if not missing:
        return {"needs_mapping": False, "row_count": len(rows)}

    headers_list = sorted(fieldnames)
    mapping = await _map_columns_with_ai(headers_list, rows[:3], import_type)

    mapped_targets = {v for v in mapping.values() if v}
    unmapped_required = sorted(required - mapped_targets)

    return {
        "needs_mapping": True,
        "mapping": mapping,
        "unmapped_required": unmapped_required,
        "row_count": len(rows),
    }


# ── POST /import/properties ───────────────────────────────────────────────────

@router.post("/properties")
async def import_properties(
    file: UploadFile = File(...),
    column_mapping: str = Form(None),
    sanitize_flat_numbers: bool = Form(False),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        rows, fieldnames = _detect_and_parse(content, file.filename or "")
    except Exception as exc:
        raise HTTPException(400, f"Invalid file: {exc}")

    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            raise HTTPException(400, "Invalid column_mapping JSON")
        rows = _apply_mapping(rows, mapping)
        fieldnames = {k for row in rows for k in row.keys()}

    missing = PROPERTIES_REQUIRED - fieldnames
    if missing:
        raise HTTPException(400, f"Missing required columns: {', '.join(sorted(missing))}")

    if len(rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS})")

    if not sanitize_flat_numbers:
        invalid = _find_invalid_flat_numbers(rows)
        if invalid:
            return {"flat_number_warning": True, "affected": invalid}

    created_properties = 0
    created_buildings = 0
    created_flats = 0
    skipped: list[str] = []
    errors: list[str] = []

    property_cache: dict[str, str] = {}
    building_cache: dict[tuple, int] = {}

    for i, row in enumerate(rows, start=2):
        try:
            prop_name     = row.get("property_name", "")
            building_name = row.get("building_name", "")
            flat_number   = row.get("flat_number", "")
            if sanitize_flat_numbers:
                flat_number = _strip_flat_number(flat_number)
            prop_address  = row.get("property_address", "") or row.get("address", "")

            if not flat_number:
                errors.append(f"Row {i}: missing required value (flat_number)")
                continue

            # ── Standalone unit: no building_name → building-less flat owned directly by the manager
            if not building_name:
                existing_flat = (
                    db.table("flats")
                    .select("uuid")
                    .ilike("flat_number", flat_number)
                    .is_("building_id", "null")
                    .execute()
                )
                if existing_flat.data:
                    skipped.append(f"Row {i}: standalone unit {flat_number} already exists")
                    continue
                flat_payload: dict = {
                    "flat_number": flat_number.upper(),
                    "building_id": None,
                    "manager_id": user["sub"],
                    "occupied": False,
                    **_flat_attrs_from_row(row),
                }
                created = db.table("flats").insert(flat_payload).execute()
                created_flats += 1
                _maybe_create_tenant_and_rent(db, row, created.data[0], skipped, errors, i)
                continue

            # ── Building-attached unit: a building needs a parent property
            if not prop_name:
                errors.append(f"Row {i}: building_name is set but property_name is missing")
                continue

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
                    payload: dict = {"name": prop_name, "manager_id": user["sub"]}
                    if prop_address:
                        payload["address"] = prop_address
                    created = db.table("properties_list").insert(payload).execute()
                    property_cache[prop_key] = created.data[0]["id"]
                    created_properties += 1

            property_uuid = property_cache[prop_key]

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

            existing_flat = (
                db.table("flats")
                .select("uuid")
                .ilike("flat_number", flat_number)
                .eq("building_id", building_id)
                .execute()
            )
            if existing_flat.data:
                skipped.append(f"Row {i}: flat {flat_number} already exists")
                continue

            flat_payload: dict = {
                "building_id": building_id,
                "flat_number": flat_number.upper(),
                "manager_id": user["sub"],
                "occupied": False,
                **_flat_attrs_from_row(row),
            }
            created = db.table("flats").insert(flat_payload).execute()
            created_flats += 1
            _maybe_create_tenant_and_rent(db, row, created.data[0], skipped, errors, i)

        except Exception as exc:
            errors.append(f"Row {i}: {clean_db_error(exc)}")

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
    column_mapping: str = Form(None),
    sanitize_flat_numbers: bool = Form(False),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
):
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large (max 5 MB)")

    try:
        rows, fieldnames = _detect_and_parse(content, file.filename or "")
    except Exception as exc:
        raise HTTPException(400, f"Invalid file: {exc}")

    if column_mapping:
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            raise HTTPException(400, "Invalid column_mapping JSON")
        rows = _apply_mapping(rows, mapping)
        fieldnames = {k for row in rows for k in row.keys()}

    missing = TENANTS_REQUIRED - fieldnames
    if missing:
        raise HTTPException(400, f"Missing required columns: {', '.join(sorted(missing))}")

    if len(rows) > MAX_ROWS:
        raise HTTPException(400, f"Too many rows (max {MAX_ROWS})")

    if not sanitize_flat_numbers:
        invalid = _find_invalid_flat_numbers(rows)
        if invalid:
            return {"flat_number_warning": True, "affected": invalid}

    created_tenants = 0
    skipped: list[str] = []
    errors: list[str] = []

    for i, row in enumerate(rows, start=2):
        try:
            name        = row.get("name", "")
            phone       = row.get("phone", "")
            flat_number = row.get("flat_number", "")
            if sanitize_flat_numbers:
                flat_number = _strip_flat_number(flat_number)

            if not name or not phone or not flat_number:
                errors.append(f"Row {i}: missing required value (name, phone or flat_number)")
                continue

            normalized_phone = normalize_phone_e164(phone)
            if not normalized_phone:
                errors.append(
                    f"Row {i}: phone '{phone}' is not a valid phone number "
                    f"(include country code, e.g. +15145550130)"
                )
                continue
            phone = normalized_phone

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

            VALID_RENT_STATUSES = {"On-time", "Upcoming", "Overdue", "At Risk"}
            raw_status = row.get("rent_status", "").strip()
            rent_status = raw_status if raw_status in VALID_RENT_STATUSES else None

            tenant_payload: dict = {"name": name, "phone": phone, "flat_uuid": flat_uuid}
            for field in ("email", "lease_start_date", "lease_end_date", "manager_notes"):
                val = row.get(field, "")
                if val:
                    tenant_payload[field] = val
            if rent_status:
                tenant_payload["rent_status"] = rent_status

            t_resp = db.table("tenants").insert(tenant_payload).execute()
            if not t_resp.data:
                errors.append(f"Row {i}: failed to create tenant record")
                continue

            tenant_uuid = t_resp.data[0]["uuid"]

            db.table("flats").update({
                "tenant_uuid": tenant_uuid,
                "occupied": True,
            }).eq("uuid", flat_uuid).execute()

            rent_amount_raw = row.get("rent_amount", "").strip()
            if rent_amount_raw:
                try:
                    monthly_rent = float(rent_amount_raw)
                    effective_from = row.get("lease_start_date", "") or str(date.today())
                    db.table("rents").insert({
                        "flat_uuid":      flat_uuid,
                        "monthly_rent":   monthly_rent,
                        "effective_from": effective_from,
                        "is_active":      True,
                    }).execute()
                except (ValueError, TypeError):
                    skipped.append(
                        f"Row {i} ({name}): rent_amount '{rent_amount_raw}' is not a valid number — "
                        f"tenant imported without a rent record"
                    )

            created_tenants += 1

        except Exception as exc:
            errors.append(f"Row {i}: {clean_db_error(exc)}")

    return {
        "created": created_tenants,
        "skipped": skipped,
        "errors":  errors,
    }
