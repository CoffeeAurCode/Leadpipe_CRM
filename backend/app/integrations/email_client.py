"""
SendGrid Email Integration Client
Handles sending email notifications using SendGrid API.
"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class EmailClient:
    """SendGrid email client for sending notifications."""
    
    def __init__(self):
        """Initialize SendGrid client with environment variables."""
        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@tenantmanagement.com")
        self.manager_email = os.getenv("MANAGER_EMAIL")
        
        if not self.api_key:
            logger.warning("SendGrid API key not configured. Email notifications will not be sent.")
            self.client = None
        else:
            self.client = SendGridAPIClient(self.api_key)
        
        if not self.manager_email:
            logger.warning("MANAGER_EMAIL not configured. Email notifications will have no recipient.")
    
    def send_email(self, subject: str, html_content: str, to_email: Optional[str] = None) -> bool:
        """
        Send an email notification.
        
        Args:
            subject: Email subject line
            html_content: HTML email body
            to_email: Recipient email (defaults to MANAGER_EMAIL from env)
            
        Returns:
            True if successful, False if failed
        """
        if not self.client:
            logger.error("SendGrid client not initialized. Check SENDGRID_API_KEY.")
            return False
        
        recipient = self.manager_email
        if not recipient:
            logger.error("No recipient email specified and MANAGER_EMAIL not set.")
            return False
        
        try:
            message = Mail(
                from_email=Email(self.from_email),
                to_emails=To(recipient),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            
            response = self.client.send(message)
            logger.info(f"Email sent successfully. Status: {response.status_code}, To: {recipient}")
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {type(e).__name__} - {str(e)}")
            return False


# Singleton instance
_email_client = None


def get_email_client() -> EmailClient:
    """Get or create the Email client singleton."""
    global _email_client
    if _email_client is None:
        _email_client = EmailClient()
    return _email_client
