"""Use case orchestration for identity-service."""

import logging
from typing import Tuple, Optional, Dict, Any

from apps.identity.application.otp_service import OtpService
from apps.identity.application.token_service import TokenService
from apps.identity.application.user_service import UserService
from apps.identity.domain.models import User
from apps.identity.domain.events import (
    UserOtpRequested,
    UserCreated,
    UserLoggedIn,
    UserUpdated,
)
from apps.identity.infrastructure.rabbitmq_publisher import RabbitMqPublisher
from apps.identity.infrastructure.repositories import RefreshTokenRepository

logger = logging.getLogger(__name__)


class RequestOtpUseCase:
    """Use case for requesting OTP."""

    def __init__(self):
        self.otp_service = OtpService()
        self.publisher = RabbitMqPublisher()

    def execute(
        self, phone_number: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        """
        Request OTP for a phone number.

        Returns:
            Tuple of (success, error_code, debug_otp, resend_after)
        """
        # Request OTP
        success, error_code, debug_otp = self.otp_service.request_otp(phone_number)

        if not success:
            return False, error_code, None, None

        # Publish event
        event = UserOtpRequested(phone_number=phone_number, purpose="login")
        self.publisher.publish(event.to_dict(), "identity.otp.requested")

        resend_after = self.otp_service.resend_cooldown

        return True, None, debug_otp, resend_after


class VerifyOtpUseCase:
    """Use case for verifying OTP and logging in user."""

    def __init__(self):
        self.otp_service = OtpService()
        self.user_service = UserService()
        self.token_service = TokenService()
        self.publisher = RabbitMqPublisher()

    def execute(
        self,
        phone_number: str,
        otp_code: str,
        user_agent: str = None,
        ip_address: str = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Verify OTP and create/login user.

        Returns:
            Tuple of (success, error_code, token_data)
        """
        # Verify OTP
        success, error_code = self.otp_service.verify_otp(phone_number, otp_code)

        if not success:
            return False, error_code, None

        # Get or create user
        user, is_created = self.user_service.get_or_create(phone_number)

        # Mark phone as verified
        user = self.user_service.mark_phone_verified(user)

        # Update last login
        user = self.user_service.update_last_login(user)

        # Generate tokens
        access_token, refresh_token, jti = self.token_service.generate_tokens(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Publish events
        if is_created:
            event = UserCreated(
                user_id=user.id,
                phone_number=user.phone_number,
                display_name=user.display_name,
                role=user.role,
                is_active=user.is_active,
            )
            self.publisher.publish(event.to_dict(), "identity.user.created")

        event = UserLoggedIn(user_id=user.id, phone_number=user.phone_number)
        self.publisher.publish(event.to_dict(), "identity.user.logged_in")

        token_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.token_service.access_token_lifetime,
            "user": {
                "id": str(user.id),
                "phone_number": user.phone_number,
                "display_name": user.display_name,
                "is_phone_verified": user.is_phone_verified,
                "role": user.role,
            },
        }

        return True, None, token_data


class RefreshTokenUseCase:
    """Use case for refreshing access token."""

    def __init__(self):
        self.token_service = TokenService()

    def execute(
        self, refresh_token: str, user_agent: str = None, ip_address: str = None
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Refresh access token.

        Returns:
            Tuple of (success, error_code, token_data)
        """
        result = self.token_service.refresh_tokens(
            refresh_token, user_agent, ip_address
        )

        if not result:
            return False, "INVALID_TOKEN", None

        access_token, new_refresh_token = result

        token_data = {
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": self.token_service.access_token_lifetime,
        }

        return True, None, token_data


class LogoutUseCase:
    """Use case for logging out user."""

    def execute(self, refresh_token: str) -> Tuple[bool, Optional[str]]:
        """
        Logout by revoking refresh token.

        Returns:
            Tuple of (success, error_code)
        """
        token_repo = RefreshTokenRepository()
        token_hash = token_repo.hash_token(refresh_token)
        db_token = token_repo.get_by_token_hash(token_hash)

        if not db_token:
            return False, "INVALID_TOKEN"

        token_repo.revoke(db_token)
        logger.info(f"User logged out: {db_token.user.phone_number}")

        return True, None


class UpdateProfileUseCase:
    """Use case for updating user profile."""

    def __init__(self):
        self.user_service = UserService()
        self.publisher = RabbitMqPublisher()

    def execute(
        self,
        user: User,
        display_name: str = None,
        first_name: str = None,
        last_name: str = None,
    ) -> Tuple[bool, Optional[User]]:
        """
        Update user profile.

        Returns:
            Tuple of (success, updated_user)
        """
        # Update profile
        updated_user = self.user_service.update_profile(
            user,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
        )

        # Publish event
        event = UserUpdated(
            user_id=updated_user.id,
            phone_number=updated_user.phone_number,
            display_name=updated_user.display_name,
            role=updated_user.role,
            is_active=updated_user.is_active,
        )
        self.publisher.publish(event.to_dict(), "identity.user.updated")

        return True, updated_user
