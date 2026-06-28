"""Tests for OTP flow and purpose validation."""

from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.domain.models import OutboxMessage, User
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(
    OTP_LENGTH=6,
    OTP_TTL_SECONDS=120,
    OTP_DEBUG_RETURN_CODE=True,
    OTP_RESEND_COOLDOWN_SECONDS=60,
    OTP_MAX_VERIFY_ATTEMPTS=5,
    OTP_MAX_REQUESTS_PER_WINDOW=3,
    OTP_RATE_LIMIT_WINDOW_SECONDS=3600,
    DEBUG=True,
    REDIS_HOST="fakeredis",
)
class OtpRequestTestCase(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.otp_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/otp/request/"
        self.verify_url = "/api/v1/auth/otp/verify/"

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()
        RedisOtpStore._shared_client = None

    def _assert_no_otp_side_effects(self, email: str):
        keys = self.otp_store.redis_client.keys(f"*{email}*")
        self.assertEqual(keys, [])

    def _assert_no_otp_event(self, email: str):
        self.assertFalse(
            OutboxMessage.objects.filter(
                event_type="SendOtpEmailRequested",
                payload__data__email=email,
            ).exists()
        )

    @staticmethod
    def _create_completed_user(email: str, **kwargs) -> User:
        user = User.objects.create(email=email, **kwargs)
        user.set_password("StrongPass123!")
        user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        return user

    def test_request_otp_with_valid_login_purpose_for_existing_user(self):
        self._create_completed_user(email="artist@example.com")

        response = self.client.post(
            self.request_url,
            {"email": "artist@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["message"], "OTP has been requested successfully.")
        self.assertEqual(data["expires_in"], 120)
        self.assertEqual(data["resend_after"], 60)
        self.assertIn("debug_otp", data)
        self.assertTrue(data["debug_otp"].isdigit())
        self.assertIsNotNone(self.otp_store.get_otp_data("artist@example.com", "LOGIN"))

    def test_request_otp_with_valid_signup_purpose_for_new_user(self):
        response = self.client.post(
            self.request_url,
            {"email": "new@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.otp_store.get_otp_data("new@example.com", "SIGNUP"))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_request_otp_with_invalid_email(self):
        response = self.client.post(
            self.request_url,
            {"email": "12345", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_EMAIL")

    def test_request_otp_rejects_lowercase_login_without_side_effects(self):
        self._create_completed_user(email="existing@example.com")

        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "login"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
        self._assert_no_otp_side_effects("existing@example.com")
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_request_otp_rejects_lowercase_signup_without_side_effects(self):
        response = self.client.post(
            self.request_url,
            {"email": "new@example.com", "purpose": "signup"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
        self._assert_no_otp_side_effects("new@example.com")
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_request_otp_rejects_mixed_case_values(self):
        for purpose in ("Login", "Signup", "LoGiN", "SiGnUp"):
            response = self.client.post(
                self.request_url,
                {"email": "case@example.com", "purpose": purpose},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
            self._assert_no_otp_side_effects("case@example.com")

    def test_request_otp_rejects_missing_empty_null_and_unknown_purpose(self):
        invalid_payloads = [
            {"email": "missing@example.com"},
            {"email": "missing@example.com", "purpose": ""},
            {"email": "missing@example.com", "purpose": None},
            {"email": "missing@example.com", "purpose": "PASSWORD_RESET"},
            {"email": "missing@example.com", "purpose": "password_reset"},
            {"email": "missing@example.com", "purpose": "RESET_PASSWORD"},
            {"email": "missing@example.com", "purpose": 123},
            {"email": "missing@example.com", "purpose": True},
            {"email": "missing@example.com", "purpose": []},
            {"email": "missing@example.com", "purpose": {}},
            {"email": "missing@example.com", "purpose": " login"},
            {"email": "missing@example.com", "purpose": "LOGIN "},
        ]
        for payload in invalid_payloads:
            response = self.client.post(self.request_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
            self._assert_no_otp_side_effects("missing@example.com")
            self.assertFalse(User.objects.filter(email="missing@example.com").exists())

    def test_request_otp_rate_limit_is_per_purpose(self):
        self._create_completed_user(email="artist@example.com")

        for _ in range(3):
            self.otp_store.increment_request_count("artist@example.com", "LOGIN")
        response = self.client.post(
            self.request_url,
            {"email": "artist@example.com", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.json()["error"]["code"], "OTP_RATE_LIMITED")

        signup_response = self.client.post(
            self.request_url,
            {"email": "new@example.com", "purpose": "SIGNUP"},
            format="json",
        )
        self.assertEqual(signup_response.status_code, status.HTTP_200_OK)


@override_settings(
    OTP_LENGTH=6,
    OTP_TTL_SECONDS=120,
    OTP_DEBUG_RETURN_CODE=True,
    OTP_RESEND_COOLDOWN_SECONDS=60,
    OTP_MAX_VERIFY_ATTEMPTS=5,
    DEBUG=True,
    REDIS_HOST="fakeredis",
)
class OtpVerifyTestCase(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.otp_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/otp/request/"
        self.verify_url = "/api/v1/auth/otp/verify/"

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()
        RedisOtpStore._shared_client = None

    @staticmethod
    def _create_completed_user(email: str, **kwargs) -> User:
        user = User.objects.create(email=email, **kwargs)
        user.set_password("StrongPass123!")
        user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        return user

    def test_verify_login_logs_in_existing_user(self):
        self._create_completed_user(email="artist@example.com")
        self.otp_store.store_otp("artist@example.com", "LOGIN", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)
        self.assertEqual(User.objects.filter(email="artist@example.com").count(), 1)

    def test_verify_signup_creates_new_user(self):
        self.otp_store.store_otp("artist@example.com", "SIGNUP", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "code": "123456", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(User.objects.filter(email="artist@example.com").exists())
        user = User.objects.get(email="artist@example.com")
        self.assertTrue(user.is_email_verified)

    def test_verify_otp_with_wrong_code(self):
        self._create_completed_user(email="artist@example.com")
        self.otp_store.store_otp("artist@example.com", "LOGIN", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "code": "000000", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_OTP")

    def test_verify_otp_expired(self):
        self._create_completed_user(email="artist@example.com")

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "OTP_EXPIRED")

    def test_verify_otp_max_attempts(self):
        self._create_completed_user(email="artist@example.com")
        self.otp_store.store_otp("artist@example.com", "LOGIN", "123456", 120)

        for _ in range(5):
            response = self.client.post(
                self.verify_url,
                {"email": "artist@example.com", "code": "000000", "purpose": "LOGIN"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "code": "000000", "purpose": "LOGIN"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.json()["error"]["code"], "OTP_MAX_ATTEMPTS_EXCEEDED")

    def test_verify_otp_rejects_lowercase_login_even_with_valid_uppercase_otp(self):
        self._create_completed_user(email="existing@example.com")
        self.otp_store.store_otp("existing@example.com", "LOGIN", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "existing@example.com", "code": "123456", "purpose": "login"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
        self.assertIsNotNone(self.otp_store.get_otp_data("existing@example.com", "LOGIN"))
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_verify_otp_rejects_lowercase_signup_even_with_valid_uppercase_otp(self):
        self.otp_store.store_otp("new@example.com", "SIGNUP", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "new@example.com", "code": "123456", "purpose": "signup"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
        self.assertIsNotNone(self.otp_store.get_otp_data("new@example.com", "SIGNUP"))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_verify_otp_rejects_mixed_case_missing_empty_null_and_unknown_purpose(self):
        self._create_completed_user(email="existing@example.com")
        self.otp_store.store_otp("existing@example.com", "LOGIN", "123456", 120)

        invalid_payloads = [
            {"email": "existing@example.com", "code": "123456", "purpose": "Login"},
            {"email": "existing@example.com", "code": "123456", "purpose": "Signup"},
            {"email": "existing@example.com", "code": "123456", "purpose": "LoGiN"},
            {"email": "existing@example.com", "code": "123456", "purpose": "SiGnUp"},
            {"email": "existing@example.com", "code": "123456"},
            {"email": "existing@example.com", "code": "123456", "purpose": ""},
            {"email": "existing@example.com", "code": "123456", "purpose": None},
            {"email": "existing@example.com", "code": "123456", "purpose": "PASSWORD_RESET"},
            {"email": "existing@example.com", "code": "123456", "purpose": 123},
            {"email": "existing@example.com", "code": "123456", "purpose": True},
            {"email": "existing@example.com", "code": "123456", "purpose": []},
            {"email": "existing@example.com", "code": "123456", "purpose": {}},
            {"email": "existing@example.com", "code": "123456", "purpose": " LOGIN"},
            {"email": "existing@example.com", "code": "123456", "purpose": "LOGIN "},
        ]
        for payload in invalid_payloads:
            response = self.client.post(self.verify_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
            self.assertIsNotNone(self.otp_store.get_otp_data("existing@example.com", "LOGIN"))
            self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_verify_otp_purpose_isolation_remains_correct(self):
        self.otp_store.store_otp("new@example.com", "SIGNUP", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "new@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(response.json()["error"]["code"], {"INVALID_OTP", "OTP_EXPIRED"})
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_verify_login_does_not_create_user(self):
        self.otp_store.store_otp("missing@example.com", "LOGIN", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "missing@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "USER_NOT_FOUND")
        self.assertFalse(User.objects.filter(email="missing@example.com").exists())
