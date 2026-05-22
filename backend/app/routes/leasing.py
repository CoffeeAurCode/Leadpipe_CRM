import json
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from supabase import Client

from app.db.session import get_service_db
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.schemas.leasing import ListingCreate, ListingUpdate, ListingResponse, LeadUpdate, LeadResponse

router = APIRouter(prefix="/leasing", tags=["Leasing"])

IST = timezone(timedelta(hours=5, minutes=30))


# ===========================================================================
# VAPI Tool Endpoints — no auth, always return 200, use service DB
# ===========================================================================

@router.get("/find-listing")
async def find_listing(
    query: str = Query(...),
    property_group_id: Optional[str] = Query(None),
    db: Client = Depends(get_service_db),
):
    """
    VAPI apiRequest tool — Find a listing by address or unit query.
    property_group_id is optional; when absent, searches all groups.
    Always returns HTTP 200.
    """
    try:
        q = (
            db.table("lease_listings")
            .select(
                "uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                "flats!inner(bedrooms, floor_number, address)"
            )
            .eq("is_active", True)
        )
        if property_group_id:
            q = q.eq("property_group_id", property_group_id)

        results = q.ilike("flat_number", f"%{query}%").limit(1).execute()

        if not results.data:
            fallback_q = (
                db.table("lease_listings")
                .select(
                    "uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                    "flats!inner(bedrooms, floor_number, address)"
                )
                .eq("is_active", True)
                .ilike("title", f"%{query}%")
                .limit(1)
            )
            if property_group_id:
                fallback_q = fallback_q.eq("property_group_id", property_group_id)
            results = fallback_q.execute()

        if not results.data:
            return {"found": False}

        listing = results.data[0]
        flat = listing.get("flats") or {}
        return {
            "found": True,
            "listing_uuid": listing["uuid"],
            "address": flat.get("address"),
            "bedrooms": flat.get("bedrooms"),
            "monthly_rent": float(listing["monthly_rent"]),
            "floor_number": str(flat.get("floor_number") or ""),
            "available_from": str(listing.get("available_from") or ""),
            "custom_rules": json.dumps(listing.get("custom_rules") or {}),
        }
    except Exception as e:
        print(f"[ERROR] find_listing: {e}")
        return {"found": False}


@router.get("/search")
async def search_available_listings(
    bedrooms: Optional[int] = Query(None),
    budget_max: Optional[float] = Query(None),
    property_group_id: Optional[str] = Query(None),
    db: Client = Depends(get_service_db),
):
    """
    VAPI apiRequest tool — Search listings by bedrooms and budget.
    property_group_id is optional; when absent, searches all groups.
    Always returns HTTP 200.
    """
    try:
        q = (
            db.table("lease_listings")
            .select(
                "uuid, flat_number, title, monthly_rent, available_from, custom_rules, "
                "flats!inner(bedrooms, floor_number, address)"
            )
            .eq("is_active", True)
        )
        if property_group_id:
            q = q.eq("property_group_id", property_group_id)
        if bedrooms is not None:
            q = q.eq("flats.bedrooms", bedrooms)
        if budget_max is not None:
            q = q.lte("monthly_rent", budget_max)

        results = q.limit(5).execute()

        if not results.data:
            return {"count": 0, "listings": []}

        listings_out = []
        for listing in results.data:
            flat = listing.get("flats") or {}
            listings_out.append({
                "listing_uuid": listing["uuid"],
                "flat_number": listing["flat_number"],
                "title": listing.get("title") or "",
                "bedrooms": flat.get("bedrooms"),
                "monthly_rent": float(listing["monthly_rent"]),
                "floor_number": str(flat.get("floor_number") or ""),
                "available_from": str(listing.get("available_from") or ""),
            })

        return {"count": len(listings_out), "listings": listings_out}
    except Exception as e:
        print(f"[ERROR] search_available_listings: {e}")
        return {"count": 0, "listings": []}


# ===========================================================================
# Manager CRUD — authenticated, RLS-enforced
# ===========================================================================

@router.get("/listings", response_model=List[ListingResponse])
async def get_listings(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    resp = db.table("lease_listings").select("*").eq("manager_id", user["sub"]).order("created_at", desc=True).execute()
    return resp.data or []


@router.post("/listings", response_model=ListingResponse, status_code=201)
async def create_listing(
    body: ListingCreate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db),
    svc_db: Client = Depends(get_service_db),
):
    # Ownership check via RLS-enforced authenticated client
    flat_resp = db.table("flats").select("flat_number, building_id").eq("uuid", str(body.flat_uuid)).limit(1).execute()
    if not flat_resp.data:
        raise HTTPException(status_code=404, detail="Flat not found")

    flat = flat_resp.data[0]
    flat_number = flat["flat_number"]

    building_resp = (
        db.table("buildings")
        .select("property_id")
        .eq("id", flat["building_id"])
        .limit(1)
        .execute()
    )
    if not building_resp.data:
        raise HTTPException(status_code=400, detail="Flat is not linked to a building")

    property_group_id = str(building_resp.data[0]["property_id"])

    payload = body.model_dump(exclude_none=True)
    payload["flat_uuid"] = str(body.flat_uuid)
    payload["flat_number"] = flat_number
    payload["property_group_id"] = property_group_id
    payload["manager_id"] = user.get("sub")

    if "custom_rules" in payload and hasattr(payload["custom_rules"], "model_dump"):
        payload["custom_rules"] = payload["custom_rules"].model_dump()
    if "available_from" in payload and payload["available_from"] is not None:
        payload["available_from"] = str(payload["available_from"])
    from decimal import Decimal
    payload = {k: float(v) if isinstance(v, Decimal) else v for k, v in payload.items()}

    # Use service client for INSERT — lease_listings has no RLS INSERT policy yet
    resp = svc_db.table("lease_listings").insert(payload).execute()
    if not resp.data:
        raise HTTPException(status_code=500, detail="Failed to create listing")
    return resp.data[0]


