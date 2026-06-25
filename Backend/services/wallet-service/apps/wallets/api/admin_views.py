
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

from apps.wallets.api.admin_serializers import (
    AdminPaymentItemSerializer,
    AdminPaymentListQuerySerializer,
    AdminWalletTransactionItemSerializer,
    AdminWalletTransactionListQuerySerializer,
)
from apps.wallets.domain.models import PaymentIntent, WalletTransaction
from apps.wallets.infrastructure.jwt_authentication import JWTAuthentication


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
        responses={200: inline_serializer(name="WalletAdminSystemHealthResponse", fields={"services": serializers.ListField(), "generated_at": serializers.DateTimeField()})},
    )
    def get(self, request, *args, **kwargs):
        return Response({"services": [{"name": settings.SERVICE_NAME, "status": "ok"}], "generated_at": timezone.now()})


class _BaseAdminListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]
    model = None
    query_serializer_class = None

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

    def _apply_common_filters(self, qs, filters):
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


class AdminWalletTransactionListView(_BaseAdminListView):
    model = WalletTransaction
    query_serializer_class = AdminWalletTransactionListQuerySerializer

    @extend_schema(
        tags=["Admin"],
        summary="List wallet transactions",
        parameters=[OpenApiParameter(name, str, OpenApiParameter.QUERY) for name in ["user_id", "type", "status", "direction", "currency", "from", "to", "cursor", "page_size"]],
        responses={200: inline_serializer(name="WalletAdminTransactionListResponse", fields={"results": AdminWalletTransactionItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _queryset(self, filters):
        qs = WalletTransaction.objects.select_related("wallet").all().order_by("-created_at", "-id")
        if filters.get("user_id"):
            qs = qs.filter(wallet__user_id=filters["user_id"])
        if filters.get("type"):
            qs = qs.filter(type=filters["type"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("direction"):
            qs = qs.filter(direction=filters["direction"])
        if filters.get("currency"):
            qs = qs.filter(currency=filters["currency"])
        return self._apply_common_filters(qs, filters)

    def _serialize_row(self, row):
        return {
            "id": row.id,
            "wallet_id": row.wallet_id,
            "user_id": row.wallet.user_id,
            "type": row.type,
            "status": row.status,
            "direction": row.direction,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "reference_type": row.reference_type,
            "reference_id": row.reference_id,
            "created_at": row.created_at,
            "completed_at": row.completed_at,
        }


class AdminPaymentListView(_BaseAdminListView):
    model = PaymentIntent
    query_serializer_class = AdminPaymentListQuerySerializer

    @extend_schema(
        tags=["Admin"],
        summary="List payments",
        parameters=[OpenApiParameter(name, str, OpenApiParameter.QUERY) for name in ["user_id", "provider", "status", "purpose", "currency", "from", "to", "cursor", "page_size"]],
        responses={200: inline_serializer(name="WalletAdminPaymentListResponse", fields={"results": AdminPaymentItemSerializer(many=True), "next_cursor": serializers.CharField(allow_null=True, required=False)})},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def _queryset(self, filters):
        qs = PaymentIntent.objects.select_related("wallet").all().order_by("-created_at", "-id")
        if filters.get("user_id"):
            qs = qs.filter(wallet__user_id=filters["user_id"])
        if filters.get("provider"):
            qs = qs.filter(provider=filters["provider"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("purpose"):
            qs = qs.filter(purpose=filters["purpose"])
        if filters.get("currency"):
            qs = qs.filter(currency=filters["currency"])
        return self._apply_common_filters(qs, filters)

    def _serialize_row(self, row):
        return {
            "id": row.id,
            "user_id": row.wallet.user_id,
            "provider": row.provider,
            "purpose": row.purpose,
            "status": row.status,
            "amount_minor": row.amount_minor,
            "currency": row.currency,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
