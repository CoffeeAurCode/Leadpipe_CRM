"""
Complaints API routes using Supabase client.
Handles CRUD operations for tenant complaints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from supabase import Client
from app.dependencies.authenticated_db import get_authenticated_db
from app.dependencies.subscription import require_active_subscription
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate, ComplaintResponse
from app.services.notifications import notify_manager_appointment_scheduled

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    complaint_data: ComplaintCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
):
    """Create a new complaint."""
    try:
        complaint_dict = complaint_data.model_dump(mode='json')

        # appointment_date belongs to the appointments table, not complaints
        appointment_date = complaint_dict.pop("appointment_date", None)
        
        # Handle UUID-based flat reference (preferred over flat_number)
        if complaint_data.flat_uuid:
            # Verify flat exists
            flat_check = db.table("flats").select("uuid").eq("uuid", str(complaint_data.flat_uuid)).execute()
            if not flat_check.data:
                raise HTTPException(status_code=404, detail="Flat not found")
        
        # Backward compatibility: Convert flat_number to flat_uuid if provided
        elif complaint_data.flat_number:
            flat = db.table("flats").select("uuid").eq("flat_number", complaint_data.flat_number).execute()
            if flat.data:
                complaint_dict['flat_uuid'] = str(flat.data[0]['uuid'])
            # Keep flat_number for legacy compatibility
        
        # Auto-assign tenant_uuid based on who lives in the flat
        if complaint_dict.get('flat_uuid') and not complaint_dict.get('tenant_uuid'):
            # Find the tenant living in this flat
            tenant = db.table("tenants").select("uuid").eq("flat_uuid", complaint_dict['flat_uuid']).execute()
            if tenant.data and len(tenant.data) > 0:
                complaint_dict['tenant_uuid'] = str(tenant.data[0]['uuid'])
        
        # Convert tenant_id to tenant_uuid if provided (backward compatibility)
        if complaint_data.tenant_id and not complaint_dict.get('tenant_uuid'):
            tenant = db.table("tenants").select("uuid").eq("id", complaint_data.tenant_id).execute()
            if tenant.data:
                complaint_dict['tenant_uuid'] = str(tenant.data[0]['uuid'])
        
        # Strip deprecated legacy fields before inserting to prevent Supabase Schema errors
        complaint_dict.pop("tenant_id", None)
        
        response = db.table("complaints").insert(complaint_dict).execute()
        
        if response.data:
            created_complaint = response.data[0]

            # Insert appointment row if appointment_date was provided
            if appointment_date:
                appt_response = db.table("appointments").insert({
                    "complaint_uuid": created_complaint["uuid"],
                    "flat_number": created_complaint.get("flat_number"),
                    "appointment_date": appointment_date,
                    "status": "scheduled"
                }).execute()

                # Notify manager via SMS + Email (non-blocking background task)
                if appt_response.data:
                    background_tasks.add_task(
                        notify_manager_appointment_scheduled,
                        appt_response.data[0]
                    )

            return created_complaint
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create complaint"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating complaint: {str(e)}"
        )


@router.get("", response_model=list[ComplaintResponse])
async def get_all_complaints(
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
):
    """Get all complaints with appointment data (if exists) ordered by created_at (newest first)."""
    try:
        # Join with appointments using explicit foreign key relationship
        # Use UUID-based relationship: fk_appointments_complaint_uuid
        response = db.table("complaints")\
            .select("*, appointments!fk_appointments_complaint_uuid(*)")\
            .order("created_at", desc=True)\
            .execute()
        
        # Flatten the response to include appointment fields at root level
        complaints = []
        for complaint in response.data:
            complaint_data = {**complaint}
            
            # Extract appointment data if exists (LEFT JOIN so might be None/empty list)
            appointments = complaint.get('appointments', [])
            if appointments and len(appointments) > 0:
                appt = appointments[0]  # Get first appointment
                complaint_data['appointment_date'] = appt.get('appointment_date')  # Column is appointment_date, not scheduled_at
                complaint_data['appointment_status'] = appt.get('status')
            else:
                complaint_data['appointment_date'] = None
                complaint_data['appointment_status'] = None
            
            # Remove nested appointments array (already flattened)
            complaint_data.pop('appointments', None)
            complaints.append(complaint_data)
        
        return complaints
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complaints: {str(e)}"
        )


@router.get("/{complaint_id}", response_model=ComplaintResponse)
async def get_complaint_by_id(
    complaint_id: int,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
):
    """Get a specific complaint by ID."""
    try:
        response = db.table("complaints")\
            .select("*")\
            .eq("id", complaint_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with id {complaint_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching complaint: {str(e)}"
        )


@router.patch("/{complaint_id}", response_model=ComplaintResponse)
async def update_complaint(
    complaint_id: int,
    complaint_data: ComplaintUpdate,
    user: dict = Depends(require_active_subscription),
    db: Client = Depends(get_authenticated_db)
):
    """Update a complaint's fields."""
    try:
        # Prepare update data (exclude unset fields)
        update_data = complaint_data.model_dump(exclude_unset=True)
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update"
            )
        
        # Update the complaint
        response = db.table("complaints")\
            .update(update_data)\
            .eq("id", complaint_id)\
            .execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Complaint with id {complaint_id} not found"
            )
        
        return response.data[0]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating complaint: {str(e)}"
        )
