from django.urls import path

from apps.expenses.api.views import ExpenseDetailView, GroupExpensesView, HealthView

urlpatterns = [
    path("groups/<uuid:group_id>/expenses/", GroupExpensesView.as_view(), name="group_expenses"),
    path("expenses/<uuid:expense_id>/", ExpenseDetailView.as_view(), name="expense_detail"),
    path("health/", HealthView.as_view(), name="health"),
]
