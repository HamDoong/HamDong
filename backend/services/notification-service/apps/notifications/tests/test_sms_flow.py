"""Tests for OTP SMS delivery flow and persistence."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.notifications.application.sms_service import SmsService
from apps.notifications.domain.models import (
    NotificationMessage,
    NotificationStatusChoices,
    ProviderDeliveryLog,
)
from apps.notifications.infrastructure.providers.base import SmsProviderError


class FailingProvider:
    provider_name = "fake"

    def send_sms(self, phone_number: str, message: str):
        raise SmsProviderError("SMS_PROVIDER_FAILED", "Provider failure")

    def send_otp(self, phone_number: str, code: str, expires_in: int):
        raise SmsProviderError("SMS_PROVIDER_FAILED", "Provider failure")


class SmsFlowTests(TestCase):
    def setUp(self):
        from apps.notifications.infrastructure import circuit_breakers

        circuit_breakers._SMS_BREAKER = None

    def tearDown(self):
        NotificationMessage.objects.all().delete()
        ProviderDeliveryLog.objects.all().delete()
        from apps.notifications.infrastructure import circuit_breakers

        circuit_breakers._SMS_BREAKER = None

    @override_settings(SMS_PROVIDER="fake")
    def test_otp_message_is_consumed_and_notification_created(self):
        service = SmsService()
        payload = {
            "event_id": "event-1",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        notification_message = service.handle_otp_command(payload)

        self.assertEqual(notification_message.status, NotificationStatusChoices.SENT)
        self.assertEqual(notification_message.recipient_masked, "0912***6789")
        self.assertEqual(NotificationMessage.objects.count(), 1)
        self.assertEqual(ProviderDeliveryLog.objects.count(), 1)

        log = ProviderDeliveryLog.objects.first()
        self.assertEqual(log.request_payload_masked["phone_number"], "0912***6789")
        self.assertEqual(log.request_payload_masked["code"], "******")
        self.assertNotIn("123456", json.dumps(log.request_payload_masked))
        self.assertNotIn("123456", json.dumps(log.response_payload))

    @override_settings(SMS_PROVIDER="fake", SMS_OTP_MAX_RETRIES=0)
    @patch("apps.notifications.application.sms_service.get_sms_provider")
    def test_notification_message_failed_on_provider_failure(self, provider_mock):
        service = SmsService()
        provider_mock.return_value = FailingProvider()
        payload = {
            "event_id": "event-2",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        notification_message = service.handle_otp_command(payload)

        self.assertEqual(notification_message.status, NotificationStatusChoices.FAILED)
        self.assertEqual(notification_message.error_code, "SMS_PROVIDER_FAILED")
        self.assertEqual(ProviderDeliveryLog.objects.count(), 1)

    @override_settings(
        SMS_PROVIDER="fake",
        SMS_CIRCUIT_FAIL_MAX=1,
        SMS_OTP_MAX_RETRIES=1,
        SMS_OTP_RETRY_DELAYS_SECONDS="0",
    )
    @patch("apps.notifications.application.sms_service.time.sleep", return_value=None)
    @patch("apps.notifications.application.sms_service.get_sms_provider")
    def test_circuit_breaker_opens_after_repeated_provider_failures(
        self, provider_mock, sleep_mock
    ):
        service = SmsService()
        provider_mock.return_value = FailingProvider()
        from apps.notifications.infrastructure import circuit_breakers

        circuit_breakers._SMS_BREAKER = None

        payload = {
            "event_id": "event-3",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        notification_message = service.handle_otp_command(payload)

        self.assertEqual(notification_message.status, NotificationStatusChoices.FAILED)
        self.assertEqual(notification_message.error_code, "SMS_CIRCUIT_OPEN")
        self.assertGreaterEqual(ProviderDeliveryLog.objects.count(), 1)

    @override_settings(SMS_PROVIDER="fake")
    def test_expired_message_becomes_skipped(self):
        service = SmsService()
        payload = {
            "event_id": "event-4",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": (
                datetime.now(timezone.utc) - timedelta(minutes=10)
            ).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "123456",
                "purpose": "login",
                "expires_in": 1,
            },
        }

        notification_message = service.handle_otp_command(payload)

        self.assertEqual(notification_message.status, NotificationStatusChoices.SKIPPED)
        self.assertEqual(notification_message.error_code, "OTP_EXPIRED")
        self.assertEqual(ProviderDeliveryLog.objects.count(), 1)

    @override_settings(SMS_PROVIDER="fake")
    def test_raw_otp_is_not_stored_and_phone_is_masked(self):
        service = SmsService()
        payload = {
            "event_id": "event-5",
            "event_type": "SendOtpSmsRequested",
            "occurred_at": datetime.now(timezone.utc).isoformat(),
            "version": 1,
            "data": {
                "phone_number": "09123456789",
                "code": "654321",
                "purpose": "login",
                "expires_in": 120,
            },
        }

        notification_message = service.handle_otp_command(payload)
        log = ProviderDeliveryLog.objects.first()

        self.assertEqual(notification_message.recipient_masked, "0912***6789")
        self.assertNotIn(
            "654321", json.dumps(notification_message.__dict__, default=str)
        )
        self.assertEqual(log.request_payload_masked["phone_number"], "0912***6789")
        self.assertNotIn("654321", json.dumps(log.request_payload_masked))
