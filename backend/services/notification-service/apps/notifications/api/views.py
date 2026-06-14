from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.serializers import (
    NotificationCreateSerializer,
    NotificationMessageSerializer,
    NotificationUpdateSerializer,
    TestEmailRequestSerializer,
    TestEmailResponseSerializer,
)
from apps.notifications.application.use_cases import (
    CreateNotificationUseCase,
    DeleteNotificationUseCase,
    GetNotificationDetailUseCase,
    ListInboxNotificationsUseCase,
    ListNotificationMessagesUseCase,
    SendTestEmailUseCase,
    UpdateNotificationUseCase,
)
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication
from apps.notifications.infrastructure.providers.base import InvalidEmailProviderError, EmailProviderError


NotificationListResponseSerializer = inline_serializer(
    name="NotificationListResponseSerializer",
    fields={
        "results": NotificationMessageSerializer(many=True),
    },
)

NotificationDeleteResponseSerializer = inline_serializer(
    name="NotificationDeleteResponseSerializer",
    fields={
        "message": serializers.CharField(),
    },
)


def _is_local_debug() -> bool:
    return bool(settings.DEBUG or settings.APP_ENV == "local")


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response({"error": {"code": code, "message": message}}, status=http_status)


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


class TestEmailView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Notifications"], summary="Send a test email", request=TestEmailRequestSerializer, responses={200: TestEmailResponseSerializer, 403: OpenApiResponse(description="Disabled outside local/debug")})
    def post(self, request):
        if not _is_local_debug():
            return _error_response("FORBIDDEN", "Test email endpoint is only available in local/debug environments.", status.HTTP_403_FORBIDDEN)

        serializer = TestEmailRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = SendTestEmailUseCase()

        try:
            notification_message = use_case.execute(
                email=serializer.validated_data["email"],
                message=serializer.validated_data["message"],
            )
        except InvalidEmailProviderError:
            return _error_response("INVALID_EMAIL_PROVIDER", "Configured email provider is not supported.", status.HTTP_500_INTERNAL_SERVER_ERROR)
        except EmailProviderError:
            return _error_response("EMAIL_PROVIDER_FAILED", "Email provider failed to send the message.", status.HTTP_502_BAD_GATEWAY)

        return Response(
            {
                "status": "sent",
                "provider": notification_message.provider,
                "message_id": notification_message.provider_message_id or str(notification_message.id),
            },
            status=status.HTTP_200_OK,
        )


class AuthenticatedNotificationAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
            return _error_response("NOT_AUTHENTICATED", "Authentication credentials were not provided.", status.HTTP_401_UNAUTHORIZED)
        return super().handle_exception(exc)


class MessagesView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="List recent notification messages", responses={200: NotificationMessageSerializer(many=True)})
    def get(self, request):
        if not _is_local_debug():
            return Response(status=status.HTTP_404_NOT_FOUND)

        limit = request.query_params.get("limit", 20)
        use_case = ListNotificationMessagesUseCase()
        messages = use_case.execute(limit=int(limit))
        serializer = NotificationMessageSerializer(messages, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationListCreateView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="List notifications", responses={200: NotificationListResponseSerializer})
    def get(self, request):
        limit = int(request.query_params.get("limit", 20))
        notifications = ListInboxNotificationsUseCase().execute(request.user, limit=limit)
        serializer = NotificationMessageSerializer(notifications, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Create notification", request=NotificationCreateSerializer, responses={201: NotificationMessageSerializer})
    def post(self, request):
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = CreateNotificationUseCase().execute(
            request.user,
            recipient_user_id=serializer.validated_data.get("recipient_user_id"),
            channel=serializer.validated_data["channel"],
            notification_type=serializer.validated_data["notification_type"],
            title=serializer.validated_data.get("title"),
            body=serializer.validated_data.get("body"),
            metadata=serializer.validated_data.get("metadata"),
        )
        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_201_CREATED)


class NotificationDetailView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="Get notification detail", responses={200: NotificationMessageSerializer})
    def get(self, request, notification_id):
        notification = GetNotificationDetailUseCase().execute(request.user, notification_id)
        if not notification:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Update notification", request=NotificationUpdateSerializer, responses={200: NotificationMessageSerializer})
    def patch(self, request, notification_id):
        notification = GetNotificationDetailUseCase().execute(request.user, notification_id)
        if not notification:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = NotificationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        updated = UpdateNotificationUseCase().execute(
            request.user,
            notification,
            title=serializer.validated_data.get("title"),
            body=serializer.validated_data.get("body"),
            metadata=serializer.validated_data.get("metadata"),
        )
        return Response(NotificationMessageSerializer(updated).data, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Delete notification", responses={200: NotificationDeleteResponseSerializer})
    def delete(self, request, notification_id):
        notification = GetNotificationDetailUseCase().execute(request.user, notification_id)
        if not notification:
            return Response(status=status.HTTP_404_NOT_FOUND)
        DeleteNotificationUseCase().execute(request.user, notification)
        return Response({"message": "Notification deleted."}, status=status.HTTP_200_OK)


# Compatibility alias.
TestSmsView = TestEmailView
