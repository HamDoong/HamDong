from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.expenses.application.use_cases import ExpenseService
from apps.expenses.api.serializers import CreateExpenseSerializer
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication
from apps.expenses.api.serializers_response import ExpenseResponseSerializer


class CreateExpenseView(APIView):
    authentication_classes = [JWTAuthentication]

    def post(self, request, group_id):
        serializer = CreateExpenseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        svc = ExpenseService()
        try:
            expense = svc.create_expense(group_id, request.user, serializer.validated_data)
        except PermissionError:
            return Response({"error": {"code": "NOT_GROUP_MEMBER", "message": "You are not an active member of this group."}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"error": {"code": str(e), "message": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

        # return full expense representation
        expense = ExpenseService().get_expense(expense.id, request.user)
        resp = ExpenseResponseSerializer({
            "id": expense.id,
            "group_id": expense.group_id,
            "created_by_user_id": expense.created_by_user_id,
            "payer_user_id": expense.payer_user_id,
            "title": expense.title,
            "description": expense.description,
            "currency": expense.currency,
            "base_amount_minor": expense.base_amount_minor,
            "tax_amount_minor": expense.tax_amount_minor,
            "service_fee_amount_minor": expense.service_fee_amount_minor,
            "total_amount_minor": expense.total_amount_minor,
            "split_method": expense.split_method,
            "status": expense.status,
            "expense_date": expense.expense_date,
            "created_at": expense.created_at,
            "updated_at": expense.updated_at,
            "participants": [
                {
                    "user_id": p.user_id,
                    "phone_number": p.phone_number,
                    "display_name_snapshot": p.display_name_snapshot,
                    "base_share_minor": p.base_share_minor,
                    "tax_share_minor": p.tax_share_minor,
                    "service_fee_share_minor": p.service_fee_share_minor,
                    "total_share_minor": p.total_share_minor,
                }
                for p in expense.participants.all()
            ],
        })
        return Response(resp.data, status=status.HTTP_201_CREATED)
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView


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
