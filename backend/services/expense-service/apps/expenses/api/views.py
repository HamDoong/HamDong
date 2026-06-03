"""Thin HTTP views for expense endpoints."""

from __future__ import annotations

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.api.serializers import CreateExpenseSerializer, UpdateExpenseSerializer
from apps.expenses.api.serializers_response import serialize_expense
from apps.expenses.application.use_cases import ExpensePermissionError, ExpenseService, ExpenseServiceError
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication


def _error_response(code: str, message: str, http_status: int) -> Response:
    return Response(
        {"error": {"code": code, "message": message}},
        status=http_status,
    )


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


class AuthenticatedExpenseAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


class GroupExpensesView(AuthenticatedExpenseAPIView):
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


class CreateExpenseView(GroupExpensesView):
    """Backward-compatible alias for older imports."""


class ExpenseResourceView(ExpenseDetailView):
    """Backward-compatible alias for older imports."""
