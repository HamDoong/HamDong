"""API views for identity service."""

import logging

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.identity.api.serializers import (
    RequestOtpSerializer,
    VerifyOtpSerializer,
    RefreshTokenSerializer,
    LogoutSerializer,
    UserSerializer,
    UpdateUserSerializer,
)
from apps.identity.api.authentication import JWTAuthentication
from apps.identity.application.use_cases import (
    RequestOtpUseCase,
    VerifyOtpUseCase,
    RefreshTokenUseCase,
    LogoutUseCase,
    UpdateProfileUseCase,
)
from apps.identity.application.token_service import TokenService
from apps.identity.infrastructure.repositories import UserRepository

logger = logging.getLogger(__name__)


class HealthView(APIView):
    """Health check endpoint."""

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
    """Request OTP endpoint."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Request an OTP",
        request=RequestOtpSerializer,
        responses={200: OpenApiResponse(description="OTP requested")},
    )
    def post(self, request):
        """Request OTP for phone number."""
        serializer = RequestOtpSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request data.",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = serializer.validated_data["phone_number"]

        # Execute use case
        use_case = RequestOtpUseCase()
        success, error_code, debug_otp, resend_after = use_case.execute(phone_number)

        if not success:
            # Map error codes to HTTP status and response
            if error_code == "INVALID_PHONE":
                return Response(
                    {
                        "error": {
                            "code": "INVALID_PHONE",
                            "message": "Invalid phone number format.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif error_code == "OTP_RATE_LIMITED":
                return Response(
                    {
                        "error": {
                            "code": "OTP_RATE_LIMITED",
                            "message": "Too many OTP requests. Please try again later.",
                        }
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            elif error_code == "OTP_IN_COOLDOWN":
                cooldown = use_case.otp_service.get_resend_cooldown(phone_number)
                return Response(
                    {
                        "error": {
                            "code": "OTP_IN_COOLDOWN",
                            "message": "Please wait before requesting a new OTP.",
                            "resend_after": cooldown,
                        }
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
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
    """Verify OTP endpoint."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Verify an OTP",
        request=VerifyOtpSerializer,
        responses={200: OpenApiResponse(description="OTP verified")},
    )
    def post(self, request):
        """Verify OTP and login user."""
        serializer = VerifyOtpSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request data.",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        phone_number = serializer.validated_data["phone_number"]
        otp_code = serializer.validated_data["code"]

        # Get user agent and IP address
        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = self._get_client_ip(request)

        # Execute use case
        use_case = VerifyOtpUseCase()
        success, error_code, token_data = use_case.execute(
            phone_number, otp_code, user_agent, ip_address
        )

        if not success:
            if error_code == "INVALID_OTP":
                return Response(
                    {
                        "error": {
                            "code": "INVALID_OTP",
                            "message": "The OTP code is invalid.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif error_code == "OTP_EXPIRED":
                return Response(
                    {
                        "error": {
                            "code": "OTP_EXPIRED",
                            "message": "The OTP code has expired.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif error_code == "OTP_MAX_ATTEMPTS_EXCEEDED":
                return Response(
                    {
                        "error": {
                            "code": "OTP_MAX_ATTEMPTS_EXCEEDED",
                            "message": "Maximum OTP verification attempts exceeded.",
                        }
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        return Response(token_data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class RefreshTokenView(APIView):
    """Refresh access token endpoint."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        request=RefreshTokenSerializer,
        responses={200: OpenApiResponse(description="Tokens refreshed")},
    )
    def post(self, request):
        """Refresh access token."""
        serializer = RefreshTokenSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request data.",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh_token = serializer.validated_data["refresh_token"]

        # Get user agent and IP address
        user_agent = request.META.get("HTTP_USER_AGENT")
        ip_address = self._get_client_ip(request)

        # Execute use case
        use_case = RefreshTokenUseCase()
        success, error_code, token_data = use_case.execute(
            refresh_token, user_agent, ip_address
        )

        if not success:
            return Response(
                {
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "The provided token is invalid.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(token_data, status=status.HTTP_200_OK)

    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


class LogoutView(APIView):
    """Logout endpoint."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Logout and revoke refresh token",
        request=LogoutSerializer,
        responses={200: OpenApiResponse(description="Logged out")},
    )
    def post(self, request):
        """Logout by revoking refresh token."""
        serializer = LogoutSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                {
                    "error": {
                        "code": "INVALID_REQUEST",
                        "message": "Invalid request data.",
                        "details": serializer.errors,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        refresh_token = serializer.validated_data["refresh_token"]

        # Execute use case
        use_case = LogoutUseCase()
        success, error_code = use_case.execute(refresh_token)

        if not success:
            return Response(
                {
                    "error": {
                        "code": "INVALID_TOKEN",
                        "message": "The provided token is invalid.",
                    }
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(
            {"message": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )


class GetCurrentUserView(APIView):
    """Get current user endpoint."""

    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        """Get current user information."""
        try:
            user = UserRepository.get_by_id(request.user.id)

            if not user:
                return Response(
                    {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "User not found.",
                        }
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An error occurred.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @extend_schema(
        tags=["Users"],
        summary="Update current user profile",
        request=UpdateUserSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request):
        """Update current user profile."""
        try:
            user = UserRepository.get_by_id(request.user.id)

            if not user:
                return Response(
                    {
                        "error": {
                            "code": "USER_NOT_FOUND",
                            "message": "User not found.",
                        }
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            serializer = UpdateUserSerializer(data=request.data, partial=True)

            if not serializer.is_valid():
                return Response(
                    {
                        "error": {
                            "code": "INVALID_REQUEST",
                            "message": "Invalid request data.",
                            "details": serializer.errors,
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            use_case = UpdateProfileUseCase()
            success, updated_user = use_case.execute(
                user,
                display_name=serializer.validated_data.get("display_name"),
                first_name=serializer.validated_data.get("first_name"),
                last_name=serializer.validated_data.get("last_name"),
            )

            response_serializer = UserSerializer(updated_user)
            return Response(response_serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error updating user: {e}")
            return Response(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An error occurred.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class JwksView(APIView):
    """JWKS (JSON Web Key Set) endpoint for public key."""

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Auth"],
        summary="Get JWKS public key set",
        responses={200: OpenApiResponse(description="JWKS document")},
    )
    def get(self, request):
        """Get JWKS."""
        try:
            token_service = TokenService()
            jwks = token_service.get_jwks()
            return Response(jwks, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving JWKS: {e}")
            return Response(
                {
                    "error": {
                        "code": "KEY_LOAD_ERROR",
                        "message": "Failed to load public key.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
