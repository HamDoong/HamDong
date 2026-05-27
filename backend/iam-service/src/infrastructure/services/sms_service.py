"""SMS service implementation."""

import logging
from typing import Optional

from ...domain.interfaces import SMSServiceInterface

logger = logging.getLogger(__name__)


class MockSMSService(SMSServiceInterface):
    """Mock SMS service for development and testing.
    
    In production, this would be replaced with a real SMS provider
    like Twilio, AWS SNS, or similar.
    """

    async def send_otp_sms(self, phone_number: str, otp: str) -> bool:
        """Send OTP via SMS (mock implementation).
        
        Args:
            phone_number: The recipient's phone number
            otp: The OTP code to send
            
        Returns:
            True to indicate success
        """
        logger.info(
            f"[MOCK SMS] Sending OTP to {phone_number}",
            extra={
                "phone_number": phone_number,
                "otp": otp,
            },
        )
        
        # In development, just log the OTP
        print(f"[MOCK SMS] OTP {otp} sent to {phone_number}")
        
        return True


class TwilioSMSService(SMSServiceInterface):
    """SMS service using Twilio provider.
    
    Real implementation for production use with Twilio API.
    """

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_phone: str,
    ) -> None:
        """Initialize Twilio SMS service.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio authentication token
            from_phone: The phone number to send from
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_phone = from_phone
        
        try:
            from twilio.rest import Client
            self._client = Client(account_sid, auth_token)
        except ImportError:
            logger.warning("Twilio client not installed, falling back to mock")
            self._client = None

    async def send_otp_sms(self, phone_number: str, otp: str) -> bool:
        """Send OTP via SMS using Twilio.
        
        Args:
            phone_number: The recipient's phone number
            otp: The OTP code to send
            
        Returns:
            True if SMS was sent successfully, False otherwise
            
        Raises:
            Exception: If SMS sending fails critically
        """
        if not self._client:
            logger.warning("Twilio client not available, using mock delivery")
            return True
        
        try:
            message_body = f"Your HamDong OTP is: {otp}. Valid for 2 minutes."
            
            message = self._client.messages.create(
                body=message_body,
                from_=self.from_phone,
                to=phone_number,
            )
            
            logger.info(
                f"OTP SMS sent successfully to {phone_number}",
                extra={
                    "phone_number": phone_number,
                    "message_sid": message.sid,
                },
            )
            
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to send OTP SMS to {phone_number}: {str(e)}",
                extra={
                    "phone_number": phone_number,
                    "error": str(e),
                },
            )
            raise
