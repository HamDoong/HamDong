"""API views for identity-service."""

from __future__ import annotations

import logging
import hmac

from django.conf import settings
from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.authentication import JWTAuthentication
from apps.identity.api.serializers import (
    BulkUserBankCardSaveResponseSerializer,
    BulkUserBankCardSaveSerializer,
    CreateUserBankCardSerializer,
    DeactivateAccountResponseSerializer,
    DeactivateAccountSerializer,
    ForgotPasswordRequestSerializer,
    ForgotPasswordVerifySerializer,
    InternalPaymentContextBankCardsRequestSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordLoginSerializer,
    PasswordResetSerializer,
    PasswordSetSerializer,
    RefreshTokenSerializer,
    RequestOtpSerializer,
    SessionListResponseSerializer,
    SessionSerializer,
    UpdateUserSerializer,
    UpdateUserBankCardSerializer,
    UserBankCardListResponseSerializer,
    UserBankCardSerializer,
    UserSerializer,
    VerifyOtpSerializer,
)
from apps.identity.application.bank_card_service import BankCardError, BankCardService, serialize_bank_card
from apps.identity.application.token_service import TokenService
from apps.identity.application.use_cases import (
    ChangePasswordUseCase,
    DeactivateAccountUseCase,
    DeleteAllSessionsUseCase,
    DeleteSessionUseCase,
    ForgotPasswordRequestUseCase,
    ForgotPasswordVerifyUseCase,
    LogoutUseCase,
    PasswordLoginUseCase,
    PasswordResetUseCase,
    RefreshTokenUseCase,
    RequestOtpUseCase,
    SessionListUseCase,
    SetPasswordUseCase,
    UpdateProfileUseCase,
    VerifyOtpUseCase,
)
from apps.identity.infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)


AuthTokenResponseSerializer = inline_serializer(
    name="AuthTokenResponseSerializer",
    fields={
        "access_token": serializers.CharField(),
        "refresh_token": serializers.CharField(),
        "token_type": serializers.CharField(),
        "expires_in": serializers.IntegerField(),
        "user": UserSerializer(),
    },
)

MessageResponseSerializer = inline_serializer(
    name="IdentityMessageResponseSerializer",
    fields={
        "message": serializers.CharField(),
    },
)

ResetTokenResponseSerializer = inline_serializer(
    name="ResetTokenResponseSerializer",
    fields={
        "reset_token": serializers.CharField(),
        "expires_in_seconds": serializers.IntegerField(),
    },
)

DeleteAllSessionsResponseSerializer = inline_serializer(
    name="DeleteAllSessionsResponseSerializer",
    fields={
        "message": serializers.CharField(),
        "revoked_count": serializers.IntegerField(),
    },
)



def _error_response(code: str, message: str, http_status: int, details=None) -> Response:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )


class RequestOtpView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Request an OTP", request=RequestOtpSerializer, responses={200: OpenApiResponse(description="OTP requested")})
    def post(self, request):
        serializer = RequestOtpSerializer(data=request.data)
        if not serializer.is_valid():
            if "purpose" in serializer.errors:
                return _error_response(
                    "INVALID_PURPOSE",
                    "Purpose must be LOGIN or SIGNUP.",
                    status.HTTP_400_BAD_REQUEST,
                    serializer.errors,
                )

            if "email" in serializer.errors and request.data.get("email"):
                return _error_response(
                    "INVALID_EMAIL",
                    "Invalid email format.",
                    status.HTTP_400_BAD_REQUEST,
                    serializer.errors,
                )

            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        email = serializer.validated_data["email"]
        purpose = serializer.validated_data["purpose"]
        use_case = RequestOtpUseCase()
        success, error_code, debug_otp, resend_after = use_case.execute(email, purpose)

        if not success:
            if error_code == "INVALID_PURPOSE":
                return _error_response("INVALID_PURPOSE", "Purpose must be LOGIN or SIGNUP.", status.HTTP_400_BAD_REQUEST)
            if error_code == "INVALID_EMAIL":
                return _error_response("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_RATE_LIMITED":
                return _error_response("OTP_RATE_LIMITED", "Too many OTP requests. Please try again later.", status.HTTP_429_TOO_MANY_REQUESTS)
            if error_code == "OTP_IN_COOLDOWN":
                cooldown = use_case.otp_service.get_resend_cooldown(email, purpose)
                return _error_response(
                    "OTP_IN_COOLDOWN",
                    "Please wait before requesting a new OTP.",
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    {"resend_after": cooldown},
                )

        response_data = {
            "message": "OTP has been requested successfully.",
            "expires_in": settings.OTP_TTL_SECONDS,
            "resend_after": resend_after,
        }
        if debug_otp:
            response_data["debug_otp"] = debug_otp
        return Response(response_data, status=status.HTTP_200_OK)


class VerifyOtpView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Verify an OTP", request=VerifyOtpSerializer, responses={200: OpenApiResponse(description="OTP verified")})
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        if not serializer.is_valid():
            if "purpose" in serializer.errors:
                return _error_response(
                    "INVALID_PURPOSE",
                    "Purpose must be LOGIN or SIGNUP.",
                    status.HTTP_400_BAD_REQUEST,
                    serializer.errors,
                )

            if "email" in serializer.errors and request.data.get("email"):
                return _error_response(
                    "INVALID_EMAIL",
                    "Invalid email format.",
                    status.HTTP_400_BAD_REQUEST,
                    serializer.errors,
                )

            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = self._get_client_ip(request)
        use_case = VerifyOtpUseCase()
        success, error_code, token_data = use_case.execute(
            serializer.validated_data["email"],
            serializer.validated_data["code"],
            serializer.validated_data["purpose"],
            user_agent,
            ip_address,
        )

        if not success:
            if error_code == "INVALID_PURPOSE":
                return _error_response("INVALID_PURPOSE", "Purpose must be LOGIN or SIGNUP.", status.HTTP_400_BAD_REQUEST)
            if error_code == "INVALID_OTP":
                return _error_response("INVALID_OTP", "The OTP code is invalid.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_EXPIRED":
                return _error_response("OTP_EXPIRED", "The OTP code has expired.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_MAX_ATTEMPTS_EXCEEDED":
                return _error_response("OTP_MAX_ATTEMPTS_EXCEEDED", "Maximum OTP verification attempts exceeded.", status.HTTP_429_TOO_MANY_REQUESTS)
            if error_code == "INVALID_EMAIL":
                return _error_response("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST)
            if error_code == "ACCOUNT_DEACTIVATED":
                return _error_response("ACCOUNT_DEACTIVATED", "This account has been deactivated.", status.HTTP_403_FORBIDDEN)
            if error_code == "USER_NOT_FOUND":
                return _error_response("USER_NOT_FOUND", "No active account exists for this email.", status.HTTP_404_NOT_FOUND)
            if error_code == "EMAIL_ALREADY_EXISTS":
                return _error_response("EMAIL_ALREADY_EXISTS", "An account already exists for this email.", status.HTTP_409_CONFLICT)

        return Response(token_data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        return x_forwarded_for.split(",")[0] if x_forwarded_for else request.META.get("REMOTE_ADDR")


class RefreshTokenView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Refresh access token", request=RefreshTokenSerializer, responses={200: OpenApiResponse(description="Tokens refreshed")})
    def post(self, request):
        serializer = RefreshTokenSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = VerifyOtpView._get_client_ip(request)
        success, error_code, token_data = RefreshTokenUseCase().execute(
            serializer.validated_data["refresh_token"],
            user_agent,
            ip_address,
        )

        if not success:
            return _error_response("INVALID_TOKEN", "The provided token is invalid.", status.HTTP_401_UNAUTHORIZED)
        return Response(token_data, status=status.HTTP_200_OK)


class LogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Logout and revoke refresh token", request=LogoutSerializer, responses={200: OpenApiResponse(description="Logged out")})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        success, _ = LogoutUseCase().execute(serializer.validated_data["refresh_token"])
        if not success:
            return _error_response("INVALID_TOKEN", "The provided token is invalid.", status.HTTP_401_UNAUTHORIZED)

        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class ForgotPasswordRequestView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Request a password-reset verification code",
        request=ForgotPasswordRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            429: OpenApiResponse(description="Too many password-reset requests"),
        },
        examples=[
            OpenApiExample(
                "Forgot password request",
                value={"email": "user@example.com"},
                request_only=True,
            ),
            OpenApiExample(
                "Generic success response",
                value={"message": "If the account exists, a verification code has been sent."},
                response_only=True,
            ),
        ],
    )
    def post(self, request):
        serializer = ForgotPasswordRequestSerializer(data=request.data)
        if not serializer.is_valid():
            if "email" in serializer.errors and request.data.get("email"):
                return _error_response("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        success, error_code, debug_otp = ForgotPasswordRequestUseCase().execute(serializer.validated_data["email"])
        if not success:
            if error_code == "OTP_RATE_LIMITED":
                return _error_response("OTP_RATE_LIMITED", "Too many password reset requests. Please try again later.", status.HTTP_429_TOO_MANY_REQUESTS)
            if error_code == "OTP_IN_COOLDOWN":
                return _error_response("OTP_IN_COOLDOWN", "Please wait before requesting a new verification code.", status.HTTP_429_TOO_MANY_REQUESTS)
            if error_code == "INVALID_EMAIL":
                return _error_response("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST)
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST)

        return Response(
            {"message": "If the account exists, a verification code has been sent."},
            status=status.HTTP_200_OK,
        )


class ForgotPasswordVerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Verify a password-reset OTP",
        request=ForgotPasswordVerifySerializer,
        responses={
            200: ResetTokenResponseSerializer,
            400: OpenApiResponse(description="Invalid or expired OTP"),
            429: OpenApiResponse(description="Too many invalid OTP attempts"),
        },
        examples=[
            OpenApiExample(
                "Verify reset OTP",
                value={"email": "user@example.com", "otp": "123456"},
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = ForgotPasswordVerifySerializer(data=request.data)
        if not serializer.is_valid():
            if "email" in serializer.errors and request.data.get("email"):
                return _error_response("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST, serializer.errors)
            if "otp" in serializer.errors:
                return _error_response("INVALID_OTP", "The OTP code is invalid.", status.HTTP_400_BAD_REQUEST, serializer.errors)
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        success, error_code, token_data = ForgotPasswordVerifyUseCase().execute(
            serializer.validated_data["email"],
            serializer.validated_data["otp"],
        )
        if not success:
            mapping = {
                "INVALID_EMAIL": ("INVALID_EMAIL", "Invalid email format.", status.HTTP_400_BAD_REQUEST),
                "INVALID_OTP": ("INVALID_OTP", "The OTP code is invalid.", status.HTTP_400_BAD_REQUEST),
                "OTP_EXPIRED": ("OTP_EXPIRED", "The OTP code has expired.", status.HTTP_400_BAD_REQUEST),
                "OTP_ALREADY_USED": ("OTP_ALREADY_USED", "The OTP code has already been used.", status.HTTP_400_BAD_REQUEST),
                "OTP_MAX_ATTEMPTS_EXCEEDED": ("OTP_MAX_ATTEMPTS_EXCEEDED", "Maximum OTP verification attempts exceeded.", status.HTTP_429_TOO_MANY_REQUESTS),
            }
            code, message, http_status = mapping.get(error_code, ("INVALID_OTP", "The OTP code is invalid.", status.HTTP_400_BAD_REQUEST))
            return _error_response(code, message, http_status)
        return Response(token_data, status=status.HTTP_200_OK)


class PasswordResetView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Reset password with a one-time reset token",
        request=PasswordResetSerializer,
        responses={
            200: MessageResponseSerializer,
            400: OpenApiResponse(description="Invalid reset token or password"),
        },
        examples=[
            OpenApiExample(
                "Reset password",
                value={
                    "reset_token": "one-time-reset-token",
                    "new_password": "StrongPassword123!",
                    "new_password_confirm": "StrongPassword123!",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        success, error_code = PasswordResetUseCase().execute(
            reset_token=serializer.validated_data["reset_token"],
            new_password=serializer.validated_data["new_password"],
            new_password_confirm=serializer.validated_data["new_password_confirm"],
        )
        if not success:
            mapping = {
                "PASSWORD_CONFIRMATION_MISMATCH": ("PASSWORD_CONFIRMATION_MISMATCH", "Password confirmation does not match.", status.HTTP_400_BAD_REQUEST),
                "WEAK_PASSWORD": ("WEAK_PASSWORD", "Password does not meet security requirements.", status.HTTP_400_BAD_REQUEST),
                "INVALID_RESET_TOKEN": ("INVALID_RESET_TOKEN", "The provided reset token is invalid.", status.HTTP_400_BAD_REQUEST),
                "RESET_TOKEN_USED": ("RESET_TOKEN_USED", "The provided reset token has already been used.", status.HTTP_400_BAD_REQUEST),
                "RESET_TOKEN_EXPIRED": ("RESET_TOKEN_EXPIRED", "The provided reset token has expired.", status.HTTP_400_BAD_REQUEST),
            }
            code, message, http_status = mapping[error_code]
            return _error_response(code, message, http_status)
        return Response({"message": "Password reset successfully."}, status=status.HTTP_200_OK)


class SessionsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="List active sessions",
        responses={200: SessionListResponseSerializer},
    )
    def get(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        results = SessionListUseCase().execute(user=user, current_jti=getattr(request.user, "token_jti", None))
        return Response({"results": results}, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Auth"],
        summary="Delete all other active sessions",
        responses={200: DeleteAllSessionsResponseSerializer},
    )
    def delete(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        revoked_count = DeleteAllSessionsUseCase().execute(user=user, current_jti=getattr(request.user, "token_jti", None))
        return Response(
            {
                "message": "All other sessions revoked successfully.",
                "revoked_count": revoked_count,
            },
            status=status.HTTP_200_OK,
        )


class SessionDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Delete one session",
        responses={204: OpenApiResponse(description="Session revoked"), 404: OpenApiResponse(description="Session not found")},
    )
    def delete(self, request, session_id):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        success = DeleteSessionUseCase().execute(user=user, session_id=str(session_id))
        if not success:
            return _error_response("SESSION_NOT_FOUND", "Session not found.", status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordSetView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Auth"], summary="Set password", request=PasswordSetSerializer, responses={200: MessageResponseSerializer})
    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = PasswordSetSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        success, error_code = SetPasswordUseCase().execute(
            user,
            serializer.validated_data["new_password"],
            serializer.validated_data["new_password_confirm"],
        )
        if not success:
            mapping = {
                "PASSWORD_ALREADY_SET": ("PASSWORD_ALREADY_SET", "Password is already set. Use change password endpoint.", status.HTTP_409_CONFLICT),
                "PASSWORD_CONFIRMATION_MISMATCH": ("PASSWORD_CONFIRMATION_MISMATCH", "Password confirmation does not match.", status.HTTP_400_BAD_REQUEST),
                "WEAK_PASSWORD": ("WEAK_PASSWORD", "Password does not meet security requirements.", status.HTTP_400_BAD_REQUEST),
            }
            code, message, http_status = mapping[error_code]
            return _error_response(code, message, http_status)
        return Response({"message": "Password has been set successfully."}, status=status.HTTP_200_OK)


class PasswordLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Login with password", request=PasswordLoginSerializer, responses={200: AuthTokenResponseSerializer})
    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = VerifyOtpView._get_client_ip(request)
        success, _, token_data = PasswordLoginUseCase().execute(
            serializer.validated_data["art_name"],
            serializer.validated_data["password"],
            user_agent,
            ip_address,
            remember_me=serializer.validated_data.get("remember_me", False),
        )
        if not success:
            return _error_response("INVALID_CREDENTIALS", "Invalid username or password.", status.HTTP_401_UNAUTHORIZED)
        return Response(token_data, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Change password",
        description="Changes the current password, revokes other refresh-token sessions for the same user, and queues a safe PasswordChanged event.",
        request=PasswordChangeSerializer,
        responses={200: MessageResponseSerializer},
        examples=[
            OpenApiExample(
                "Password change request",
                value={
                    "current_password": "OldPassword123!",
                    "new_password": "NewPassword123!",
                    "new_password_confirm": "NewPassword123!",
                },
                request_only=True,
            )
        ],
    )
    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                "Invalid request data.",
                status.HTTP_400_BAD_REQUEST,
                serializer.errors,
            )

        success, error_code = ChangePasswordUseCase().execute(
            user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
            serializer.validated_data["new_password_confirm"],
            current_jti=getattr(request.user, "token_jti", None),
        )
        if not success:
            mapping = {
                "PASSWORD_CONFIRMATION_MISMATCH": ("PASSWORD_CONFIRMATION_MISMATCH", "Password confirmation does not match.", status.HTTP_400_BAD_REQUEST),
                "INVALID_CURRENT_PASSWORD": ("INVALID_CURRENT_PASSWORD", "Current password is incorrect.", status.HTTP_400_BAD_REQUEST),
                "PASSWORD_REUSE_NOT_ALLOWED": ("PASSWORD_REUSE_NOT_ALLOWED", "New password must be different from the current password.", status.HTTP_400_BAD_REQUEST),
                "WEAK_PASSWORD": ("WEAK_PASSWORD", "Password does not meet security requirements.", status.HTTP_400_BAD_REQUEST),
            }
            code, message, http_status = mapping[error_code]
            return _error_response(code, message, http_status)
        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Get current user profile",
        description="Returns the authenticated user's current profile. New private profile fields are returned only from identity-service and are not published in general UserUpdated events.",
        responses={200: UserSerializer},
    )
    def get(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Users"],
        summary="Update current user profile",
        description=(
            "Partially updates the authenticated user's editable profile fields. "
            "Editable fields: art_name, first_name, last_name, display_name, phone_number, "
            "date_of_birth, city, bio. Read-only or ignored fields such as email, role, "
            "is_email_verified, avatar_url, and password are not updated."
        ),
        request=UpdateUserSerializer,
        responses={200: UserSerializer},
        examples=[
            OpenApiExample(
                "Patch profile",
                value={
                    "display_name": "علی احمدی",
                    "phone_number": "09123456789",
                    "date_of_birth": "1998-07-01",
                    "city": "Tehran",
                    "bio": "Backend developer",
                },
                request_only=True,
            )
        ],
    )
    def patch(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = UpdateUserSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            error_mappings = {
                "art_name": ("INVALID_ART_NAME", "Art name format is invalid."),
                "display_name": ("INVALID_DISPLAY_NAME", "Display name is invalid."),
                "phone_number": ("INVALID_PHONE_NUMBER", "Phone number is invalid."),
                "date_of_birth": ("INVALID_DATE_OF_BIRTH", "Date of birth is invalid."),
                "city": ("INVALID_CITY", "City is invalid."),
                "bio": ("INVALID_BIO", "Biography is invalid."),
                "first_name": ("INVALID_FIRST_NAME", "First name is invalid."),
                "last_name": ("INVALID_LAST_NAME", "Last name is invalid."),
            }
            for field_name, (code, message) in error_mappings.items():
                if field_name in serializer.errors:
                    return _error_response(code, message, status.HTTP_400_BAD_REQUEST, serializer.errors)
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        try:
            _, updated_user = UpdateProfileUseCase().execute(
                user,
                **serializer.validated_data,
            )
        except ValueError as exc:
            if str(exc) == "ART_NAME_ALREADY_EXISTS":
                return _error_response("ART_NAME_ALREADY_EXISTS", "This art name is already taken.", status.HTTP_409_CONFLICT)
            if str(exc) == "PHONE_NUMBER_ALREADY_EXISTS":
                return _error_response("PHONE_NUMBER_ALREADY_EXISTS", "This phone number is already in use.", status.HTTP_409_CONFLICT)
            if str(exc) == "INVALID_ART_NAME":
                return _error_response("INVALID_ART_NAME", "Art name format is invalid.", status.HTTP_400_BAD_REQUEST)
            if str(exc) == "INVALID_DISPLAY_NAME":
                return _error_response("INVALID_DISPLAY_NAME", "Display name is invalid.", status.HTTP_400_BAD_REQUEST)
            if str(exc) == "INVALID_PHONE_NUMBER":
                return _error_response("INVALID_PHONE_NUMBER", "Phone number is invalid.", status.HTTP_400_BAD_REQUEST)
            if str(exc) == "INVALID_DATE_OF_BIRTH":
                return _error_response("INVALID_DATE_OF_BIRTH", "Date of birth is invalid.", status.HTTP_400_BAD_REQUEST)
            raise

        return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)


class MeBankCardsView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="List current user's bank cards",
        parameters=[OpenApiParameter(name="include_inactive", required=False, type=bool)],
        responses={200: UserBankCardListResponseSerializer},
    )
    def get(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        include_inactive = str(request.query_params.get("include_inactive", "false")).lower() in {"1", "true", "yes"}
        cards = BankCardService().list_cards(user, include_inactive=include_inactive)
        return Response({"items": [serialize_bank_card(card) for card in cards]})

    @extend_schema(
        tags=["Users"],
        summary="Create a bank card",
        request=CreateUserBankCardSerializer,
        responses={201: UserBankCardSerializer},
    )
    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        serializer = CreateUserBankCardSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            card, created = BankCardService().create_card(user, **serializer.validated_data)
        except BankCardError as exc:
            http_status = status.HTTP_409_CONFLICT if exc.code in {"CARD_ALREADY_EXISTS", "BANK_CARD_LIMIT_EXCEEDED"} else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status, exc.fields)
        return Response(serialize_bank_card(card), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MeBankCardDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Users"], summary="Update a bank card", request=UpdateUserBankCardSerializer, responses={200: UserBankCardSerializer})
    def patch(self, request, card_id):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        serializer = UpdateUserBankCardSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            card = BankCardService().update_card(user, card_id, serializer.validated_data)
        except BankCardError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            if exc.code == "CARD_NUMBER_IMMUTABLE":
                http_status = status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status, exc.fields)
        return Response(serialize_bank_card(card))

    @extend_schema(tags=["Users"], summary="Delete a bank card", responses={204: OpenApiResponse(description="Bank card deactivated")})
    def delete(self, request, card_id):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        try:
            BankCardService().delete_card(user, card_id)
        except BankCardError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status, exc.fields)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeBankCardsBulkView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Users"], summary="Bulk save bank cards", request=BulkUserBankCardSaveSerializer, responses={200: BulkUserBankCardSaveResponseSerializer})
    def put(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        serializer = BulkUserBankCardSaveSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        deleted_card_ids = serializer.validated_data.get("deleted_card_ids", [])
        try:
            items = BankCardService().bulk_save(
                user,
                serializer.validated_data.get("cards", []),
                deleted_card_ids=deleted_card_ids,
            )
        except BankCardError as exc:
            http_status = status.HTTP_409_CONFLICT if exc.code in {"BANK_CARD_LIMIT_EXCEEDED"} else status.HTTP_400_BAD_REQUEST
            if exc.code == "NOT_FOUND":
                http_status = status.HTTP_404_NOT_FOUND
            return _error_response(exc.code, exc.message, http_status, exc.fields)
        return Response({"items": items, "deleted_card_ids": deleted_card_ids})


class DeactivateAccountView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Users"], summary="Deactivate current account", request=DeactivateAccountSerializer, responses={200: DeactivateAccountResponseSerializer})
    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        serializer = DeactivateAccountSerializer(data=request.data or {})
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            result, updated_user = DeactivateAccountUseCase().execute(
                user,
                current_password=serializer.validated_data.get("current_password"),
                reason=serializer.validated_data.get("reason"),
            )
        except BankCardError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_400_BAD_REQUEST, exc.fields)
        if result == "ALREADY_DEACTIVATED":
            return Response(
                {
                    "status": result,
                    "message": "Your account is already deactivated.",
                    "deactivated_at": updated_user.deleted_at,
                }
            )
        return Response(
            {
                "status": result,
                "message": "Your account has been deactivated successfully.",
                "deactivated_at": updated_user.deleted_at,
            }
        )


class InternalPaymentContextBankCardsView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def _is_authorized(self, request) -> bool:
        expected = str(getattr(settings, "INTERNAL_SERVICE_TOKEN", "hamdong-internal-token"))
        provided = request.headers.get("X-Internal-Service-Token") or request.META.get("HTTP_X_INTERNAL_SERVICE_TOKEN")
        return bool(provided and hmac.compare_digest(provided, expected))

    @extend_schema(
        tags=["Internal"],
        summary="Resolve owner bank cards for internal payment contexts",
        request=InternalPaymentContextBankCardsRequestSerializer,
        responses={200: UserBankCardListResponseSerializer},
    )
    def post(self, request):
        if not self._is_authorized(request):
            return _error_response("FORBIDDEN", "Internal authorization failed.", status.HTTP_403_FORBIDDEN)
        serializer = InternalPaymentContextBankCardsRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        items = BankCardService().resolve_payment_context_cards(
            serializer.validated_data["owner_user_id"],
            card_ids=serializer.validated_data.get("card_ids"),
        )
        return Response({"items": items})


class JwksView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Auth"], summary="Get JWKS public key set", responses={200: OpenApiResponse(description="JWKS document")})
    def get(self, request):
        try:
            jwks = TokenService().get_jwks()
            return Response(jwks, status=status.HTTP_200_OK)
        except Exception as exc:
            logger.error("Error retrieving JWKS: %s", exc)
            return _error_response("KEY_LOAD_ERROR", "Failed to load public key.", status.HTTP_500_INTERNAL_SERVER_ERROR)
