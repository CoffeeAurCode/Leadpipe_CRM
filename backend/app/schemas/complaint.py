from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class ComplaintBase(BaseModel):
    flat_number: Optional[str] = None
    category: str
    priority: str
    description: str
    status: str
    source: str = "AI_AGENT"


class ComplaintCreate(ComplaintBase):
    tenant_id: Optional[int] = None


class ComplaintUpdate(BaseModel):
    flat_number: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    tenant_id: Optional[int] = None


class ComplaintResponse(ComplaintBase):
    id: int
    tenant_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
