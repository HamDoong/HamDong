from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.api.serializers import (
    DashboardActionItemListResponseSerializer,
    DashboardActionItemQuerySerializer,
    DashboardActivityListResponseSerializer,
    DashboardActivityQuerySerializer,
    DashboardSummaryQuerySerializer,
    DashboardSummaryResponseSerializer,
    ErrorResponseSerializer,
)
from apps.dashboard.application.use_cases import (
    GetDashboardSummaryUseCase,
    ListDashboardActionItemsUseCase,
    ListDashboardActivityFeedUseCase,
)
from apps.dashboard.infrastructure.jwt_authentication import JWTAuthentication


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


class AuthenticatedDashboardAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class DashboardSummaryView(AuthenticatedDashboardAPIView):
    @extend_schema(
        tags=["Dashboard"],
        summary="Get dashboard summary",
        parameters=[
            OpenApiParameter(name="currency", required=False, type=str),
        ],
        responses={200: DashboardSummaryResponseSerializer, 401: ErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = DashboardSummaryQuerySerializer(
            data={key: request.query_params.get(key) for key in ("currency",) if key in request.query_params}
        )
        serializer.is_valid(raise_exception=True)
        payload = GetDashboardSummaryUseCase().execute(
            request.auth,
            currency=serializer.validated_data.get("currency"),
        )
        return Response(payload, status=status.HTTP_200_OK)


class DashboardActionItemsView(AuthenticatedDashboardAPIView):
    @extend_schema(
        tags=["Dashboard"],
        summary="List dashboard action items",
        parameters=[
            OpenApiParameter(name="type", required=False, type=str),
            OpenApiParameter(name="priority", required=False, type=str),
            OpenApiParameter(name="group_id", required=False, type=str),
            OpenApiParameter(name="cursor", required=False, type=str),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses={200: DashboardActionItemListResponseSerializer, 401: ErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = DashboardActionItemQuerySerializer(
            data={
                key: request.query_params.get(key)
                for key in ("type", "priority", "group_id", "cursor", "page_size")
                if key in request.query_params
            }
        )
        serializer.is_valid(raise_exception=True)
        try:
            results, next_cursor = ListDashboardActionItemsUseCase().execute(
                request.auth,
                filters=serializer.validated_data,
            )
        except ValueError:
            raise serializers.ValidationError({"cursor": ["INVALID_CURSOR"]})
        return Response({"results": results, "next_cursor": next_cursor}, status=status.HTTP_200_OK)


class DashboardActivityFeedView(AuthenticatedDashboardAPIView):
    @extend_schema(
        tags=["Dashboard"],
        summary="List dashboard activity feed",
        parameters=[
            OpenApiParameter(name="group_id", required=False, type=str),
            OpenApiParameter(name="type", required=False, type=str),
            OpenApiParameter(name="from", required=False, type=str, description="YYYY-MM-DD"),
            OpenApiParameter(name="to", required=False, type=str, description="YYYY-MM-DD"),
            OpenApiParameter(name="cursor", required=False, type=str),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses={200: DashboardActivityListResponseSerializer, 401: ErrorResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        serializer = DashboardActivityQuerySerializer(
            data={
                ("from_" if key == "from" else key): request.query_params.get(key)
                for key in ("group_id", "type", "from", "to", "cursor", "page_size")
                if key in request.query_params
            }
        )
        serializer.is_valid(raise_exception=True)
        try:
            results, next_cursor = ListDashboardActivityFeedUseCase().execute(
                request.user.sub,
                filters=serializer.validated_data,
            )
        except ValueError:
            raise serializers.ValidationError({"cursor": ["INVALID_CURSOR"]})
        return Response({"results": results, "next_cursor": next_cursor}, status=status.HTTP_200_OK)
