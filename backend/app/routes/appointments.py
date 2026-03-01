"""
Appointments API routes using Supabase client.
Handles CRUD operations for appointments.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from supabase import Client
from app.db.session import get_db
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentUpdate,
    AppointmentResponse,
    AppointmentStatus,
    VapiAppointmentViewItem,
    VapiAppointmentViewResponse,
    VapiAppointmentUpdateRequest,
    VapiAppointmentUpdateResponse,
)
from app.services.notifications import notify_manager_appointment_scheduled
from datetime import datetime, timezone
from typing import Optional

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ===========================================================================
# VAPI tool endpoints — placed before /{appointment_id} routes to avoid
# FastAPI route shadowing.  These MUST stay above the dynamic path routes.
# ===========================================================================

@router.get("/view", response_model=VapiAppointmentViewResponse)
async def vapi_view_appointments(
    flat_number: str = Query(..., description="Flat number to look up appointments for"),
    db: Client = Depends(get_db),
):
    """
    VAPI tool — View active appointments for a flat.

    Active = appointment_date >= now AND status != 'completed'.
    Returns an empty list if the flat has no upcoming appointments.
    """
    try:
        # 1. Normalize flat_number and validate it exists
        normalized_flat = flat_number.strip().upper()
        flat_check = db.table("flats").select("id").ilike("flat_number", normalized_flat).execute()
        if not flat_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat '{flat_number}' not found",
            )

        # 2. Fetch ALL appointments for this flat (no date or status filter)
        apts_resp = (
            db.table("appointments")
            .select("id, uuid, flat_number, appointment_date, status, complaint_id")
            .ilike("flat_number", normalized_flat)
            .order("appointment_date")
            .execute()
        )

        if not apts_resp.data:
            return {"appointments": []}

        # 3. Fetch category from complaints table for each appointment
        appointments_out = []
        for apt in apts_resp.data:
            category = None
            complaint_id = apt.get("complaint_id")
            if complaint_id:
                complaint_resp = (
                    db.table("complaints")
                    .select("category")
                    .eq("id", complaint_id)
                    .maybe_single()
                    .execute()
                )
                if complaint_resp.data:
                    category = complaint_resp.data.get("category")

            appointments_out.append(
                VapiAppointmentViewItem(
                    appointment_id=apt.get("uuid"),
                    id=apt["id"],
                    category=category,
                    appointment_date=apt["appointment_date"],
                    status=apt["status"],
                )
            )

        return {"appointments": appointments_out}

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] vapi_view_appointments failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {str(e)}",
        )


@router.patch("/update", response_model=VapiAppointmentUpdateResponse)
async def vapi_update_appointment(
    flat_number: str = Query(..., description="Flat number the appointment belongs to"),
    id: int = Query(..., description="Primary key of the appointment"),
    new_appointment_date: str = Query(..., description="New date/time in format YYYY-MM-DD HH:MM:SS"),
    db: Client = Depends(get_db),
):
    """
    VAPI tool — Reschedule an appointment.

    Accepts flat_number, id, and new_appointment_date as URL query parameters.
    Refuses updates if the appointment is already completed.
    """
    try:
        # 1. Normalize flat_number and validate it exists
        normalized_flat = flat_number.strip().upper()
        flat_check = db.table("flats").select("id").ilike("flat_number", normalized_flat).execute()
        if not flat_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flat '{flat_number}' not found",
            )

        # 2. Fetch the appointment by id AND flat_number together
        apt_resp = (
            db.table("appointments")
            .select("*")
            .eq("id", id)
            .ilike("flat_number", normalized_flat)
            .maybe_single()
            .execute()
        )

        if not apt_resp.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found",
            )

        apt = apt_resp.data

        # 3. Refuse if already completed
        if apt.get("status") == "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reschedule a completed appointment",
            )

        # 4. Update appointment_date exactly as provided (YYYY-MM-DD HH:MM:SS)
        update_resp = (
            db.table("appointments")
            .update({"appointment_date": new_appointment_date})
            .eq("id", apt["id"])
            .execute()
        )

        if not update_resp.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update appointment",
            )

        updated = update_resp.data[0]
        return VapiAppointmentUpdateResponse(
            id=updated["id"],
            new_appointment_date=updated["appointment_date"],
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] vapi_update_appointment failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating appointment: {str(e)}",
        )


# ===========================================================================
# Original CRUD endpoints — unchanged
# ===========================================================================

@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
async def create_appointment(
    appointment_data: AppointmentCreate,
    background_tasks: BackgroundTasks,
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
        
        # Use mode='json' to serialize datetime and enum to strings
        insert_data = appointment_data.model_dump(mode='json')
        
        # Create appointment
        response = db.table("appointments").insert(insert_data).execute()
        
        if response.data:
            created_appointment = response.data[0]
            
            # Trigger background notification to manager
            # This runs after the response is sent, non-blocking
            background_tasks.add_task(
                notify_manager_appointment_scheduled,
                created_appointment
            )
            
            return created_appointment
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
        # Join with complaints table using explicit FK name
        # Must specify FK because appointments has 2 relationships to complaints
        query = db.table("appointments")\
            .select("*, complaints!fk_appointments_complaint_uuid(category, description, priority)")
        
        # Apply filters
        if start_date:
            query = query.gte("appointment_date", start_date)
        if end_date:
            query = query.lte("appointment_date", end_date)
        if flat_number:
            query = query.eq("flat_number", flat_number)
        
        response = query.order("appointment_date").execute()
        
        # Flatten response to include complaint fields at root level
        appointments = []
        for apt in response.data:
            apt_data = {**apt}
            
            # Extract complaint data if exists (LEFT JOIN returns dict or None)
            complaints_data = apt.get('complaints')
            
            if complaints_data and isinstance(complaints_data, dict):
                # Single complaint object
                apt_data['complaint_category'] = complaints_data.get('category')
                apt_data['complaint_description'] = complaints_data.get('description')
                apt_data['complaint_priority'] = complaints_data.get('priority')
            else:
                apt_data['complaint_category'] = None
                apt_data['complaint_description'] = None
                apt_data['complaint_priority'] = None
            
            # Remove nested complaints array
            apt_data.pop('complaints', None)
            appointments.append(apt_data)
        
        return appointments
    except Exception as e:
        print(f"[ERROR] Appointments fetch failed: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching appointments: {type(e).__name__} - {str(e)}"
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
        # Use mode='json' to serialize datetime and enum to strings
        update_data = appointment_data.model_dump(exclude_unset=True, mode='json')
        
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
