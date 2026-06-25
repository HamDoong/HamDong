
from __future__ import annotations

import base64
import uuid
from datetime import datetime, time, timezone as dt_timezone
from itertools import chain

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import permissions, serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.settlements.api.admin_serializers import (
    AdminFailedEventItemSerializer,
    AdminFailedEventListQuerySerializer,
    AdminOutboxItemSerializer,
    AdminOutboxListQuerySerializer,
    AdminSettlementItemSerializer,
    AdminSettlementListQuerySerializer,
)
from apps.settlements.domain.models import InboxMessage, ManualSettlement, OutboxMessage, SettlementPlanItem
from apps.settlements.infrastructure.jwt_authentication import JWTAuthentication


SENSITIVE_KEYS = {"otp", "reset_token", "refresh_token", "password", "card_number", "provider_secret", "private_key", "smtp_password"}


def _error_response(code: str, message: str, http_status: int, details=None) -> Response:
    payload = {"error": {"code": code, "message": message}}
    if details is not None:
        payload["error"]["details"] = details
    return Response(payload, status=http_status)


def _mask_payload(value):
    if isinstance(value, dict):
        masked = {}
        for key, item in value.items():
            lower = str(key).lower()
            if any(secret in lower for secret in SENSITIVE_KEYS):
                masked[key] = "***"
            else:
                masked[key] = _mask_payload(item)
        return masked
    if isinstance(value, list):
        return [_mask_payload(item) for item in value]
    return value


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
        responses={
            200: inline_serializer(
                name="SettlementAdminSystemHealthResponse",
                fields={"services": serializers.ListField(), "generated_at": serializers.DateTimeField()},
            )
        },
    )
    def get(self, request, *args, **kwargs):
        return Response({"services": [{"name": settings.SERVICE_NAME, "status": "ok"}], "generated_at": timezone.now()})


class AdminSettlementListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        tags=["Admin"],
        summary="List settlements",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("group_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("payer_user_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("payee_user_id", str, OpenApiParameter.QUERY),
            OpenApiParameter("currency", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: inline_serializer(name="SettlementAdminListResponse", fields={"results": AdminSettlementItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        serializer = AdminSettlementListQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            items = self._list_items(serializer.validated_data)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, {"cursor": ["Invalid cursor."]})
        page_size = serializer.validated_data.get("page_size", 20)
        page = items[:page_size]
        next_cursor = _CursorPaginator.encode(page[-1]["created_at"], page[-1]["id"]) if len(items) > page_size and page else None
        return Response({"results": page, "next_cursor": next_cursor})

    def _list_items(self, filters):
        items = []
        settlement_qs = ManualSettlement.objects.all()
        plan_qs = SettlementPlanItem.objects.all()
        if filters.get("status"):
            settlement_qs = settlement_qs.filter(status=filters["status"])
            plan_qs = plan_qs.filter(status=filters["status"])
        if filters.get("group_id"):
            settlement_qs = settlement_qs.filter(group_id=filters["group_id"])
            plan_qs = plan_qs.filter(group_id=filters["group_id"])
        if filters.get("payer_user_id"):
            settlement_qs = settlement_qs.filter(payer_user_id=filters["payer_user_id"])
            plan_qs = plan_qs.filter(payer_user_id=filters["payer_user_id"])
        if filters.get("payee_user_id"):
            settlement_qs = settlement_qs.filter(receiver_user_id=filters["payee_user_id"])
            plan_qs = plan_qs.filter(receiver_user_id=filters["payee_user_id"])
        if filters.get("currency"):
            settlement_qs = settlement_qs.filter(currency=filters["currency"])
            plan_qs = plan_qs.filter(currency=filters["currency"])
        if filters.get("from"):
            start = datetime.combine(filters["from"], time.min).replace(tzinfo=dt_timezone.utc)
            settlement_qs = settlement_qs.filter(created_at__gte=start)
            plan_qs = plan_qs.filter(created_at__gte=start)
        if filters.get("to"):
            end = datetime.combine(filters["to"], time.max).replace(tzinfo=dt_timezone.utc)
            settlement_qs = settlement_qs.filter(created_at__lte=end)
            plan_qs = plan_qs.filter(created_at__lte=end)
        for item in plan_qs:
            items.append({
                "id": item.id,
                "source_type": "SETTLEMENT_PLAN_ITEM",
                "group_id": item.group_id,
                "payer_user_id": item.payer_user_id,
                "payee_user_id": item.receiver_user_id,
                "amount_minor": item.amount_minor,
                "currency": item.currency,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
        for item in settlement_qs:
            items.append({
                "id": item.id,
                "source_type": "MANUAL_SETTLEMENT",
                "group_id": item.group_id,
                "payer_user_id": item.payer_user_id,
                "payee_user_id": item.receiver_user_id,
                "amount_minor": item.amount_minor,
                "currency": item.currency,
                "status": item.status,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            })
        items.sort(key=lambda row: (row["created_at"], row["id"]), reverse=True)
        if filters.get("cursor"):
            created_at, object_id = _CursorPaginator.decode(filters["cursor"])
            items = [row for row in items if (row["created_at"] < created_at or (row["created_at"] == created_at and row["id"] < object_id))]
        return items


class _BaseMessageListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]
    model = None
    query_serializer_class = None
    response_item_serializer = None

    def get(self, request, *args, **kwargs):
        serializer = self.query_serializer_class(data=request.query_params)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, serializer.errors)
        try:
            qs = self._queryset(serializer.validated_data)
        except ValueError:
            return _error_response("INVALID_REQUEST", "Invalid query parameters.", status.HTTP_400_BAD_REQUEST, {"cursor": ["Invalid cursor."]})
        page_size = serializer.validated_data.get("page_size", 20)
        rows = list(qs[: page_size + 1])
        next_cursor = _CursorPaginator.encode(rows[page_size - 1].created_at, rows[page_size - 1].id) if len(rows) > page_size else None
        return Response({"results": [self._serialize_row(row) for row in rows[:page_size]], "next_cursor": next_cursor})

    def _queryset(self, filters):
        qs = self.model.objects.all().order_by("-created_at", "-id")
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("event_type"):
            qs = qs.filter(event_type__icontains=filters["event_type"])
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


class AdminOutboxListView(_BaseMessageListView):
    model = OutboxMessage
    query_serializer_class = AdminOutboxListQuerySerializer
    response_item_serializer = AdminOutboxItemSerializer

    @extend_schema(
        tags=["Admin"],
        summary="List outbox messages",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("event_type", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: inline_serializer(name="SettlementAdminOutboxResponse", fields={"results": AdminOutboxItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _serialize_row(self, row):
        return {
            "id": row.id,
            "event_id": row.event_id,
            "event_type": row.event_type,
            "status": row.status,
            "payload": _mask_payload(row.payload or {}),
            "retry_count": row.retry_count,
            "created_at": row.created_at,
            "published_at": row.published_at,
        }


class AdminFailedEventsListView(_BaseMessageListView):
    model = InboxMessage
    query_serializer_class = AdminFailedEventListQuerySerializer
    response_item_serializer = AdminFailedEventItemSerializer

    @extend_schema(
        tags=["Admin"],
        summary="List failed events",
        parameters=[
            OpenApiParameter("status", str, OpenApiParameter.QUERY),
            OpenApiParameter("event_type", str, OpenApiParameter.QUERY),
            OpenApiParameter("from", str, OpenApiParameter.QUERY),
            OpenApiParameter("to", str, OpenApiParameter.QUERY),
            OpenApiParameter("cursor", str, OpenApiParameter.QUERY),
            OpenApiParameter("page_size", int, OpenApiParameter.QUERY),
        ],
        responses={200: inline_serializer(name="SettlementAdminFailedEventsResponse", fields={"results": AdminFailedEventItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _queryset(self, filters):
        if "status" not in filters:
            filters = {**filters, "status": "FAILED"}
        return super()._queryset(filters)

    def _serialize_row(self, row):
        return {
            "id": row.id,
            "event_id": row.event_id,
            "event_type": row.event_type,
            "source_service": row.source_service,
            "routing_key": row.routing_key,
            "status": row.status,
            "error_message": row.error_message,
            "payload": _mask_payload(row.payload or {}),
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
