
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.wallets.domain.models import (
    CurrencyChoices,
    GatewayTransaction,
    GatewayTransactionStatusChoices,
    InboxMessage,
    InboxMessageStatusChoices,
    LedgerEntry,
    LedgerEntryTypeChoices,
    OutboxMessage,
    OutboxMessageStatusChoices,
    PaymentCallbackLog,
    PaymentIntent,
    PaymentIntentStatusChoices,
    PaymentProviderChoices,
    PaymentPurposeChoices,
    SettlementItemProjection,
    SettlementItemStatusChoices,
    SettlementPlanStatusChoices,
    TopUp,
    TopUpStatusChoices,
    UserProjection,
    Wallet,
    WalletStatusChoices,
    WalletTransaction,
    WalletTransactionStatusChoices,
    WalletTransactionTypeChoices,
    Withdrawal,
    WithdrawalStatusChoices,
)


def normalize_uuid(value):
    if value in (None, ""):
        return None
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def coerce_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


@dataclass(frozen=True)
class CursorRecord:
    created_at: datetime
    object_id: uuid.UUID


class UserProjectionRepository:
    @staticmethod
    def upsert_from_event(**data):
        identity_user_id = normalize_uuid(data.get("user_id") or data.get("identity_user_id"))
        if not identity_user_id:
            return None
        defaults = {
            "email": data.get("email", ""),
            "art_name": data.get("art_name"),
            "first_name": data.get("first_name"),
            "last_name": data.get("last_name"),
            "role": data.get("role", "USER"),
            "is_active": data.get("is_active", True),
        }
        obj, _ = UserProjection.objects.update_or_create(
            identity_user_id=identity_user_id,
            defaults=defaults,
        )
        return obj

    @staticmethod
    def get(user_id):
        return UserProjection.objects.filter(identity_user_id=normalize_uuid(user_id)).first()


class WalletRepository:
    @staticmethod
    def get_or_create_for_user(user_id, currency: str = CurrencyChoices.IRR, *, for_update: bool = False):
        user_id = normalize_uuid(user_id)
        qs = Wallet.objects
        if for_update:
            qs = qs.select_for_update()
        wallet = qs.filter(user_id=user_id, currency=currency).first()
        if wallet:
            return wallet, False
        try:
            with transaction.atomic():
                wallet, created = Wallet.objects.get_or_create(
                    user_id=user_id,
                    currency=currency,
                    defaults={"status": WalletStatusChoices.ACTIVE},
                )
            if for_update:
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            return wallet, created
        except IntegrityError:
            wallet = Wallet.objects.select_for_update().get(user_id=user_id, currency=currency) if for_update else Wallet.objects.get(user_id=user_id, currency=currency)
            return wallet, False

    @staticmethod
    def get_for_user(user_id, currency: str = CurrencyChoices.IRR):
        return Wallet.objects.filter(user_id=normalize_uuid(user_id), currency=currency).first()

    @staticmethod
    def refresh_balances(wallet: Wallet) -> Wallet:
        agg = wallet.ledger_entries.aggregate(
            available_credit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.AVAILABLE_CREDIT)), 0),
            available_debit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.AVAILABLE_DEBIT)), 0),
            reserved_credit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.RESERVED_CREDIT)), 0),
            reserved_debit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.RESERVED_DEBIT)), 0),
        )
        available = int(agg["available_credit"] or 0) - int(agg["available_debit"] or 0)
        reserved = int(agg["reserved_credit"] or 0) - int(agg["reserved_debit"] or 0)
        inflow_types = [
            WalletTransactionTypeChoices.TOP_UP,
            WalletTransactionTypeChoices.TRANSFER_RECEIVED,
            WalletTransactionTypeChoices.SETTLEMENT_RECEIVED,
            WalletTransactionTypeChoices.REFUND,
            WalletTransactionTypeChoices.ADJUSTMENT,
        ]
        outflow_types = [
            WalletTransactionTypeChoices.WITHDRAWAL,
            WalletTransactionTypeChoices.TRANSFER_SENT,
            WalletTransactionTypeChoices.SETTLEMENT_PAYMENT,
        ]
        tx_agg = wallet.transactions.aggregate(
            total_inflow=Coalesce(Sum("amount_minor", filter=Q(status=WalletTransactionStatusChoices.COMPLETED, type__in=inflow_types, direction="IN")), 0),
            total_outflow=Coalesce(Sum("amount_minor", filter=Q(status=WalletTransactionStatusChoices.COMPLETED, type__in=outflow_types, direction="OUT")), 0),
        )
        Wallet.objects.filter(pk=wallet.pk).update(
            available_balance_minor=available,
            reserved_balance_minor=reserved,
            total_inflow_minor=int(tx_agg["total_inflow"] or 0),
            total_outflow_minor=int(tx_agg["total_outflow"] or 0),
            last_ledger_recalculated_at=timezone.now(),
            updated_at=timezone.now(),
        )
        wallet.refresh_from_db()
        return wallet


