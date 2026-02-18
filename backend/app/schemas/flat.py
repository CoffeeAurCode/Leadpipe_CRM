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
    occupied: Optional[bool] = Field(True, description="Is the flat currently occupied?")


class FlatCreate(BaseModel):
    """Schema for creating a new flat"""
    flat_number: str = Field(..., description="Unique flat/unit identifier (e.g., '101', 'A-205')")
    address: Optional[str] = Field(None, description="Building address or identifier")
    floor_number: Optional[int] = Field(None, ge=0, description="Floor number")
    bedrooms: Optional[int] = Field(None, ge=1, le=10, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, ge=0, le=10, description="Number of bathrooms")
    image_url: Optional[str] = Field(None, description="URL to property image in Supabase Storage")


class FlatUpdate(BaseModel):
    """Update flat information"""
    address: Optional[str] = None
    floor_number: Optional[int] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=10)
    bathrooms: Optional[int] = Field(None, ge=0, le=10)
    occupied: Optional[bool] = None


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
    uuid: UUID  # NEW: UUID for external references
    created_at: datetime
    image_url: Optional[str] = None  # Added image_url field
    tenant_uuid: Optional[UUID] = None  # FK to tenant
    tenant: Optional[TenantResponse] = None  # Nested tenant details
    
    model_config = ConfigDict(from_attributes=True)


class FlatVerifyRequest(BaseModel):
    """Schema for verifying if a flat exists (for VAPI)"""
    flat_number: str = Field(..., description="Flat number to verify")


class FlatVerifyResponse(BaseModel):
    """Schema for flat verification response"""
    exists: bool = Field(..., description="Whether the flat exists in the database")
    flat: Optional[FlatResponse] = Field(None, description="Flat details if exists")
