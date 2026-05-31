from django.db import transaction
from django.conf import settings

from apps.settlements.application.balance_service import BalanceService
from apps.settlements.application.debt_service import DebtService
from apps.settlements.domain.events import SettlementCancelled, SettlementConfirmed, SettlementCreated, SettlementRejected
from apps.settlements.domain.models import CurrencyChoices, ManualSettlementStatusChoices
from apps.settlements.domain.rules import (
    ensure_active_member,
    ensure_different_participants,
    ensure_amount_within_limit,
    ensure_group_active,
    ensure_irr_currency,
    ensure_positive_amount,
    ensure_settlement_can_be_modified,
    InvalidSettlementStatusError,
    NotGroupMemberError,
    SettlementNotFoundError,
    SettlementPermissionDeniedError,
)
from apps.settlements.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.settlements.infrastructure.repositories import (
    DebtLedgerRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    ManualSettlementRepository,
)


class SettlementService:
    def __init__(self, publisher=None, debt_service=None, balance_service=None):
        self.publisher = publisher or RabbitMQPublisher()
        self.debt_service = debt_service or DebtService(publisher=self.publisher, balance_service=balance_service or BalanceService())
        self.balance_service = balance_service or BalanceService()

    def _get_group_and_member(self, group_id, user_id):
        group = GroupProjectionRepository.get(group_id)
        ensure_group_active(group)
        member = GroupMemberProjectionRepository.get_active_member(group_id, user_id)
        ensure_active_member(member)
        return group, member

    @transaction.atomic
    def create_manual_settlement(self, group_id, payer_user_id, payload):
        self._get_group_and_member(group_id, payer_user_id)
        receiver_user_id = payload.get("receiver_user_id")
        ensure_different_participants(payer_user_id, receiver_user_id)
        receiver = GroupMemberProjectionRepository.get_active_member(group_id, receiver_user_id)
        ensure_active_member(receiver)
        amount_minor = int(payload.get("amount_minor", 0))
        ensure_positive_amount(amount_minor)
        ensure_amount_within_limit(amount_minor, getattr(settings, "MAX_SETTLEMENT_AMOUNT_MINOR", 100000000000))
        ensure_irr_currency(payload.get("currency", CurrencyChoices.IRR))
        settlement = ManualSettlementRepository.create_pending(
            group_id=group_id,
            payer_user_id=payer_user_id,
            receiver_user_id=receiver_user_id,
            amount_minor=amount_minor,
            currency=CurrencyChoices.IRR,
            description=payload.get("description"),
            created_by_user_id=payer_user_id,
        )
        self.publisher.publish(
            "SettlementCreated",
            {
                "settlement_id": str(settlement.id),
                "group_id": str(settlement.group_id),
                "payer_user_id": str(settlement.payer_user_id),
                "receiver_user_id": str(settlement.receiver_user_id),
                "amount_minor": settlement.amount_minor,
                "currency": settlement.currency,
                "status": settlement.status,
            },
            "settlement.created",
        )
        return settlement

    def list_group_settlements(self, group_id, requester_user_id, filters=None):
        self._get_group_and_member(group_id, requester_user_id)
        return ManualSettlementRepository.list_by_group(group_id, filters=filters)

    @transaction.atomic
    def confirm_settlement(self, settlement_id, user_id):
        settlement = ManualSettlementRepository.get(settlement_id)
        if not settlement:
            raise SettlementNotFoundError()
        ensure_settlement_can_be_modified(settlement)
        if str(settlement.receiver_user_id) != str(user_id):
            raise SettlementPermissionDeniedError()
        ManualSettlementRepository.confirm(settlement, user_id)
        self.debt_service.create_manual_settlement_ledger(settlement)
        self.publisher.publish(
            "SettlementConfirmed",
            {
                "settlement_id": str(settlement.id),
                "group_id": str(settlement.group_id),
                "payer_user_id": str(settlement.payer_user_id),
                "receiver_user_id": str(settlement.receiver_user_id),
                "amount_minor": settlement.amount_minor,
                "currency": settlement.currency,
                "confirmed_by_user_id": str(user_id),
            },
            "settlement.confirmed",
        )
        return settlement

    @transaction.atomic
    def reject_settlement(self, settlement_id, user_id, reason=None):
        settlement = ManualSettlementRepository.get(settlement_id)
        if not settlement:
            raise SettlementNotFoundError()
        ensure_settlement_can_be_modified(settlement)
        if str(settlement.receiver_user_id) != str(user_id):
            raise SettlementPermissionDeniedError()
        ManualSettlementRepository.reject(settlement, user_id)
        self.publisher.publish(
            "SettlementRejected",
            {
                "settlement_id": str(settlement.id),
                "group_id": str(settlement.group_id),
                "payer_user_id": str(settlement.payer_user_id),
                "receiver_user_id": str(settlement.receiver_user_id),
                "amount_minor": settlement.amount_minor,
                "currency": settlement.currency,
                "rejected_by_user_id": str(user_id),
                "reason": reason,
            },
            "settlement.rejected",
        )
        return settlement

    @transaction.atomic
    def cancel_settlement(self, settlement_id, user_id):
        settlement = ManualSettlementRepository.get(settlement_id)
        if not settlement:
            raise SettlementNotFoundError()
        ensure_settlement_can_be_modified(settlement)
        if str(settlement.payer_user_id) != str(user_id):
            raise SettlementPermissionDeniedError()
        ManualSettlementRepository.cancel(settlement, user_id)
        self.publisher.publish(
            "SettlementCancelled",
            {
                "settlement_id": str(settlement.id),
                "group_id": str(settlement.group_id),
                "payer_user_id": str(settlement.payer_user_id),
                "receiver_user_id": str(settlement.receiver_user_id),
                "amount_minor": settlement.amount_minor,
                "currency": settlement.currency,
                "cancelled_by_user_id": str(user_id),
            },
            "settlement.cancelled",
        )
        return settlement