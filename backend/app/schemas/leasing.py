from pydantic import BaseModel, Field
from typing import Optional, List, Any
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal


class CustomRules(BaseModel):
    max_occupants: Optional[int] = None
    income_required: Optional[bool] = False
    pets_allowed: Optional[str] = "no"
    vegetarian_only: Optional[bool] = False
    lease_term_months: Optional[int] = 11
    custom_question: Optional[str] = ""


class ListingCreate(BaseModel):
    flat_uuid: UUID
    title: Optional[str] = None
    monthly_rent: Decimal
    description: Optional[str] = None
    available_from: Optional[date] = None
    photo_urls: Optional[List[str]] = Field(default_factory=list)
    is_active: Optional[bool] = True
    custom_rules: Optional[CustomRules] = Field(default_factory=CustomRules)


class ListingUpdate(BaseModel):
    title: Optional[str] = None
    monthly_rent: Optional[Decimal] = None
    description: Optional[str] = None
    available_from: Optional[date] = None
    photo_urls: Optional[List[str]] = None
    is_active: Optional[bool] = None
    custom_rules: Optional[CustomRules] = None


class ListingResponse(BaseModel):
    id: int
    uuid: UUID
    property_group_id: UUID
    flat_uuid: UUID
    flat_number: str
    title: Optional[str] = None
    monthly_rent: Decimal
    description: Optional[str] = None
    available_from: Optional[date] = None
    photo_urls: List[str] = Field(default_factory=list)
    is_active: bool
    custom_rules: Any = Field(default_factory=dict)
    manager_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class LeadUpdate(BaseModel):
    qualification_status: Optional[str] = None
    manager_notes: Optional[str] = None
    notes: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    uuid: UUID
    property_group_id: Optional[UUID] = None
    manager_id: Optional[UUID] = None
    listing_uuid: Optional[UUID] = None
    interested_listing_ids: Optional[List[UUID]] = Field(default_factory=list)
    caller_name: str
    phone: str
    email: Optional[str] = None
    bedrooms: Optional[int] = None
    budget_max: Optional[Decimal] = None
    move_in_timeline: Optional[str] = None
    occupants: Optional[int] = None
    floor_preference: Optional[str] = None
    qualification_status: str
    disqualifying_reason: Optional[str] = None
    qualifying_answers: Any = Field(default_factory=dict)
    notes: Optional[str] = None
    source: Optional[str] = "voice"
    call_id: Optional[str] = None
    call_duration_seconds: Optional[int] = None
    manager_notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
