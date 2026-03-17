from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List
from enum import Enum
from uuid import UUID


class AppointmentStatus(str, Enum):
    """Enum for appointment status"""
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    DONE = "done"
    COMPLETED = "completed"   # legacy alias — VAPI uses this value



class AppointmentBase(BaseModel):
    appointment_date: str = Field(..., description="Scheduled date and time for the appointment")
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
    appointment_date: Optional[str] = None
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


# ---------------------------------------------------------------------------
# VAPI-specific schemas for GET /appointments/view
# ---------------------------------------------------------------------------

class VapiAppointmentViewItem(BaseModel):
    """A single active appointment returned to the VAPI tool."""
    appointment_id: Optional[str] = Field(None, description="UUID of the appointment")
    id: int = Field(..., description="Integer primary key of the appointment")
    category: Optional[str] = Field(None, description="Complaint category")
    appointment_date: str = Field(..., description="Scheduled date/time of the appointment")
    status: str = Field(..., description="Current appointment status")

    model_config = ConfigDict(from_attributes=True)


class VapiAppointmentViewResponse(BaseModel):
    """Response wrapper for GET /appointments/view."""
    appointments: List[VapiAppointmentViewItem]


# ---------------------------------------------------------------------------
# VAPI-specific schemas for PATCH /appointments/update
# ---------------------------------------------------------------------------

class VapiAppointmentUpdateRequest(BaseModel):
    """Request body for PATCH /appointments/update."""
    flat_number: str = Field(..., description="Flat number the appointment belongs to")
    id: int = Field(..., description="Primary key of the appointment")
    new_appointment_date: str = Field(..., description="New scheduled date/time in format YYYY-MM-DD HH:MM:SS")


class VapiAppointmentUpdateResponse(BaseModel):
    """Response for PATCH /appointments/update."""
    id: int
    new_appointment_date: str


class VapiAppointmentCancelResponse(BaseModel):
    """Response for PATCH /appointments/cancel."""
    id: int
    status: str


# ---------------------------------------------------------------------------
# VAPI-specific schema for GET /appointments/availability
# ---------------------------------------------------------------------------

class VapiAvailabilityResponse(BaseModel):
    """Response for GET /appointments/availability.

    status values:
      'available'   — no scheduled appointment exists at the requested time
      'unavailable' — a scheduled appointment already exists at that time
    """
    status: str = Field(..., description="'available' or 'unavailable'")
