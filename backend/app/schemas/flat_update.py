from pydantic import BaseModel, Field
from typing import Optional, Literal
from app.schemas.flat import FlatUpdate

class TenantUpdate(BaseModel):
    """Schema for tenant data in update requests"""
    name: str = Field(..., min_length=1, description="Tenant's full name")
    phone: str = Field(..., min_length=10, description="Tenant's phone number")

class FlatEditRequest(BaseModel):
    """
    Request schema for editing a flat and managing its tenant.
    Combines flat details update with tenant operations.
    """
    # Flat fields to update (optional)
    flat_details: Optional[FlatUpdate] = None
    
    # Tenant operation
    action: Literal['UPDATE_FLAT_ONLY', 'ADD_TENANT', 'UPDATE_TENANT', 'REMOVE_TENANT'] = Field(
        ..., 
        description="Action to perform on the flat/tenant"
    )
    
    # Tenant data (required for ADD_TENANT and UPDATE_TENANT)
    tenant_data: Optional[TenantUpdate] = None
