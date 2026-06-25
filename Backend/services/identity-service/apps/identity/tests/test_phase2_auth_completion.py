from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import (
    OutboxMessage,
    PasswordResetChallenge,
    PasswordResetToken,
    RefreshToken,
    User,
)
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore
from apps.identity.infrastructure.repositories import PasswordResetChallengeRepository


@override_settings(
    DEBUG=True,
    OTP_DEBUG_RETURN_CODE=True,
    REDIS_HOST="fakeredis",
    PASSWORD_RESET_OTP_TTL_SECONDS=600,
    PASSWORD_RESET_TOKEN_TTL_SECONDS=600,
    JWT_ACCESS_TOKEN_LIFETIME_SECONDS=900,
    JWT_REFRESH_TOKEN_LIFETIME_SECONDS=604800,
    JWT_REMEMBER_ME_REFRESH_TOKEN_LIFETIME_SECONDS=2592000,
)
class ForgotPasswordRequestTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.redis_store = RedisOtpStore()
        self.url = "/api/v1/auth/password/forgot/request/"
        self.user = User.objects.create(email="artist@example.com")

    def tearDown(self):
        self.redis_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def test_request_returns_same_generic_response_for_existing_non_existing_and_deactivated_accounts(self):
        existing = self.client.post(self.url, {"email": "artist@example.com"}, format="json")
        missing = self.client.post(self.url, {"email": "missing@example.com"}, format="json")
        self.redis_store.redis_client.flushdb()
        self.user.is_active = False
        self.user.save(update_fields=["is_active", "updated_at"])
        deactivated = self.client.post(self.url, {"email": "artist@example.com"}, format="json")

        self.assertEqual(existing.status_code, status.HTTP_200_OK)
        self.assertEqual(existing.json(), {"message": "If the account exists, a verification code has been sent."})
        self.assertEqual(missing.status_code, status.HTTP_200_OK)
        self.assertEqual(missing.json(), existing.json())
        self.assertEqual(deactivated.status_code, status.HTTP_200_OK)
        self.assertEqual(deactivated.json(), existing.json())

    def test_request_stores_hashed_otp_and_creates_outbox_event_only_for_existing_active_user(self):
        response = self.client.post(self.url, {"email": "artist@example.com"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        challenge = PasswordResetChallenge.objects.get(email="artist@example.com")
        self.assertNotEqual(challenge.otp_hash, "")
        self.assertNotEqual(challenge.otp_hash, "123456")
        self.assertEqual(challenge.status, PasswordResetChallenge.StatusChoices.PENDING)

        event = OutboxMessage.objects.get(event_type="SendOtpEmailRequested")
        self.assertEqual(event.routing_key, "identity.otp.requested")
        self.assertEqual(event.payload["data"]["email"], "artist@example.com")
        self.assertEqual(event.payload["data"]["purpose"], "PASSWORD_RESET")
        self.assertNotEqual(event.payload["data"]["code"], challenge.otp_hash)

        missing_response = self.client.post(self.url, {"email": "missing@example.com"}, format="json")
        self.assertEqual(missing_response.status_code, status.HTTP_200_OK)
        self.assertEqual(PasswordResetChallenge.objects.filter(email="missing@example.com").count(), 0)
        self.assertEqual(OutboxMessage.objects.filter(event_type="SendOtpEmailRequested").count(), 1)

    def test_request_enforces_cooldown_without_account_enumeration(self):
        first = self.client.post(self.url, {"email": "artist@example.com"}, format="json")
        second = self.client.post(self.url, {"email": "artist@example.com"}, format="json")
        third = self.client.post(self.url, {"email": "unknown@example.com"}, format="json")

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(second.json()["error"]["code"], "OTP_IN_COOLDOWN")
        self.assertEqual(third.status_code, status.HTTP_200_OK)


@override_settings(
    DEBUG=True,
    REDIS_HOST="fakeredis",
    PASSWORD_RESET_OTP_TTL_SECONDS=600,
    PASSWORD_RESET_TOKEN_TTL_SECONDS=600,
)
class ForgotPasswordVerifyTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.redis_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/password/forgot/request/"
        self.verify_url = "/api/v1/auth/password/forgot/verify/"
        self.user = User.objects.create(email="artist@example.com")
        self.user.set_password("OldPass123!")
        self.user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])

    def tearDown(self):
        self.redis_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def _request_and_get_otp(self) -> str:
        response = self.client.post(self.request_url, {"email": "artist@example.com"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        event = OutboxMessage.objects.filter(event_type="SendOtpEmailRequested").latest("created_at")
        return event.payload["data"]["code"]

    def test_verify_valid_otp_returns_reset_token_without_logging_user_in(self):
        otp = self._request_and_get_otp()

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "otp": otp},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("reset_token", data)
        self.assertEqual(data["expires_in_seconds"], 600)
        self.assertNotIn("access_token", data)
        self.assertNotIn("refresh_token", data)

        stored_token = PasswordResetToken.objects.get(user=self.user)
        self.assertNotEqual(stored_token.token_hash, data["reset_token"])
        challenge = PasswordResetChallenge.objects.get(email="artist@example.com")
        self.assertEqual(challenge.status, PasswordResetChallenge.StatusChoices.VERIFIED)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OldPass123!"))

    def test_verify_wrong_otp_increments_attempts_and_locks_after_max_attempts(self):
        self._request_and_get_otp()

        challenge = PasswordResetChallenge.objects.get(email="artist@example.com")
        for _ in range(challenge.max_attempts):
            response = self.client.post(
                self.verify_url,
                {"email": "artist@example.com", "otp": "000000"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()["error"]["code"], "INVALID_OTP")

        challenge.refresh_from_db()
        self.assertEqual(challenge.attempt_count, challenge.max_attempts)
        self.assertEqual(challenge.status, PasswordResetChallenge.StatusChoices.LOCKED)

        response = self.client.post(
            self.verify_url,
            {"email": "artist@example.com", "otp": "000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(response.json()["error"]["code"], "OTP_MAX_ATTEMPTS_EXCEEDED")

    def test_verify_rejects_expired_and_used_challenges(self):
        otp = self._request_and_get_otp()
        challenge = PasswordResetChallenge.objects.get(email="artist@example.com")
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=["expires_at", "updated_at"])

        expired = self.client.post(self.verify_url, {"email": "artist@example.com", "otp": otp}, format="json")
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired.json()["error"]["code"], "OTP_EXPIRED")

        challenge.refresh_from_db()
        challenge.status = PasswordResetChallenge.StatusChoices.USED
        challenge.used_at = timezone.now()
        challenge.save(update_fields=["status", "used_at", "updated_at"])
        used = self.client.post(self.verify_url, {"email": "artist@example.com", "otp": otp}, format="json")
        self.assertEqual(used.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(used.json()["error"]["code"], "OTP_ALREADY_USED")


@override_settings(
    DEBUG=True,
    REDIS_HOST="fakeredis",
    PASSWORD_RESET_OTP_TTL_SECONDS=600,
    PASSWORD_RESET_TOKEN_TTL_SECONDS=600,
    JWT_ACCESS_TOKEN_LIFETIME_SECONDS=900,
    JWT_REFRESH_TOKEN_LIFETIME_SECONDS=604800,
    JWT_REMEMBER_ME_REFRESH_TOKEN_LIFETIME_SECONDS=2592000,
)
class PasswordResetFlowTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.redis_store = RedisOtpStore()
        self.request_url = "/api/v1/auth/password/forgot/request/"
        self.verify_url = "/api/v1/auth/password/forgot/verify/"
        self.reset_url = "/api/v1/auth/password/reset/"
        self.login_url = "/api/v1/auth/password/login/"
        self.refresh_url = "/api/v1/auth/token/refresh/"
        self.user = User.objects.create(email="artist@example.com", art_name="artist-user")
        self.user.set_password("OldPass123!")
        self.user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        self.token_service = TokenService()

    def tearDown(self):
        self.redis_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def _get_reset_token(self, *, reset_throttle: bool = False) -> str:
        if reset_throttle:
            self.redis_store.redis_client.flushdb()
        request_response = self.client.post(self.request_url, {"email": "artist@example.com"}, format="json")
        self.assertEqual(request_response.status_code, status.HTTP_200_OK)
        otp = OutboxMessage.objects.filter(event_type="SendOtpEmailRequested").latest("created_at").payload["data"]["code"]
        verify_response = self.client.post(self.verify_url, {"email": "artist@example.com", "otp": otp}, format="json")
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        return verify_response.json()["reset_token"]

    def test_password_reset_changes_password_revokes_old_sessions_and_emits_event(self):
        old_login = self.client.post(
            self.login_url,
            {"art_name": "artist-user", "password": "OldPass123!", "remember_me": True},
            format="json",
        )
        self.assertEqual(old_login.status_code, status.HTTP_200_OK)
        old_refresh = old_login.json()["refresh_token"]

        reset_token = self._get_reset_token()
        response = self.client.post(
            self.reset_url,
            {
                "reset_token": reset_token,
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["message"], "Password reset successfully.")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewStrongPass123!"))
        self.assertFalse(self.user.check_password("OldPass123!"))

        token_row = PasswordResetToken.objects.get(user=self.user)
        self.assertIsNotNone(token_row.used_at)
        refresh_row = RefreshToken.objects.get(token_hash=RefreshToken.objects.get(user=self.user).token_hash)
        self.assertIsNotNone(refresh_row.revoked_at)

        old_refresh_response = self.client.post(self.refresh_url, {"refresh_token": old_refresh}, format="json")
        self.assertEqual(old_refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

        old_password_login = self.client.post(
            self.login_url,
            {"art_name": "artist-user", "password": "OldPass123!"},
            format="json",
        )
        self.assertEqual(old_password_login.status_code, status.HTTP_401_UNAUTHORIZED)

        new_password_login = self.client.post(
            self.login_url,
            {"art_name": "artist-user", "password": "NewStrongPass123!"},
            format="json",
        )
        self.assertEqual(new_password_login.status_code, status.HTTP_200_OK)

        event = OutboxMessage.objects.filter(event_type="PasswordResetCompleted").latest("created_at")
        self.assertEqual(event.payload["data"]["user_id"], str(self.user.id))
        self.assertEqual(set(event.payload["data"].keys()), {"user_id", "completed_at"})
        self.assertNotIn("reset_token", str(event.payload["data"]).lower())
        self.assertNotIn("otp", str(event.payload["data"]).lower())
        self.assertNotIn("refresh_token", str(event.payload["data"]).lower())

    def test_password_reset_rejects_mismatch_weak_invalid_expired_and_used_tokens(self):
        reset_token = self._get_reset_token()

        mismatch = self.client.post(
            self.reset_url,
            {
                "reset_token": reset_token,
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "Mismatch123!",
            },
            format="json",
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(mismatch.json()["error"]["code"], "PASSWORD_CONFIRMATION_MISMATCH")

        weak = self.client.post(
            self.reset_url,
            {
                "reset_token": reset_token,
                "new_password": "12345678",
                "new_password_confirm": "12345678",
            },
            format="json",
        )
        self.assertEqual(weak.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(weak.json()["error"]["code"], "WEAK_PASSWORD")

        invalid = self.client.post(
            self.reset_url,
            {
                "reset_token": "invalid-token",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid.json()["error"]["code"], "INVALID_RESET_TOKEN")

        token_row = PasswordResetToken.objects.get(user=self.user)
        token_row.expires_at = timezone.now() - timedelta(seconds=1)
        token_row.save(update_fields=["expires_at", "updated_at"])
        expired = self.client.post(
            self.reset_url,
            {
                "reset_token": reset_token,
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired.json()["error"]["code"], "RESET_TOKEN_EXPIRED")

        fresh_token = self._get_reset_token(reset_throttle=True)
        used_once = self.client.post(
            self.reset_url,
            {
                "reset_token": fresh_token,
                "new_password": "AnotherStrongPass123!",
                "new_password_confirm": "AnotherStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(used_once.status_code, status.HTTP_200_OK)

        used_again = self.client.post(
            self.reset_url,
            {
                "reset_token": fresh_token,
                "new_password": "YetAnotherStrongPass123!",
                "new_password_confirm": "YetAnotherStrongPass123!",
            },
            format="json",
        )
        self.assertEqual(used_again.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(used_again.json()["error"]["code"], "RESET_TOKEN_USED")


@override_settings(
    DEBUG=True,
    REDIS_HOST="fakeredis",
    JWT_ACCESS_TOKEN_LIFETIME_SECONDS=900,
    JWT_REFRESH_TOKEN_LIFETIME_SECONDS=604800,
    JWT_REMEMBER_ME_REFRESH_TOKEN_LIFETIME_SECONDS=2592000,
)
class RememberMeAndSessionsTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.redis_store = RedisOtpStore()
        self.login_url = "/api/v1/auth/password/login/"
        self.sessions_url = "/api/v1/auth/sessions/"
        self.refresh_url = "/api/v1/auth/token/refresh/"
        self.user = User.objects.create(email="artist@example.com", art_name="artist-user")
        self.user.set_password("StrongPass123!")
        self.user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        self.other_user = User.objects.create(email="other@example.com", art_name="other-user")
        self.other_user.set_password("StrongPass123!")
        self.other_user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])

    def tearDown(self):
        self.redis_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def _login(self, art_name: str, password: str, remember_me=None):
        payload = {"art_name": art_name, "password": password}
        if remember_me is not None:
            payload["remember_me"] = remember_me
        return self.client.post(
            self.login_url,
            payload,
            format="json",
            HTTP_USER_AGENT="Mozilla/5.0",
            REMOTE_ADDR="192.168.10.44",
        )

    def test_remember_me_controls_refresh_lifetime_without_extending_access_token(self):
        default_login = self._login("artist-user", "StrongPass123!")
        false_login = self._login("artist-user", "StrongPass123!", False)
        true_login = self._login("artist-user", "StrongPass123!", True)

        self.assertEqual(default_login.status_code, status.HTTP_200_OK)
        self.assertEqual(false_login.status_code, status.HTTP_200_OK)
        self.assertEqual(true_login.status_code, status.HTTP_200_OK)

        sessions = list(RefreshToken.objects.filter(user=self.user).order_by("created_at"))
        self.assertEqual(len(sessions), 3)
        default_session, false_session, true_session = sessions

        default_lifetime = int((default_session.expires_at - default_session.created_at).total_seconds())
        false_lifetime = int((false_session.expires_at - false_session.created_at).total_seconds())
        true_lifetime = int((true_session.expires_at - true_session.created_at).total_seconds())

        self.assertAlmostEqual(default_lifetime, settings.JWT_REFRESH_TOKEN_LIFETIME_SECONDS, delta=5)
        self.assertAlmostEqual(false_lifetime, settings.JWT_REFRESH_TOKEN_LIFETIME_SECONDS, delta=5)
        self.assertAlmostEqual(true_lifetime, settings.JWT_REMEMBER_ME_REFRESH_TOKEN_LIFETIME_SECONDS, delta=5)
        self.assertFalse(default_session.remember_me)
        self.assertFalse(false_session.remember_me)
        self.assertTrue(true_session.remember_me)
        self.assertEqual(default_login.json()["expires_in"], settings.JWT_ACCESS_TOKEN_LIFETIME_SECONDS)
        self.assertEqual(true_login.json()["expires_in"], settings.JWT_ACCESS_TOKEN_LIFETIME_SECONDS)

    def test_invalid_remember_me_type_is_rejected(self):
        response = self._login("artist-user", "StrongPass123!", "true")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "INVALID_REQUEST")

    def test_sessions_list_requires_auth_and_only_returns_current_users_sessions(self):
        missing = self.client.get(self.sessions_url)
        self.assertEqual(missing.status_code, status.HTTP_401_UNAUTHORIZED)

        current_login = self._login("artist-user", "StrongPass123!", True)
        other_login = self._login("artist-user", "StrongPass123!", False)
        self._login("other-user", "StrongPass123!", False)
        access_token = current_login.json()["access_token"]

        response = self.client.get(self.sessions_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(len(payload["results"]), 2)
        self.assertTrue(any(item["is_current"] for item in payload["results"]))
        self.assertTrue(all(item["user_agent"] == "Mozilla/5.0" for item in payload["results"]))
        self.assertTrue(all(item["ip_address"] == "192.168.10.0" for item in payload["results"]))
        serialized = str(payload).lower()
        self.assertNotIn("refresh_token", serialized)
        self.assertNotIn("jti", serialized)
        self.assertNotIn(other_login.json()["refresh_token"], serialized)

    def test_delete_session_revokes_only_owned_session_and_delete_all_revokes_others(self):
        current_login = self._login("artist-user", "StrongPass123!", True)
        other_login = self._login("artist-user", "StrongPass123!", False)
        foreign_login = self._login("other-user", "StrongPass123!", False)

        access_token = current_login.json()["access_token"]
        session_rows = list(RefreshToken.objects.filter(user=self.user, revoked_at__isnull=True).order_by("created_at"))
        current_session = next(session for session in session_rows if str(session.jti) == TokenService().verify_access_token(current_login.json()["access_token"])["jti"])
        other_session = next(session for session in session_rows if session.id != current_session.id)
        foreign_session = RefreshToken.objects.filter(user=self.other_user, revoked_at__isnull=True).first()

        delete_other = self.client.delete(
            f"{self.sessions_url}{other_session.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(delete_other.status_code, status.HTTP_204_NO_CONTENT)
        other_session.refresh_from_db()
        self.assertIsNotNone(other_session.revoked_at)

        refresh_deleted = self.client.post(self.refresh_url, {"refresh_token": other_login.json()["refresh_token"]}, format="json")
        self.assertEqual(refresh_deleted.status_code, status.HTTP_401_UNAUTHORIZED)

        delete_foreign = self.client.delete(
            f"{self.sessions_url}{foreign_session.id}/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(delete_foreign.status_code, status.HTTP_404_NOT_FOUND)

        delete_all = self.client.delete(self.sessions_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(delete_all.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(delete_all.json()["revoked_count"], 0)

        foreign_refresh = self.client.post(self.refresh_url, {"refresh_token": foreign_login.json()["refresh_token"]}, format="json")
        self.assertEqual(foreign_refresh.status_code, status.HTTP_200_OK)

        repeated = self.client.delete(self.sessions_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(repeated.status_code, status.HTTP_200_OK)


@override_settings(DEBUG=True, REDIS_HOST="fakeredis")
class AuthCompletionSwaggerTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.redis_store = RedisOtpStore()

    def tearDown(self):
        self.redis_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def test_schema_contains_new_auth_paths_and_login_remember_me(self):
        response = self.client.get("/api/schema/?format=json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        paths = payload["paths"]
        self.assertIn("/api/v1/auth/password/forgot/request/", paths)
        self.assertIn("/api/v1/auth/password/forgot/verify/", paths)
        self.assertIn("/api/v1/auth/password/reset/", paths)
        self.assertIn("/api/v1/auth/sessions/", paths)
        self.assertIn("/api/v1/auth/sessions/{session_id}/", paths)

        login_schema = payload["components"]["schemas"]["PasswordLogin"]["properties"]
        self.assertIn("remember_me", login_schema)

        rendered = str(payload).lower()
        self.assertNotIn("example-reset-token", rendered)
        self.assertNotIn("raw-jti", rendered)
