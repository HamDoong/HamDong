
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

from apps.identity.api.authentication import JWTAuthentication
from apps.identity.api.admin_serializers import (
    AdminBankCardSerializer,
    AdminUserDetailSerializer,
    AdminUserItemSerializer,
    AdminUserListQuerySerializer,
)


def _error_response(code: str, message: str, http_status: int, details=None) -> Response:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(getattr(request.user, "role", None) == "ADMIN")


class AdminSystemHealthView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="Admin system health",
        responses={
            200: inline_serializer(
                name="IdentityAdminSystemHealthResponse",
                fields={
                    "services": serializers.ListField(),
                    "generated_at": serializers.DateTimeField(),
                },
            )
        },
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "services": [{"name": settings.SERVICE_NAME, "status": "ok"}],
                "generated_at": timezone.now(),
            }
        )


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


class AdminUserListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="List users",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("role", str, OpenApiParameter.QUERY),
            OpenApiParameter("email", str, OpenApiParameter.QUERY),
            OpenApiParameter("art_name", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={
            200: inline_serializer(
                name="IdentityAdminUserListResponse",
                fields={
                    "results": AdminUserItemSerializer(many=True),
                    "next_cursor": serializers.CharField(allow_null=True, required=False),
                },
            ),
            400: inline_serializer(name="IdentityAdminUserListError", fields={"error": serializers.DictField()}),
        },
    )
    def get(self, request, *args, **kwargs):
        serializer = AdminUserListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        filters = serializer.validated_data
        try:
            qs = self._queryset(filters)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, {"cursor": ["Invalid cursor."]})
        page_size = filters.get("page_size", 20)
        rows = list(qs[: page_size + 1])
        next_cursor = _CursorPaginator.encode(rows[page_size - 1]) if len(rows) > page_size else None
        payload = [self._item_payload(user) for user in rows[:page_size]]
        return Response({"results": payload, "next_cursor": next_cursor})

    def _queryset(self, filters):
        from apps.identity.domain.models import User

        qs = User.objects.all().order_by("-created_at", "-id")
        status_filter = filters.get("status")
        if status_filter == "ACTIVE":
            qs = qs.filter(is_active=True)
        elif status_filter == "INACTIVE":
            qs = qs.filter(is_active=False)
        if filters.get("role"):
            qs = qs.filter(role=filters["role"])
        if filters.get("email"):
            qs = qs.filter(email__icontains=filters["email"].strip())
        if filters.get("art_name"):
            qs = qs.filter(art_name__icontains=filters["art_name"].strip())
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

    def _item_payload(self, user):
        return {
            "id": user.id,
            "email": user.email,
            "art_name": user.art_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }


class AdminUserDetailView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(tags=["Admin"], summary="Get user detail", responses={200: AdminUserDetailSerializer})
    def get(self, request, user_id, *args, **kwargs):
        from apps.identity.domain.models import User

        user = User.objects.filter(id=user_id).prefetch_related("bank_cards").first()
        if not user:
            return _error_response("USER_NOT_FOUND", "User not found.", status.HTTP_404_NOT_FOUND)
        payload = {
            "id": user.id,
            "email": user.email,
            "art_name": user.art_name,
            "role": user.role,
            "is_active": user.is_active,
            "is_email_verified": user.is_email_verified,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "city": user.city,
            "bio": user.bio,
            "avatar_url": user.avatar_url,
            "last_login_at": user.last_login_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "bank_cards": [
                {
                    "id": card.id,
                    "holder_name": card.holder_name,
                    "bank_name": card.bank_name,
                    "masked_card_number": card.masked_card_number,
                    "card_number_last4": card.card_number_last4,
                    "is_default": card.is_default,
                    "is_active": card.is_active,
                    "created_at": card.created_at,
                    "updated_at": card.updated_at,
                }
                for card in user.bank_cards.all().order_by("-is_default", "-updated_at", "-created_at")
            ],
        }
        return Response(payload)
