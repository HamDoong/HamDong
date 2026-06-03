from django.urls import path

from apps.expenses.api.views import ExpenseItemView, GroupExpensesView, HealthView

urlpatterns = [
    path("groups/<uuid:group_id>/expenses/", GroupExpensesView.as_view(), name="group_expenses"),
    path("expenses/<uuid:expense_id>/", ExpenseItemView.as_view(), name="expense_item"),
    path("health/", HealthView.as_view(), name="health"),
]
