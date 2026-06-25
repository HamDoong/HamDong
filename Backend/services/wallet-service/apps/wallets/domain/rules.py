
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalletServiceError(Exception):
    message: str
    code: str = "WALLET_ERROR"
    status_code: int = 400

    def __str__(self) -> str:
        return self.message


class AuthenticationRequiredError(WalletServiceError):
    def __init__(self, message: str = "Authentication credentials were not provided."):
        super().__init__(message, code="AUTH_REQUIRED", status_code=401)


class WalletNotFoundError(WalletServiceError):
    def __init__(self, message: str = "Wallet not found."):
        super().__init__(message, code="WALLET_NOT_FOUND", status_code=404)


class WalletInactiveError(WalletServiceError):
    def __init__(self, message: str = "Wallet is not active."):
        super().__init__(message, code="WALLET_INACTIVE", status_code=409)


class InvalidWalletCursorError(WalletServiceError):
    def __init__(self, message: str = "Invalid cursor."):
        super().__init__(message, code="INVALID_CURSOR", status_code=400)


class SettlementItemNotFoundError(WalletServiceError):
    def __init__(self, message: str = "Settlement plan item not found."):
        super().__init__(message, code="SETTLEMENT_ITEM_NOT_FOUND", status_code=404)


class SettlementItemNotPayableError(WalletServiceError):
    def __init__(self, message: str = "Settlement plan item is not payable."):
        super().__init__(message, code="SETTLEMENT_ITEM_NOT_PAYABLE", status_code=409)


class SettlementItemForbiddenError(WalletServiceError):
    def __init__(self, message: str = "You are not allowed to pay this settlement item."):
        super().__init__(message, code="SETTLEMENT_ITEM_FORBIDDEN", status_code=403)


class IdempotencyKeyRequiredError(WalletServiceError):
    def __init__(self, message: str = "idempotency_key is required."):
        super().__init__(message, code="IDEMPOTENCY_KEY_REQUIRED", status_code=400)


class IdempotencyConflictError(WalletServiceError):
    def __init__(self, message: str = "The idempotency key was already used for another operation."):
        super().__init__(message, code="IDEMPOTENCY_CONFLICT", status_code=409)


class InsufficientBalanceError(WalletServiceError):
    def __init__(self, message: str = "Insufficient available balance."):
        super().__init__(message, code="INSUFFICIENT_BALANCE", status_code=409)


class InvalidCurrencyError(WalletServiceError):
    def __init__(self, message: str = "Unsupported currency."):
        super().__init__(message, code="INVALID_CURRENCY", status_code=400)


class InvalidAmountError(WalletServiceError):
    def __init__(self, message: str = "Amount must be greater than zero."):
        super().__init__(message, code="INVALID_AMOUNT", status_code=400)


class PaymentMethodNotFoundError(WalletServiceError):
    def __init__(self, message: str = "Payment method not found or inactive."):
        super().__init__(message, code="PAYMENT_METHOD_NOT_FOUND", status_code=400)


class WithdrawalNotFoundError(WalletServiceError):
    def __init__(self, message: str = "Withdrawal not found."):
        super().__init__(message, code="WITHDRAWAL_NOT_FOUND", status_code=404)


class WithdrawalStateError(WalletServiceError):
    def __init__(self, message: str = "Withdrawal cannot transition to the requested state."):
        super().__init__(message, code="WITHDRAWAL_STATE_ERROR", status_code=409)


class InvalidProviderError(WalletServiceError):
    def __init__(self, message: str = "Unsupported payment provider."):
        super().__init__(message, code="INVALID_PROVIDER", status_code=400)


class PaymentIntentNotFoundError(WalletServiceError):
    def __init__(self, message: str = "Payment intent not found."):
        super().__init__(message, code="PAYMENT_INTENT_NOT_FOUND", status_code=404)


class PaymentIntentForbiddenError(WalletServiceError):
    def __init__(self, message: str = "You are not allowed to access this payment intent."):
        super().__init__(message, code="PAYMENT_INTENT_FORBIDDEN", status_code=403)


class PaymentIntentExpiredError(WalletServiceError):
    def __init__(self, message: str = "Payment intent has expired."):
        super().__init__(message, code="PAYMENT_INTENT_EXPIRED", status_code=409)


class PaymentIntentStateError(WalletServiceError):
    def __init__(self, message: str = "Payment intent cannot transition to the requested state."):
        super().__init__(message, code="PAYMENT_INTENT_STATE_ERROR", status_code=409)


class PaymentVerificationFailedError(WalletServiceError):
    def __init__(self, message: str = "Payment verification failed."):
        super().__init__(message, code="PAYMENT_VERIFY_FAILED", status_code=409)


class PaymentVerificationRetryableError(WalletServiceError):
    def __init__(self, message: str = "Payment verification should be retried."):
        super().__init__(message, code="PAYMENT_VERIFY_RETRYABLE", status_code=409)


class ProviderReferenceConflictError(WalletServiceError):
    def __init__(self, message: str = "Provider reference is already linked to another payment intent."):
        super().__init__(message, code="PROVIDER_REFERENCE_CONFLICT", status_code=409)


class UnsupportedPaymentPurposeError(WalletServiceError):
    def __init__(self, message: str = "Unsupported payment purpose."):
        super().__init__(message, code="UNSUPPORTED_PAYMENT_PURPOSE", status_code=400)


def ensure_positive_amount(amount_minor: int) -> int:
    if int(amount_minor) <= 0:
        raise InvalidAmountError()
    return int(amount_minor)


def ensure_irr_currency(currency: str) -> str:
    if str(currency) != "IRR":
        raise InvalidCurrencyError("Only IRR currency is supported in this phase.")
    return "IRR"