class WalletTransactionRepository:
    @staticmethod
    def get_by_wallet_and_idempotency(wallet: Wallet, idempotency_key: str):
        return WalletTransaction.objects.filter(wallet=wallet, idempotency_key=idempotency_key).first()

    @staticmethod
    def create(**kwargs):
        return WalletTransaction.objects.create(**kwargs)

    @staticmethod
    def get_for_wallet(wallet: Wallet, transaction_id):
        return WalletTransaction.objects.filter(wallet=wallet, id=normalize_uuid(transaction_id)).first()

    @staticmethod
    def list_for_wallet(wallet: Wallet, *, filters: dict | None = None):
        filters = filters or {}
        qs = WalletTransaction.objects.filter(wallet=wallet).order_by("-created_at", "-id")
        if filters.get("type"):
            qs = qs.filter(type=filters["type"])
        if filters.get("status"):
            qs = qs.filter(status=filters["status"])
        if filters.get("from_at"):
            qs = qs.filter(created_at__gte=filters["from_at"])
        if filters.get("to"):
            qs = qs.filter(created_at__lte=filters["to"])
        return qs


class LedgerRepository:
    @staticmethod
    def create_many(entries: Iterable[dict]):
        objects = [LedgerEntry(**entry) for entry in entries]
        return LedgerEntry.objects.bulk_create(objects)

    @staticmethod
    def ledger_totals_for_wallet(wallet: Wallet) -> dict:
        agg = wallet.ledger_entries.aggregate(
            available_credit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.AVAILABLE_CREDIT)), 0),
            available_debit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.AVAILABLE_DEBIT)), 0),
            reserved_credit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.RESERVED_CREDIT)), 0),
            reserved_debit=Coalesce(Sum("amount_minor", filter=Q(entry_type=LedgerEntryTypeChoices.RESERVED_DEBIT)), 0),
        )
        return {k: int(v or 0) for k, v in agg.items()}


class SettlementItemProjectionRepository:
    @staticmethod
    def upsert_from_generated(plan_id, group_id, currency, plan_status, items: list[dict], occurred_at):
        rows = []
        occurred = coerce_datetime(occurred_at) or timezone.now()
        for item in items or []:
            item_id = normalize_uuid(item.get("item_id") or item.get("id"))
            if not item_id:
                continue
            defaults = {
                "plan_id": normalize_uuid(plan_id),
                "group_id": normalize_uuid(group_id),
                "payer_user_id": normalize_uuid(item.get("payer_user_id")),
                "payee_user_id": normalize_uuid(item.get("receiver_user_id") or item.get("payee_user_id")),
                "amount_minor": int(item.get("amount_minor") or 0),
                "currency": item.get("currency") or currency or CurrencyChoices.IRR,
                "item_status": item.get("status") or SettlementItemStatusChoices.PENDING,
                "plan_status": plan_status or SettlementPlanStatusChoices.DRAFT,
                "created_at": coerce_datetime(item.get("created_at") or occurred) or occurred,
                "updated_at": occurred,
            }
            row, _ = SettlementItemProjection.objects.update_or_create(item_id=item_id, defaults=defaults)
            rows.append(row)
        return rows

    @staticmethod
    def update_plan_status(plan_id, plan_status, occurred_at):
        return SettlementItemProjection.objects.filter(plan_id=normalize_uuid(plan_id)).update(
            plan_status=plan_status,
            updated_at=coerce_datetime(occurred_at) or timezone.now(),
        )

    @staticmethod
    def update_item_status(item_id, item_status, occurred_at):
        return SettlementItemProjection.objects.filter(item_id=normalize_uuid(item_id)).update(
            item_status=item_status,
            updated_at=coerce_datetime(occurred_at) or timezone.now(),
        )

    @staticmethod
    def get_for_update(item_id):
        return SettlementItemProjection.objects.select_for_update().filter(item_id=normalize_uuid(item_id)).first()

    @staticmethod
    def get(item_id):
        return SettlementItemProjection.objects.filter(item_id=normalize_uuid(item_id)).first()

    @staticmethod
    def list_pending_payables(user_id, currency: str = CurrencyChoices.IRR):
        return SettlementItemProjection.objects.filter(
            payer_user_id=normalize_uuid(user_id),
            currency=currency,
            plan_status=SettlementPlanStatusChoices.ACTIVE,
            item_status__in=[SettlementItemStatusChoices.PENDING, SettlementItemStatusChoices.REJECTED],
        ).order_by("-updated_at", "-item_id")

    @staticmethod
    def list_pending_receivables(user_id, currency: str = CurrencyChoices.IRR):
        return SettlementItemProjection.objects.filter(
            payee_user_id=normalize_uuid(user_id),
            currency=currency,
            plan_status=SettlementPlanStatusChoices.ACTIVE,
            item_status__in=[SettlementItemStatusChoices.PENDING, SettlementItemStatusChoices.REPORTED],
        ).order_by("-updated_at", "-item_id")


