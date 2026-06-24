
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.wallets.domain.models import (
    CurrencyChoices,
    LedgerEntryTypeChoices,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
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
    InvalidWalletCursorError,
    PaymentMethodNotFoundError,
    SettlementItemForbiddenError,
    SettlementItemNotFoundError,
    SettlementItemNotPayableError,
    WalletInactiveError,
    WalletServiceError,
    WithdrawalNotFoundError,
    WithdrawalStateError,
    ensure_irr_currency,
    ensure_positive_amount,
)
from apps.wallets.infrastructure.clients import IdentityBankCardClient
from apps.wallets.infrastructure.event_envelope import build_event_envelope
from apps.wallets.infrastructure.repositories import (
    LedgerRepository,
    SettlementItemProjectionRepository,
    UserProjectionRepository,
    WalletRepository,
    WalletTransactionRepository,
    WithdrawalRepository,
    OutboxRepository,
)


PAYABLE_ITEM_STATUSES = {
    SettlementItemStatusChoices.PENDING,
    SettlementItemStatusChoices.REJECTED,
}
RECEIVABLE_ITEM_STATUSES = {
    SettlementItemStatusChoices.PENDING,
    SettlementItemStatusChoices.REPORTED,
}


class WalletService:
    def __init__(self, bank_card_client: IdentityBankCardClient | None = None):
        self.bank_card_client = bank_card_client or IdentityBankCardClient()

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

    def _settlement_summary_item(self, item, *, counterparty_user_id) -> dict[str, Any]:
        counterparty = UserProjectionRepository.get(counterparty_user_id)
        return {
            "settlement_plan_item_id": item.item_id,
            "plan_id": item.plan_id,
            "group_id": item.group_id,
            "counterparty": {
                "user_id": counterparty_user_id,
                "art_name": counterparty.art_name if counterparty else None,
            },
            "amount_minor": item.amount_minor,
            "currency": item.currency,
            "status": item.item_status,
            "updated_at": item.updated_at,
        }

    def get_or_create_wallet(self, requester_user_id, currency: str = CurrencyChoices.IRR) -> Wallet:
        wallet, _ = WalletRepository.get_or_create_for_user(
            requester_user_id,
            currency=currency or getattr(settings, "DEFAULT_CURRENCY", CurrencyChoices.IRR),
        )
        return wallet

    def get_my_wallet(self, requester_user_id):
        return self._wallet_payload(self.get_or_create_wallet(requester_user_id))

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
