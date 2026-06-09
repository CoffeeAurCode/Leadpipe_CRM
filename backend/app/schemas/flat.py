from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class FlatBase(BaseModel):
    flat_number: str = Field(..., description="Unique flat/unit identifier (e.g., '101', 'A-205')")
    address: Optional[str] = Field(None, description="Building address or identifier")
    floor_number: Optional[int] = Field(None, description="Floor number")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")
    living_rooms: Optional[int] = Field(None, description="Number of living rooms")
    kitchen: Optional[int] = Field(None, description="Number of kitchens")
    occupied: Optional[bool] = Field(True, description="Is the flat currently occupied?")


class FlatCreate(BaseModel):
    """Schema for creating a new flat"""
    flat_number: str = Field(..., description="Unique flat/unit identifier (e.g., '101', 'A-205')")
    address: Optional[str] = Field(None, description="Legacy free-text address")
    floor_number: Optional[int] = Field(None, ge=0, description="Floor number")
    bedrooms: Optional[int] = Field(None, ge=1, le=10, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, ge=0, le=10, description="Number of bathrooms")
    living_rooms: Optional[int] = Field(None, ge=0, le=20, description="Number of living rooms")
    kitchen: Optional[int] = Field(None, ge=0, le=5, description="Number of kitchens")
    image_url: Optional[str] = Field(None, description="URL to property image in Supabase Storage")
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "Canada"


class FlatUpdate(BaseModel):
    """Update flat information"""
    address: Optional[str] = None
    floor_number: Optional[int] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=10)
    bathrooms: Optional[int] = Field(None, ge=0, le=10)
    living_rooms: Optional[int] = Field(None, ge=0, le=20)
    kitchen: Optional[int] = Field(None, ge=0, le=5)
    occupied: Optional[bool] = None
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class TenantResponse(BaseModel):
    """Schema for tenant in flat response"""
    id: int
    uuid: UUID
    name: str
    phone: str
    created_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)


class FlatResponse(FlatBase):
    """Schema for flat responses"""
    id: int
    uuid: UUID
    created_at: datetime
    image_url: Optional[str] = None
    tenant_uuid: Optional[UUID] = None
    tenant: Optional[TenantResponse] = None
    building_id: Optional[UUID] = None
    property_type_id: Optional[UUID] = None
    street_address: Optional[str] = None
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    quebec_size: Optional[str] = None
    building_name: Optional[str] = None
    property_name: Optional[str] = None
    is_listed: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class FlatVerifyPhoneRequest(BaseModel):
    """Schema for verifying a caller's phone against a flat's tenant (for VAPI)"""
    flat_number: Optional[str] = Field(None, description="Flat number to look up")
    phone_number: Optional[str] = Field(None, description="Caller's phone number — populated automatically from call metadata")


class FlatVerifyPhoneResponse(BaseModel):
    """Schema for phone verification response.

    result           — plain-English summary the LLM reads directly.
    status           — machine-readable status for VAPI variable extraction.
    datetime         — current IST time, only on valid responses.
    property_group_id — UUID of the PropertyGroup; only on valid responses.
    """
    result: str = Field(..., description="Plain-English outcome for the LLM")
    status: str = Field(..., description="'valid', 'invalid', or 'vacant'")
    datetime: Optional[str] = Field(None, description="Current server datetime in IST (ISO 8601), only on valid responses")
    property_group_id: Optional[str] = Field(None, description="PropertyGroup UUID, only on valid responses")
