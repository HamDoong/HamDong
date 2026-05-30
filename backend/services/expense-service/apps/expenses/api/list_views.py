from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.expenses.application.use_cases import ExpenseService
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication
from apps.expenses.api.serializers_response import ExpenseResponseSerializer


class ListExpensesView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, group_id):
        svc = ExpenseService()
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 50))
        filters = {}
        if request.query_params.get("payer_user_id"):
            filters["payer_user_id"] = request.query_params.get("payer_user_id")
        if request.query_params.get("created_by_user_id"):
            filters["created_by_user_id"] = request.query_params.get("created_by_user_id")
        if request.query_params.get("from_date"):
            filters["from_date"] = request.query_params.get("from_date")
        if request.query_params.get("to_date"):
            filters["to_date"] = request.query_params.get("to_date")

        try:
            expenses = svc.list_expenses(group_id, request.user, filters=filters, page=page, page_size=page_size)
        except PermissionError:
            return Response({"error": {"code": "NOT_GROUP_MEMBER"}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"error": {"code": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

        data = []
        for expense in expenses:
            data.append(ExpenseResponseSerializer({
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
            }).data)

        return Response(data)


class ExpenseDetailView(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request, expense_id):
        svc = ExpenseService()
        try:
            expense = svc.get_expense(expense_id, request.user)
        except PermissionError:
            return Response({"error": {"code": "NOT_GROUP_MEMBER"}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError:
            return Response({"error": {"code": "NOT_FOUND"}}, status=status.HTTP_404_NOT_FOUND)

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

        return Response(resp.data)
