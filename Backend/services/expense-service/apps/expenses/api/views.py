"""Thin HTTP views for expense endpoints."""

from __future__ import annotations

from django.conf import settings
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.api.serializers import CreateExpenseSerializer, ExpensePaymentOptionsResponseSerializer, ExpensePaymentOptionsUpdateSerializer, UpdateExpenseSerializer
from apps.expenses.api.serializers_response import ExpenseResponseSerializer, serialize_expense
from apps.expenses.application.use_cases import (
    ExpensePermissionError,
    ExpenseService,
    ExpenseServiceError,
)
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    @extend_schema(
        tags=["Expenses"],
        summary="Health check",
        description="Return the service health payload for the expense service.",
        responses={200: OpenApiResponse(description="Service health response")},
    )
    def get(self, request, *args, **kwargs):
        return Response(
            {
                "service": settings.SERVICE_NAME,
                "status": "ok",
                "version": settings.SERVICE_VERSION,
            }
        )


class AuthenticatedExpenseAPIView(APIView):
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


class GroupExpensesView(AuthenticatedExpenseAPIView):
    @extend_schema(
        tags=["Expenses"],
        summary="List group expenses",
        description="List expenses for a group visible to an authenticated group member.",
        parameters=[
            OpenApiParameter(name="payer_user_id", required=False, type=str),
            OpenApiParameter(name="created_by_user_id", required=False, type=str),
            OpenApiParameter(name="from_date", required=False, type=str),
            OpenApiParameter(name="to_date", required=False, type=str),
            OpenApiParameter(name="page", required=False, type=int),
            OpenApiParameter(name="page_size", required=False, type=int),
        ],
        responses={200: ExpenseResponseSerializer(many=True)},
    )
    def get(self, request, group_id):
        service = ExpenseService()
        filters = {
            key: request.query_params.get(key)
            for key in ("payer_user_id", "created_by_user_id", "from_date", "to_date")
            if request.query_params.get(key)
        }
        try:
            expenses = service.list_expenses(
                group_id,
                request.user,
                filters=filters,
                page=request.query_params.get("page", 1),
                page_size=request.query_params.get("page_size", 50),
            )
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)

        return Response([serialize_expense(expense) for expense in expenses])

    @extend_schema(
        tags=["Expenses"],
        summary="Create expense",
        description="Create a new expense using the amount_minor contract.",
        request=CreateExpenseSerializer,
        responses={
            201: ExpenseResponseSerializer,
            400: OpenApiResponse(description="Validation or contract error"),
            401: OpenApiResponse(description="Authentication required"),
            403: OpenApiResponse(description="Not allowed for this group"),
        },
    )
    def post(self, request, group_id):
        serializer = CreateExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                str(serializer.errors),
                status.HTTP_400_BAD_REQUEST,
            )

        service = ExpenseService()
        try:
            expense = service.create_expense(group_id, request.user, serializer.validated_data)
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_400_BAD_REQUEST)

        return Response(serialize_expense(expense), status=status.HTTP_201_CREATED)


class ExpenseDetailView(AuthenticatedExpenseAPIView):
    @extend_schema(
        tags=["Expenses"],
        summary="Get expense detail",
        description="Return a single expense by id.",
        responses={200: ExpenseResponseSerializer},
    )
    def get(self, request, expense_id):
        service = ExpenseService()
        try:
            expense = service.get_expense(expense_id, request.user)
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status)

        return Response(serialize_expense(expense))

    @extend_schema(
        tags=["Expenses"],
        summary="Update expense",
        description="Update mutable expense fields using the amount_minor contract.",
        request=UpdateExpenseSerializer,
        responses={200: ExpenseResponseSerializer},
    )
    def patch(self, request, expense_id):
        serializer = UpdateExpenseSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return _error_response(
                "INVALID_REQUEST",
                str(serializer.errors),
                status.HTTP_400_BAD_REQUEST,
            )

        service = ExpenseService()
        try:
            expense = service.update_expense(expense_id, request.user, serializer.validated_data)
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status)

        return Response(serialize_expense(expense))

    @extend_schema(
        tags=["Expenses"],
        summary="Delete expense",
        description="Soft delete an expense and return the resulting expense status.",
        responses={200: OpenApiResponse(description="Expense deleted")},
    )
    def delete(self, request, expense_id):
        service = ExpenseService()
        try:
            expense = service.delete_expense(expense_id, request.user)
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status)

        return Response({"id": str(expense.id), "status": expense.status}, status=status.HTTP_200_OK)


class ExpensePaymentOptionsView(AuthenticatedExpenseAPIView):
    @extend_schema(
        tags=["Expenses"],
        summary="Get expense payment options",
        description="Return the selected payment cards for an expense. Full card number is returned only in this authorized payment context.",
        responses={200: ExpensePaymentOptionsResponseSerializer},
    )
    def get(self, request, expense_id):
        service = ExpenseService()
        try:
            payload = service.get_expense_payment_options(expense_id, request.user)
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status)
        return Response(payload)

    @extend_schema(
        tags=["Expenses"],
        summary="Replace expense payment options",
        request=ExpensePaymentOptionsUpdateSerializer,
        responses={200: ExpensePaymentOptionsResponseSerializer},
    )
    def put(self, request, expense_id):
        serializer = ExpensePaymentOptionsUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return _error_response("INVALID_REQUEST", str(serializer.errors), status.HTTP_400_BAD_REQUEST)
        service = ExpenseService()
        try:
            payload = service.replace_expense_payment_options(
                expense_id,
                request.user,
                serializer.validated_data["payment_card_ids"],
            )
        except ExpensePermissionError as exc:
            return _error_response(exc.code, exc.message, status.HTTP_403_FORBIDDEN)
        except ExpenseServiceError as exc:
            http_status = status.HTTP_404_NOT_FOUND if exc.code == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return _error_response(exc.code, exc.message, http_status)
        return Response(payload)


class CreateExpenseView(GroupExpensesView):
    """Backward-compatible alias for older imports."""


class ExpenseResourceView(ExpenseDetailView):
    """Backward-compatible alias for older imports."""
