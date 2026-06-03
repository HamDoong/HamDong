from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.expenses.api.serializers import (
    CreateExpenseSerializer,
    ExpenseResponseSerializer,
    UpdateExpenseSerializer,
)
from apps.expenses.application.use_cases import ExpenseService
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication


def _serialize_expense(expense):
    return ExpenseResponseSerializer(
        {
            "id": expense.id,
            "group_id": expense.group_id,
            "title": expense.title,
            "description": expense.description,
            "payer_user_id": expense.payer_user_id,
            "created_by_user_id": expense.created_by_user_id,
            "currency": expense.currency,
            "base_amount_minor": expense.base_amount_minor,
            "tax_amount_minor": expense.tax_amount_minor,
            "service_fee_amount_minor": expense.service_fee_amount_minor,
            "total_amount_minor": expense.total_amount_minor,
            "split_method": expense.split_method,
            "status": expense.status,
            "expense_date": expense.expense_date,
            "participants": [
                {
                    "user_id": participant.user_id,
                    "phone_number": participant.phone_number,
                    "display_name_snapshot": participant.display_name_snapshot,
                    "base_share_minor": participant.base_share_minor,
                    "tax_share_minor": participant.tax_share_minor,
                    "service_fee_share_minor": participant.service_fee_share_minor,
                    "total_share_minor": participant.total_share_minor,
                    "is_included": participant.is_included,
                }
                for participant in expense.participants.all().order_by("created_at")
            ],
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
        }
    ).data


class GroupExpensesView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id):
        serializer = CreateExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        service = ExpenseService()
        try:
            expense = service.create_expense(group_id, request.user, serializer.validated_data)
        except PermissionError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

        return Response(_serialize_expense(expense), status=status.HTTP_201_CREATED)

    def get(self, request, group_id):
        filters = {
            key: value
            for key, value in {
                "payer_user_id": request.query_params.get("payer_user_id"),
                "created_by_user_id": request.query_params.get("created_by_user_id"),
                "from_date": request.query_params.get("from_date"),
                "to_date": request.query_params.get("to_date"),
            }.items()
            if value
        }
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))

        service = ExpenseService()
        try:
            expenses = service.list_expenses(
                group_id,
                request.user,
                filters=filters,
                page=page,
                page_size=page_size,
            )
        except PermissionError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_400_BAD_REQUEST)

        return Response([_serialize_expense(expense) for expense in expenses], status=status.HTTP_200_OK)


class ExpenseItemView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, expense_id):
        service = ExpenseService()
        try:
            expense = service.get_expense(expense_id, request.user)
        except PermissionError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_expense(expense), status=status.HTTP_200_OK)

    def patch(self, request, expense_id):
        serializer = UpdateExpenseSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        service = ExpenseService()
        try:
            expense = service.update_expense(expense_id, request.user, serializer.validated_data)
        except PermissionError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            response_status = status.HTTP_404_NOT_FOUND if str(exc) == "NOT_FOUND" else status.HTTP_400_BAD_REQUEST
            return Response({"error": {"code": str(exc)}}, status=response_status)

        return Response(_serialize_expense(expense), status=status.HTTP_200_OK)

    def delete(self, request, expense_id):
        service = ExpenseService()
        try:
            service.delete_expense(expense_id, request.user)
        except PermissionError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as exc:
            return Response({"error": {"code": str(exc)}}, status=status.HTTP_404_NOT_FOUND)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ExpenseDetailView(ExpenseItemView):
    pass


class UpdateExpenseView(ExpenseItemView):
    pass


class DeleteExpenseView(ExpenseItemView):
    pass


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
