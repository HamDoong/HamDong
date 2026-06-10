"""Use case orchestration for identity-service."""

import logging
from typing import Any, Dict, Optional, Tuple

from apps.identity.application.otp_service import OtpService
from apps.identity.application.token_service import TokenService
from apps.identity.application.user_service import UserService
from apps.identity.domain.events import SendOtpSmsRequested, UserCreated, UserLoggedIn, UserUpdated
from apps.identity.domain.models import User
from apps.identity.domain.rules import ArtNameRule, PhoneNumberRule
from apps.identity.infrastructure.rabbitmq_publisher import RabbitMqPublisher
from apps.identity.infrastructure.repositories import RefreshTokenRepository, UserRepository

logger = logging.getLogger(__name__)


def build_token_response(
    user: User,
    token_service: TokenService,
    access_token: str,
    refresh_token: str,
) -> Dict[str, Any]:
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": token_service.access_token_lifetime,
        "user": {
            "id": str(user.id),
            "phone_number": user.phone_number,
            "display_name": user.display_name,
            "art_name": user.art_name,
            "is_phone_verified": user.is_phone_verified,
            "role": user.role,
        },
    }


class RequestOtpUseCase:
    """Use case for requesting OTP."""

    def __init__(self):
        self.otp_service = OtpService()
        self.publisher = RabbitMqPublisher()

    def execute(
        self, phone_number: str
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[int]]:
        request_result = self.otp_service.request_otp(phone_number)
        if len(request_result) == 3:
            success, error_code, debug_otp = request_result
            otp_code = debug_otp
        else:
            success, error_code, otp_code, debug_otp = request_result

        if not success:
            return False, error_code, None, None

        event = SendOtpSmsRequested(
            phone_number=phone_number,
            code=otp_code,
            purpose="login",
            expires_in=self.otp_service.otp_ttl,
        )
        self.publisher.publish(event.to_dict(), "identity.otp.requested")
        return True, None, debug_otp, self.otp_service.resend_cooldown


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
        success, error_code = self.otp_service.verify_otp(phone_number, otp_code)
        if not success:
            return False, error_code, None

        user, is_created = self.user_service.get_or_create(phone_number)
        user = self.user_service.mark_phone_verified(user)
        user = self.user_service.update_last_login(user)

        access_token, refresh_token, _ = self.token_service.generate_tokens(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        if is_created:
            event = UserCreated(
                user_id=user.id,
                phone_number=user.phone_number,
                display_name=user.display_name,
                art_name=user.art_name,
                role=user.role,
                is_active=user.is_active,
            )
            self.publisher.publish(event.to_dict(), "identity.user.created")

        event = UserLoggedIn(user_id=user.id, phone_number=user.phone_number)
        self.publisher.publish(event.to_dict(), "identity.user.logged_in")

        return True, None, build_token_response(user, self.token_service, access_token, refresh_token)


class RefreshTokenUseCase:
    """Use case for refreshing access token."""

    def __init__(self):
        self.token_service = TokenService()

    def execute(
        self,
        refresh_token: str,
        user_agent: str = None,
        ip_address: str = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        result = self.token_service.refresh_tokens(refresh_token, user_agent, ip_address)
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
        token_hash = RefreshTokenRepository.hash_token(refresh_token)
        db_token = RefreshTokenRepository.get_by_token_hash(token_hash)

        if not db_token:
            return False, "INVALID_TOKEN"

        RefreshTokenRepository.revoke(db_token)
        logger.info("User logged out: %s", PhoneNumberRule.mask(db_token.user.phone_number))
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
        art_name: str = None,
    ) -> Tuple[bool, Optional[User]]:
        updated_user = self.user_service.update_profile(
            user,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            art_name=art_name,
        )

        event = UserUpdated(
            user_id=updated_user.id,
            phone_number=updated_user.phone_number,
            display_name=updated_user.display_name,
            art_name=updated_user.art_name,
            role=updated_user.role,
            is_active=updated_user.is_active,
        )
        self.publisher.publish(event.to_dict(), "identity.user.updated")
        return True, updated_user


class SetPasswordUseCase:
    def __init__(self):
        self.user_service = UserService()

    def execute(
        self,
        user: User,
        new_password: str,
        new_password_confirm: str,
    ) -> Tuple[bool, Optional[str]]:
        if new_password != new_password_confirm:
            return False, "PASSWORD_CONFIRMATION_MISMATCH"
        try:
            self.user_service.set_initial_password(user, new_password)
        except ValueError as exc:
            return False, str(exc)
        return True, None


class PasswordLoginUseCase:
    def __init__(self):
        self.token_service = TokenService()
        self.user_service = UserService()
        self.publisher = RabbitMqPublisher()

    def execute(
        self,
        art_name: str,
        password: str,
        user_agent: str = None,
        ip_address: str = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        normalized_art_name = ArtNameRule.normalize(art_name)
        user = UserRepository.get_by_art_name(normalized_art_name) if normalized_art_name else None
        if not user or not user.is_active or not user.has_usable_password() or not user.check_password(password):
            return False, "INVALID_CREDENTIALS", None

        user = self.user_service.update_last_login(user)
        access_token, refresh_token, _ = self.token_service.generate_tokens(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        event = UserLoggedIn(user_id=user.id, phone_number=user.phone_number)
        self.publisher.publish(event.to_dict(), "identity.user.logged_in")
        return True, None, build_token_response(user, self.token_service, access_token, refresh_token)


class ChangePasswordUseCase:
    def __init__(self):
        self.user_service = UserService()

    def execute(
        self,
        user: User,
        current_password: str,
        new_password: str,
        new_password_confirm: str,
    ) -> Tuple[bool, Optional[str]]:
        if new_password != new_password_confirm:
            return False, "PASSWORD_CONFIRMATION_MISMATCH"
        try:
            self.user_service.change_password(user, current_password, new_password)
        except ValueError as exc:
            return False, str(exc)
        return True, None
