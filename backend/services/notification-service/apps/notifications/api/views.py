from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated

from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication

from apps.notifications.api.serializers import (
    NotificationMessageSerializer,
    TestSmsRequestSerializer,
    TestSmsResponseSerializer,
)
from apps.notifications.application.use_cases import (
    ListNotificationMessagesUseCase,
    SendTestSmsUseCase,
)
from apps.notifications.infrastructure.providers.base import (
    InvalidSmsProviderError,
    SmsProviderError,
)


def _is_local_debug() -> bool:
    return bool(settings.DEBUG or settings.APP_ENV == "local")

def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )

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


class TestSmsView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Notifications"],
        summary="Send a test SMS",
        request=TestSmsRequestSerializer,
        responses={
            200: TestSmsResponseSerializer,
            403: OpenApiResponse(description="Disabled outside local/debug"),
        },
    )
    def post(self, request):
        if not _is_local_debug():
            return Response(
                {
                    "error": {
                        "code": "FORBIDDEN",
                        "message": "Test SMS endpoint is only available in local/debug environments.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = TestSmsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = SendTestSmsUseCase()

        try:
            notification_message = use_case.execute(
                phone_number=serializer.validated_data["phone_number"],
                message=serializer.validated_data["message"],
            )
        except InvalidSmsProviderError:
            return Response(
                {
                    "error": {
                        "code": "INVALID_SMS_PROVIDER",
                        "message": "Configured SMS provider is not supported.",
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except SmsProviderError:
            return Response(
                {
                    "error": {
                        "code": "SMS_PROVIDER_FAILED",
                        "message": "SMS provider failed to send the message.",
                    }
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "status": "sent",
                "provider": notification_message.provider,
                "message_id": notification_message.provider_message_id
                or str(notification_message.id),
            },
            status=status.HTTP_200_OK,
        )


class AuthenticatedNotificationAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            return _error_response(
                "NOT_AUTHENTICATED",
                "Authentication credentials were not provided.",
                status.HTTP_401_UNAUTHORIZED,
            )
        return super().handle_exception(exc)


class MessagesView(AuthenticatedNotificationAPIView):

    @extend_schema(
        tags=["Notifications"],
        summary="List recent notification messages",
        responses={200: NotificationMessageSerializer(many=True)},
    )
    def get(self, request):
        if not _is_local_debug():
            return Response(status=status.HTTP_404_NOT_FOUND)

        limit = request.query_params.get("limit", 20)
        use_case = ListNotificationMessagesUseCase()
        messages = use_case.execute(limit=int(limit))
        serializer = NotificationMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
