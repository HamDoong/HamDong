from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.settlements.domain.models import (
    GroupBalanceSnapshot,
    GroupMemberStatusChoices,
    ManualSettlement,
    ManualSettlementStatusChoices,
    ReminderDispatchTypeChoices,
    SettlementPlan,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.infrastructure.event_envelope import build_event_envelope
from apps.settlements.infrastructure.repositories import (
    GroupMemberProjectionRepository,
    GroupProjectionRepository,
    OutboxRepository,
    ReminderDispatchRepository,
)


class SettlementReminderScheduler:
    def __init__(self):
        self.enabled = settings.REMINDER_ENABLED
        self.min_interval = timedelta(hours=settings.REMINDER_MIN_INTERVAL_HOURS)
        self.exchange = settings.SETTLEMENT_REMINDER_EXCHANGE
        self.payment_min_amount_minor = int(settings.PAYMENT_REMINDER_MIN_AMOUNT_MINOR)
        self.pending_settlement_after = timedelta(hours=settings.PENDING_SETTLEMENT_REMINDER_AFTER_HOURS)
        self.plan_item_after = timedelta(hours=settings.PLAN_ITEM_REMINDER_AFTER_HOURS)

    def _group(self, group_id):
        return GroupProjectionRepository.get(group_id)

    def _member(self, group_id, user_id):
        return GroupMemberProjectionRepository.get(group_id, user_id)

    def _eligible(self, reminder_type, group_id, target_user_id):
        existing = ReminderDispatchRepository.eligible(reminder_type, group_id, target_user_id)
        return not existing or not existing.next_allowed_at or existing.next_allowed_at <= timezone.now()

    def _record_and_queue(self, *, reminder_type, group_id, target_user_id, reference_id, routing_key, event_type, data):
        if not self._eligible(reminder_type, group_id, target_user_id):
            return None
        now = timezone.now()
        with transaction.atomic():
            envelope = build_event_envelope(
                event_type,
                data,
                source_service="settlement-service",
                routing_key=routing_key,
                correlation_id=str(uuid4()),
                causation_id=str(reference_id or uuid4()),
            )
            log = ReminderDispatchRepository.upsert_target(
                reminder_type=reminder_type,
                group_id=group_id,
                settlement_plan_id=data.get("plan_id"),
                settlement_plan_item_id=data.get("item_id"),
                manual_settlement_id=data.get("settlement_id"),
                recipient_user_id=target_user_id,
                recipient_phone_number=data.get("target_phone_number") or data.get("receiver_phone_number") or data.get("payer_phone_number", ""),
                source_event_id=envelope["event_id"],
                next_allowed_at=now + self.min_interval,
                last_sent_at=now,
                sent_count=1,
                metadata=data,
            )
            outbox = OutboxRepository.create(
                aggregate_type="ReminderDispatch",
                aggregate_id=reference_id,
                event_type=event_type,
                routing_key=routing_key,
                exchange=self.exchange,
                payload=envelope,
                source_service="settlement-service",
                correlation_id=envelope["correlation_id"],
                causation_id=envelope["causation_id"],
            )
            return log, outbox

    def enqueue_payment_reminders(self):
        if not self.enabled:
            return []
        queued = []
        for balance in GroupBalanceSnapshot.objects.filter(net_balance_minor__lt=0):
            if abs(int(balance.net_balance_minor)) < self.payment_min_amount_minor:
                continue
            group = self._group(balance.group_id)
            if not group or group.status == "ARCHIVED":
                continue
            member = self._member(balance.group_id, balance.user_id)
            if not member or member.status != GroupMemberStatusChoices.ACTIVE:
                continue
            result = self._record_and_queue(
                reminder_type=ReminderDispatchTypeChoices.PAYMENT_REMINDER,
                group_id=balance.group_id,
                target_user_id=balance.user_id,
                reference_id=balance.id,
                routing_key="settlement.payment_reminder.requested",
                event_type="PaymentReminderRequested",
                data={
                    "group_id": str(balance.group_id),
                    "target_user_id": str(balance.user_id),
                    "target_phone_number": member.phone_number,
                    "target_display_name": member.display_name_snapshot or member.phone_number,
                    "amount_minor": abs(int(balance.net_balance_minor)),
                    "currency": balance.currency,
                    "reason": "NEGATIVE_BALANCE",
                    "message_context": {"group_title": group.title},
                },
            )
            if result:
                queued.append(result)
        return queued

    def enqueue_confirmation_reminders(self):
        if not self.enabled:
            return []
        queued = []
        threshold = timezone.now() - self.pending_settlement_after
        settlements = ManualSettlement.objects.filter(status=ManualSettlementStatusChoices.PENDING_CONFIRMATION, created_at__lte=threshold)
        for settlement in settlements:
            group = self._group(settlement.group_id)
            if not group or group.status == "ARCHIVED" or int(settlement.amount_minor) <= 0:
                continue
            member = self._member(settlement.group_id, settlement.receiver_user_id)
            payer_member = self._member(settlement.group_id, settlement.payer_user_id)
            if not member or member.status != GroupMemberStatusChoices.ACTIVE:
                continue
            result = self._record_and_queue(
                reminder_type=ReminderDispatchTypeChoices.SETTLEMENT_CONFIRMATION_REMINDER,
                group_id=settlement.group_id,
                target_user_id=settlement.receiver_user_id,
                reference_id=settlement.id,
                routing_key="settlement.confirmation_reminder.requested",
                event_type="SettlementConfirmationReminderRequested",
                data={
                    "settlement_id": str(settlement.id),
                    "group_id": str(settlement.group_id),
                    "receiver_user_id": str(settlement.receiver_user_id),
                    "receiver_phone_number": member.phone_number,
                    "payer_display_name": (payer_member.display_name_snapshot if payer_member else str(settlement.payer_user_id)),
                    "amount_minor": int(settlement.amount_minor),
                    "currency": settlement.currency,
                },
            )
            if result:
                queued.append(result)
        return queued

    def enqueue_plan_item_reminders(self):
        if not self.enabled:
            return []
        queued = []
        threshold = timezone.now() - self.plan_item_after
        plans = SettlementPlan.objects.filter(status=SettlementPlanStatusChoices.ACTIVE)
        for plan in plans:
            group = self._group(plan.group_id)
            if not group or group.status == "ARCHIVED":
                continue
            items = SettlementPlanItem.objects.filter(settlement_plan_id=plan.id, status=SettlementPlanItemStatusChoices.PENDING, created_at__lte=threshold)
            for item in items:
                if int(item.amount_minor) <= 0:
                    continue
                member = self._member(plan.group_id, item.payer_user_id)
                receiver = self._member(plan.group_id, item.receiver_user_id)
                if not member or member.status != GroupMemberStatusChoices.ACTIVE:
                    continue
                result = self._record_and_queue(
                    reminder_type=ReminderDispatchTypeChoices.SETTLEMENT_PLAN_ITEM_REMINDER,
                    group_id=plan.group_id,
                    target_user_id=item.payer_user_id,
                    reference_id=item.id,
                    routing_key="settlement.plan_item_reminder.requested",
                    event_type="SettlementPlanItemReminderRequested",
                    data={
                        "plan_id": str(plan.id),
                        "item_id": str(item.id),
                        "group_id": str(plan.group_id),
                        "payer_user_id": str(item.payer_user_id),
                        "payer_phone_number": member.phone_number,
                        "receiver_display_name": receiver.display_name_snapshot if receiver else str(item.receiver_user_id),
                        "amount_minor": int(item.amount_minor),
                        "currency": item.currency,
                        "message_context": {"group_title": group.title},
                    },
                )
                if result:
                    queued.append(result)
        return queued

    def run(self):
        queued = []
        queued.extend(self.enqueue_payment_reminders())
        queued.extend(self.enqueue_confirmation_reminders())
        queued.extend(self.enqueue_plan_item_reminders())
        return queued