class WithdrawalRepository:
    @staticmethod
    def get_by_wallet_and_idempotency(wallet: Wallet, idempotency_key: str):
        return Withdrawal.objects.filter(wallet=wallet, idempotency_key=idempotency_key).first()

    @staticmethod
    def create(**kwargs):
        return Withdrawal.objects.create(**kwargs)

    @staticmethod
    def list_for_wallet(wallet: Wallet):
        return Withdrawal.objects.filter(wallet=wallet).order_by("-created_at", "-id")

    @staticmethod
    def get_for_wallet(wallet: Wallet, withdrawal_id):
        return Withdrawal.objects.filter(wallet=wallet, id=normalize_uuid(withdrawal_id)).first()

    @staticmethod
    def pending_for_wallet(wallet: Wallet):
        return Withdrawal.objects.filter(
            wallet=wallet,
            status__in=[WithdrawalStatusChoices.PENDING, WithdrawalStatusChoices.PROCESSING],
        ).order_by("-created_at", "-id")


class PaymentIntentRepository:
    @staticmethod
    def get_by_wallet_and_idempotency(wallet: Wallet, idempotency_key: str):
        return PaymentIntent.objects.filter(wallet=wallet, idempotency_key=idempotency_key).first()

    @staticmethod
    def create(**kwargs):
        return PaymentIntent.objects.create(**kwargs)

    @staticmethod
    def get_for_wallet(wallet: Wallet, payment_intent_id):
        return PaymentIntent.objects.filter(wallet=wallet, id=normalize_uuid(payment_intent_id)).select_related("wallet").first()

    @staticmethod
    def get_for_wallet_update(wallet: Wallet, payment_intent_id):
        return PaymentIntent.objects.select_for_update().filter(wallet=wallet, id=normalize_uuid(payment_intent_id)).select_related("wallet").first()

    @staticmethod
    def set_status(intent: PaymentIntent, status: str, *, failure_reason: str | None = None, provider_reference: str | None = None, verified_at=None):
        if failure_reason is not None:
            intent.failure_reason = failure_reason
        if provider_reference:
            intent.provider_reference = provider_reference
        if verified_at is not None:
            intent.verified_at = verified_at
        intent.status = status
        intent.updated_at = timezone.now()
        fields = ["status", "updated_at"]
        if failure_reason is not None:
            fields.append("failure_reason")
        if provider_reference:
            fields.append("provider_reference")
        if verified_at is not None:
            fields.append("verified_at")
        intent.save(update_fields=fields)
        return intent

    @staticmethod
    def mark_callback_received(intent: PaymentIntent, *, provider_reference: str | None = None, callback_at=None):
        intent.status = PaymentIntentStatusChoices.CALLBACK_RECEIVED
        intent.last_callback_at = callback_at or timezone.now()
        if provider_reference:
            intent.provider_reference = provider_reference
        intent.save(update_fields=["status", "last_callback_at", "provider_reference", "updated_at"])
        return intent


