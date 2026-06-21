from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.settlements.application.reminder_service import ReminderService
from apps.settlements.domain.models import (
    DebtReminderRequest,
    DebtReminderSourceChoices,
    GroupReminderSettings,
    OutboxMessage,
    SettlementPlan,
    SettlementPlanItem,
    SettlementPlanItemStatusChoices,
    SettlementPlanStatusChoices,
)
from apps.settlements.tests.plan_test_helpers import (
    api_client,
    auth_user,
    create_group,
    create_member,
    create_user_projection,
)


@override_settings(
    DEFAULT_FIRST_REMINDER_AFTER_HOURS=24,
    DEFAULT_REMINDER_REPEAT_INTERVAL_HOURS=48,
    DEFAULT_MAXIMUM_REMINDERS=3,
    MINIMUM_REMINDER_INTERVAL_HOURS=1,
    MAXIMUM_REMINDER_INTERVAL_HOURS=720,
    MANUAL_REMINDER_COOLDOWN_MINUTES=30,
    REMINDER_SCHEDULER_BATCH_SIZE=100,
)
class SettlementReminderTests(TestCase):
    def setUp(self):
        self.owner = auth_user()
        self.admin = auth_user()
        self.member = auth_user()
        self.owner_profile = create_user_projection(
            identity_user_id=self.owner.sub,
            art_name="Owner",
            email="owner@example.com",
        )
        self.admin_profile = create_user_projection(
            identity_user_id=self.admin.sub,
            art_name="Admin",
            email="admin@example.com",
        )
        self.member_profile = create_user_projection(
            identity_user_id=self.member.sub,
            art_name="Member",
            email="member@example.com",
        )
        self.group = create_group(title="North Trip", owner_user_id=self.owner.sub)
        create_member(
            self.group.group_id,
            user_id=self.owner.sub,
            role="OWNER",
            email=self.owner_profile.email,
            art_name_snapshot=self.owner_profile.art_name,
        )
        create_member(
            self.group.group_id,
            user_id=self.admin.sub,
            role="ADMIN",
            email=self.admin_profile.email,
            art_name_snapshot=self.admin_profile.art_name,
        )
        create_member(
            self.group.group_id,
            user_id=self.member.sub,
            role="MEMBER",
            email=self.member_profile.email,
            art_name_snapshot=self.member_profile.art_name,
        )
        self.client = api_client(self.owner)
        self.service = ReminderService()
        self.plan = SettlementPlan.objects.create(
            group_id=self.group.group_id,
            currency="IRR",
            status=SettlementPlanStatusChoices.ACTIVE,
            generated_by_user_id=self.owner.sub,
            activated_by_user_id=self.owner.sub,
            activated_at=timezone.now() - timedelta(hours=26),
            source_balance_calculated_at=timezone.now() - timedelta(hours=26),
            total_debt_minor=250000,
            transaction_count=1,
        )
        self.item = SettlementPlanItem.objects.create(
            settlement_plan_id=self.plan.id,
            group_id=self.group.group_id,
            payer_user_id=self.member.sub,
            receiver_user_id=self.owner.sub,
            amount_minor=250000,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.PENDING,
            order_index=0,
        )

    def test_member_can_view_settings_and_get_defaults(self):
        response = api_client(self.member).get(
            reverse("group_reminder_settings", kwargs={"group_id": self.group.group_id})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["group_id"], str(self.group.group_id))
        self.assertTrue(response.data["is_enabled"])
        self.assertEqual(response.data["first_reminder_after_hours"], 24)
        self.assertEqual(GroupReminderSettings.objects.filter(group_id=self.group.group_id).count(), 1)

    def test_only_owner_or_admin_can_update_settings(self):
        payload = {
            "first_reminder_after_hours": 12,
            "repeat_interval_hours": 36,
            "maximum_reminders": 2,
            "send_in_app": True,
            "send_email": True,
        }

        owner_response = api_client(self.owner).patch(
            reverse("group_reminder_settings", kwargs={"group_id": self.group.group_id}),
            payload,
            format="json",
        )
        admin_response = api_client(self.admin).patch(
            reverse("group_reminder_settings", kwargs={"group_id": self.group.group_id}),
            {"maximum_reminders": 1},
            format="json",
        )
        member_response = api_client(self.member).patch(
            reverse("group_reminder_settings", kwargs={"group_id": self.group.group_id}),
            {"maximum_reminders": 1},
            format="json",
        )

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(admin_response.status_code, 200)
        self.assertEqual(member_response.status_code, 403)
        settings_obj = GroupReminderSettings.objects.get(group_id=self.group.group_id)
        self.assertEqual(settings_obj.maximum_reminders, 1)
        self.assertEqual(settings_obj.updated_by_user_id, self.admin.sub)

    def test_settings_validation_rejects_enabled_without_channel(self):
        response = self.client.patch(
            reverse("group_reminder_settings", kwargs={"group_id": self.group.group_id}),
            {"is_enabled": True, "send_in_app": False, "send_email": False},
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "REMINDER_SETTINGS_INVALID")

    def test_scheduler_creates_one_debt_reminder_and_outbox_message(self):
        result = self.service.process_scheduler_batch()

        self.assertEqual(result["created_count"], 1)
        reminder = DebtReminderRequest.objects.get()
        outbox = OutboxMessage.objects.get()
        self.assertEqual(reminder.source, DebtReminderSourceChoices.AUTOMATIC)
        self.assertEqual(reminder.status, "QUEUED")
        self.assertEqual(reminder.sequence_number, 1)
        self.assertEqual(outbox.event_type, "DebtReminderRequested")
        self.assertEqual(outbox.routing_key, "settlement.debt_reminder.requested")
        self.assertEqual(outbox.payload["event_type"], "DebtReminderRequested")
        self.assertEqual(outbox.payload["data"]["recipient_email"], self.member_profile.email)
        self.assertEqual(outbox.payload["data"]["amount_minor"], 250000)

    def test_scheduler_is_idempotent_within_same_window(self):
        first = self.service.process_scheduler_batch()
        second = self.service.process_scheduler_batch()

        self.assertEqual(first["created_count"], 1)
        self.assertEqual(second["created_count"], 0)
        self.assertEqual(DebtReminderRequest.objects.count(), 1)
        self.assertEqual(OutboxMessage.objects.count(), 1)

    def test_manual_item_reminder_creates_event_and_enforces_cooldown(self):
        with patch(
            "apps.settlements.application.reminder_service.timezone.now",
            return_value=timezone.now(),
        ):
            first_response = self.client.post(
                reverse("send_manual_item_reminder", kwargs={"item_id": self.item.id}),
                {"send_in_app": True, "send_email": False},
                format="json",
            )
            second_response = self.client.post(
                reverse("send_manual_item_reminder", kwargs={"item_id": self.item.id}),
                {"send_in_app": True, "send_email": False},
                format="json",
            )

        self.assertEqual(first_response.status_code, 202)
        self.assertEqual(second_response.status_code, 202)
        reminders = DebtReminderRequest.objects.filter(
            settlement_plan_item_id=self.item.id,
            source=DebtReminderSourceChoices.MANUAL_ITEM,
        )
        self.assertEqual(reminders.count(), 1)
        self.assertEqual(reminders.first().requested_by_user_id, self.owner.sub)
        self.assertEqual(reminders.first().channels, ["IN_APP"])
        self.assertEqual(
            OutboxMessage.objects.filter(event_type="DebtReminderRequested").count(),
            1,
        )

    def test_group_manual_run_only_processes_requested_group(self):
        other_group = create_group(title="South Trip", owner_user_id=self.owner.sub)
        create_member(other_group.group_id, user_id=self.owner.sub, role="OWNER", email=self.owner_profile.email)
        other_plan = SettlementPlan.objects.create(
            group_id=other_group.group_id,
            currency="IRR",
            status=SettlementPlanStatusChoices.ACTIVE,
            generated_by_user_id=self.owner.sub,
            activated_by_user_id=self.owner.sub,
            activated_at=timezone.now() - timedelta(hours=30),
            source_balance_calculated_at=timezone.now() - timedelta(hours=30),
            total_debt_minor=99999,
            transaction_count=1,
        )
        SettlementPlanItem.objects.create(
            settlement_plan_id=other_plan.id,
            group_id=other_group.group_id,
            payer_user_id=self.member.sub,
            receiver_user_id=self.owner.sub,
            amount_minor=99999,
            currency="IRR",
            status=SettlementPlanItemStatusChoices.PENDING,
            order_index=0,
        )

        response = self.client.post(
            reverse("run_group_reminders", kwargs={"group_id": self.group.group_id}),
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            DebtReminderRequest.objects.filter(group_id=self.group.group_id).count(),
            1,
        )
        self.assertEqual(
            DebtReminderRequest.objects.filter(group_id=other_group.group_id).count(),
            0,
        )
