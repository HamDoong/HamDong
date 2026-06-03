"""Backward-compatible imports for expense list/detail views."""

from apps.expenses.api.views import ExpenseDetailView, GroupExpensesView


class ListExpensesView(GroupExpensesView):
    """Alias kept for older imports."""
