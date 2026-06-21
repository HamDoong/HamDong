from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APITestCase

from apps.notifications.domain.models import (
    NotificationChannelChoices,
    NotificationMessage,
    NotificationMessageTypeChoices,
    NotificationPriorityChoices,
    NotificationStatusChoices,
)
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication
from apps.notifications.infrastructure.repositories import NotificationRepository


def auth_user(user_id: str, role: str = "USER"):
    return SimpleNamespace(
        is_authenticated=True,
        id=user_id,
        sub=user_id,
        role=role,
        email=f"{user_id}@example.com",
    )


@override_settings(DEBUG=True, APP_ENV="local", EMAIL_PROVIDER="fake")
class NotificationReadStatusApiTests(APITestCase):
    user1_id = "11111111-1111-1111-1111-111111111111"
    user2_id = "22222222-2222-2222-2222-222222222222"

    def setUp(self):
        self.user1 = auth_user(self.user1_id)
        self.user2 = auth_user(self.user2_id)

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_notification(self, *, user_id=None, is_read=False, priority=NotificationPriorityChoices.NORMAL, notification_type=NotificationMessageTypeChoices.REMINDER, is_deleted=False, channel=NotificationChannelChoices.IN_APP):
        notification = NotificationMessage.objects.create(
            recipient_user_id=user_id or self.user1_id,
            recipient_email=f"{user_id or self.user1_id}@example.com",
            recipient=str(user_id or self.user1_id),
            recipient_masked="masked@example.com",
            channel=channel,
            message_type=notification_type,
            title="Payment reminder",
            body="Please settle your share.",
            metadata={"safe": True},
            priority=priority,
            is_read=is_read,
            read_at=timezone.now() if is_read else None,
            status=NotificationStatusChoices.SENT,
            is_deleted=is_deleted,
        )
        return notification

    def test_list_returns_only_current_user_notifications(self):
        self.create_notification(user_id=self.user1_id)
        self.create_notification(user_id=self.user2_id)

        self.authenticate(self.user1)
        response = self.client.get("/api/v1/notifications/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["recipient_user_id"], self.user1_id)

    def test_list_supports_filters_and_limit(self):
        first = self.create_notification(is_read=False, priority=NotificationPriorityChoices.HIGH)
        second = self.create_notification(is_read=True, priority=NotificationPriorityChoices.HIGH)
        self.create_notification(is_read=False, priority=NotificationPriorityChoices.NORMAL)
        self.authenticate(self.user1)

        response = self.client.get("/api/v1/notifications/?is_read=false&priority=HIGH&notification_type=REMINDER&limit=5")

        self.assertEqual(response.status_code, 200)
        items = response.json()["results"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], str(first.id))
        self.assertNotEqual(items[0]["id"], str(second.id))

    def test_list_rejects_invalid_filters(self):
        self.authenticate(self.user1)

        invalid_bool = self.client.get("/api/v1/notifications/?is_read=notabool")
        self.assertEqual(invalid_bool.status_code, 400)

        invalid_priority = self.client.get("/api/v1/notifications/?priority=BAD")
        self.assertEqual(invalid_priority.status_code, 400)

        invalid_type = self.client.get("/api/v1/notifications/?notification_type=BAD")
        self.assertEqual(invalid_type.status_code, 400)

        invalid_limit = self.client.get("/api/v1/notifications/?limit=-1")
        self.assertEqual(invalid_limit.status_code, 400)

    def test_list_cursor_pagination_is_stable(self):
        notifications = [self.create_notification() for _ in range(3)]
        created_at = timezone.now()
        NotificationMessage.objects.all().update(created_at=created_at)
        self.authenticate(self.user1)

        first_page = self.client.get("/api/v1/notifications/?page_size=2")
        self.assertEqual(first_page.status_code, 200)
        first_results = first_page.json()["results"]
        next_cursor = first_page.json()["next_cursor"]
        self.assertEqual(len(first_results), 2)
        self.assertTrue(next_cursor)

        second_page = self.client.get(f"/api/v1/notifications/?page_size=2&cursor={next_cursor}")
        self.assertEqual(second_page.status_code, 200)
        second_results = second_page.json()["results"]
        self.assertEqual(len(second_results), 1)

        first_ids = {item["id"] for item in first_results}
        second_ids = {item["id"] for item in second_results}
        self.assertTrue(first_ids.isdisjoint(second_ids))
        self.assertEqual(first_ids | second_ids, {str(item.id) for item in notifications})

    def test_unread_count_is_user_scoped_and_priority_aware(self):
        self.create_notification(user_id=self.user1_id, is_read=False, priority=NotificationPriorityChoices.NORMAL)
        self.create_notification(user_id=self.user1_id, is_read=False, priority=NotificationPriorityChoices.HIGH)
        self.create_notification(user_id=self.user1_id, is_read=True, priority=NotificationPriorityChoices.URGENT)
        self.create_notification(user_id=self.user1_id, is_read=False, priority=NotificationPriorityChoices.URGENT, is_deleted=True)
        self.create_notification(user_id=self.user2_id, is_read=False, priority=NotificationPriorityChoices.URGENT)

        self.authenticate(self.user1)
        response = self.client.get("/api/v1/notifications/unread-count/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"unread_count": 2, "important_unread_count": 1})

    def test_mark_one_read_is_idempotent_and_user_scoped(self):
        notification = self.create_notification(is_read=False)
        other = self.create_notification(user_id=self.user2_id, is_read=False)

        self.authenticate(self.user1)
        first = self.client.post(f"/api/v1/notifications/{notification.id}/read/", {}, format="json")
        self.assertEqual(first.status_code, 200)
        first_read_at = first.json()["read_at"]
        self.assertTrue(first.json()["is_read"])

        second = self.client.post(f"/api/v1/notifications/{notification.id}/read/", {}, format="json")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["read_at"], first_read_at)

        forbidden = self.client.post(f"/api/v1/notifications/{other.id}/read/", {}, format="json")
        self.assertEqual(forbidden.status_code, 404)

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(notification.read_at.isoformat().replace("+00:00", "Z"), first_read_at.replace("+00:00", "Z"))

    def test_mark_all_read_updates_only_current_users_unread_notifications(self):
        unread_one = self.create_notification(is_read=False)
        unread_two = self.create_notification(is_read=False)
        already_read = self.create_notification(is_read=True)
        other_user = self.create_notification(user_id=self.user2_id, is_read=False)
        original_read_at = already_read.read_at

        self.authenticate(self.user1)
        response = self.client.post("/api/v1/notifications/read-all/", {}, format="json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["updated_count"], 2)

        unread_one.refresh_from_db()
        unread_two.refresh_from_db()
        already_read.refresh_from_db()
        other_user.refresh_from_db()

        self.assertTrue(unread_one.is_read)
        self.assertTrue(unread_two.is_read)
        self.assertEqual(unread_one.read_at, unread_two.read_at)
        self.assertEqual(already_read.read_at, original_read_at)
        self.assertFalse(other_user.is_read)

        repeat = self.client.post("/api/v1/notifications/read-all/", {}, format="json")
        self.assertEqual(repeat.status_code, 200)
        self.assertEqual(repeat.json()["updated_count"], 0)

    def test_response_does_not_expose_sensitive_internal_fields(self):
        self.create_notification(is_read=False)
        self.authenticate(self.user1)

        response = self.client.get("/api/v1/notifications/")
        item = response.json()["results"][0]

        self.assertIn("priority", item)
        self.assertIn("is_read", item)
        self.assertIn("read_at", item)
        self.assertNotIn("provider", item)
        self.assertNotIn("provider_message_id", item)
        self.assertNotIn("error_message", item)
        self.assertNotIn("last_error", item)

    def test_missing_token_returns_401(self):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 401)

    @patch.object(
        JWTAuthentication,
        "authenticate",
        side_effect=AuthenticationFailed({"code": "INVALID_TOKEN", "message": "The provided token is invalid."}),
    )
    def test_invalid_token_returns_401(self, _mock_auth):
        response = self.client.get("/api/v1/notifications/")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "INVALID_TOKEN")


