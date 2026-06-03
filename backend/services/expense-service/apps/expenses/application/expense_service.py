from .use_cases import ExpenseService


def get_service() -> ExpenseService:
    return ExpenseService()
