"""Tests for RabbitMQ identity event publishing."""

from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.identity.application.use_cases import (
    RequestOtpUseCase,
    UpdateProfileUseCase,
    VerifyOtpUseCase,
)
from apps.identity.domain.models import *


@override_settings(DEBUG=True, OTP_DEBUG_RETURN_CODE=True)
class IdentityEventPublishingTestCase(TestCase):
    """Test identity event publishing from use cases."""

    def setUp(self):
        self.email = "09123456789"

    def tearDown(self):
        User.objects.all().delete()

    @patch(
        "apps.identity.application.use_cases.RabbitMqPublisher.publish",
        return_value=True,
    )
    @patch(
        "apps.identity.application.use_cases.OtpService.request_otp",
        return_value=(True, None, "123456", "123456"),
    )
    def test_user_otp_requested_event_published(self, request_otp_mock, publish_mock):
        use_case = RequestOtpUseCase()

        success, error_code, debug_otp, resend_after = use_case.execute(
            self.email
        )

        self.assertTrue(success)
        self.assertIsNone(error_code)
        self.assertEqual(debug_otp, "123456")
        self.assertEqual(resend_after, use_case.otp_service.resend_cooldown)
        publish_mock.assert_called_once()

        event_data, routing_key = publish_mock.call_args.args
        self.assertEqual(routing_key, "identity.otp.requested")
        self.assertEqual(event_data["event_type"], "SendOtpEmailRequested")
        self.assertEqual(event_data["data"]["email"], self.email)
        self.assertEqual(event_data["data"]["code"], "123456")
        self.assertEqual(event_data["data"]["expires_in"], use_case.otp_service.otp_ttl)

    @patch(
        "apps.identity.application.use_cases.RabbitMqPublisher.publish",
        return_value=True,
    )
    @patch(
        "apps.identity.application.use_cases.TokenService.generate_tokens",
        return_value=("access", "refresh", "jti"),
    )
    @patch("apps.identity.application.use_cases.UserService.update_last_login")
    @patch("apps.identity.application.use_cases.UserService.mark_phone_verified")
    @patch("apps.identity.application.use_cases.UserService.get_or_create")
    @patch(
        "apps.identity.application.use_cases.OtpService.verify_otp",
        return_value=(True, None),
    )
    def test_user_created_and_logged_in_events_published_for_new_user(
        self,
        verify_otp_mock,
        get_or_create_mock,
        mark_verified_mock,
        update_login_mock,
        token_generate_mock,
        publish_mock,
    ):
        user = User.objects.create(email=self.email)
        get_or_create_mock.return_value = (user, True)
        mark_verified_mock.return_value = user
        update_login_mock.return_value = user

        use_case = VerifyOtpUseCase()
        success, error_code, token_data = use_case.execute(
            self.email,
            "123456",
            user_agent="pytest",
            ip_address="127.0.0.1",
        )

        self.assertTrue(success)
        self.assertIsNone(error_code)
        self.assertEqual(token_data["access_token"], "access")
        self.assertEqual(publish_mock.call_count, 2)

        routing_keys = [call.args[1] for call in publish_mock.call_args_list]
        event_types = [
            call.args[0]["event_type"] for call in publish_mock.call_args_list
        ]

        self.assertIn("identity.user.created", routing_keys)
        self.assertIn("identity.user.logged_in", routing_keys)
        self.assertIn("UserCreated", event_types)
        self.assertIn("UserLoggedIn", event_types)

    @patch(
        "apps.identity.application.use_cases.RabbitMqPublisher.publish",
        return_value=True,
    )
    @patch("apps.identity.application.use_cases.UserService.update_profile")
    def test_user_updated_event_published_on_profile_update(
        self, update_profile_mock, publish_mock
    ):
        user = User.objects.create(
            email=self.email, art_name="Old Name"
        )
        user.art_name = "New Name"
        update_profile_mock.return_value = user

        use_case = UpdateProfileUseCase()
        success, updated_user = use_case.execute(user, art_name="New Name")

        self.assertTrue(success)
        self.assertEqual(updated_user.art_name, "New Name")
        publish_mock.assert_called_once()

        event_data, routing_key = publish_mock.call_args.args
        self.assertEqual(routing_key, "identity.user.updated")
        self.assertEqual(event_data["event_type"], "UserUpdated")
        self.assertEqual(event_data["data"]["email"], self.email)

    @patch(
        "apps.identity.application.use_cases.RabbitMqPublisher.publish",
        return_value=False,
    )
    @patch(
        "apps.identity.application.use_cases.OtpService.request_otp",
        return_value=(True, None, None),
    )
    def test_rabbitmq_unavailable_does_not_break_otp_request(
        self, request_otp_mock, publish_mock
    ):
        use_case = RequestOtpUseCase()

        success, error_code, debug_otp, resend_after = use_case.execute(
            self.email
        )

        self.assertTrue(success)
        self.assertIsNone(error_code)
        self.assertIsNone(debug_otp)
        self.assertIsNotNone(resend_after)
        publish_mock.assert_called_once()
