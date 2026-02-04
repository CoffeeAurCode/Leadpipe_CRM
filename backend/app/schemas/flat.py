from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional


class FlatBase(BaseModel):
    flat_number: str = Field(..., description="Unique flat/apartment number")
    building_name: Optional[str] = Field(None, description="Building name or identifier")
    floor_number: Optional[int] = Field(None, ge=0, description="Floor number (0 for ground floor)")
    bedrooms: Optional[int] = Field(None, ge=0, le=10, description="Number of bedrooms")
    occupied: bool = Field(True, description="Whether the flat is currently occupied")


class FlatCreate(FlatBase):
    """Schema for creating a new flat"""
    pass


class FlatUpdate(BaseModel):
    """Schema for updating flat details"""
    building_name: Optional[str] = None
    floor_number: Optional[int] = Field(None, ge=0)
    bedrooms: Optional[int] = Field(None, ge=0, le=10)
    occupied: Optional[bool] = None


class FlatResponse(FlatBase):
    """Schema for flat responses"""
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class FlatVerifyRequest(BaseModel):
    """Schema for verifying if a flat exists (for VAPI)"""
    flat_number: str = Field(..., description="Flat number to verify")


class FlatVerifyResponse(BaseModel):
    """Schema for flat verification response"""
    exists: bool = Field(..., description="Whether the flat exists in the database")
    flat: Optional[FlatResponse] = Field(None, description="Flat details if exists")