@router.patch("/listings/{listing_uuid}", response_model=ListingResponse)
async def update_listing(
    listing_uuid: str,
    body: ListingUpdate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    payload = body.model_dump(exclude_unset=True)
    if "custom_rules" in payload and payload["custom_rules"] is not None:
        if hasattr(payload["custom_rules"], "model_dump"):
            payload["custom_rules"] = payload["custom_rules"].model_dump()
    if "available_from" in payload and payload["available_from"] is not None:
        payload["available_from"] = str(payload["available_from"])

    payload["updated_at"] = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")
    from decimal import Decimal
    payload = {k: float(v) if isinstance(v, Decimal) else v for k, v in payload.items()}

    resp = db.table("lease_listings").update(payload).eq("uuid", listing_uuid).eq("manager_id", user["sub"]).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Listing not found")
    return resp.data[0]


@router.delete("/listings/{listing_uuid}", status_code=204)
async def delete_listing(
    listing_uuid: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    db.table("lease_listings").delete().eq("uuid", listing_uuid).eq("manager_id", user["sub"]).execute()
    return None


@router.get("/leads", response_model=List[LeadResponse])
async def get_leads(
    listing_uuid: Optional[str] = Query(None),
    qualification_status: Optional[str] = Query(None),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    q = db.table("lease_leads").select("*").eq("manager_id", user["sub"]).order("created_at", desc=True)
    if listing_uuid:
        q = q.or_(f"listing_uuid.eq.{listing_uuid},interested_listing_ids.cs.{{{listing_uuid}}}")
    if qualification_status:
        q = q.eq("qualification_status", qualification_status)
    resp = q.execute()
    return resp.data or []


@router.patch("/leads/{lead_uuid}", response_model=LeadResponse)
async def update_lead(
    lead_uuid: str,
    body: LeadUpdate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    _MANAGER_EDITABLE_STATUSES = {"contacted", "toured", "converted", "lost"}
    payload = body.model_dump(exclude_unset=True)

    if "qualification_status" in payload and payload["qualification_status"] not in _MANAGER_EDITABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Managers can only set status to: contacted, toured, converted, lost",
        )

    payload["updated_at"] = datetime.now(IST).strftime("%Y-%m-%dT%H:%M:%S")

    resp = db.table("lease_leads").update(payload).eq("uuid", lead_uuid).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Lead not found")
    return resp.data[0]


@router.delete("/leads/{lead_uuid}", status_code=204)
async def delete_lead(
    lead_uuid: str,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    db.table("lease_leads").delete().eq("uuid", lead_uuid).execute()
    return None


@router.get("/metrics")
async def get_leasing_metrics(
    days: int = Query(30),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    q = db.table("lease_leads").select("qualification_status, call_duration_seconds")\
        .eq("manager_id", user["sub"])\
        .gte("created_at", since)
    resp = q.execute()
    leads = resp.data or []

    total = len(leads)
    qualified = sum(1 for l in leads if l["qualification_status"] == "qualified")
    not_qualified = sum(1 for l in leads if l["qualification_status"] == "not_qualified")
    unmatched = sum(1 for l in leads if l["qualification_status"] == "unmatched")

    durations = [l["call_duration_seconds"] for l in leads if l.get("call_duration_seconds")]
    avg_duration = int(sum(durations) / len(durations)) if durations else 0

    return {
        "total_calls": total,
        "qualified": qualified,
        "not_qualified": not_qualified,
        "unmatched": unmatched,
        "qualification_rate": round(qualified / total * 100, 1) if total else 0,
        "avg_duration_seconds": avg_duration,
    }


@router.get("/export")
async def export_leads(
    listing_uuid: Optional[str] = Query(None),
    qualification_status: Optional[str] = Query(None),
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_service_db),
):
    q = db.table("lease_leads").select("*").eq("manager_id", user["sub"]).order("created_at", desc=True)
    if listing_uuid:
        q = q.eq("listing_uuid", listing_uuid)
    if qualification_status:
        q = q.eq("qualification_status", qualification_status)
    resp = q.execute()
    leads = resp.data or []

    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        "Name", "Phone", "Email", "Bedrooms", "Budget Max", "Move-in Timeline",
        "Occupants", "Floor Preference", "Qualification Status", "Disqualifying Reason",
        "Notes", "Manager Notes", "Source", "Call ID", "Created At",
    ]
    writer.writerow(headers)
    for lead in leads:
        writer.writerow([
            lead.get("caller_name", ""),
            lead.get("phone", ""),
            lead.get("email", ""),
            lead.get("bedrooms", ""),
            lead.get("budget_max", ""),
            lead.get("move_in_timeline", ""),
            lead.get("occupants", ""),
            lead.get("floor_preference", ""),
            lead.get("qualification_status", ""),
            lead.get("disqualifying_reason", ""),
            lead.get("notes", ""),
            lead.get("manager_notes", ""),
            lead.get("source", ""),
            lead.get("call_id", ""),
            lead.get("created_at", ""),
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
