
from __future__ import annotations

import base64
import uuid
from datetime import datetime, time, timezone as dt_timezone

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.api.admin_serializers import AdminNotificationItemSerializer, AdminNotificationListQuerySerializer
from apps.notifications.domain.models import NotificationMessage
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(code: str, message: str, http_status: int, details=None) -> Response:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "role", None) == "ADMIN")


class _CursorPaginator:
    @staticmethod
    def encode(created_at, object_id) -> str:
        raw = f"{created_at.isoformat()}|{object_id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    @staticmethod
    def decode(value: str):
        try:
            raw = base64.urlsafe_b64decode(str(value).encode("ascii")).decode("utf-8")
            created_at, object_id = raw.split("|", 1)
            return datetime.fromisoformat(created_at), uuid.UUID(object_id)
        except Exception as exc:
            raise ValueError("Invalid cursor.") from exc


class AdminSystemHealthView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="Admin system health",
        responses={200: inline_serializer(name="NotificationAdminSystemHealthResponse", fields={"services": serializers.ListField(), "generated_at": serializers.DateTimeField()})},
    )
    def get(self, request, *args, **kwargs):
        return Response({"services": [{"name": settings.SERVICE_NAME, "status": "ok"}], "generated_at": timezone.now()})


class AdminNotificationListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="List notifications",
        parameters=[OpenApiParameter(name, str, OpenApiParameter.QUERY) for name in ["user_id", "channel", "status", "type", "from", "to", "cursor", "page_size"]],
        responses={200: inline_serializer(name="NotificationAdminListResponse", fields={"results": AdminNotificationItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        serializer = AdminNotificationListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            qs = self._queryset(serializer.validated_data)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, {"cursor": ["Invalid cursor."]})
        page_size = serializer.validated_data.get("page_size", 20)
        rows = list(qs[: page_size + 1])
        next_cursor = _CursorPaginator.encode(rows[page_size - 1].created_at, rows[page_size - 1].id) if len(rows) > page_size else None
        payload = [{"id": row.id, "recipient_user_id": row.recipient_user_id, "channel": row.channel, "message_type": row.message_type, "status": row.status, "created_at": row.created_at, "updated_at": row.updated_at} for row in rows[:page_size]]
        return Response({"results": payload, "next_cursor": next_cursor})

    def _queryset(self, filters):
        qs = NotificationMessage.objects.filter(is_deleted=False).order_by("-created_at", "-id")
        if filters.get("user_id"):
            qs = qs.filter(recipient_user_id=filters["user_id"])
        if filters.get("channel"):
            qs = qs.filter(channel=filters["channel"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("type"):
            qs = qs.filter(message_type=filters["type"])
        if filters.get("from"):
            start = datetime.combine(filters["from"], time.min).replace(tzinfo=dt_timezone.utc)
            qs = qs.filter(created_at__gte=start)
        if filters.get("to"):
            end = datetime.combine(filters["to"], time.max).replace(tzinfo=dt_timezone.utc)
            qs = qs.filter(created_at__lte=end)
        if filters.get("cursor"):
            created_at, object_id = _CursorPaginator.decode(filters["cursor"])
            qs = qs.filter(Q(created_at__lt=created_at) | Q(created_at=created_at, id__lt=object_id))
        return qs
