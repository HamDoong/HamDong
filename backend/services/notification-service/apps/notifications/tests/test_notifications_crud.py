from types import SimpleNamespace
from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APITestCase

from apps.notifications.domain.models import NotificationMessage, NotificationStatusChoices
from apps.notifications.infrastructure.jwt_authentication import JWTAuthentication


def fake_authenticate(self, request):
    return (
        SimpleNamespace(
            is_authenticated=True,
            id="11111111-1111-1111-1111-111111111111",
            sub="11111111-1111-1111-1111-111111111111",
            role="USER",
        ),
        None,
    )


class NotificationCrudTests(APITestCase):
    @override_settings(DEBUG=True, APP_ENV="local", SMS_PROVIDER="fake")
    @patch.object(JWTAuthentication, "authenticate", fake_authenticate)
    def test_notification_crud_flow(self):
        create = self.client.post(
            "/api/v1/notifications/",
            {
                "recipient_user_id": "11111111-1111-1111-1111-111111111111",
                "channel": "IN_APP",
                "notification_type": "CUSTOM",
                "title": "یادآوری پرداخت",
                "body": "لطفاً سهم شام جمعه را تسویه کن.",
                "metadata": {"group_id": "22222222-2222-2222-2222-222222222222", "amount_minor": 300000},
            },
            format="json",
        )
        self.assertEqual(create.status_code, 201)
        notification_id = create.json()["id"]

        listing = self.client.get("/api/v1/notifications/")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["results"][0]["body"], "لطفاً سهم شام جمعه را تسویه کن.")

        detail = self.client.get(f"/api/v1/notifications/{notification_id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["metadata"]["amount_minor"], 300000)

        patch_response = self.client.patch(
            f"/api/v1/notifications/{notification_id}/",
            {"title": "یادآوری دوستانه", "body": "لطفاً هر وقت فرصت داشتی سهمت را پرداخت کن."},
            format="json",
        )
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()["title"], "یادآوری دوستانه")

        notification = NotificationMessage.objects.get(id=notification_id)
        notification.status = NotificationStatusChoices.SENT
        notification.save(update_fields=["status"])

        sent_patch = self.client.patch(f"/api/v1/notifications/{notification_id}/", {"title": "x"}, format="json")
        self.assertEqual(sent_patch.status_code, 409)

        notification.status = NotificationStatusChoices.PENDING
        notification.save(update_fields=["status"])
        delete_response = self.client.delete(f"/api/v1/notifications/{notification_id}/")
        self.assertEqual(delete_response.status_code, 200)

        listing_after = self.client.get("/api/v1/notifications/")
        self.assertEqual(listing_after.status_code, 200)
        self.assertEqual(listing_after.json()["results"], [])

        detail_after = self.client.get(f"/api/v1/notifications/{notification_id}/")
        self.assertEqual(detail_after.status_code, 404)
