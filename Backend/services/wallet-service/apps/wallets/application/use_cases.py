
from __future__ import annotations

from apps.wallets.application.wallet_service import WalletService


class GetMyWalletUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user):
        return self.service.get_my_wallet(user.id)


class ListWalletTransactionsUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, filters):
        return self.service.list_transactions(user.id, filters)


class GetWalletTransactionUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, transaction_id):
        return self.service.get_transaction(user.id, transaction_id)


class PaySettlementItemWithWalletUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, item_id, idempotency_key: str):
        return self.service.pay_settlement_item(user.id, item_id, idempotency_key)


class GetWalletSummaryUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user):
        return self.service.get_wallet_summary(user.id)


class CreateWithdrawalUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, payload):
        return self.service.create_withdrawal(
            user.id,
            amount_minor=payload["amount_minor"],
            currency=payload["currency"],
            payment_method_id=payload["payment_method_id"],
            idempotency_key=payload["idempotency_key"],
        )


class ListWithdrawalsUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user):
        return self.service.list_withdrawals(user.id)


class GetWithdrawalUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, withdrawal_id):
        return self.service.get_withdrawal(user.id, withdrawal_id)


class CancelWithdrawalUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, withdrawal_id):
        return self.service.cancel_withdrawal(user.id, withdrawal_id)


class CreatePaymentIntentUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, payload):
        return self.service.create_payment_intent(
            user.id,
            purpose=payload["purpose"],
            amount_minor=payload["amount_minor"],
            currency=payload["currency"],
            provider=payload["provider"],
            idempotency_key=payload["idempotency_key"],
        )


class GetPaymentIntentUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, payment_intent_id):
        return self.service.get_payment_intent(user.id, payment_intent_id)


class HandleGatewayCallbackUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, provider: str, payload: dict, *, method: str = "POST"):
        return self.service.handle_gateway_callback(provider, payload, method=method)


class VerifyPaymentIntentUseCase:
    def __init__(self, service: WalletService | None = None):
        self.service = service or WalletService()

    def execute(self, user, provider: str, payload: dict):
        return self.service.verify_payment_intent(
            user.id,
            provider=provider,
            payment_intent_id=payload["payment_intent_id"],
            provider_reference=payload.get("provider_reference"),
        )
