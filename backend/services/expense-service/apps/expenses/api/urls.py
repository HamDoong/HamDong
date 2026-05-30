from django.urls import path

from apps.expenses.api.views import CreateExpenseView, HealthView
from apps.expenses.api.list_views import ListExpensesView, ExpenseDetailView
from apps.expenses.api.update_views import UpdateExpenseView, DeleteExpenseView

urlpatterns = [
    path("groups/<uuid:group_id>/expenses/", CreateExpenseView.as_view(), name="create_expense"),
    path("groups/<uuid:group_id>/expenses/list/", ListExpensesView.as_view(), name="list_expenses"),
    path("expenses/<uuid:expense_id>/", ExpenseDetailView.as_view(), name="expense_detail"),
    path("expenses/<uuid:expense_id>/update/", UpdateExpenseView.as_view(), name="update_expense"),
    path("expenses/<uuid:expense_id>/delete/", DeleteExpenseView.as_view(), name="delete_expense"),
    path("health/", HealthView.as_view(), name="health"),
]
