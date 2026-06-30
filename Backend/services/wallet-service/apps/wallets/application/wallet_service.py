
from __future__ import annotations

import base64
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.wallets.domain.models import (
    CurrencyChoices,
    GatewayTransaction,
    GatewayTransactionStatusChoices,
    LedgerEntryTypeChoices,
    PaymentIntent,
    PaymentIntentStatusChoices,
    PaymentProviderChoices,
    PaymentPurposeChoices,
    SettlementItemProjection,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    TopUp,
    TopUpStatusChoices,
    Wallet,
    WalletTransaction,
    WalletTransactionDirectionChoices,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
    Withdrawal,
    WithdrawalStatusChoices,
)
from apps.wallets.domain.rules import (
    IdempotencyConflictError,
    IdempotencyKeyRequiredError,
    InsufficientBalanceError,
    InvalidCurrencyError,
    InvalidProviderError,
    InvalidWalletCursorError,
    PaymentIntentExpiredError,
    PaymentIntentNotFoundError,
    PaymentMethodNotFoundError,
    ProviderReferenceConflictError,
    SettlementItemForbiddenError,
    SettlementItemNotFoundError,
    SettlementItemNotPayableError,
    UnsupportedPaymentPurposeError,
    WalletInactiveError,
    WalletServiceError,
    WithdrawalNotFoundError,
    WithdrawalStateError,
    ensure_irr_currency,
    ensure_positive_amount,
)
from apps.wallets.infrastructure.clients import IdentityBankCardClient
from apps.wallets.infrastructure.event_envelope import build_event_envelope
from apps.wallets.infrastructure.payment_providers import PaymentProviderRequestError, get_provider_adapter
from apps.wallets.infrastructure.repositories import (
    GatewayTransactionRepository,
    LedgerRepository,
    OutboxRepository,
    PaymentCallbackLogRepository,
    PaymentIntentRepository,
    SettlementItemProjectionRepository,
    TopUpRepository,
    UserProjectionRepository,
    WalletRepository,
    WalletTransactionRepository,
    WithdrawalRepository,
)


PAYABLE_ITEM_STATUSES = {
    SettlementItemStatusChoices.PENDING,
    SettlementItemStatusChoices.REJECTED,
}
RECEIVABLE_ITEM_STATUSES = {
    SettlementItemStatusChoices.PENDING,
    SettlementItemStatusChoices.REPORTED,
}
TERMINAL_PAYMENT_STATUSES = {
    PaymentIntentStatusChoices.SUCCEEDED,
    PaymentIntentStatusChoices.FAILED,
    PaymentIntentStatusChoices.EXPIRED,
    PaymentIntentStatusChoices.CANCELLED,
}


