from __future__ import annotations

from django.test import TestCase, override_settings
from django.utils import timezone
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
class OtpLoginSignupRequestPrecheckTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.otp_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/otp/request/"
        self.verify_url = "/api/v1/auth/otp/verify/"

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()
        OutboxMessage.objects.all().delete()
        RedisOtpStore._shared_client = None

    @staticmethod
    def _create_user(email: str, *, completed: bool = False, **kwargs) -> User:
        user = User.objects.create(email=email, **kwargs)
        if completed:
            user.set_password("StrongPass123!")
            user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        return user

    def _assert_no_otp_side_effects(self, email: str, purpose: str):
        self.assertIsNone(self.otp_store.get_otp_data(email, purpose))
        self.assertFalse(
            OutboxMessage.objects.filter(
                event_type="SendOtpEmailRequested",
                payload__data__email=email,
                payload__data__purpose=purpose,
            ).exists()
        )

    def test_login_request_for_existing_active_completed_user_succeeds(self):
        self._create_user("existing@example.com", completed=True)

        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.otp_store.get_otp_data("existing@example.com", "LOGIN"))
        event = OutboxMessage.objects.get(event_type="SendOtpEmailRequested")
        self.assertEqual(event.payload["data"]["email"], "existing@example.com")
        self.assertEqual(event.payload["data"]["purpose"], "LOGIN")

    def test_login_request_for_missing_email_returns_404_without_side_effects(self):
        response = self.client.post(
            self.request_url,
            {"email": "missing@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_NOT_REGISTERED")
        self._assert_no_otp_side_effects("missing@example.com", "LOGIN")

    def test_signup_request_for_new_email_succeeds_without_creating_user(self):
        response = self.client.post(
            self.request_url,
            {"email": "new@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.otp_store.get_otp_data("new@example.com", "SIGNUP"))
        self.assertFalse(User.objects.filter(email="new@example.com").exists())
        event = OutboxMessage.objects.get(event_type="SendOtpEmailRequested")
        self.assertEqual(event.payload["data"]["email"], "new@example.com")
        self.assertEqual(event.payload["data"]["purpose"], "SIGNUP")

    def test_signup_request_for_existing_active_email_returns_conflict_without_side_effects(self):
        self._create_user("existing@example.com", completed=True)

        response = self.client.post(
            self.request_url,
            {"email": "existing@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_ALREADY_EXISTS")
        self._assert_no_otp_side_effects("existing@example.com", "SIGNUP")

    def test_login_request_for_inactive_user_returns_forbidden_without_side_effects(self):
        self._create_user("disabled@example.com", completed=True, is_active=False)

        response = self.client.post(
            self.request_url,
            {"email": "disabled@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_DEACTIVATED")
        self._assert_no_otp_side_effects("disabled@example.com", "LOGIN")

    def test_signup_request_for_inactive_user_returns_forbidden_without_side_effects(self):
        self._create_user("disabled@example.com", completed=True, is_active=False)

        response = self.client.post(
            self.request_url,
            {"email": "disabled@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_DEACTIVATED")
        self._assert_no_otp_side_effects("disabled@example.com", "SIGNUP")

    def test_login_request_for_deleted_user_returns_forbidden_without_side_effects(self):
        self._create_user(
            "deleted@example.com",
            completed=True,
            deleted_at=timezone.now(),
        )

        response = self.client.post(
            self.request_url,
            {"email": "deleted@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_DEACTIVATED")
        self._assert_no_otp_side_effects("deleted@example.com", "LOGIN")

    def test_signup_request_for_deleted_user_returns_forbidden_without_side_effects(self):
        self._create_user(
            "deleted@example.com",
            completed=True,
            deleted_at=timezone.now(),
        )

        response = self.client.post(
            self.request_url,
            {"email": "deleted@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "ACCOUNT_DEACTIVATED")
        self._assert_no_otp_side_effects("deleted@example.com", "SIGNUP")

    def test_login_request_for_incomplete_signup_returns_conflict_without_side_effects(self):
        self._create_user("incomplete@example.com", completed=False)

        response = self.client.post(
            self.request_url,
            {"email": "incomplete@example.com", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "SIGNUP_NOT_COMPLETED")
        self._assert_no_otp_side_effects("incomplete@example.com", "LOGIN")

    def test_signup_request_for_incomplete_signup_returns_existing_email_without_side_effects(self):
        self._create_user("incomplete@example.com", completed=False)

        response = self.client.post(
            self.request_url,
            {"email": "incomplete@example.com", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_ALREADY_EXISTS")
        self._assert_no_otp_side_effects("incomplete@example.com", "SIGNUP")

    def test_invalid_purpose_returns_bad_request_without_side_effects(self):
        response = self.client.post(
            self.request_url,
            {"email": "user@example.com", "purpose": "RESET_PASSWORD"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PURPOSE")
        self._assert_no_otp_side_effects("user@example.com", "LOGIN")
        self._assert_no_otp_side_effects("user@example.com", "SIGNUP")

    def test_request_normalizes_email_before_login_precheck(self):
        self._create_user("existing@example.com", completed=True)

        response = self.client.post(
            self.request_url,
            {"email": " Existing@Example.COM ", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(self.otp_store.get_otp_data("existing@example.com", "LOGIN"))
        event = OutboxMessage.objects.get(event_type="SendOtpEmailRequested")
        self.assertEqual(event.payload["data"]["email"], "existing@example.com")

    def test_verify_login_does_not_issue_tokens_for_incomplete_signup(self):
        self._create_user("incomplete@example.com", completed=False)
        self.otp_store.store_otp("incomplete@example.com", "LOGIN", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "incomplete@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "SIGNUP_NOT_COMPLETED")
        self.assertNotIn("access_token", response.json())
        self.assertEqual(User.objects.filter(email="incomplete@example.com").count(), 1)

    def test_verify_signup_does_not_create_duplicate_user(self):
        self._create_user("existing@example.com", completed=True)
        self.otp_store.store_otp("existing@example.com", "SIGNUP", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "existing@example.com", "code": "123456", "purpose": "SIGNUP"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()["error"]["code"], "EMAIL_ALREADY_EXISTS")
        self.assertNotIn("access_token", response.json())
        self.assertEqual(User.objects.filter(email="existing@example.com").count(), 1)

    def test_verify_purpose_isolation_prevents_signup_otp_from_logging_in(self):
        self.otp_store.store_otp("new@example.com", "SIGNUP", "123456", 120)

        response = self.client.post(
            self.verify_url,
            {"email": "new@example.com", "code": "123456", "purpose": "LOGIN"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(response.json()["error"]["code"], {"INVALID_OTP", "OTP_EXPIRED"})
        self.assertFalse(User.objects.filter(email="new@example.com").exists())


@override_settings(DEBUG=True, REDIS_HOST="fakeredis")
class OtpSwaggerRegressionTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.otp_store = RedisOtpStore()

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def test_schema_includes_otp_and_user_search_paths(self):
        response = self.client.get("/api/schema/?format=json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        paths = payload["paths"]

        self.assertIn("/api/v1/auth/otp/request/", paths)
        self.assertIn("/api/v1/auth/otp/verify/", paths)
        self.assertIn("/api/v1/users/search/", paths)
        self.assertIn("/api/v1/users/{user_id}/public/", paths)

        request_post = paths["/api/v1/auth/otp/request/"]["post"]
        verify_post = paths["/api/v1/auth/otp/verify/"]["post"]

        purpose_schema_ref = payload["components"]["schemas"]["RequestOtp"]["properties"]["purpose"]["$ref"]
        purpose_schema_name = purpose_schema_ref.rsplit("/", 1)[-1]
        self.assertEqual(
            set(payload["components"]["schemas"][purpose_schema_name]["enum"]),
            {"LOGIN", "SIGNUP"},
        )
        self.assertIn("404", request_post["responses"])
        self.assertIn("409", request_post["responses"])
        self.assertIn("409", verify_post["responses"])

        rendered = str(payload).lower()
        self.assertNotIn("example-reset-token", rendered)