class GatewayTransactionRepository:
    @staticmethod
    def get_or_create_for_intent(payment_intent: PaymentIntent, defaults: dict | None = None):
        defaults = defaults or {}
        obj, _ = GatewayTransaction.objects.get_or_create(payment_intent=payment_intent, defaults=defaults)
        return obj

    @staticmethod
    def get_for_intent(payment_intent: PaymentIntent):
        return GatewayTransaction.objects.filter(payment_intent=payment_intent).first()

    @staticmethod
    def find_by_provider_reference(provider: str, provider_reference: str):
        if not provider_reference:
            return None
        return GatewayTransaction.objects.filter(provider=provider, provider_reference=provider_reference).select_related("payment_intent").first()

    @staticmethod
    def lock_for_intent(payment_intent: PaymentIntent):
        return GatewayTransaction.objects.select_for_update().filter(payment_intent=payment_intent).first()

    @staticmethod
    def record_callback(payment_intent: PaymentIntent, *, provider: str, provider_reference: str | None, provider_amount_minor: int | None, provider_currency: str | None, provider_status: str | None, payload: dict, callback_at=None):
        obj, created = GatewayTransaction.objects.select_for_update().get_or_create(
            payment_intent=payment_intent,
            defaults={
                "provider": provider,
                "provider_reference": provider_reference,
                "status": GatewayTransactionStatusChoices.CALLBACK_RECEIVED,
                "provider_amount_minor": provider_amount_minor,
                "provider_currency": provider_currency or CurrencyChoices.IRR,
                "provider_status": provider_status,
                "last_callback_payload": payload,
                "last_callback_at": callback_at or timezone.now(),
                "callback_count": 1,
            },
        )
        updates = []
        obj.provider = provider
        if provider_reference:
            obj.provider_reference = provider_reference
            updates.append("provider_reference")
        if provider_amount_minor is not None:
            obj.provider_amount_minor = int(provider_amount_minor)
            updates.append("provider_amount_minor")
        if provider_currency:
            obj.provider_currency = provider_currency
            updates.append("provider_currency")
        if provider_status:
            obj.provider_status = provider_status
            updates.append("provider_status")
        obj.last_callback_payload = payload
        obj.last_callback_at = callback_at or timezone.now()
        obj.status = GatewayTransactionStatusChoices.CALLBACK_RECEIVED
        obj.callback_count = 1 if created else int(obj.callback_count or 0) + 1
        obj.save(update_fields=list(set(updates + ["provider", "last_callback_payload", "last_callback_at", "status", "callback_count", "updated_at"])))
        return obj

    @staticmethod
    def record_verification(
        gateway_tx: GatewayTransaction,
        *,
        status: str,
        provider_reference: str | None = None,
        provider_amount_minor: int | None = None,
        provider_currency: str | None = None,
        provider_status: str | None = None,
        response_payload: dict | None = None,
        verified_at=None,
    ):
        if provider_reference:
            gateway_tx.provider_reference = provider_reference
        if provider_amount_minor is not None:
            gateway_tx.provider_amount_minor = int(provider_amount_minor)
        if provider_currency:
            gateway_tx.provider_currency = provider_currency
        if provider_status:
            gateway_tx.provider_status = provider_status
        gateway_tx.status = status
        gateway_tx.last_verify_response = response_payload or {}
        gateway_tx.verification_attempts = int(gateway_tx.verification_attempts or 0) + 1
        gateway_tx.verified_at = verified_at
        gateway_tx.save(
            update_fields=[
                "provider_reference",
                "provider_amount_minor",
                "provider_currency",
                "provider_status",
                "status",
                "last_verify_response",
                "verification_attempts",
                "verified_at",
                "updated_at",
            ]
        )
        return gateway_tx


class TopUpRepository:
    @staticmethod
    def create(**kwargs):
        return TopUp.objects.create(**kwargs)

    @staticmethod
    def get_by_payment_intent(payment_intent: PaymentIntent):
        return TopUp.objects.filter(payment_intent=payment_intent).first()

    @staticmethod
    def get_by_wallet_and_idempotency(wallet: Wallet, idempotency_key: str):
        return TopUp.objects.filter(wallet=wallet, idempotency_key=idempotency_key).first()

    @staticmethod
    def get_or_create_for_intent(payment_intent: PaymentIntent, defaults: dict | None = None):
        defaults = defaults or {}
        top_up, _ = TopUp.objects.get_or_create(payment_intent=payment_intent, defaults=defaults)
        return top_up

    @staticmethod
    def mark_completed(top_up: TopUp, *, wallet_transaction: WalletTransaction, gateway_transaction: GatewayTransaction | None = None, provider_reference: str | None = None, completed_at=None):
        top_up.status = TopUpStatusChoices.COMPLETED
        top_up.wallet_transaction = wallet_transaction
        top_up.gateway_transaction = gateway_transaction
        if provider_reference:
            top_up.provider_reference = provider_reference
        top_up.completed_at = completed_at or timezone.now()
        top_up.failed_at = None
        top_up.failure_reason = None
        top_up.save(
            update_fields=[
                "status",
                "wallet_transaction",
                "gateway_transaction",
                "provider_reference",
                "completed_at",
                "failed_at",
                "failure_reason",
                "updated_at",
            ]
        )
        return top_up

    @staticmethod
    def mark_failed(top_up: TopUp, *, gateway_transaction: GatewayTransaction | None = None, provider_reference: str | None = None, reason: str, failed_at=None):
        top_up.status = TopUpStatusChoices.FAILED
        top_up.gateway_transaction = gateway_transaction
        if provider_reference:
            top_up.provider_reference = provider_reference
        top_up.failure_reason = reason
        top_up.failed_at = failed_at or timezone.now()
        top_up.save(
            update_fields=[
                "status",
                "gateway_transaction",
                "provider_reference",
                "failure_reason",
                "failed_at",
                "updated_at",
            ]
        )
        return top_up

    @staticmethod
    def mark_processing(top_up: TopUp, *, gateway_transaction: GatewayTransaction | None = None, provider_reference: str | None = None):
        top_up.status = TopUpStatusChoices.PROCESSING
        top_up.gateway_transaction = gateway_transaction
        if provider_reference:
            top_up.provider_reference = provider_reference
        top_up.save(update_fields=["status", "gateway_transaction", "provider_reference", "updated_at"])
        return top_up


