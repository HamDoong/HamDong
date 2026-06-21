from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.serializers import (
    NotificationCreateSerializer,
    NotificationListQuerySerializer,
    NotificationMessageSerializer,
    NotificationReadSerializer,
    NotificationsReadAllSerializer,
    NotificationUpdateSerializer,
    TestEmailRequestSerializer,
    TestEmailResponseSerializer,
    UnreadCountSerializer,
)
from apps.notifications.application.use_cases import (
    CountUnreadNotificationsUseCase,
    CreateNotificationUseCase,
    DeleteNotificationUseCase,
    GetNotificationDetailUseCase,
    ListInboxNotificationsUseCase,
    ListNotificationMessagesUseCase,
    MarkAllNotificationsReadUseCase,
    MarkNotificationReadUseCase,
    NotificationQuery,
    SendTestEmailUseCase,
    UpdateNotificationUseCase,
)
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication
from apps.notifications.infrastructure.providers.base import EmailProviderError, InvalidEmailProviderError


NotificationListResponseSerializer = inline_serializer(
    name="NotificationListResponseSerializer",
    fields={
        "results": NotificationMessageSerializer(many=True),
        "next_cursor": serializers.CharField(allow_null=True, required=False),
    },
)

NotificationDeleteResponseSerializer = inline_serializer(
    name="NotificationDeleteResponseSerializer",
    fields={
        "message": serializers.CharField(),
    },
)

EmptyRequestSerializer = inline_serializer(
    name="EmptyRequestSerializer",
    fields={},
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
            detail = getattr(exc, "detail", None)
            if isinstance(detail, dict):
                return Response({"error": detail}, status=status.HTTP_401_UNAUTHORIZED)
            return _error_response(
                "NOT_AUTHENTICATED",
                "Authentication credentials were not provided.",
                status.HTTP_401_UNAUTHORIZED,
            )

        if isinstance(exc, PermissionError):
            return _error_response(
                str(exc),
                "You do not have permission to perform this action.",
                status.HTTP_403_FORBIDDEN,
            )

        if isinstance(exc, ValueError):
            error_code = str(exc)

            if error_code == "NOTIFICATION_NOT_EDITABLE":
                return _error_response(
                    error_code,
                    "This notification can no longer be edited.",
                    status.HTTP_409_CONFLICT,
                )
            if error_code == "INVALID_CURSOR":
                return _error_response(
                    error_code,
                    "The provided cursor is invalid.",
                    status.HTTP_400_BAD_REQUEST,
                )

            return _error_response(
                error_code,
                "The requested operation is invalid.",
                status.HTTP_400_BAD_REQUEST,
            )

        if isinstance(exc, ValidationError):
            return Response({"error": {"code": "INVALID_REQUEST", "message": exc.detail}}, status=status.HTTP_400_BAD_REQUEST)

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
    @extend_schema(
        tags=["Notifications"],
        summary="List current-user notifications",
        parameters=[
            OpenApiParameter(name="limit", required=False, type=int, description="Limit-based pagination. Cannot be combined with cursor/page_size."),
            OpenApiParameter(name="cursor", required=False, type=str, description="Opaque cursor for stable newest-first pagination."),
            OpenApiParameter(name="page_size", required=False, type=int, description="Cursor page size. Ignored unless cursor pagination is used."),
            OpenApiParameter(name="is_read", required=False, type=bool),
            OpenApiParameter(name="priority", required=False, type=str, enum=["LOW", "NORMAL", "HIGH", "URGENT"]),
            OpenApiParameter(name="notification_type", required=False, type=str),
        ],
        responses={200: NotificationListResponseSerializer},
    )
    def get(self, request):
        query_serializer = NotificationListQuerySerializer(
            data={key: request.query_params.get(key) for key in ("limit", "cursor", "page_size", "is_read", "priority", "notification_type") if key in request.query_params}
        )
        query_serializer.is_valid(raise_exception=True)
        query = NotificationQuery(**query_serializer.validated_data)
        notifications, next_cursor = ListInboxNotificationsUseCase().execute(request.user, query)
        serializer = NotificationMessageSerializer(notifications, many=True)
        payload = {"results": serializer.data}
        if "cursor" in request.query_params or "page_size" in request.query_params:
            payload["next_cursor"] = next_cursor
        return Response(payload, status=status.HTTP_200_OK)

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
            priority=serializer.validated_data.get("priority"),
        )
        return Response(NotificationMessageSerializer(notification).data, status=status.HTTP_201_CREATED)


class NotificationUnreadCountView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="Count current-user unread notifications", responses={200: UnreadCountSerializer})
    def get(self, request):
        counts = CountUnreadNotificationsUseCase().execute(request.user)
        return Response(UnreadCountSerializer(counts).data, status=status.HTTP_200_OK)


class NotificationReadView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="Mark one current-user notification as read", request=EmptyRequestSerializer, responses={200: NotificationReadSerializer})
    def post(self, request, notification_id):
        notification = MarkNotificationReadUseCase().execute(request.user, notification_id)
        if not notification:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(
            NotificationReadSerializer(
                {
                    "id": notification.id,
                    "is_read": notification.is_read,
                    "read_at": notification.read_at,
                }
            ).data,
            status=status.HTTP_200_OK,
        )


class NotificationReadAllView(AuthenticatedNotificationAPIView):
    @extend_schema(tags=["Notifications"], summary="Mark all current-user notifications as read", request=EmptyRequestSerializer, responses={200: NotificationsReadAllSerializer})
    def post(self, request):
        updated_count, read_at = MarkAllNotificationsReadUseCase().execute(request.user)
        return Response(
            NotificationsReadAllSerializer({"updated_count": updated_count, "read_at": read_at}).data,
            status=status.HTTP_200_OK,
        )


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
            priority=serializer.validated_data.get("priority"),
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
