"""
Notification Service
Orchestrates sending notifications to managers via SMS and Email.
"""
import os
import logging
from typing import Dict, Any
from datetime import datetime
from app.integrations.twilio_client import get_twilio_client
from app.integrations.email_client import get_email_client

logger = logging.getLogger(__name__)


def notify_manager_appointment_scheduled(appointment: Dict[str, Any]) -> None:
    """
    Notify manager when an appointment is scheduled.
    
    Sends both SMS and Email notifications.
    Errors are logged but do not raise exceptions.
    
    Args:
        appointment: Appointment data dictionary from database
    """
    try:
        # Extract appointment details
        flat_number = appointment.get('flat_number', 'Unknown')
        appointment_date = appointment.get('appointment_date')
        notes = appointment.get('notes', '')
        
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
        
        # Get associated complaint data if available
        complaint_category = appointment.get('complaint_category', 'N/A')
        complaint_description = appointment.get('complaint_description', 'N/A')
        complaint_priority = appointment.get('complaint_priority', 'medium')
        
        # Format SMS message (keep it concise, ~160 chars)
        sms_message = (
            f"🔔 New Appointment Scheduled\n"
            f"Flat: {flat_number}\n"
            f"Date: {formatted_date_short}\n"
            f"Issue: {complaint_category}\n"
            f"Priority: {complaint_priority.upper()}"
        )
        
        # Format Email HTML content
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
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .info-box {{
            background: white;
            padding: 20px;
            margin: 15px 0;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .label {{
            font-weight: 600;
            color: #667eea;
            display: inline-block;
            width: 140px;
        }}
        .value {{
            color: #333;
        }}
        .priority-high {{ color: #e74c3c; font-weight: bold; }}
        .priority-medium {{ color: #f39c12; font-weight: bold; }}
        .priority-low {{ color: #27ae60; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1 style="margin: 0;">🔔 New Appointment Scheduled</h1>
        <p style="margin: 10px 0 0 0; opacity: 0.9;">Tenant Management System</p>
    </div>
    <div class="content">
        <div class="info-box">
            <p><span class="label">Flat Number:</span> <span class="value">{flat_number}</span></p>
            <p><span class="label">Appointment Date:</span> <span class="value">{formatted_date}</span></p>
            <p><span class="label">Complaint Category:</span> <span class="value">{complaint_category}</span></p>
            <p><span class="label">Priority:</span> <span class="value priority-{complaint_priority.lower()}">{complaint_priority.upper()}</span></p>
        </div>
        
        {'<div class="info-box"><p><strong>Description:</strong></p><p>' + complaint_description + '</p></div>' if complaint_description and complaint_description != 'N/A' else ''}
        
        {'<div class="info-box"><p><strong>Notes:</strong></p><p>' + notes + '</p></div>' if notes else ''}
        
        <p style="margin-top: 25px; color: #666;">
            Please review and prepare for the scheduled appointment.
        </p>
    </div>
    <div class="footer">
        <p>This is an automated notification from the Tenant Management System.</p>
        <p>© 2026 Tenant Management Platform</p>
    </div>
</body>
</html>
"""
        
        # Send SMS notification
        try:
            twilio_client = get_twilio_client()
            manager_phone = os.getenv("MANAGER_PHONE", "+919998064026")
            twilio_client.send_sms(to=manager_phone, message=sms_message)
        except Exception as e:
            logger.error(f"SMS notification failed: {type(e).__name__} - {str(e)}")
        
        # Send Email notification
        try:
            email_client = get_email_client()
            email_subject = f"New Appointment: Flat {flat_number} - {formatted_date_short}"
            email_client.send_email(subject=email_subject, html_content=email_html)
        except Exception as e:
            logger.error(f"Email notification failed: {type(e).__name__} - {str(e)}")
        
        logger.info(f"Manager notification dispatched for appointment at flat {flat_number}")
    
    except Exception as e:
        # Catch-all to ensure notification failures don't crash the system
        logger.error(f"Notification service error: {type(e).__name__} - {str(e)}")
