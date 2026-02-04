"""
Appointments API routes using Supabase client.
Handles CRUD operations for appointments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from supabase import Client
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse
)
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Client = Depends(get_db)
):
    """Create a new appointment."""
    try:
        # Verify flat exists
        flat_response = db.table("flats")\
            .select("id")\
            .eq("flat_number", appointment_data.flat_number)\
            .execute()
        
        if not flat_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat {appointment_data.flat_number} not found"
            )
        
        # Create appointment
        response = db.table("appointments").insert(appointment_data.model_dump()).execute()
        
        if response.data:
            return response.data[0]
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create appointment"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating appointment: {str(e)}"
        )


@router.get("", response_model=list[AppointmentResponse])
async def get_appointments(
    start_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    end_date: Optional[str] = Query(None, description="End date (ISO format)"),
    flat_number: Optional[str] = Query(None, description="Filter by flat number"),
    db: Client = Depends(get_db)
):
    """
    Get all appointments with optional filters.
    
    Query params:
    - start_date: Filter appointments from this date (ISO format: 2024-01-01)
    - end_date: Filter appointments until this date
    - flat_number: Filter by specific flat
    """
    try:
        query = db.table("appointments").select("*")
        
        # Apply filters
        if start_date:
            query = query.gte("appointment_date", start_date)
        if end_date:
            query = query.lte("appointment_date", end_date)
        if flat_number:
            query = query.eq("flat_number", flat_number)
        
        response = query.order("appointment_date").execute()
        return response.data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}"
        )


@router.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment_by_id(
    appointment_id: int,
    db: Client = Depends(get_db)
):
    """Get a specific appointment by ID."""
    try:
        response = db.table("appointments")\
            .select("*")\
            .eq("id", appointment_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointment: {str(e)}"
        )


@router.patch("/{appointment_id}", response_model=AppointmentResponse)
async def update_appointment(
    appointment_id: int,
    appointment_data: AppointmentUpdate,
    db: Client = Depends(get_db)
):
    """Update an appointment's details."""
    try:
        # Prepare update data (exclude unset fields)
        update_data = appointment_data.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update the appointment
        response = db.table("appointments")\
            .update(update_data)\
            .eq("id", appointment_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment: {str(e)}"
        )


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_appointment(
    appointment_id: int,
    db: Client = Depends(get_db)
):
    """
    Cancel an appointment (sets status to 'cancelled').
    Use DELETE method for semantic clarity.
    """
    try:
        # Update status to cancelled instead of deleting
        response = db.table("appointments")\
            .update({"status": "cancelled"})\
            .eq("id", appointment_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Appointment with id {appointment_id} not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling appointment: {str(e)}"
        )