@override_settings(DEBUG=True, APP_ENV="local", EMAIL_PROVIDER="fake")
class NotificationReadStatusRepositoryTests(TransactionTestCase):
    reset_sequences = True

    def test_repository_applies_default_priority_and_unread_state(self):
        notification = NotificationRepository.create_notification_message(
            recipient_user_id=uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            recipient_email="artist@example.com",
            recipient="artist@example.com",
            recipient_masked="ar***@e***.com",
            channel=NotificationChannelChoices.IN_APP,
            message_type=NotificationMessageTypeChoices.REMINDER,
            title="Reminder",
            body="Pay please",
            metadata={},
            status=NotificationStatusChoices.PENDING,
        )

        self.assertEqual(notification.priority, NotificationPriorityChoices.HIGH)
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_mark_read_is_idempotent(self):
        notification = NotificationMessage.objects.create(
            recipient_user_id=uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            recipient_email="artist@example.com",
            recipient="artist@example.com",
            recipient_masked="ar***@e***.com",
            channel=NotificationChannelChoices.IN_APP,
            message_type=NotificationMessageTypeChoices.INVITE,
            title="Invite",
            body="Join us",
            metadata={},
            priority=NotificationPriorityChoices.NORMAL,
            status=NotificationStatusChoices.PENDING,
        )

        first = NotificationRepository.mark_read_for_user(notification.id, notification.recipient_user_id)
        second = NotificationRepository.mark_read_for_user(notification.id, notification.recipient_user_id)

        self.assertTrue(first.is_read)
        self.assertIsNotNone(first.read_at)
        self.assertEqual(first.read_at, second.read_at)
