from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.expenses.application.use_cases import ExpenseService
from apps.expenses.infrastructure.jwt_authentication import JWTAuthentication


class UpdateExpenseView(APIView):
    authentication_classes = [JWTAuthentication]

    def patch(self, request, expense_id):
        svc = ExpenseService()
        try:
            expense = svc.update_expense(expense_id, request.user, request.data)
        except PermissionError:
            return Response({"error": {"code": "NOT_ALLOWED"}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            return Response({"error": {"code": str(e)}}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"id": str(expense.id), "version": expense.version})


class DeleteExpenseView(APIView):
    authentication_classes = [JWTAuthentication]

    def delete(self, request, expense_id):
        svc = ExpenseService()
        try:
            expense = svc.delete_expense(expense_id, request.user)
        except PermissionError:
            return Response({"error": {"code": "NOT_ALLOWED"}}, status=status.HTTP_403_FORBIDDEN)
        except ValueError:
            return Response({"error": {"code": "NOT_FOUND"}}, status=status.HTTP_404_NOT_FOUND)

        return Response({"id": str(expense.id)})