class WalletService:
    def __init__(self, bank_card_client: IdentityBankCardClient | None = None):
        self.bank_card_client = bank_card_client or IdentityBankCardClient()



    def _json_safe(self, value):
        if isinstance(value, dict):
            return {str(key): self._json_safe(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [self._json_safe(item) for item in value]
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    def _encode_cursor(self, obj) -> str:
        raw = f"{obj.created_at.isoformat()}|{obj.id}"
        return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")

    def _decode_cursor(self, value: str):
        try:
            raw = base64.urlsafe_b64decode(str(value).encode("ascii")).decode("utf-8")
            created_at, object_id = raw.split("|", 1)
            return datetime.fromisoformat(created_at), object_id
        except Exception as exc:
            raise InvalidWalletCursorError() from exc

    def _wallet_payload(self, wallet: Wallet) -> dict[str, Any]:
        wallet = WalletRepository.refresh_balances(wallet)
        return {
            "id": wallet.id,
            "currency": wallet.currency,
            "status": wallet.status,
            "available_balance_minor": wallet.available_balance_minor,
            "reserved_balance_minor": wallet.reserved_balance_minor,
            "total_inflow_minor": wallet.total_inflow_minor,
            "total_outflow_minor": wallet.total_outflow_minor,
            "created_at": wallet.created_at,
            "updated_at": wallet.updated_at,
        }

    def _transaction_payload(self, tx: WalletTransaction) -> dict[str, Any]:
        return {
            "id": tx.id,
            "type": tx.type,
            "status": tx.status,
            "direction": tx.direction,
            "amount_minor": tx.amount_minor,
            "currency": tx.currency,
            "description": tx.description,
            "reference_type": tx.reference_type,
            "reference_id": tx.reference_id,
            "created_at": tx.created_at,
            "completed_at": tx.completed_at,
        }

    def _withdrawal_payload(self, withdrawal: Withdrawal) -> dict[str, Any]:
        return {
            "id": withdrawal.id,
            "amount_minor": withdrawal.amount_minor,
            "currency": withdrawal.currency,
            "payment_method_id": withdrawal.payment_method_id,
            "payment_method_masked": withdrawal.payment_method_masked,
            "status": withdrawal.status,
            "created_at": withdrawal.created_at,
            "updated_at": withdrawal.updated_at,
            "completed_at": withdrawal.completed_at,
            "cancelled_at": withdrawal.cancelled_at,
            "failed_at": withdrawal.failed_at,
        }

    def _payment_intent_payload(self, intent: PaymentIntent) -> dict[str, Any]:
        top_up = getattr(intent, "top_up", None)
        gateway_transaction = getattr(intent, "gateway_transaction", None)
        return {
            "payment_intent_id": intent.id,
            "purpose": intent.purpose,
            "amount_minor": intent.amount_minor,
            "currency": intent.currency,
            "provider": intent.provider,
            "status": intent.status,
            "payment_url": intent.payment_url,
            "expires_at": intent.expires_at,
            "provider_reference": intent.provider_reference,
            "created_at": intent.created_at,
            "updated_at": intent.updated_at,
            "verified_at": intent.verified_at,
            "top_up_id": top_up.id if top_up else None,
            "wallet_transaction_id": top_up.wallet_transaction_id if top_up and top_up.wallet_transaction_id else None,
            "failure_reason": intent.failure_reason,
            "provider_status": gateway_transaction.provider_status if gateway_transaction else None,
        }

    def _payment_verify_payload(self, intent: PaymentIntent) -> dict[str, Any]:
        top_up = getattr(intent, "top_up", None)
        wallet = intent.wallet
        wallet = WalletRepository.refresh_balances(wallet)
        return {
            "payment_intent_id": intent.id,
            "top_up_id": top_up.id if top_up else None,
            "wallet_transaction_id": top_up.wallet_transaction_id if top_up and top_up.wallet_transaction_id else None,
            "status": intent.status,
            "amount_minor": intent.amount_minor,
            "currency": intent.currency,
            "provider": intent.provider,
            "provider_reference": intent.provider_reference,
            "verified_at": intent.verified_at,
            "wallet_balance_minor": wallet.available_balance_minor,
            "failure_reason": intent.failure_reason,
        }

    def _settlement_summary_item(self, item: SettlementItemProjection, *, counterparty_user_id):
        counterparty = UserProjectionRepository.get(counterparty_user_id)
        return {
            "settlement_plan_item_id": item.item_id,
            "plan_id": item.plan_id,
            "group_id": item.group_id,
            "counterparty": {
                "user_id": counterparty_user_id,
                "art_name": getattr(counterparty, "art_name", None),
            },
            "amount_minor": item.amount_minor,
            "currency": item.currency,
            "status": item.item_status,
            "updated_at": item.updated_at,
        }

    def get_or_create_wallet(self, requester_user_id, currency: str = CurrencyChoices.IRR):
        wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=currency)
        return WalletRepository.refresh_balances(wallet)

    def get_my_wallet(self, requester_user_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        return self._wallet_payload(wallet)

    def list_transactions(self, requester_user_id, filters: dict[str, Any] | None = None):
        wallet = self.get_or_create_wallet(requester_user_id)
        filters = filters or {}
        qs = WalletTransactionRepository.list_for_wallet(wallet, filters=filters)
        if filters.get("cursor"):
            cursor_created_at, cursor_id = self._decode_cursor(filters["cursor"])
            qs = qs.filter(Q(created_at__lt=cursor_created_at) | Q(created_at=cursor_created_at, id__lt=cursor_id)).order_by("-created_at", "-id")
        page_size = min(int(filters.get("page_size") or 20), 100)
        rows = list(qs[: page_size + 1])
        next_cursor = None
        if len(rows) > page_size:
            next_cursor = self._encode_cursor(rows[page_size - 1])
            rows = rows[:page_size]
        return [self._transaction_payload(row) for row in rows], next_cursor

    def get_transaction(self, requester_user_id, transaction_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        tx = WalletTransactionRepository.get_for_wallet(wallet, transaction_id)
        if not tx:
            raise WalletServiceError("Wallet transaction not found.", code="WALLET_TRANSACTION_NOT_FOUND", status_code=404)
        return self._transaction_payload(tx)

    def pay_settlement_item(self, requester_user_id, item_id, idempotency_key: str):
        if not idempotency_key:
            raise IdempotencyKeyRequiredError()
        now = timezone.now()
        with transaction.atomic():
            payer_wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, for_update=True)
            if payer_wallet.status != "ACTIVE":
                raise WalletInactiveError()
            existing = WalletTransactionRepository.get_by_wallet_and_idempotency(payer_wallet, idempotency_key)
            if existing:
                if str(existing.reference_id) != str(item_id):
                    raise IdempotencyConflictError()
                return {
                    "transaction_id": existing.id,
                    "settlement_plan_item_id": item_id,
                    "status": existing.status,
                    "amount_minor": existing.amount_minor,
                    "currency": existing.currency,
                    "paid_at": existing.completed_at,
                }

            item = SettlementItemProjectionRepository.get_for_update(item_id)
            if not item:
                raise SettlementItemNotFoundError()
            if str(item.payer_user_id) != str(requester_user_id):
                raise SettlementItemForbiddenError()
            if str(item.payee_user_id) == str(requester_user_id):
                raise SettlementItemForbiddenError("Payee cannot pay instead of payer.")
            if item.plan_status != SettlementPlanStatusChoices.ACTIVE:
                raise SettlementItemNotPayableError("Settlement plan is not active.")
            if item.item_status not in PAYABLE_ITEM_STATUSES:
                raise SettlementItemNotPayableError()
            if item.wallet_payment_transaction_id:
                prior = payer_wallet.transactions.filter(id=item.wallet_payment_transaction_id).first()
                if prior:
                    return {
                        "transaction_id": prior.id,
                        "settlement_plan_item_id": item.item_id,
                        "status": prior.status,
                        "amount_minor": prior.amount_minor,
                        "currency": prior.currency,
                        "paid_at": prior.completed_at,
                    }
                raise SettlementItemNotPayableError("Settlement item has already been paid.")

            payee_wallet, _ = WalletRepository.get_or_create_for_user(item.payee_user_id, currency=item.currency, for_update=True)
            if payee_wallet.status != "ACTIVE":
                raise WalletInactiveError("Payee wallet is not active.")

            payer_wallet = WalletRepository.refresh_balances(payer_wallet)
            payee_wallet = WalletRepository.refresh_balances(payee_wallet)

            if payer_wallet.currency != item.currency or payee_wallet.currency != item.currency:
                raise InvalidCurrencyError("Wallet currency does not match settlement currency.")
            if payer_wallet.available_balance_minor < item.amount_minor:
                raise InsufficientBalanceError()

            operation_id = uuid4()
            payer_tx = WalletTransactionRepository.create(
                wallet=payer_wallet,
                operation_id=operation_id,
                type=WalletTransactionTypeChoices.SETTLEMENT_PAYMENT,
                status=WalletTransactionStatusChoices.COMPLETED,
                direction=WalletTransactionDirectionChoices.OUT,
                amount_minor=item.amount_minor,
                currency=item.currency,
                description="Wallet settlement payment",
                reference_type="SETTLEMENT_PLAN_ITEM",
                reference_id=item.item_id,
                idempotency_key=idempotency_key,
                completed_at=now,
            )
            payee_tx = WalletTransactionRepository.create(
                wallet=payee_wallet,
                operation_id=operation_id,
                type=WalletTransactionTypeChoices.SETTLEMENT_RECEIVED,
                status=WalletTransactionStatusChoices.COMPLETED,
                direction=WalletTransactionDirectionChoices.IN,
                amount_minor=item.amount_minor,
                currency=item.currency,
                description="Wallet settlement received",
                reference_type="SETTLEMENT_PLAN_ITEM",
                reference_id=item.item_id,
                idempotency_key=f"incoming:{payer_tx.id}",
                completed_at=now,
            )
            LedgerRepository.create_many(
                [
                    {
                        "wallet": payer_wallet,
                        "transaction": payer_tx,
                        "entry_type": LedgerEntryTypeChoices.AVAILABLE_DEBIT,
                        "amount_minor": item.amount_minor,
                        "currency": item.currency,
                    },
                    {
                        "wallet": payee_wallet,
                        "transaction": payee_tx,
                        "entry_type": LedgerEntryTypeChoices.AVAILABLE_CREDIT,
                        "amount_minor": item.amount_minor,
                        "currency": item.currency,
                    },
                ]
            )
            item.wallet_payment_transaction_id = payer_tx.id
            item.wallet_payment_completed_at = now
            item.updated_at = now
            item.save(update_fields=["wallet_payment_transaction_id", "wallet_payment_completed_at", "updated_at"])
            WalletRepository.refresh_balances(payer_wallet)
            WalletRepository.refresh_balances(payee_wallet)

            payload = build_event_envelope(
                "WalletSettlementPaid",
                {
                    "wallet_transaction_id": str(payer_tx.id),
                    "settlement_plan_item_id": str(item.item_id),
                    "payer_user_id": str(item.payer_user_id),
                    "payee_user_id": str(item.payee_user_id),
                    "amount_minor": item.amount_minor,
                    "currency": item.currency,
                    "paid_at": now.isoformat(),
                },
                source_service="wallet-service",
                routing_key="wallet.settlement.paid",
                correlation_id=str(operation_id),
                causation_id=str(operation_id),
            )
            OutboxRepository.create(
                aggregate_type="WalletTransaction",
                aggregate_id=payer_tx.id,
                event_id=payload["event_id"],
                event_type=payload["event_type"],
                event_version=payload["event_version"],
                routing_key=payload["routing_key"],
                exchange=getattr(settings, "WALLET_RABBITMQ_EXCHANGE", "hamdong.wallet"),
                correlation_id=payload["correlation_id"],
                causation_id=payload["causation_id"],
                payload=payload,
                source_service="wallet-service",
            )
            return {
                "transaction_id": payer_tx.id,
                "settlement_plan_item_id": item.item_id,
                "status": payer_tx.status,
                "amount_minor": item.amount_minor,
                "currency": item.currency,
                "paid_at": payer_tx.completed_at,
            }

    def get_wallet_summary(self, requester_user_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        payables = [
            self._settlement_summary_item(item, counterparty_user_id=item.payee_user_id)
            for item in SettlementItemProjectionRepository.list_pending_payables(requester_user_id)[:20]
        ]
        receivables = [
            self._settlement_summary_item(item, counterparty_user_id=item.payer_user_id)
            for item in SettlementItemProjectionRepository.list_pending_receivables(requester_user_id)[:20]
        ]
        recent_transactions = [
            self._transaction_payload(tx)
            for tx in WalletTransactionRepository.list_for_wallet(wallet)[:5]
        ]
        pending_withdrawals = [
            self._withdrawal_payload(row)
            for row in WithdrawalRepository.pending_for_wallet(wallet)[:10]
        ]
        return {
            "wallet": self._wallet_payload(wallet),
            "pending_receivables": receivables,
            "pending_payables": payables,
            "recent_transactions": recent_transactions,
            "pending_withdrawals": pending_withdrawals,
            "generated_at": timezone.now(),
        }

    def create_withdrawal(self, requester_user_id, *, amount_minor: int, currency: str, payment_method_id, idempotency_key: str):
        if not idempotency_key:
            raise IdempotencyKeyRequiredError()
        amount_minor = ensure_positive_amount(amount_minor)
        currency = ensure_irr_currency(currency)
        cards = self.bank_card_client.resolve_payment_context_cards(requester_user_id, [payment_method_id])
        if not cards:
            raise PaymentMethodNotFoundError()
        card = cards[0]
        if not card.get("is_active", False):
            raise PaymentMethodNotFoundError()
        masked = card.get("masked_card_number")
        with transaction.atomic():
            wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=currency, for_update=True)
            if wallet.status != "ACTIVE":
                raise WalletInactiveError()
            existing = WithdrawalRepository.get_by_wallet_and_idempotency(wallet, idempotency_key)
            if existing:
                return self._withdrawal_payload(existing)
            wallet = WalletRepository.refresh_balances(wallet)
            if wallet.available_balance_minor < amount_minor:
                raise InsufficientBalanceError()
            tx = WalletTransactionRepository.create(
                wallet=wallet,
                type=WalletTransactionTypeChoices.WITHDRAWAL,
                status=WalletTransactionStatusChoices.PENDING,
                direction=WalletTransactionDirectionChoices.OUT,
                amount_minor=amount_minor,
                currency=currency,
                description="Withdrawal request",
                reference_type="WITHDRAWAL",
                reference_id=uuid4(),
                idempotency_key=idempotency_key,
            )
            LedgerRepository.create_many(
                [
                    {
                        "wallet": wallet,
                        "transaction": tx,
                        "entry_type": LedgerEntryTypeChoices.AVAILABLE_DEBIT,
                        "amount_minor": amount_minor,
                        "currency": currency,
                    },
                    {
                        "wallet": wallet,
                        "transaction": tx,
                        "entry_type": LedgerEntryTypeChoices.RESERVED_CREDIT,
                        "amount_minor": amount_minor,
                        "currency": currency,
                    },
                ]
            )
            withdrawal = WithdrawalRepository.create(
                wallet=wallet,
                amount_minor=amount_minor,
                currency=currency,
                payment_method_id=payment_method_id,
                payment_method_masked=masked,
                status=WithdrawalStatusChoices.PENDING,
                idempotency_key=idempotency_key,
                withdrawal_transaction=tx,
            )
            tx.reference_id = withdrawal.id
            tx.save(update_fields=["reference_id", "updated_at"])
            WalletRepository.refresh_balances(wallet)
            return self._withdrawal_payload(withdrawal)

    def list_withdrawals(self, requester_user_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        return [self._withdrawal_payload(row) for row in WithdrawalRepository.list_for_wallet(wallet)]

    def get_withdrawal(self, requester_user_id, withdrawal_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        row = WithdrawalRepository.get_for_wallet(wallet, withdrawal_id)
        if not row:
            raise WithdrawalNotFoundError()
        return self._withdrawal_payload(row)

    def cancel_withdrawal(self, requester_user_id, withdrawal_id):
        with transaction.atomic():
            wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, for_update=True)
            row = WithdrawalRepository.get_for_wallet(wallet, withdrawal_id)
            if not row:
                raise WithdrawalNotFoundError()
            return self._cancel_withdrawal_locked(row, wallet)

    def _cancel_withdrawal_locked(self, row: Withdrawal, wallet: Wallet):
        now = timezone.now()
        if row.status != WithdrawalStatusChoices.PENDING:
            raise WithdrawalStateError("Only pending withdrawals can be cancelled.")
        cancel_tx = WalletTransactionRepository.create(
            wallet=wallet,
            type=WalletTransactionTypeChoices.ADJUSTMENT,
            status=WalletTransactionStatusChoices.COMPLETED,
            direction=WalletTransactionDirectionChoices.IN,
            amount_minor=row.amount_minor,
            currency=row.currency,
            description="Withdrawal cancelled",
            reference_type="WITHDRAWAL",
            reference_id=row.id,
            idempotency_key=f"cancel:{row.id}",
            completed_at=now,
        )
        LedgerRepository.create_many(
            [
                {
                    "wallet": wallet,
                    "transaction": cancel_tx,
                    "entry_type": LedgerEntryTypeChoices.AVAILABLE_CREDIT,
                    "amount_minor": row.amount_minor,
                    "currency": row.currency,
                },
                {
                    "wallet": wallet,
                    "transaction": cancel_tx,
                    "entry_type": LedgerEntryTypeChoices.RESERVED_DEBIT,
                    "amount_minor": row.amount_minor,
                    "currency": row.currency,
                },
            ]
        )
        row.status = WithdrawalStatusChoices.CANCELLED
        row.cancelled_at = now
        row.cancel_transaction = cancel_tx
        row.save(update_fields=["status", "cancelled_at", "cancel_transaction", "updated_at"])
        tx = row.withdrawal_transaction
        tx.status = WalletTransactionStatusChoices.CANCELLED
        tx.cancelled_at = now
        tx.save(update_fields=["status", "cancelled_at", "updated_at"])
        WalletRepository.refresh_balances(wallet)
        return self._withdrawal_payload(row)

    def complete_withdrawal(self, withdrawal_id):
        with transaction.atomic():
            row = Withdrawal.objects.select_for_update().select_related("wallet", "withdrawal_transaction").filter(id=withdrawal_id).first()
            if not row:
                raise WithdrawalNotFoundError()
            if row.status not in {WithdrawalStatusChoices.PENDING, WithdrawalStatusChoices.PROCESSING}:
                raise WithdrawalStateError("Withdrawal cannot be completed.")
            wallet = Wallet.objects.select_for_update().get(pk=row.wallet_id)
            now = timezone.now()
            LedgerRepository.create_many(
                [
                    {
                        "wallet": wallet,
                        "transaction": row.withdrawal_transaction,
                        "entry_type": LedgerEntryTypeChoices.RESERVED_DEBIT,
                        "amount_minor": row.amount_minor,
                        "currency": row.currency,
                    },
                ]
            )
            row.status = WithdrawalStatusChoices.COMPLETED
            row.completed_at = now
            row.save(update_fields=["status", "completed_at", "updated_at"])
            tx = row.withdrawal_transaction
            tx.status = WalletTransactionStatusChoices.COMPLETED
            tx.completed_at = now
            tx.save(update_fields=["status", "completed_at", "updated_at"])
            WalletRepository.refresh_balances(wallet)
            return self._withdrawal_payload(row)

    def fail_withdrawal(self, withdrawal_id, reason: str = "Provider failed."):
        with transaction.atomic():
            row = Withdrawal.objects.select_for_update().select_related("wallet", "withdrawal_transaction").filter(id=withdrawal_id).first()
            if not row:
                raise WithdrawalNotFoundError()
            if row.status not in {WithdrawalStatusChoices.PENDING, WithdrawalStatusChoices.PROCESSING}:
                raise WithdrawalStateError("Withdrawal cannot fail in its current state.")
            wallet = Wallet.objects.select_for_update().get(pk=row.wallet_id)
            now = timezone.now()
            release_tx = WalletTransactionRepository.create(
                wallet=wallet,
                type=WalletTransactionTypeChoices.ADJUSTMENT,
                status=WalletTransactionStatusChoices.COMPLETED,
                direction=WalletTransactionDirectionChoices.IN,
                amount_minor=row.amount_minor,
                currency=row.currency,
                description="Withdrawal failed",
                reference_type="WITHDRAWAL",
                reference_id=row.id,
                idempotency_key=f"failed:{row.id}",
                completed_at=now,
            )
            LedgerRepository.create_many(
                [
                    {
                        "wallet": wallet,
                        "transaction": release_tx,
                        "entry_type": LedgerEntryTypeChoices.AVAILABLE_CREDIT,
                        "amount_minor": row.amount_minor,
                        "currency": row.currency,
                    },
                    {
                        "wallet": wallet,
                        "transaction": release_tx,
                        "entry_type": LedgerEntryTypeChoices.RESERVED_DEBIT,
                        "amount_minor": row.amount_minor,
                        "currency": row.currency,
                    },
                ]
            )
            row.status = WithdrawalStatusChoices.FAILED
            row.failed_at = now
            row.failure_reason = reason
            row.cancel_transaction = release_tx
            row.save(update_fields=["status", "failed_at", "failure_reason", "cancel_transaction", "updated_at"])
            tx = row.withdrawal_transaction
            tx.status = WalletTransactionStatusChoices.FAILED
            tx.failure_reason = reason
            tx.save(update_fields=["status", "failure_reason", "updated_at"])
            WalletRepository.refresh_balances(wallet)
            return self._withdrawal_payload(row)

    def _validate_payment_provider(self, provider: str) -> str:
        normalized = str(provider or "").upper().strip()
        if normalized not in {PaymentProviderChoices.FAKE, PaymentProviderChoices.ZARINPAL}:
            raise InvalidProviderError()
        return normalized

    def _validate_payment_purpose(self, purpose: str) -> str:
        normalized = str(purpose or "").upper().strip()
        if normalized not in {PaymentPurposeChoices.WALLET_TOP_UP, PaymentPurposeChoices.SETTLEMENT_PAYMENT}:
            raise UnsupportedPaymentPurposeError()
        if normalized != PaymentPurposeChoices.WALLET_TOP_UP:
            raise UnsupportedPaymentPurposeError("Only WALLET_TOP_UP is supported in this phase.")
        return normalized

    def _expire_payment_intent_if_needed(self, intent: PaymentIntent):
        if intent.status in TERMINAL_PAYMENT_STATUSES:
            return intent
        if intent.expires_at <= timezone.now():
            PaymentIntentRepository.set_status(
                intent,
                PaymentIntentStatusChoices.EXPIRED,
                failure_reason="Payment intent has expired.",
            )
            top_up = getattr(intent, "top_up", None)
            if top_up and top_up.status not in {TopUpStatusChoices.COMPLETED, TopUpStatusChoices.CANCELLED}:
                TopUpRepository.mark_failed(top_up, gateway_transaction=getattr(intent, "gateway_transaction", None), provider_reference=intent.provider_reference, reason="Payment intent has expired.")
        return intent

    def create_payment_intent(self, requester_user_id, *, purpose: str, amount_minor: int, currency: str, provider: str, idempotency_key: str):
        if not idempotency_key:
            raise IdempotencyKeyRequiredError()
        amount_minor = ensure_positive_amount(amount_minor)
        currency = ensure_irr_currency(currency)
        provider = self._validate_payment_provider(provider)
        purpose = self._validate_payment_purpose(purpose)
        expires_in_minutes = int(getattr(settings, "PAYMENT_INTENT_EXPIRES_IN_MINUTES", 30))
        adapter = get_provider_adapter(provider)

        with transaction.atomic():
            wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=currency, for_update=True)
            if wallet.status != "ACTIVE":
                raise WalletInactiveError()
            existing = PaymentIntentRepository.get_by_wallet_and_idempotency(wallet, idempotency_key)
            if existing:
                self._expire_payment_intent_if_needed(existing)
                existing = PaymentIntentRepository.get_for_wallet(wallet, existing.id)
                return self._payment_intent_payload(existing)

            now = timezone.now()
            intent = PaymentIntentRepository.create(
                wallet=wallet,
                purpose=purpose,
                amount_minor=amount_minor,
                currency=currency,
                provider=provider,
                idempotency_key=idempotency_key,
                status=PaymentIntentStatusChoices.REDIRECT_REQUIRED,
                payment_url="https://fake-gateway/placeholder",
                expires_at=now + timedelta(minutes=expires_in_minutes),
                metadata={},
            )
            if purpose == PaymentPurposeChoices.WALLET_TOP_UP:
                TopUpRepository.create(
                    wallet=wallet,
                    payment_intent=intent,
                    amount_minor=amount_minor,
                    currency=currency,
                    status=TopUpStatusChoices.PENDING,
                    provider=provider,
                    idempotency_key=idempotency_key,
                )

        try:
            request_result = adapter.request_payment(intent)
        except PaymentProviderRequestError as exc:
            with transaction.atomic():
                wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=currency, for_update=True)
                intent = PaymentIntentRepository.get_for_wallet_update(wallet, intent.id)
                top_up = TopUpRepository.get_by_payment_intent(intent)
                safe_payload = self._json_safe(exc.payload or {"provider": provider})
                intent.metadata = {"provider_request": safe_payload}
                intent.provider_reference = exc.provider_reference
                intent.save(update_fields=["metadata", "provider_reference", "updated_at"])
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.FAILED,
                    failure_reason="Payment provider request failed.",
                    provider_reference=exc.provider_reference,
                )
                gateway_tx = None
                if provider == PaymentProviderChoices.ZARINPAL or exc.provider_reference:
                    gateway_tx = GatewayTransactionRepository.get_or_create_for_intent(
                        intent,
                        defaults={"provider": provider, "status": GatewayTransactionStatusChoices.FAILED},
                    )
                    GatewayTransactionRepository.record_request(
                        gateway_tx,
                        status=GatewayTransactionStatusChoices.FAILED,
                        provider_reference=exc.provider_reference,
                        provider_status=exc.provider_status,
                        response_payload=safe_payload,
                    )
                if top_up:
                    TopUpRepository.mark_failed(
                        top_up,
                        gateway_transaction=gateway_tx,
                        provider_reference=exc.provider_reference,
                        reason="Payment provider request failed.",
                    )
            raise WalletServiceError(
                "Payment provider request failed.",
                code="PAYMENT_PROVIDER_REQUEST_FAILED",
                status_code=502 if exc.retryable else 400,
            )

        with transaction.atomic():
            wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=currency, for_update=True)
            intent = PaymentIntentRepository.get_for_wallet_update(wallet, intent.id)
            top_up = TopUpRepository.get_by_payment_intent(intent)

            intent.payment_url = request_result.payment_url
            intent.provider_reference = request_result.provider_reference
            intent.metadata = {"provider_request": self._json_safe(request_result.payload or {})}
            intent.save(update_fields=["payment_url", "provider_reference", "metadata", "updated_at"])

            if top_up and request_result.provider_reference:
                top_up.provider_reference = request_result.provider_reference
                top_up.save(update_fields=["provider_reference", "updated_at"])

            if provider == PaymentProviderChoices.ZARINPAL or request_result.provider_reference:
                gateway_tx = GatewayTransactionRepository.get_or_create_for_intent(
                    intent,
                    defaults={
                        "provider": provider,
                        "status": GatewayTransactionStatusChoices.VERIFYING,
                        "provider_reference": request_result.provider_reference,
                    },
                )
                GatewayTransactionRepository.record_request(
                    gateway_tx,
                    status=GatewayTransactionStatusChoices.VERIFYING,
                    provider_reference=request_result.provider_reference,
                    provider_status=request_result.provider_status,
                    response_payload=self._json_safe(request_result.payload or {}),
                )
            return self._payment_intent_payload(intent)

    def get_payment_intent(self, requester_user_id, payment_intent_id):
        wallet = self.get_or_create_wallet(requester_user_id)
        intent = PaymentIntentRepository.get_for_wallet(wallet, payment_intent_id)
        if not intent:
            raise PaymentIntentNotFoundError()
        self._expire_payment_intent_if_needed(intent)
        intent = PaymentIntentRepository.get_for_wallet(wallet, payment_intent_id)
        return self._payment_intent_payload(intent)

    def _extract_callback_parts(self, payload: dict[str, Any]):
        payment_intent_id = payload.get("payment_intent_id") or payload.get("intent_id")
        provider_reference = (
            payload.get("provider_reference")
            or payload.get("ref")
            or payload.get("reference")
            or payload.get("Authority")
            or payload.get("authority")
        )
        amount_minor = payload.get("amount_minor")
        if amount_minor in (None, ""):
            amount_minor = payload.get("amount")
        currency = payload.get("currency") or CurrencyChoices.IRR
        provider_status = (
            payload.get("provider_status")
            or payload.get("Status")
            or payload.get("status")
            or payload.get("result")
            or "success"
        )
        return payment_intent_id, provider_reference, amount_minor, currency, provider_status

    def handle_gateway_callback(self, provider: str, payload: dict[str, Any], *, method: str = "POST"):
        provider = self._validate_payment_provider(provider)
        payload = self._json_safe(payload)
        payment_intent_id, provider_reference, amount_minor, currency, provider_status = self._extract_callback_parts(payload)
        intent = None
        if payment_intent_id:
            try:
                intent = PaymentIntent.objects.select_related("wallet").filter(id=payment_intent_id).first()
            except Exception:
                intent = None
        PaymentCallbackLogRepository.create(
            provider=provider,
            payment_intent=intent,
            provider_reference=provider_reference,
            method=method,
            payload=payload,
        )
        if not intent:
            return {"message": "Callback received."}

        normalized_provider_status = str(provider_status or "").upper()
        with transaction.atomic():
            intent = PaymentIntent.objects.select_for_update().select_related("wallet").get(pk=intent.pk)
            existing_ref = GatewayTransactionRepository.find_by_provider_reference(provider, str(provider_reference)) if provider_reference else None
            if existing_ref and existing_ref.payment_intent_id != intent.id:
                raise ProviderReferenceConflictError()
            gateway_tx = GatewayTransactionRepository.record_callback(
                intent,
                provider=provider,
                provider_reference=str(provider_reference) if provider_reference else None,
                provider_amount_minor=int(amount_minor) if amount_minor not in (None, "") else None,
                provider_currency=currency,
                provider_status=str(provider_status),
                payload=payload,
                callback_at=timezone.now(),
            )
            top_up = TopUpRepository.get_by_payment_intent(intent)

            if intent.status in {PaymentIntentStatusChoices.SUCCEEDED, PaymentIntentStatusChoices.EXPIRED, PaymentIntentStatusChoices.CANCELLED}:
                return {"message": "Callback received."}

            failure_statuses = {"FAIL", "FAILED", "CANCELLED", "CANCELED"}
            if provider == PaymentProviderChoices.ZARINPAL and normalized_provider_status == "NOK":
                failure_statuses.add("NOK")

            if normalized_provider_status in failure_statuses:
                gateway_tx.status = GatewayTransactionStatusChoices.FAILED
                gateway_tx.save(update_fields=["status", "updated_at"])
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.FAILED,
                    failure_reason="Provider callback reported failed payment.",
                    provider_reference=gateway_tx.provider_reference,
                )
                if top_up and top_up.status != TopUpStatusChoices.COMPLETED:
                    TopUpRepository.mark_failed(
                        top_up,
                        gateway_transaction=gateway_tx,
                        provider_reference=gateway_tx.provider_reference,
                        reason="Provider callback reported failed payment.",
                    )
                return {"message": "Callback received."}

            PaymentIntentRepository.mark_callback_received(
                intent,
                provider_reference=gateway_tx.provider_reference,
                callback_at=gateway_tx.last_callback_at,
            )
            if top_up and top_up.status == TopUpStatusChoices.PENDING:
                TopUpRepository.mark_processing(top_up, gateway_transaction=gateway_tx, provider_reference=gateway_tx.provider_reference)
        return {"message": "Callback received."}

    def _emit_top_up_completed_event(self, *, intent: PaymentIntent, top_up: TopUp, tx: WalletTransaction, completed_at):
        payload = build_event_envelope(
            "WalletTopUpCompleted",
            {
                "payment_intent_id": str(intent.id),
                "top_up_id": str(top_up.id),
                "wallet_transaction_id": str(tx.id),
                "user_id": str(intent.wallet.user_id),
                "amount_minor": intent.amount_minor,
                "currency": intent.currency,
                "provider": intent.provider,
                "provider_reference": intent.provider_reference,
                "completed_at": completed_at.isoformat(),
            },
            source_service="wallet-service",
            routing_key="wallet.topup.completed",
            correlation_id=str(intent.id),
            causation_id=str(intent.id),
        )
        OutboxRepository.create(
            aggregate_type="PaymentIntent",
            aggregate_id=intent.id,
            event_id=payload["event_id"],
            event_type=payload["event_type"],
            event_version=payload["event_version"],
            routing_key=payload["routing_key"],
            exchange=getattr(settings, "WALLET_RABBITMQ_EXCHANGE", "hamdong.wallet"),
            correlation_id=payload["correlation_id"],
            causation_id=payload["causation_id"],
            payload=payload,
            source_service="wallet-service",
        )

    def verify_payment_intent(self, requester_user_id, *, provider: str, payment_intent_id, provider_reference: str | None = None):
        provider = self._validate_payment_provider(provider)
        adapter = get_provider_adapter(provider)

        wallet = self.get_or_create_wallet(requester_user_id, currency=CurrencyChoices.IRR)
        precheck_intent = PaymentIntentRepository.get_for_wallet(wallet, payment_intent_id)
        if not precheck_intent:
            raise PaymentIntentNotFoundError()
        self._expire_payment_intent_if_needed(precheck_intent)
        precheck_intent.refresh_from_db()
        if precheck_intent.status == PaymentIntentStatusChoices.EXPIRED:
            raise PaymentIntentExpiredError()

        with transaction.atomic():
            wallet, _ = WalletRepository.get_or_create_for_user(requester_user_id, currency=CurrencyChoices.IRR, for_update=True)
            intent = PaymentIntentRepository.get_for_wallet_update(wallet, payment_intent_id)
            if not intent:
                raise PaymentIntentNotFoundError()
            if intent.status == PaymentIntentStatusChoices.EXPIRED:
                raise PaymentIntentExpiredError()
            if intent.purpose != PaymentPurposeChoices.WALLET_TOP_UP:
                raise UnsupportedPaymentPurposeError("Only WALLET_TOP_UP is supported in this phase.")

            top_up = TopUpRepository.get_or_create_for_intent(
                intent,
                defaults={
                    "wallet": wallet,
                    "amount_minor": intent.amount_minor,
                    "currency": intent.currency,
                    "status": TopUpStatusChoices.PENDING,
                    "provider": intent.provider,
                    "idempotency_key": intent.idempotency_key,
                },
            )
            if top_up.wallet_transaction_id and intent.status == PaymentIntentStatusChoices.SUCCEEDED:
                return self._payment_verify_payload(intent)

            gateway_tx = GatewayTransactionRepository.lock_for_intent(intent)
            if not gateway_tx:
                gateway_tx = GatewayTransactionRepository.get_or_create_for_intent(
                    intent,
                    defaults={"provider": provider, "status": GatewayTransactionStatusChoices.VERIFYING},
                )
            callback_log = PaymentCallbackLogRepository.last_for_intent(intent)
            callback_payload = dict(gateway_tx.last_callback_payload or {})
            if callback_log and callback_log.payload:
                callback_payload = dict(callback_log.payload)

            verification_reference = provider_reference or intent.provider_reference or gateway_tx.provider_reference
            existing_ref = GatewayTransactionRepository.find_by_provider_reference(provider, str(verification_reference)) if verification_reference else None
            if existing_ref and existing_ref.payment_intent_id != intent.id:
                raise ProviderReferenceConflictError()

            result = adapter.verify(intent, callback_payload=callback_payload, provider_reference=str(verification_reference) if verification_reference else None)
            if result.provider_reference:
                existing_ref = GatewayTransactionRepository.find_by_provider_reference(provider, result.provider_reference)
                if existing_ref and existing_ref.payment_intent_id != intent.id:
                    raise ProviderReferenceConflictError()

            now = timezone.now()
            if result.status == "RETRYABLE":
                GatewayTransactionRepository.record_verification(
                    gateway_tx,
                    status=GatewayTransactionStatusChoices.RETRYABLE,
                    provider_reference=result.provider_reference,
                    provider_amount_minor=result.provider_amount_minor,
                    provider_currency=result.currency,
                    provider_status=result.provider_status,
                    response_payload=result.payload,
                    verified_at=None,
                )
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.RETRYABLE,
                    failure_reason="Provider verification timed out.",
                    provider_reference=result.provider_reference,
                )
                TopUpRepository.mark_processing(top_up, gateway_transaction=gateway_tx, provider_reference=result.provider_reference)
                intent.refresh_from_db()
                return self._payment_verify_payload(intent)

            if result.status == "FAILED":
                GatewayTransactionRepository.record_verification(
                    gateway_tx,
                    status=GatewayTransactionStatusChoices.FAILED,
                    provider_reference=result.provider_reference,
                    provider_amount_minor=result.provider_amount_minor,
                    provider_currency=result.currency,
                    provider_status=result.provider_status,
                    response_payload=result.payload,
                    verified_at=now,
                )
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.FAILED,
                    failure_reason="Provider verification failed.",
                    provider_reference=result.provider_reference,
                    verified_at=now,
                )
                TopUpRepository.mark_failed(
                    top_up,
                    gateway_transaction=gateway_tx,
                    provider_reference=result.provider_reference,
                    reason="Provider verification failed.",
                    failed_at=now,
                )
                intent.refresh_from_db()
                return self._payment_verify_payload(intent)

            if result.provider_amount_minor != int(intent.amount_minor):
                GatewayTransactionRepository.record_verification(
                    gateway_tx,
                    status=GatewayTransactionStatusChoices.FAILED,
                    provider_reference=result.provider_reference,
                    provider_amount_minor=result.provider_amount_minor,
                    provider_currency=result.currency,
                    provider_status="amount_mismatch",
                    response_payload=result.payload,
                    verified_at=now,
                )
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.FAILED,
                    failure_reason="Provider amount mismatch.",
                    provider_reference=result.provider_reference,
                    verified_at=now,
                )
                TopUpRepository.mark_failed(
                    top_up,
                    gateway_transaction=gateway_tx,
                    provider_reference=result.provider_reference,
                    reason="Provider amount mismatch.",
                    failed_at=now,
                )
                intent.refresh_from_db()
                return self._payment_verify_payload(intent)

            existing_tx = WalletTransactionRepository.get_by_wallet_and_idempotency(wallet, f"payment-intent:{intent.id}")
            if existing_tx:
                PaymentIntentRepository.set_status(
                    intent,
                    PaymentIntentStatusChoices.SUCCEEDED,
                    provider_reference=result.provider_reference,
                    verified_at=existing_tx.completed_at or now,
                )
                GatewayTransactionRepository.record_verification(
                    gateway_tx,
                    status=GatewayTransactionStatusChoices.SUCCEEDED,
                    provider_reference=result.provider_reference,
                    provider_amount_minor=result.provider_amount_minor,
                    provider_currency=result.currency,
                    provider_status=result.provider_status,
                    response_payload=result.payload,
                    verified_at=existing_tx.completed_at or now,
                )
                TopUpRepository.mark_completed(
                    top_up,
                    wallet_transaction=existing_tx,
                    gateway_transaction=gateway_tx,
                    provider_reference=result.provider_reference,
                    completed_at=existing_tx.completed_at or now,
                )
                intent.refresh_from_db()
                return self._payment_verify_payload(intent)

            tx = WalletTransactionRepository.create(
                wallet=wallet,
                type=WalletTransactionTypeChoices.TOP_UP,
                status=WalletTransactionStatusChoices.COMPLETED,
                direction=WalletTransactionDirectionChoices.IN,
                amount_minor=int(intent.amount_minor),
                currency=intent.currency,
                description="Wallet top up",
                reference_type="PAYMENT_INTENT",
                reference_id=intent.id,
                idempotency_key=f"payment-intent:{intent.id}",
                completed_at=now,
                metadata={"provider": provider},
            )
            LedgerRepository.create_many(
                [
                    {
                        "wallet": wallet,
                        "transaction": tx,
                        "entry_type": LedgerEntryTypeChoices.AVAILABLE_CREDIT,
                        "amount_minor": int(intent.amount_minor),
                        "currency": intent.currency,
                    },
                ]
            )
            WalletRepository.refresh_balances(wallet)
            GatewayTransactionRepository.record_verification(
                gateway_tx,
                status=GatewayTransactionStatusChoices.SUCCEEDED,
                provider_reference=result.provider_reference,
                provider_amount_minor=result.provider_amount_minor,
                provider_currency=result.currency,
                provider_status=result.provider_status,
                response_payload=result.payload,
                verified_at=now,
            )
            PaymentIntentRepository.set_status(
                intent,
                PaymentIntentStatusChoices.SUCCEEDED,
                provider_reference=result.provider_reference,
                verified_at=now,
            )
            TopUpRepository.mark_completed(
                top_up,
                wallet_transaction=tx,
                gateway_transaction=gateway_tx,
                provider_reference=result.provider_reference,
                completed_at=now,
            )
            intent.refresh_from_db()
            self._emit_top_up_completed_event(intent=intent, top_up=top_up, tx=tx, completed_at=now)
            return self._payment_verify_payload(intent)
