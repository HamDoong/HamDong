from django.db import transaction

from apps.settlements.application.balance_service import BalanceService
from apps.settlements.application.settlement_service import SettlementService
from apps.settlements.application.settlement_plan_algorithm import (
    generate_settlement_plan,
)
from apps.settlements.domain.events import (
    SettlementPlanActivated,
    SettlementPlanCancelled,
    SettlementPlanCompleted,
    SettlementPlanExpired,
    SettlementPlanGenerated,
    SettlementPlanItemConfirmed,
    SettlementPlanItemReported,
    SettlementPlanItemRejected,
)
from apps.settlements.domain.models import (
    CurrencyChoices,
    ManualSettlementStatusChoices,
    SettlementPlanEventTypeChoices,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.domain.plan_rules import (
    InvalidPlanItemActionError,
    NoBalancesFoundError,
    SettlementPlanAlreadyActiveError,
    SettlementPlanNotFoundError,
    ensure_active_group,
    ensure_owner_or_admin,
    ensure_plan_item_actor,
    ensure_plan_item_status,
    ensure_plan_member,
    ensure_plan_status,
)
from apps.settlements.infrastructure.publishers import RabbitMQPublisher
from apps.settlements.infrastructure.repositories import (
    GroupBalanceSnapshotRepository,
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    ManualSettlementRepository,
    SettlementPlanEventLogRepository,
    SettlementPlanItemRepository,
    SettlementPlanRepository,
    UserProjectionRepository,
)


class SettlementPlanService:
    def __init__(self, publisher=None, balance_service=None, settlement_service=None):
        self.publisher = publisher or RabbitMQPublisher()
        self.balance_service = balance_service or BalanceService()
        self.settlement_service = settlement_service or SettlementService(
            publisher=self.publisher, balance_service=self.balance_service
        )

    def _publish(self, event, routing_key):
        self.publisher.publish(event.event_type, event.data, routing_key)

    def _group_and_member(self, group_id, user_id, require_owner_or_admin=False):
        group = GroupProjectionRepository.get(group_id)
        ensure_active_group(group)
        member = GroupMemberProjectionRepository.get_active_member(group_id, user_id)
        if require_owner_or_admin:
            ensure_owner_or_admin(member)
        else:
            ensure_plan_member(member)
        return group, member

    def _latest_balance_snapshots(self, group_id):
        return list(
            GroupBalanceSnapshotRepository.list_by_group(
                group_id, currency=CurrencyChoices.IRR
            )
        )

    def _source_timestamp(self, snapshots):
        return max(snapshot.calculated_at for snapshot in snapshots)

    def _serialize_user_display_name(self, user_id):
        user = UserProjectionRepository.get(user_id)
        if not user:
            return None
        return (
            user.display_name
            or " ".join(part for part in [user.first_name, user.last_name] if part)
            or None
        )

    def _plan_payload(self, plan, items):
        return {
            "id": str(plan.id),
            "group_id": str(plan.group_id),
            "currency": plan.currency,
            "status": plan.status,
            "total_debt_minor": plan.total_debt_minor,
            "transaction_count": plan.transaction_count,
            "source_balance_calculated_at": plan.source_balance_calculated_at.isoformat(),
            "created_at": plan.created_at.isoformat(),
            "updated_at": plan.updated_at.isoformat(),
            "items": [
                {
                    "id": str(item.id),
                    "payer_user_id": str(item.payer_user_id),
                    "payer_display_name": self._serialize_user_display_name(
                        item.payer_user_id
                    ),
                    "receiver_user_id": str(item.receiver_user_id),
                    "receiver_display_name": self._serialize_user_display_name(
                        item.receiver_user_id
                    ),
                    "amount_minor": item.amount_minor,
                    "status": item.status,
                    "order_index": item.order_index,
                }
                for item in items
            ],
        }

    @transaction.atomic
    def generate_plan(self, group_id, user_id):
        group, member = self._group_and_member(
            group_id, user_id, require_owner_or_admin=True
        )
        snapshots = self._latest_balance_snapshots(group_id)
        if not snapshots:
            raise NoBalancesFoundError()
        source_calculated_at = self._source_timestamp(snapshots)
        balances = [
            {
                "user_id": str(snapshot.user_id),
                "net_balance_minor": snapshot.net_balance_minor,
            }
            for snapshot in snapshots
        ]
        instructions = generate_settlement_plan(balances)
        total_debt_minor = sum(
            snapshot.net_balance_minor
            for snapshot in snapshots
            if snapshot.net_balance_minor > 0
        )
        plan = SettlementPlanRepository.create(
            group_id=group.group_id,
            currency=CurrencyChoices.IRR,
            status=SettlementPlanStatusChoices.DRAFT,
            generated_by_user_id=member.user_id,
            source_balance_calculated_at=source_calculated_at,
            total_debt_minor=total_debt_minor,
            transaction_count=len(instructions),
        )
        items = []
        for instruction in instructions:
            items.append(
                SettlementPlanItemRepository.create(
                    settlement_plan_id=plan.id,
                    group_id=group.group_id,
                    payer_user_id=instruction.payer_user_id,
                    receiver_user_id=instruction.receiver_user_id,
                    amount_minor=instruction.amount_minor,
                    currency=CurrencyChoices.IRR,
                    status=SettlementPlanItemStatusChoices.PENDING,
                    order_index=instruction.order_index,
                )
            )
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.PLAN_GENERATED,
            metadata={
                "transaction_count": len(instructions),
                "total_debt_minor": total_debt_minor,
            },
        )
        self._publish(
            SettlementPlanGenerated(
                plan.id,
                group.group_id,
                plan.currency,
                plan.transaction_count,
                plan.total_debt_minor,
            ),
            "settlement.plan.generated",
        )
        return plan, items

    def get_latest_plan(self, group_id, user_id):
        self._group_and_member(group_id, user_id)
        plan = SettlementPlanRepository.get_latest_active_for_group(group_id)
        if not plan:
            plan = (
                SettlementPlanRepository.list_by_group(group_id)
                .filter(status=SettlementPlanStatusChoices.DRAFT)
                .first()
            )
        if not plan:
            raise SettlementPlanNotFoundError()
        items = list(SettlementPlanItemRepository.list_by_plan(plan.id))
        return plan, items

    @transaction.atomic
    def activate_plan(self, plan_id, user_id):
        plan = SettlementPlanRepository.get(plan_id)
        if not plan:
            raise SettlementPlanNotFoundError()
        _, member = self._group_and_member(
            plan.group_id, user_id, require_owner_or_admin=True
        )
        ensure_plan_status(plan, [SettlementPlanStatusChoices.DRAFT])
        if SettlementPlanRepository.has_active_for_group(plan.group_id):
            raise SettlementPlanAlreadyActiveError()
        snapshots = self._latest_balance_snapshots(plan.group_id)
        if (
            not snapshots
            or max(snapshot.calculated_at for snapshot in snapshots)
            > plan.source_balance_calculated_at
        ):
            SettlementPlanRepository.mark_expired(plan)
            SettlementPlanEventLogRepository.create(
                settlement_plan_id=plan.id,
                actor_user_id=member.user_id,
                event_type=SettlementPlanEventTypeChoices.PLAN_EXPIRED,
            )
            self._publish(
                SettlementPlanExpired(plan.id, plan.group_id),
                "settlement.plan.expired",
            )
            plan._expired = True
            return plan
        SettlementPlanRepository.mark_active(plan, member.user_id)
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.PLAN_ACTIVATED,
        )
        self._publish(
            SettlementPlanActivated(plan.id, plan.group_id, member.user_id),
            "settlement.plan.activated",
        )
        plan._expired = False
        return plan

    @transaction.atomic
    def cancel_plan(self, plan_id, user_id):
        plan = SettlementPlanRepository.get(plan_id)
        if not plan:
            raise SettlementPlanNotFoundError()
        _, member = self._group_and_member(
            plan.group_id, user_id, require_owner_or_admin=True
        )
        ensure_plan_status(
            plan,
            [SettlementPlanStatusChoices.DRAFT, SettlementPlanStatusChoices.ACTIVE],
        )
        items = list(SettlementPlanItemRepository.list_by_plan(plan.id))
        for item in items:
            if item.status == SettlementPlanItemStatusChoices.PENDING:
                SettlementPlanItemRepository.mark_cancelled(item)
                SettlementPlanEventLogRepository.create(
                    settlement_plan_id=plan.id,
                    settlement_plan_item_id=item.id,
                    actor_user_id=member.user_id,
                    event_type=SettlementPlanEventTypeChoices.ITEM_CANCELLED,
                )
            elif (
                item.status == SettlementPlanItemStatusChoices.REPORTED
                and item.manual_settlement_id
            ):
                settlement = ManualSettlementRepository.get(item.manual_settlement_id)
                if (
                    settlement
                    and settlement.status
                    == ManualSettlementStatusChoices.PENDING_CONFIRMATION
                ):
                    ManualSettlementRepository.cancel(settlement, member.user_id)
                SettlementPlanItemRepository.mark_cancelled(item)
                SettlementPlanEventLogRepository.create(
                    settlement_plan_id=plan.id,
                    settlement_plan_item_id=item.id,
                    actor_user_id=member.user_id,
                    event_type=SettlementPlanEventTypeChoices.ITEM_CANCELLED,
                )
        SettlementPlanRepository.mark_cancelled(plan, member.user_id)
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.PLAN_CANCELLED,
        )
        self._publish(
            SettlementPlanCancelled(plan.id, plan.group_id, member.user_id),
            "settlement.plan.cancelled",
        )
        return plan

    @transaction.atomic
    def report_plan_item_paid(self, item_id, user_id, description=None):
        item = SettlementPlanItemRepository.get(item_id)
        if not item:
            raise InvalidPlanItemActionError()
        plan = SettlementPlanRepository.get(item.settlement_plan_id)
        if not plan:
            raise SettlementPlanNotFoundError()
        _, member = self._group_and_member(plan.group_id, user_id)
        ensure_plan_status(plan, [SettlementPlanStatusChoices.ACTIVE])
        ensure_plan_item_status(
            item,
            [
                SettlementPlanItemStatusChoices.PENDING,
                SettlementPlanItemStatusChoices.REJECTED,
            ],
        )
        ensure_plan_item_actor(item, user_id, "payer_user_id")
        settlement = ManualSettlementRepository.create_pending(
            group_id=plan.group_id,
            payer_user_id=item.payer_user_id,
            receiver_user_id=item.receiver_user_id,
            amount_minor=item.amount_minor,
            currency=item.currency,
            description=description,
            created_by_user_id=user_id,
        )
        SettlementPlanItemRepository.mark_reported(item, settlement.id)
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            settlement_plan_item_id=item.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.ITEM_REPORTED,
            metadata={"manual_settlement_id": str(settlement.id)},
        )
        self._publish(
            SettlementPlanItemReported(
                plan.id,
                item.id,
                plan.group_id,
                item.payer_user_id,
                item.receiver_user_id,
                item.amount_minor,
                settlement.id,
            ),
            "settlement.plan_item.reported",
        )
        return item, settlement

    @transaction.atomic
    def confirm_plan_item(self, item_id, user_id):
        item = SettlementPlanItemRepository.get(item_id)
        if not item:
            raise InvalidPlanItemActionError()
        plan = SettlementPlanRepository.get(item.settlement_plan_id)
        if not plan:
            raise SettlementPlanNotFoundError()
        _, member = self._group_and_member(plan.group_id, user_id)
        ensure_plan_item_status(item, [SettlementPlanItemStatusChoices.REPORTED])
        ensure_plan_item_actor(item, user_id, "receiver_user_id")
        settlement = ManualSettlementRepository.get(item.manual_settlement_id)
        if not settlement:
            raise InvalidPlanItemActionError()
        self.settlement_service.confirm_settlement(settlement.id, user_id)
        SettlementPlanItemRepository.mark_confirmed(item)
        self.balance_service.recalculate_group(plan.group_id, currency=plan.currency)
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            settlement_plan_item_id=item.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.ITEM_CONFIRMED,
        )
        self._publish(
            SettlementPlanItemConfirmed(
                plan.id,
                item.id,
                plan.group_id,
                item.payer_user_id,
                item.receiver_user_id,
                item.amount_minor,
            ),
            "settlement.plan_item.confirmed",
        )
        items = list(SettlementPlanItemRepository.list_by_plan(plan.id))
        if items and all(
            entry.status == SettlementPlanItemStatusChoices.CONFIRMED for entry in items
        ):
            SettlementPlanRepository.mark_completed(plan)
            SettlementPlanEventLogRepository.create(
                settlement_plan_id=plan.id,
                actor_user_id=member.user_id,
                event_type=SettlementPlanEventTypeChoices.PLAN_COMPLETED,
            )
            self._publish(
                SettlementPlanCompleted(plan.id, plan.group_id, plan.completed_at),
                "settlement.plan.completed",
            )
        return item, settlement

    @transaction.atomic
    def reject_plan_item(self, item_id, user_id, reason=None):
        item = SettlementPlanItemRepository.get(item_id)
        if not item:
            raise InvalidPlanItemActionError()
        plan = SettlementPlanRepository.get(item.settlement_plan_id)
        if not plan:
            raise SettlementPlanNotFoundError()
        _, member = self._group_and_member(plan.group_id, user_id)
        ensure_plan_item_status(item, [SettlementPlanItemStatusChoices.REPORTED])
        ensure_plan_item_actor(item, user_id, "receiver_user_id")
        settlement = ManualSettlementRepository.get(item.manual_settlement_id)
        if not settlement:
            raise InvalidPlanItemActionError()
        self.settlement_service.reject_settlement(settlement.id, user_id, reason=reason)
        SettlementPlanItemRepository.mark_rejected(item)
        SettlementPlanEventLogRepository.create(
            settlement_plan_id=plan.id,
            settlement_plan_item_id=item.id,
            actor_user_id=member.user_id,
            event_type=SettlementPlanEventTypeChoices.ITEM_REJECTED,
            metadata={"reason": reason} if reason else None,
        )
        self._publish(
            SettlementPlanItemRejected(
                plan.id,
                item.id,
                plan.group_id,
                item.payer_user_id,
                item.receiver_user_id,
                item.amount_minor,
            ),
            "settlement.plan_item.rejected",
        )
        return item, settlement
