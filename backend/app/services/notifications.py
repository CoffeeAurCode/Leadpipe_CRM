"""
Notification Service
Orchestrates sending notifications to managers via SMS and Email.
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from supabase import Client
from app.integrations.twilio_client import get_twilio_client
from app.integrations.email_client import get_email_client

logger = logging.getLogger(__name__)


def notify_tenant_appointment(
    flat_uuid: str,
    event: str,  # "created" | "rescheduled" | "cancelled"
    flat_number: str,
    db: Client,
    new_date: Optional[str] = None,
) -> None:
    """
    Send a personalised SMS to the tenant when an appointment is created,
    rescheduled, or cancelled. Errors are logged and never raised.

    Args:
        flat_uuid: UUID of the flat (used to look up the tenant).
        event: One of "created", "rescheduled", "cancelled".
        flat_number: Flat number string used in the SMS message text.
        db: Supabase client instance.
        new_date: ISO date string for rescheduled events (optional).
    """
    try:
        # Look up tenant by flat_uuid
        tenant_resp = (
            db.table("tenants")
            .select("name, phone")
            .eq("flat_uuid", flat_uuid)
            .maybe_single()
            .execute()
        )
        if not tenant_resp.data:
            logger.warning(f"notify_tenant_appointment: no tenant for flat_uuid={flat_uuid}")
            return

        tenant_name = tenant_resp.data.get("name") or "Tenant"
        phone = tenant_resp.data.get("phone")
        if not phone:
            logger.warning(f"notify_tenant_appointment: tenant has no phone (flat_uuid={flat_uuid})")
            return

        # Format new_date for the rescheduled message
        formatted_date = new_date or ""
        if new_date:
            try:
                dt = datetime.fromisoformat(new_date.replace("T", " ").replace("Z", ""))
                formatted_date = dt.strftime("%d %b %Y at %I:%M %p")
            except Exception:
                formatted_date = new_date

        if event == "created":
            message = (
                f"Hi {tenant_name}, a new maintenance appointment has been "
                f"scheduled for flat {flat_number}."
            )
        elif event == "rescheduled":
            message = (
                f"Hi {tenant_name}, your maintenance appointment for flat "
                f"{flat_number} has been rescheduled to {formatted_date}."
            )
        elif event == "cancelled":
            message = (
                f"Hi {tenant_name}, your maintenance appointment for flat "
                f"{flat_number} has been cancelled."
            )
        else:
            logger.warning(f"notify_tenant_appointment: unknown event '{event}'")
            return

        get_twilio_client().send_sms(to=phone, message=message)
        logger.info(f"Tenant SMS ({event}) sent to {phone} for flat {flat_number}")

    except Exception as e:
        logger.error(f"notify_tenant_appointment failed: {type(e).__name__} - {str(e)}")


def notify_manager_appointment_scheduled(appointment: Dict[str, Any]) -> None:
    """
    Notify manager when an appointment is scheduled.
    
    Fetches related complaint and tenant data from database.
    Sends both SMS and Email notifications with complete details.
    Errors are logged but do not raise exceptions.
    
    Args:
        appointment: Appointment data dictionary from database
    """
    try:
        from supabase import create_client
        
        # Get database client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            logger.error("Database credentials not configured. Cannot fetch complaint details.")
            return
        
        db = create_client(supabase_url, supabase_key)
        
        # Extract appointment details
        appointment_id = appointment.get('id')
        flat_number = appointment.get('flat_number', 'Unknown')
        appointment_date = appointment.get('appointment_date')
        appointment_status = appointment.get('status', 'scheduled')
        notes = appointment.get('notes', '')
        complaint_uuid = appointment.get('complaint_uuid')
        
        # Format date/time for display
        try:
            if isinstance(appointment_date, str):
                dt = datetime.fromisoformat(appointment_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime("%B %d, %Y at %I:%M %p")
                formatted_date_short = dt.strftime("%d %b, %I:%M %p")
            else:
                formatted_date = str(appointment_date)
                formatted_date_short = str(appointment_date)
        except Exception as e:
            logger.warning(f"Error formatting date: {e}")
            formatted_date = str(appointment_date)
            formatted_date_short = str(appointment_date)
        
        # Fetch complaint details if complaint_uuid exists
        complaint_id = None
        complaint_category = 'N/A'
        complaint_description = 'N/A'
        complaint_priority = 'medium'
        tenant_name = 'N/A'
        
        if complaint_uuid:
            try:
                complaint_response = db.table("complaints")\
                    .select("*")\
                    .eq("uuid", complaint_uuid)\
                    .execute()
                
                if complaint_response.data and len(complaint_response.data) > 0:
                    complaint = complaint_response.data[0]
                    complaint_id = complaint.get('id')
                    complaint_category = complaint.get('category', 'N/A')
                    complaint_description = complaint.get('description', 'N/A')
                    complaint_priority = complaint.get('priority', 'medium')
                    tenant_name = complaint.get('tenant_name', 'N/A')
            except Exception as e:
                logger.warning(f"Could not fetch complaint details: {e}")
        
        # Fetch flat details and feature flags
        flat_id = None
        sms_enabled = False
        email_enabled = False
        
        try:
            # Get flat UUID and ID
            flat_response = db.table("flats")\
                .select("uuid, id")\
                .eq("flat_number", flat_number)\
                .execute()
            
            if flat_response.data and len(flat_response.data) > 0:
                flat_uuid = flat_response.data[0].get('uuid')
                flat_id = flat_response.data[0].get('id')
                
                # Fetch feature flags
                from app.services.feature_service import FeatureService
                from app.core.features import Feature
                import asyncio
                
                # The notification is often called from background task, so run_until_complete isn't safe if loop is running
                # However, since this is a background task running in an event loop, we should await it, BUT the function is sync.
                # To be safe in a sync context called by FastAPI BackgroundTasks, we create a new event loop.
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import nest_asyncio
                        nest_asyncio.apply()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                feature_service = FeatureService(db)
                # Helper function to run the async check
                async def get_flags():
                    s = await feature_service.is_feature_enabled(flat_id, Feature.SMS_REMINDERS)
                    e = await feature_service.is_feature_enabled(flat_id, Feature.EMAIL_REMINDERS)
                    return s, e
                
                sms_enabled, email_enabled = loop.run_until_complete(get_flags())
                
                logger.info(f"Notification flags for flat {flat_number}: SMS={sms_enabled}, EMAIL={email_enabled}")

                # Fetch tenant details from flat if not already set
                if tenant_name == 'N/A':
                    # Get tenant using reverse lookup
                    tenant_response = db.table("tenants")\
                        .select("name")\
                        .eq("flat_uuid", flat_uuid)\
                        .execute()
                    
                    if tenant_response.data and len(tenant_response.data) > 0:
                        tenant_name = tenant_response.data[0].get('name', 'N/A')
        except Exception as e:
            logger.warning(f"Could not fetch tenant/feature details: {e}")
        
        # Format SMS message (keep it concise)
        sms_message = (
            f"🔔 New Visit Scheduled\n"
            f"\n"
            f"Flat: {flat_number}\n"
            f"Category: {complaint_category}\n"
            f"Priority: {complaint_priority.upper()}\n"
            f"Appointment: {formatted_date_short}\n"
            f"\n"
            f"Tenant: {tenant_name}"
        )
        
        # Format Email HTML content with all details
        email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 650px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 35px;
            border-radius: 12px 12px 0 0;
            text-align: center;
        }}
        .content {{
            background: white;
            padding: 35px;
            border-radius: 0 0 12px 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .section {{
            margin: 25px 0;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #f0f0f0;
        }}
        .info-row {{
            display: flex;
            padding: 12px 0;
            border-bottom: 1px solid #f8f8f8;
        }}
        .info-row:last-child {{
            border-bottom: none;
        }}
        .label {{
            font-weight: 600;
            color: #666;
            min-width: 160px;
            flex-shrink: 0;
        }}
        .value {{
            color: #333;
            flex-grow: 1;
        }}
        .priority-high {{ 
            color: #e74c3c; 
            font-weight: bold;
            background: #fee;
            padding: 4px 12px;
            border-radius: 4px;
            display: inline-block;
        }}
        .priority-medium {{ 
            color: #f39c12; 
            font-weight: bold;
            background: #ffeaa7;
            padding: 4px 12px;
            border-radius: 4px;
            display: inline-block;
        }}
        .priority-low {{ 
            color: #27ae60; 
            font-weight: bold;
            background: #d5f4e6;
            padding: 4px 12px;
            border-radius: 4px;
            display: inline-block;
        }}
        .description-box {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-top: 10px;
            border-left: 4px solid #667eea;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #f0f0f0;
            color: #999;
            font-size: 13px;
        }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            background: #667eea;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0; font-size: 28px;">🔔 New Appointment Scheduled</h1>
        <p style="margin: 12px 0 0 0; opacity: 0.95; font-size: 14px;">Tenant Management System</p>
    </div>
    
    <div class="content">
        <!-- Appointment Details -->
        <div class="section">
            <div class="section-title">📅 Appointment Details</div>
            <div class="info-row">
                <span class="label">Appointment ID:</span>
                <span class="value">#{appointment_id}</span>
            </div>
            <div class="info-row">
                <span class="label">Scheduled Date/Time:</span>
                <span class="value"><strong>{formatted_date}</strong></span>
            </div>
            <div class="info-row">
                <span class="label">Status:</span>
                <span class="value"><span class="badge">{appointment_status.upper()}</span></span>
            </div>
        </div>
        
        <!-- Complaint Details -->
        <div class="section">
            <div class="section-title">🔧 Complaint Details</div>
            {'<div class="info-row"><span class="label">Complaint ID:</span><span class="value">#' + str(complaint_id) + '</span></div>' if complaint_id else ''}
            <div class="info-row">
                <span class="label">Category:</span>
                <span class="value"><strong>{complaint_category}</strong></span>
            </div>
            <div class="info-row">
                <span class="label">Priority:</span>
                <span class="value"><span class="priority-{complaint_priority.lower()}">{complaint_priority.upper()}</span></span>
            </div>
            {f'<div class="description-box"><strong>Description:</strong><br>{complaint_description}</div>' if complaint_description and complaint_description != 'N/A' else ''}
        </div>
        
        <!-- Property & Tenant Details -->
        <div class="section">
            <div class="section-title">🏠 Property & Tenant</div>
            <div class="info-row">
                <span class="label">Flat Number:</span>
                <span class="value"><strong>{flat_number}</strong></span>
            </div>
            <div class="info-row">
                <span class="label">Tenant Name:</span>
                <span class="value">{tenant_name}</span>
            </div>
        </div>
        
        <!-- Additional Notes -->
        {f'<div class="section"><div class="section-title">📝 Additional Notes</div><div class="description-box">{notes}</div></div>' if notes else ''}
        
        <p style="margin-top: 30px; padding: 15px; background: #f0f7ff; border-radius: 8px; border-left: 4px solid #667eea;">
            <strong>Action Required:</strong> Please review the complaint details and prepare for the scheduled visit.
        </p>
    </div>
    
    <div class="footer">
        <p>This is an automated notification from the Tenant Management System.</p>
        <p style="margin-top: 5px; color: #bbb;">© 2026 Tenant Management Platform</p>
    </div>
</body>
</html>
"""
        
        # Send SMS notification
        if sms_enabled:
            try:
                twilio_client = get_twilio_client()
                manager_phone = os.getenv("MANAGER_PHONE", "+919998064026")
                sms_result = twilio_client.send_sms(to=manager_phone, message=sms_message)
                if sms_result:
                    logger.info(f"SMS notification sent for appointment #{appointment_id}")
            except Exception as e:
                logger.error(f"SMS notification failed: {type(e).__name__} - {str(e)}")
        else:
            logger.info(f"SMS notification skipped for flat {flat_number} (feature disabled)")
        
        # Send Email notification
        if email_enabled:
            try:
                email_client = get_email_client()
                email_subject = f"🔔 New Appointment: Flat {flat_number} - {formatted_date_short}"
                email_success = email_client.send_email(subject=email_subject, html_content=email_html)
                if email_success:
                    logger.info(f"Email notification sent for appointment #{appointment_id}")
            except Exception as e:
                logger.error(f"Email notification failed: {type(e).__name__} - {str(e)}")
        else:
            logger.info(f"Email notification skipped for flat {flat_number} (feature disabled)")
        
        logger.info(f"Manager notification process completed for appointment #{appointment_id} (Flat {flat_number})")
    
    except Exception as e:
        # Catch-all to ensure notification failures don't crash the system
        logger.error(f"Notification service error: {type(e).__name__} - {str(e)}")
