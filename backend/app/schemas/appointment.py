from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum


class AppointmentStatus(str, Enum):
    """Enum for appointment status"""
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"


class AppointmentBase(BaseModel):
    flat_number: str = Field(..., description="Flat number for the appointment")
    appointment_date: datetime = Field(..., description="Scheduled date and time for the appointment")
    status: AppointmentStatus = Field(AppointmentStatus.SCHEDULED, description="Current status of the appointment")
    notes: Optional[str] = Field(None, description="Additional notes or instructions")


class AppointmentCreate(AppointmentBase):
    """Schema for creating a new appointment"""
    complaint_id: Optional[int] = Field(None, description="Related complaint ID if linked to a complaint")


class AppointmentUpdate(BaseModel):
    """Schema for updating an appointment"""
    appointment_date: Optional[datetime] = None
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    """Schema for appointment responses"""
    id: int
    complaint_id: Optional[int] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
