from django.urls import path

from apps.expenses.api.views import ExpenseDetailView, ExpensePaymentOptionsView, GroupExpensesView, HealthView

urlpatterns = [
    path("groups/<uuid:group_id>/expenses/", GroupExpensesView.as_view(), name="group_expenses"),
    path("expenses/<uuid:expense_id>/", ExpenseDetailView.as_view(), name="expense_detail"),
    path("expenses/<uuid:expense_id>/payment-options/", ExpensePaymentOptionsView.as_view(), name="expense_payment_options"),
    path("health/", HealthView.as_view(), name="health"),
]
