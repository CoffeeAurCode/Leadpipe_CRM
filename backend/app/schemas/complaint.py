from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID


class ComplaintBase(BaseModel):
    category: str
    appointment_datetime: str
    description: str
    status: str
    source: str = "AI_AGENT"


class ComplaintCreate(ComplaintBase):
    """Create complaint with UUID-based references (preferred) or legacy fields"""
    # NEW: UUID-based references (preferred)
    tenant_uuid: Optional[UUID] = None
    flat_uuid: Optional[UUID] = None
    
    # DEPRECATED: Kept for backward compatibility
    tenant_id: Optional[int] = None
    flat_number: Optional[str] = None


class ComplaintUpdate(BaseModel):
    """Update complaint fields"""
    category: Optional[str] = None
    appointment_datetime: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    
    # NEW: Allow updating UUID references
    flat_uuid: Optional[UUID] = None
    tenant_uuid: Optional[UUID] = None
    
    # DEPRECATED: Old fields
    flat_number: Optional[str] = None
    tenant_id: Optional[int] = None


class ComplaintResponse(ComplaintBase):
    """Response includes both UUID and legacy fields"""
    id: int
    uuid: UUID  # NEW: Complaint's own UUID
    
    # NEW: UUID references
    tenant_uuid: Optional[UUID] = None
    flat_uuid: Optional[UUID] = None
    
    # DEPRECATED: Legacy fields (still returned for compatibility)
    tenant_id: Optional[int] = None
    flat_number: Optional[str] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
