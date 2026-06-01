from datetime import datetime, timezone

from django.test import TestCase, override_settings

from apps.settlements.domain.models import (
    GroupMemberProjection,
    GroupProjection,
    OutboxMessage,
    ReminderDispatchLog,
    SettlementPlan,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
    UserProjection,
)
from apps.settlements.infrastructure.reminder_scheduler import SettlementReminderScheduler


class SettlementReminderSchedulerTests(TestCase):
    @override_settings(REMINDER_ENABLED=True, REMINDER_MIN_INTERVAL_HOURS=24)
    def test_scheduler_creates_outbox_message_for_pending_plan_item(self):
        owner = UserProjection.objects.create(
            identity_user_id="00000000-0000-0000-0000-000000000001",
            phone_number="09120000001",
            display_name="Owner",
        )
        payer = UserProjection.objects.create(
            identity_user_id="00000000-0000-0000-0000-000000000002",
            phone_number="09120000002",
            display_name="Payer",
        )
        group = GroupProjection.objects.create(
            group_id="00000000-0000-0000-0000-000000000010",
            title="Trip to Shiraz",
            created_by_user_id=owner.identity_user_id,
        )
        GroupMemberProjection.objects.create(
            group_id=group.group_id,
            user_id=payer.identity_user_id,
            phone_number=payer.phone_number,
            display_name_snapshot=payer.display_name,
        )
        plan = SettlementPlan.objects.create(
            group_id=group.group_id,
            currency="IRR",
            status=SettlementPlanStatusChoices.ACTIVE,
            generated_by_user_id=owner.identity_user_id,
            source_balance_calculated_at=datetime(2026, 5, 31, 0, 0, tzinfo=timezone.utc),
            total_debt_minor=50000,
            transaction_count=1,
        )
        SettlementPlanItem.objects.create(
            settlement_plan_id=plan.id,
            group_id=group.group_id,
            payer_user_id=payer.identity_user_id,
            receiver_user_id=owner.identity_user_id,
            amount_minor=50000,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.PENDING,
            order_index=0,
        )

        queued = SettlementReminderScheduler().run()

        self.assertEqual(len(queued), 1)
        self.assertEqual(OutboxMessage.objects.count(), 1)
        self.assertEqual(ReminderDispatchLog.objects.count(), 1)
        outbox = OutboxMessage.objects.first()
        self.assertEqual(outbox.event_type, "PAYMENT_REMINDER")
        self.assertEqual(outbox.routing_key, "settlement.reminder.requested")
        self.assertEqual(outbox.payload["event_type"], "PAYMENT_REMINDER")
        self.assertEqual(outbox.payload["data"]["recipient_phone_number"], payer.phone_number)
