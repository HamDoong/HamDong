"""API views for identity service."""

import logging

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.authentication import JWTAuthentication
from apps.identity.api.serializers import (
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordLoginSerializer,
    PasswordSetSerializer,
    RefreshTokenSerializer,
    RequestOtpSerializer,
    UpdateUserSerializer,
    UserSerializer,
    VerifyOtpSerializer,
)
from apps.identity.application.token_service import TokenService
from apps.identity.application.use_cases import (
    ChangePasswordUseCase,
    LogoutUseCase,
    PasswordLoginUseCase,
    RefreshTokenUseCase,
    RequestOtpUseCase,
    SetPasswordUseCase,
    UpdateProfileUseCase,
    VerifyOtpUseCase,
)
from apps.identity.infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)


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
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        phone_number = serializer.validated_data["phone_number"]
        use_case = RequestOtpUseCase()
        success, error_code, debug_otp, resend_after = use_case.execute(phone_number)

        if not success:
            if error_code == "INVALID_PHONE":
                return _error_response("INVALID_PHONE", "Invalid phone number format.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_RATE_LIMITED":
                return _error_response("OTP_RATE_LIMITED", "Too many OTP requests. Please try again later.", status.HTTP_429_TOO_MANY_REQUESTS)
            if error_code == "OTP_IN_COOLDOWN":
                cooldown = use_case.otp_service.get_resend_cooldown(phone_number)
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
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = self._get_client_ip(request)
        use_case = VerifyOtpUseCase()
        success, error_code, token_data = use_case.execute(
            serializer.validated_data["phone_number"],
            serializer.validated_data["code"],
            user_agent,
            ip_address,
        )

        if not success:
            if error_code == "INVALID_OTP":
                return _error_response("INVALID_OTP", "The OTP code is invalid.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_EXPIRED":
                return _error_response("OTP_EXPIRED", "The OTP code has expired.", status.HTTP_400_BAD_REQUEST)
            if error_code == "OTP_MAX_ATTEMPTS_EXCEEDED":
                return _error_response("OTP_MAX_ATTEMPTS_EXCEEDED", "Maximum OTP verification attempts exceeded.", status.HTTP_429_TOO_MANY_REQUESTS)

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
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

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
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        success, _ = LogoutUseCase().execute(serializer.validated_data["refresh_token"])
        if not success:
            return _error_response("INVALID_TOKEN", "The provided token is invalid.", status.HTTP_401_UNAUTHORIZED)

        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class PasswordSetView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = PasswordSetSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

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

    def post(self, request):
        serializer = PasswordLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = VerifyOtpView._get_client_ip(request)
        success, _, token_data = PasswordLoginUseCase().execute(
            serializer.validated_data["art_name"],
            serializer.validated_data["password"],
            user_agent,
            ip_address,
        )
        if not success:
            return _error_response("INVALID_CREDENTIALS", "Invalid username or password.", status.HTTP_401_UNAUTHORIZED)
        return Response(token_data, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = PasswordChangeSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        success, error_code = ChangePasswordUseCase().execute(
            user,
            serializer.validated_data["current_password"],
            serializer.validated_data["new_password"],
            serializer.validated_data["new_password_confirm"],
        )
        if not success:
            mapping = {
                "INVALID_CURRENT_PASSWORD": ("INVALID_CURRENT_PASSWORD", "Current password is incorrect.", status.HTTP_400_BAD_REQUEST),
                "PASSWORD_CONFIRMATION_MISMATCH": ("PASSWORD_CONFIRMATION_MISMATCH", "Password confirmation does not match.", status.HTTP_400_BAD_REQUEST),
                "PASSWORD_REUSE_NOT_ALLOWED": ("PASSWORD_REUSE_NOT_ALLOWED", "New password must be different from the current password.", status.HTTP_400_BAD_REQUEST),
                "WEAK_PASSWORD": ("WEAK_PASSWORD", "Password does not meet security requirements.", status.HTTP_400_BAD_REQUEST),
            }
            code, message, http_status = mapping[error_code]
            return _error_response(code, message, http_status)

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class GetCurrentUserView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=["Users"], summary="Get current user profile", responses={200: UserSerializer})
    def get(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)

    @extend_schema(tags=["Users"], summary="Update current user profile", request=UpdateUserSerializer, responses={200: UserSerializer})
    def patch(self, request):
        user = UserRepository.get_by_id(request.user.id)
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)

        serializer = UpdateUserSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            if serializer.errors.get("art_name") == ["INVALID_ART_NAME"]:
                return _error_response("INVALID_ART_NAME", "Art name format is invalid.", status.HTTP_400_BAD_REQUEST)
            return _error_response("INVALID_REQUEST", "Invalid request data.", status.HTTP_400_BAD_REQUEST, serializer.errors)

        try:
            _, updated_user = UpdateProfileUseCase().execute(
                user,
                display_name=serializer.validated_data.get("display_name"),
                art_name=serializer.validated_data.get("art_name"),
                first_name=serializer.validated_data.get("first_name"),
                last_name=serializer.validated_data.get("last_name"),
            )
        except ValueError as exc:
            if str(exc) == "ART_NAME_ALREADY_EXISTS":
                return _error_response("ART_NAME_ALREADY_EXISTS", "This art name is already taken.", status.HTTP_409_CONFLICT)
            if str(exc) == "INVALID_ART_NAME":
                return _error_response("INVALID_ART_NAME", "Art name format is invalid.", status.HTTP_400_BAD_REQUEST)
            raise

        return Response(UserSerializer(updated_user).data, status=status.HTTP_200_OK)


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
