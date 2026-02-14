"""
Twilio SMS Integration Client
Handles sending SMS notifications using Twilio API.
"""
import os
from twilio.rest import Client
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TwilioClient:
    """Twilio SMS client for sending notifications."""
    
    def __init__(self):
        """Initialize Twilio client with environment variables."""
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Twilio credentials not fully configured. SMS notifications will not be sent.")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
    
    def send_sms(self, to: str, message: str) -> Optional[str]:
        """
        Send an SMS message.
        
        Args:
            to: Recipient phone number (E.164 format: +919998064026)
            message: Message content
            
        Returns:
            Message SID if successful, None if failed
        """
        if not self.client:
            logger.error("Twilio client not initialized. Check environment variables.")
            return None
        
        try:
            message_obj = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to
            )
            logger.info(f"SMS sent successfully. SID: {message_obj.sid}, To: {to}")
            return message_obj.sid
        except Exception as e:
            logger.error(f"Failed to send SMS to {to}: {type(e).__name__} - {str(e)}")
            return None


# Singleton instance
_twilio_client = None


def get_twilio_client() -> TwilioClient:
    """Get or create the Twilio client singleton."""
    global _twilio_client
    if _twilio_client is None:
        _twilio_client = TwilioClient()
    return _twilio_client
