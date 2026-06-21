"""API tests for notification-service endpoints."""

from types import SimpleNamespace

from django.test import override_settings
from rest_framework.test import APITestCase


class NotificationApiTests(APITestCase):
    @override_settings(DEBUG=True, APP_ENV="local", EMAIL_PROVIDER="fake")
    def test_test_sms_endpoint_works_in_local_debug(self):
        response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "email": "artist@example.com",
                "message": "Test message from HamDong",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sent")
        self.assertEqual(data["provider"], "fake")
        self.assertTrue(data["message_id"])

    @override_settings(DEBUG=False, APP_ENV="production", EMAIL_PROVIDER="fake")
    def test_test_sms_endpoint_is_blocked_in_production(self):
        response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "email": "artist@example.com",
                "message": "Test message from HamDong",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True, APP_ENV="local", EMAIL_PROVIDER="fake")
    def test_messages_endpoint_is_available_locally(self):
        test_response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "email": "artist@example.com",
                "message": "Test message from HamDong",
            },
            format="json",
        )
        self.assertEqual(test_response.status_code, 200)
    
        # messages endpoint is now protected by access token
        response_without_token = self.client.get("/api/v1/notifications/messages/")
        self.assertEqual(response_without_token.status_code, 401)
    
        self.client.force_authenticate(
            user=SimpleNamespace(
                is_authenticated=True,
                user_id="11111111-1111-1111-1111-111111111111",
                id="11111111-1111-1111-1111-111111111111",
            )
        )
    
        response = self.client.get("/api/v1/notifications/messages/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()) >= 1)
