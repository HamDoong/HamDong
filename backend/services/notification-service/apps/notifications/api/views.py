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
    TestSmsRequestSerializer,
    TestSmsResponseSerializer,
)
from apps.notifications.application.use_cases import (
    CreateNotificationUseCase,
    DeleteNotificationUseCase,
    GetNotificationDetailUseCase,
    ListInboxNotificationsUseCase,
    ListNotificationMessagesUseCase,
    SendTestSmsUseCase,
    UpdateNotificationUseCase,
)
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication
from apps.notifications.infrastructure.providers.base import InvalidSmsProviderError, SmsProviderError


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


class TestSmsView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(tags=["Notifications"], summary="Send a test SMS", request=TestSmsRequestSerializer, responses={200: TestSmsResponseSerializer, 403: OpenApiResponse(description="Disabled outside local/debug")})
    def post(self, request):
        if not _is_local_debug():
            return _error_response("FORBIDDEN", "Test SMS endpoint is only available in local/debug environments.", status.HTTP_403_FORBIDDEN)

        serializer = TestSmsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        use_case = SendTestSmsUseCase()

        try:
            notification_message = use_case.execute(
                phone_number=serializer.validated_data["phone_number"],
                message=serializer.validated_data["message"],
            )
        except InvalidSmsProviderError:
            return _error_response("INVALID_SMS_PROVIDER", "Configured SMS provider is not supported.", status.HTTP_500_INTERNAL_SERVER_ERROR)
        except SmsProviderError:
            return _error_response("SMS_PROVIDER_FAILED", "SMS provider failed to send the message.", status.HTTP_502_BAD_GATEWAY)

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
        return Response({"results": NotificationMessageSerializer(notifications, many=True).data}, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Create notification", request=NotificationCreateSerializer, responses={201: NotificationMessageSerializer})
    def post(self, request):
        serializer = NotificationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient_user_id = serializer.validated_data.get("recipient_user_id") or getattr(request.user, "sub", request.user.id)
        actor_role = getattr(request.user, "role", "USER")
        if str(recipient_user_id) != str(getattr(request.user, "sub", request.user.id)) and actor_role not in ("ADMIN", "SYSTEM"):
            return _error_response("PERMISSION_DENIED", "You do not have permission to create this notification.", status.HTTP_403_FORBIDDEN)

        notification = CreateNotificationUseCase().execute(
            request.user,
            recipient_user_id=recipient_user_id,
            channel=serializer.validated_data["channel"],
            notification_type=serializer.validated_data["notification_type"],
            title=serializer.validated_data.get("title", ""),
            body=serializer.validated_data.get("body", ""),
            metadata=serializer.validated_data.get("metadata", {}),
        )
        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_201_CREATED)


class NotificationDetailView(AuthenticatedNotificationAPIView):
    def get_object(self, request, notification_id):
        return GetNotificationDetailUseCase().execute(request.user, notification_id)

    @extend_schema(tags=["Notifications"], summary="Get notification detail", responses={200: NotificationMessageSerializer})
    def get(self, request, notification_id):
        notification = self.get_object(request, notification_id)
        if not notification:
            return _error_response("NOTIFICATION_NOT_FOUND", "Notification not found.", status.HTTP_404_NOT_FOUND)
        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Update notification", request=NotificationUpdateSerializer, responses={200: NotificationMessageSerializer})
    def patch(self, request, notification_id):
        notification = self.get_object(request, notification_id)
        if not notification:
            return _error_response("NOTIFICATION_NOT_FOUND", "Notification not found.", status.HTTP_404_NOT_FOUND)

        serializer = NotificationUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        try:
            notification = UpdateNotificationUseCase().execute(request.user, notification, **serializer.validated_data)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to edit this notification.", status.HTTP_403_FORBIDDEN)
        except ValueError:
            return _error_response("NOTIFICATION_NOT_EDITABLE", "Sent notifications cannot be edited.", status.HTTP_409_CONFLICT)

        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_200_OK)

    @extend_schema(tags=["Notifications"], summary="Delete notification", responses={200: NotificationDeleteResponseSerializer})
    def delete(self, request, notification_id):
        notification = self.get_object(request, notification_id)
        if not notification:
            return _error_response("NOTIFICATION_NOT_FOUND", "Notification not found.", status.HTTP_404_NOT_FOUND)

        try:
            DeleteNotificationUseCase().execute(request.user, notification)
        except PermissionError:
            return _error_response("PERMISSION_DENIED", "You do not have permission to delete this notification.", status.HTTP_403_FORBIDDEN)

        return Response({"message": "Notification deleted successfully."}, status=status.HTTP_200_OK)
