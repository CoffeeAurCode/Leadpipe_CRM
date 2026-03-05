"""Tenant schemas for API requests and responses"""
from pydantic import BaseModel, Field, ConfigDict, computed_field
from datetime import date, datetime
from typing import Optional
from uuid import UUID


class TenantBase(BaseModel):
    """Base tenant model with common fields"""
    name: str = Field(..., description="Tenant's full name")
    phone: str = Field(..., description="Tenant's phone number (unique)")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant"""
    flat_uuid: Optional[UUID] = Field(None, description="UUID of the flat this tenant lives in")
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    rent_status: Optional[str] = Field(None, description="On-time | Upcoming | Overdue | At Risk")
    payment_schedule: Optional[str] = Field(None, description="monthly | quarterly | custom")
    manager_notes: Optional[str] = None


class TenantUpdate(BaseModel):
    """Schema for updating tenant fields"""
    name: Optional[str] = Field(None, description="Update tenant's name")
    phone: Optional[str] = Field(None, description="Update tenant's phone")
    flat_uuid: Optional[UUID] = Field(None, description="Reassign tenant to a different flat")
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    rent_status: Optional[str] = None
    payment_schedule: Optional[str] = None
    manager_notes: Optional[str] = None


class TenantResponse(TenantBase):
    """Schema for tenant responses, with computed lease fields and joined data."""
    id: int
    uuid: UUID
    flat_uuid: Optional[UUID] = None
    created_at: datetime
    # Stored lease fields
    lease_start_date: Optional[date] = None
    lease_end_date: Optional[date] = None
    rent_status: Optional[str] = None
    payment_schedule: Optional[str] = None
    manager_notes: Optional[str] = None
    # Joined from flats table
    flat_number: Optional[str] = None
    # Joined from rents table (monthly_rent + effective_from where is_active=true)
    rent_amount: Optional[float] = None
    due_date: Optional[date] = None
    # Feature flag from property_features table
    tenant_details_enabled: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def tenancy_duration_months(self) -> Optional[int]:
        """Months since the tenant record was created."""
        if not self.created_at:
            return None
        now = datetime.now(tz=self.created_at.tzinfo)
        return max(0, int((now - self.created_at).days / 30))

    @computed_field
    @property
    def lease_duration_months(self) -> Optional[int]:
        """Total months covered by the lease contract."""
        if not self.lease_start_date or not self.lease_end_date:
            return None
        return max(0, int((self.lease_end_date - self.lease_start_date).days / 30))

    @computed_field
    @property
    def remaining_time_on_lease_days(self) -> Optional[int]:
        """Days remaining until lease_end_date (negative if already expired)."""
        if not self.lease_end_date:
            return None
        return (self.lease_end_date - date.today()).days

    @computed_field
    @property
    def lease_status(self) -> str:
        """Derived status: Active | Expiring Soon | Expired | No Lease."""
        if not self.lease_start_date or not self.lease_end_date:
            return "No Lease"
        today = date.today()
        if self.lease_end_date < today:
            return "Expired"
        remaining = (self.lease_end_date - today).days
        if remaining <= 30:
            return "Expiring Soon"
        if self.lease_start_date <= today:
            return "Active"
        return "Upcoming"


class TenantWithFlat(TenantResponse):
    """Extended response with flat address"""
    address: Optional[str] = None
