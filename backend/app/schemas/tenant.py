"""Tenant schemas for API requests and responses"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class TenantBase(BaseModel):
    """Base tenant model with common fields"""
    name: str = Field(..., description="Tenant's full name")
    phone: str = Field(..., description="Tenant's phone number (unique)")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""
    flat_uuid: Optional[UUID] = Field(None, description="UUID of the flat this tenant lives in")


class TenantUpdate(BaseModel):
    """Schema for updating tenant fields"""
    name: Optional[str] = Field(None, description="Update tenant's name")
    phone: Optional[str] = Field(None, description="Update tenant's phone")
    flat_uuid: Optional[UUID] = Field(None, description="Reassign tenant to a different flat")


class TenantResponse(TenantBase):
    """Schema for tenant responses"""
    id: int
    uuid: UUID  # Tenant's unique identifier
    flat_uuid: Optional[UUID] = None  # Which flat does this tenant live in?
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class TenantWithFlat(TenantResponse):
    """Extended response with flat details"""
    flat_number: Optional[str] = None  # Denormalized for convenience
    address: Optional[str] = None
