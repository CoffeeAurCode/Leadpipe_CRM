from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum
from uuid import UUID


class AppointmentStatus(str, Enum):
    """Enum for appointment status"""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class AppointmentBase(BaseModel):
    appointment_date: datetime = Field(..., description="Scheduled date and time for the appointment")
    status: AppointmentStatus = Field(AppointmentStatus.SCHEDULED, description="Current status of the appointment")
    notes: Optional[str] = Field(None, description="Additional notes or instructions")


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment"""
    # NEW: UUID-based references (preferred)
    complaint_uuid: Optional[UUID] = Field(None, description="Related complaint UUID if linked to a complaint")
    flat_uuid: Optional[UUID] = Field(None, description="Flat UUID for the appointment")
    
    # DEPRECATED: Kept for backward compatibility
    complaint_id: Optional[int] = Field(None, description="Related complaint ID (deprecated, use complaint_uuid)")
    flat_number: Optional[str] = Field(None, description="Flat number (deprecated, use flat_uuid)")


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment"""
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment responses"""
    id: int
    uuid: UUID  # NEW: Appointment's own UUID
    
    # NEW: UUID references
    complaint_uuid: Optional[UUID] = None
    flat_uuid: Optional[UUID] = None
    
    # DEPRECATED: Legacy fields (still returned for compatibility)
    complaint_id: Optional[int] = None
    flat_number: Optional[str] = None
    
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