class PaymentCallbackLogRepository:
    @staticmethod
    def create(**kwargs):
        return PaymentCallbackLog.objects.create(**kwargs)

    @staticmethod
    def last_for_intent(payment_intent: PaymentIntent):
        return PaymentCallbackLog.objects.filter(payment_intent=payment_intent).order_by("-received_at").first()


class OutboxRepository:
    @staticmethod
    def create(**data):
        payload = data.get("payload") or {}
        event_id = normalize_uuid(data.get("event_id") or payload.get("event_id")) or uuid.uuid4()
        correlation_id = normalize_uuid(data.get("correlation_id") or payload.get("correlation_id")) or event_id
        causation_id = normalize_uuid(data.get("causation_id") or payload.get("causation_id")) or correlation_id
        return OutboxMessage.objects.create(
            source_service=data.get("source_service", "wallet-service"),
            aggregate_type=data.get("aggregate_type", data.get("event_type", "WalletEvent")),
            aggregate_id=normalize_uuid(data.get("aggregate_id")),
            event_id=event_id,
            event_type=data.get("event_type") or payload.get("event_type"),
            event_version=int(data.get("event_version", payload.get("event_version", 1))),
            routing_key=data.get("routing_key") or payload.get("routing_key"),
            exchange=data.get("exchange", "hamdong.wallet"),
            correlation_id=correlation_id,
            causation_id=causation_id,
            payload=payload,
        )

    @staticmethod
    def pending(limit: int = 50, max_retry_count: int = 5):
        return list(
            OutboxMessage.objects.filter(
                status__in=[OutboxMessageStatusChoices.PENDING, OutboxMessageStatusChoices.FAILED],
                retry_count__lt=max_retry_count,
                available_at__lte=timezone.now(),
            )
            .order_by("created_at")[:limit]
        )

    @staticmethod
    def mark_published(message: OutboxMessage):
        message.status = OutboxMessageStatusChoices.PUBLISHED
        message.published_at = timezone.now()
        message.last_error = None
        message.save(update_fields=["status", "published_at", "last_error", "updated_at"])

    @staticmethod
    def mark_failed(message: OutboxMessage, error: str):
        message.status = OutboxMessageStatusChoices.FAILED
        message.retry_count += 1
        message.last_error = error
        retry_delays = str(getattr(settings, "EVENT_RETRY_DELAY_SECONDS", "10,30,60")).split(",")
        delay = int(retry_delays[min(message.retry_count - 1, len(retry_delays) - 1)].strip() or 10)
        message.available_at = timezone.now() + timedelta(seconds=delay)
        message.save(update_fields=["status", "retry_count", "last_error", "available_at", "updated_at"])


class InboxRepository:
    @staticmethod
    def was_processed(event_id) -> bool:
        return InboxMessage.objects.filter(event_id=normalize_uuid(event_id)).exists()

    @staticmethod
    def mark_processed(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.PROCESSED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj

    @staticmethod
    def mark_skipped(event_id, event_type, source_service, routing_key, payload):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.SKIPPED,
                "processed_at": timezone.now(),
                "error_message": None,
            },
        )
        return obj

    @staticmethod
    def mark_failed(event_id, event_type, source_service, routing_key, payload, error):
        obj, _ = InboxMessage.objects.update_or_create(
            event_id=normalize_uuid(event_id),
            defaults={
                "event_type": event_type,
                "source_service": source_service,
                "routing_key": routing_key,
                "payload": payload,
                "status": InboxMessageStatusChoices.FAILED,
                "processed_at": timezone.now(),
                "error_message": error,
            },
        )
        return obj
