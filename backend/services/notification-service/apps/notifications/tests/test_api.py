"""API tests for notification-service endpoints."""

from django.test import TestCase, override_settings


class NotificationApiTests(TestCase):
    @override_settings(DEBUG=True, APP_ENV="local", SMS_PROVIDER="fake")
    def test_test_sms_endpoint_works_in_local_debug(self):
        response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "phone_number": "09123456789",
                "message": "Test message from HamDong",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "sent")
        self.assertEqual(data["provider"], "fake")
        self.assertTrue(data["message_id"])

    @override_settings(DEBUG=False, APP_ENV="production", SMS_PROVIDER="fake")
    def test_test_sms_endpoint_is_blocked_in_production(self):
        response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "phone_number": "09123456789",
                "message": "Test message from HamDong",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True, APP_ENV="local", SMS_PROVIDER="fake")
    def test_messages_endpoint_is_available_locally(self):
        test_response = self.client.post(
            "/api/v1/notifications/sms/test/",
            {
                "phone_number": "09123456789",
                "message": "Test message from HamDong",
            },
            format="json",
        )
        self.assertEqual(test_response.status_code, 200)

        response = self.client.get("/api/v1/notifications/messages/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.json()) >= 1)
