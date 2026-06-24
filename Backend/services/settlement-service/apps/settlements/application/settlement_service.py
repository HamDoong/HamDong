from datetime import datetime

from django.conf import settings
from django.db import transaction

from apps.settlements.application.balance_service import BalanceService
from apps.settlements.application.debt_service import DebtService
from apps.settlements.domain.models import (
    CurrencyChoices,
    ManualSettlementStatusChoices,
    SettlementPlanItemStatusChoices,
)
from apps.settlements.domain.rules import (
    InvalidSettlementCursorError,
    SettlementNotFoundError,
    SettlementPermissionDeniedError,
    ensure_active_member,
    ensure_amount_within_limit,
    ensure_different_participants,
    ensure_group_active,
    ensure_irr_currency,
    ensure_positive_amount,
    ensure_settlement_can_be_modified,
)
from apps.settlements.infrastructure.rabbitmq_publisher import RabbitMQPublisher
from apps.settlements.infrastructure.repositories import (
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    ManualSettlementRepository,
    SettlementPlanItemRepository,
    UserProjectionRepository,
)


class SettlementService:
    def __init__(self, publisher=None, debt_service=None, balance_service=None):
        self.publisher = publisher or RabbitMQPublisher()
        self.debt_service = debt_service or DebtService(
            publisher=self.publisher,
            balance_service=balance_service or BalanceService(),
        )
        self.balance_service = balance_service or BalanceService()

    def _get_group_and_member(self, group_id, user_id):
        group = GroupProjectionRepository.get(group_id)
        ensure_group_active(group)
        member = GroupMemberProjectionRepository.get_active_member(group_id, user_id)
        ensure_active_member(member)
        return group, member

    def _encode_cursor(self, item):
        return (
            f"{item['updated_at'].isoformat()}|"
            f"{item['created_at'].isoformat()}|"
            f"{item['source_type']}|{item['id']}"
        )

    def _decode_cursor(self, value):
        try:
            updated_at, created_at, source_type, item_id = str(value).split("|", 3)
            return (
                datetime.fromisoformat(updated_at),
                datetime.fromisoformat(created_at),
                source_type,
                item_id,
            )
        except Exception as exc:
            raise InvalidSettlementCursorError() from exc

    def _counterparty_art_name(self, group_id, counterparty_user_id):
        member = GroupMemberProjectionRepository.get(group_id, counterparty_user_id)
        if member and member.art_name_snapshot:
            return member.art_name_snapshot
        user = UserProjectionRepository.get(counterparty_user_id)
        if user:
            return user.art_name
        return None

    def _build_feed_item(self, record, requester_user_id):
        direction = "PAY" if str(record.payer_user_id) == str(requester_user_id) else "RECEIVE"
        counterparty_user_id = (
            record.receiver_user_id if direction == "PAY" else record.payer_user_id
        )
        action_required = None
        allowed_actions = []

        if record.source_type == "SETTLEMENT_PLAN_ITEM":
            if direction == "PAY" and record.status == SettlementPlanItemStatusChoices.PENDING:
                action_required = "PAY"
                allowed_actions = ["REPORT_PAID"]
            elif (
                direction == "RECEIVE"
                and record.status == SettlementPlanItemStatusChoices.REPORTED
            ):
                action_required = "CONFIRM"
                allowed_actions = ["CONFIRM", "REJECT"]
        elif record.source_type == "MANUAL_SETTLEMENT":
            if (
                direction == "RECEIVE"
                and record.status == ManualSettlementStatusChoices.PENDING_CONFIRMATION
            ):
                action_required = "CONFIRM"
                allowed_actions = ["CONFIRM", "REJECT"]
            elif (
                direction == "PAY"
                and record.status == ManualSettlementStatusChoices.PENDING_CONFIRMATION
            ):
                allowed_actions = ["CANCEL"]

        group = GroupProjectionRepository.get(record.group_id)
        return {
            "id": record.id,
            "source_type": record.source_type,
            "source_id": record.source_id,
            "group": {
                "id": record.group_id,
                "title": group.title if group else "",
            },
            "counterparty": {
                "user_id": counterparty_user_id,
                "art_name": self._counterparty_art_name(
                    record.group_id, counterparty_user_id
                ),
            },
            "direction": direction,
            "amount_minor": record.amount_minor,
            "currency": record.currency,
            "status": record.status,
            "action_required": action_required,
            "allowed_actions": allowed_actions,
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }

    def list_my_settlements(self, requester_user_id, filters=None):
        filters = filters or {}
        cursor_data = None
        if filters.get("cursor"):
            cursor_data = self._decode_cursor(filters["cursor"])

        active_group_ids = GroupMemberProjectionRepository.list_active_group_ids_for_user(
            requester_user_id
        )
        if not active_group_ids:
            return [], None

        plan_items = SettlementPlanItemRepository.list_for_user_feed(
            requester_user_id,
            active_group_ids=active_group_ids,
            filters=filters,
        )
        manual_settlements = ManualSettlementRepository.list_for_user_feed(
            requester_user_id,
            active_group_ids=active_group_ids,
            filters=filters,
        )
        items = [
            self._build_feed_item(record, requester_user_id)
            for record in [*plan_items, *manual_settlements]
        ]
        if filters.get("action_required") is True:
            items = [item for item in items if item["action_required"]]

        items.sort(
            key=lambda item: (
                item["updated_at"],
                item["created_at"],
                str(item["source_type"]),
                str(item["id"]),
            ),
            reverse=True,
        )

        if cursor_data:
            (
                cursor_updated_at,
                cursor_created_at,
                cursor_source_type,
                cursor_id,
            ) = cursor_data
            items = [
                item
                for item in items
                if (
                    item["updated_at"],
                    item["created_at"],
                    str(item["source_type"]),
                    str(item["id"]),
                )
                < (
                    cursor_updated_at,
                    cursor_created_at,
                    str(cursor_source_type),
                    str(cursor_id),
                )
            ]

        page_size = min(int(filters.get("page_size") or 20), 100)
        page_items = items[: page_size + 1]
        next_cursor = None
        if len(page_items) > page_size:
            next_cursor = self._encode_cursor(page_items[page_size - 1])
            page_items = page_items[:page_size]
        return page_items, next_cursor

    @transaction.atomic
    def create_manual_settlement(self, group_id, payer_user_id, payload):
        self._get_group_and_member(group_id, payer_user_id)
        receiver_user_id = payload.get("receiver_user_id")
        ensure_different_participants(payer_user_id, receiver_user_id)
        receiver = GroupMemberProjectionRepository.get_active_member(
            group_id, receiver_user_id
        )
        ensure_active_member(receiver)
        amount_minor = int(payload.get("amount_minor", 0))
        ensure_positive_amount(amount_minor)
        ensure_amount_within_limit(
            amount_minor, getattr(settings, "MAX_SETTLEMENT_AMOUNT_MINOR", 100000000000)
        )
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
