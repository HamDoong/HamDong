"""Tests for OTP purpose-separated request/verify flows."""

from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.domain.models import User
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(
    DEBUG=True,
    OTP_LENGTH=6,
    OTP_TTL_SECONDS=120,
    OTP_DEBUG_RETURN_CODE=True,
    REDIS_HOST="fakeredis",
)
class OtpPurposeFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.otp_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/otp/request/"
        self.verify_url = "/api/v1/auth/otp/verify/"
        self.publisher = patch(
            "apps.identity.infrastructure.rabbitmq_publisher.RabbitMqPublisher.publish",
            return_value=True,
        )
        self.publisher.start()
        self.addCleanup(self.publisher.stop)

    def tearDown(self):
        self.otp_store.redis_client.flushdb()

    def test_login_request_for_existing_email(self):
        User.objects.create(email="existing@example.com", art_name="existing-user", is_active=True)
        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("debug_otp", response.json())
        self.assertIsNotNone(self.otp_store.get_otp_data("existing@example.com", "LOGIN"))

    def test_login_request_for_unregistered_email_returns_not_registered(self):
        response = self.client.post(
            self.request_url,
            {"email": "missing@example.com", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_NOT_REGISTERED")
        self.assertIsNone(self.otp_store.get_otp_data("missing@example.com", "LOGIN"))
        self.assertEqual(User.objects.filter(email="missing@example.com").count(), 0)

    def test_login_verify_does_not_create_new_user(self):
        self.otp_store.store_otp("missing@example.com", "123456", 120, "LOGIN")
        response = self.client.post(
            self.verify_url,
            {"email": "missing@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_NOT_REGISTERED")
        self.assertFalse(User.objects.filter(email="missing@example.com").exists())

    def test_signup_request_for_new_email(self):
        response = self.client.post(
            self.request_url,
            {"email": "new@example.com", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("debug_otp", response.json())
        self.assertIsNotNone(self.otp_store.get_otp_data("new@example.com", "SIGNUP"))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_signup_request_for_existing_email_returns_conflict(self):
        User.objects.create(email="existing@example.com", art_name="existing-user", is_active=True)
        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_ALREADY_REGISTERED")
        self.assertIsNone(self.otp_store.get_otp_data("existing@example.com", "SIGNUP"))

    def test_signup_verify_creates_user(self):
        self.otp_store.store_otp("new@example.com", "123456", 120, "SIGNUP")
        response = self.client.post(
            self.verify_url,
            {"email": "new@example.com", "code": "123456", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertIn("access_token", payload)
        self.assertTrue(User.objects.filter(email="new@example.com", is_email_verified=True).exists())

    def test_purposes_do_not_mix(self):
        self.otp_store.store_otp("new@example.com", "123456", 120, "SIGNUP")
        response = self.client.post(
            self.verify_url,
            {"email": "new@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "OTP_EXPIRED")
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

        User.objects.create(email="existing@example.com", art_name="existing-user", is_active=True)
        self.otp_store.store_otp("existing@example.com", "654321", 120, "LOGIN")
        response = self.client.post(
            self.verify_url,
            {"email": "existing@example.com", "code": "654321", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "OTP_EXPIRED")

    def test_deactivated_account_is_blocked(self):
        User.objects.create(email="disabled@example.com", art_name="disabled-user", is_active=False)
        login_request = self.client.post(
            self.request_url,
            {"email": "disabled@example.com", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(login_request.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(login_request.json()["error"]["code"], "ACCOUNT_DEACTIVATED")

        signup_request = self.client.post(
            self.request_url,
            {"email": "disabled@example.com", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(signup_request.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(signup_request.json()["error"]["code"], "ACCOUNT_DEACTIVATED")

        self.otp_store.store_otp("disabled@example.com", "123456", 120, "LOGIN")
        verify = self.client.post(
            self.verify_url,
            {"email": "disabled@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(verify.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(verify.json()["error"]["code"], "ACCOUNT_DEACTIVATED")

    def test_missing_and_invalid_purpose(self):
        missing_request = self.client.post(self.request_url, {"email": "user@example.com"}, format="json")
        self.assertEqual(missing_request.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_request.json()["error"]["code"], "INVALID_PURPOSE")

        invalid_request = self.client.post(
            self.request_url,
            {"email": "user@example.com", "purpose": "PASSWORD_RESET"},
            format="json",
        )
        self.assertEqual(invalid_request.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid_request.json()["error"]["code"], "INVALID_PURPOSE")

        missing_verify = self.client.post(
            self.verify_url,
            {"email": "user@example.com", "code": "123456"},
            format="json",
        )
        self.assertEqual(missing_verify.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing_verify.json()["error"]["code"], "INVALID_PURPOSE")

    def test_login_request_rate_limit_is_purpose_specific(self):
        User.objects.create(email="existing@example.com", art_name="existing-user", is_active=True)
        cooldown_patch = patch(
            "apps.identity.infrastructure.redis_otp_store.RedisOtpStore.is_in_cooldown",
            return_value=False,
        )
        set_cooldown_patch = patch(
            "apps.identity.infrastructure.redis_otp_store.RedisOtpStore.set_cooldown",
            return_value=None,
        )
        cooldown_patch.start()
        set_cooldown_patch.start()
        self.addCleanup(cooldown_patch.stop)
        self.addCleanup(set_cooldown_patch.stop)

        for _ in range(3):
            response = self.client.post(
                self.request_url,
                {"email": "existing@example.com", "purpose": "LOGIN"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.json()["error"]["code"], "OTP_RATE_LIMITED")

        signup = self.client.post(
            self.request_url,
            {"email": "other@example.com", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(signup.status_code, status.HTTP_200_OK)
