"""Backward-compatible imports for expense update/delete views."""

from apps.expenses.api.views import ExpenseDetailView


class UpdateExpenseView(ExpenseDetailView):
    """Alias kept for older imports."""


class DeleteExpenseView(ExpenseDetailView):
    """Alias kept for older imports."""
