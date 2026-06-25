
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

from apps.groups.api.admin_serializers import AdminGroupItemSerializer, AdminGroupListQuerySerializer
from apps.groups.infrastructure.jwt_authentication import JWTAuthentication
from apps.groups.domain.models import Group


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
    def encode(obj) -> str:
        raw = f"{obj.created_at.isoformat()}|{obj.id}"
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
        responses={
            200: inline_serializer(
                name="GroupAdminSystemHealthResponse",
                fields={"services": serializers.ListField(), "generated_at": serializers.DateTimeField()},
            )
        },
    )
    def get(self, request, *args, **kwargs):
        return Response({"services": [{"name": settings.SERVICE_NAME, "status": "ok"}], "generated_at": timezone.now()})


class AdminGroupListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="List groups",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("owner_user_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: inline_serializer(
                name="GroupAdminListResponse",
                fields={"results": AdminGroupItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)},
            )
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = AdminGroupListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            qs = self._queryset(serializer.validated_data)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, {"cursor": ["Invalid cursor."]})
        page_size = serializer.validated_data.get("page_size", 20)
        rows = list(qs[: page_size + 1])
        next_cursor = _CursorPaginator.encode(rows[page_size - 1]) if len(rows) > page_size else None
        results = [
            {
                "id": row.id,
                "title": row.display_title,
                "status": row.status,
                "created_by_user_id": row.created_by_user_id,
                "member_count": row.member_count,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows[:page_size]
        ]
        return Response({"results": results, "next_cursor": next_cursor})

    def _queryset(self, filters):
        qs = Group.objects.all().order_by("-created_at", "-id")
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("owner_user_id"):
            qs = qs.filter(created_by_user_id=filters["owner_user_id"])
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
