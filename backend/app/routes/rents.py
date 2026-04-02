"""
Rent Management API routes.
Isolated module - does not touch existing flat/tenant/complaint logic.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from pydantic import BaseModel
from decimal import Decimal
from datetime import date
from typing import Optional

router = APIRouter(prefix="/rents", tags=["Rents"])


class RentSetRequest(BaseModel):
    flat_uuid: str
    monthly_rent: Decimal
    effective_from: date


class RentResponse(BaseModel):
    id: int
    flat_uuid: str
    monthly_rent: float
    effective_from: str
    is_active: bool
    created_at: str


@router.post("/set", status_code=status.HTTP_201_CREATED)
async def set_rent(request: RentSetRequest, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Set a new rent for a flat.
    - Deactivates previous active rent
    - Inserts new rent as active
    """
    flat_uuid = str(request.flat_uuid)

    # Deactivate any existing active rent for this flat
    db.table("rents") \
        .update({"is_active": False}) \
        .eq("flat_uuid", flat_uuid) \
        .eq("is_active", True) \
        .execute()

    # Insert new active rent
    new_rent = db.table("rents").insert({
        "flat_uuid": flat_uuid,
        "monthly_rent": float(request.monthly_rent),
        "effective_from": str(request.effective_from),
        "is_active": True,
    }).execute()

    if not new_rent.data:
        raise HTTPException(status_code=500, detail="Failed to create rent record")

    return new_rent.data[0]


@router.get("/{flat_uuid}")
async def get_active_rent(flat_uuid: str, user: dict = Depends(require_active_subscription), db: Client = Depends(get_authenticated_db)):
    """
    Returns the current active rent for a flat.
    Returns null if no rent is set.
    """
    result = db.table("rents") \
        .select("*") \
        .eq("flat_uuid", flat_uuid) \
        .eq("is_active", True) \
        .limit(1) \
        .execute()

    if not result.data:
        return {"rent": None}

    return {"rent": result.data[0]}
