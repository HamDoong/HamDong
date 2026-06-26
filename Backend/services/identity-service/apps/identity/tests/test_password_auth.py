from __future__ import annotations

from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import OutboxMessage, RefreshToken, User
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(DEBUG=True, OTP_DEBUG_RETURN_CODE=True, REDIS_HOST="fakeredis")
class PasswordAuthenticationTests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.client = APIClient()
        self.token_service = TokenService()
        self.otp_store = RedisOtpStore()
        self.email = "password.user@example.com"
        self.user = User.objects.create(email=self.email)
        self.user.set_password("StrongPass123!")
        self.user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        RedisOtpStore._shared_client = None

    def _otp_login(self):
        response = self.client.post("/api/v1/auth/otp/request/", {"email": self.email, "purpose": "LOGIN"}, format="json")
        self.assertEqual(response.status_code, 200)
        code = response.json()["debug_otp"]
        response = self.client.post("/api/v1/auth/otp/verify/", {"email": self.email, "code": code, "purpose": "LOGIN"}, format="json")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_otp_login_still_works(self):
        data = self._otp_login()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_patch_me_sets_profile_fields(self):
        data = self._otp_login()
        response = self.client.patch(
            "/api/v1/users/me/",
            {
                "art_name": "ali_artist",
                "display_name": "Ali Artist",
                "phone_number": "09123456789",
                "city": "Tehran",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["art_name"], "ali_artist")
        self.assertEqual(payload["display_name"], "Ali Artist")
        self.assertEqual(payload["phone_number"], "+989123456789")
        self.assertEqual(payload["city"], "Tehran")

    def test_duplicate_art_name_fails(self):
        User.objects.create(email="taken@example.com", art_name="taken_name")
        user2 = User.objects.create(email="second@example.com", art_name="second-name")
        access_token, _, _ = self.token_service.generate_tokens(user2)
        response = self.client.patch(
            "/api/v1/users/me/",
            {"art_name": "taken_name"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ART_NAME_ALREADY_EXISTS")

    def test_password_set_login_and_change_revokes_other_sessions(self):
        set_password_user = User.objects.create(email="setpass.user@example.com")
        access_token, _, _ = self.token_service.generate_tokens(set_password_user)

        response = self.client.patch(
            "/api/v1/users/me/",
            {"art_name": "ali_artist"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            "/api/v1/auth/password/set/",
            {"new_password": "StrongPass123!", "new_password_confirm": "StrongPass123!"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 200)

        first_login = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": "ali_artist", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(first_login.status_code, 200)
        first_login_data = first_login.json()

        second_login = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": "ali_artist", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(second_login.status_code, 200)
        second_login_data = second_login.json()

        self.assertEqual(
            RefreshToken.objects.filter(user__email="setpass.user@example.com", revoked_at__isnull=True).count(),
            3,
        )

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {first_login_data['access_token']}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Password changed successfully.")

        user = User.objects.get(email="setpass.user@example.com")
        self.assertTrue(user.check_password("NewStrongPass123!"))
        self.assertFalse(user.check_password("StrongPass123!"))

        active_tokens = RefreshToken.objects.filter(user=user, revoked_at__isnull=True)
        self.assertEqual(active_tokens.count(), 1)
        self.assertEqual(str(active_tokens.first().jti), str(self.token_service.verify_refresh_token(first_login_data["refresh_token"])["jti"]))

        self.assertIsNone(self.token_service.verify_refresh_token(second_login_data["refresh_token"]))
        self.assertIsNotNone(self.token_service.verify_refresh_token(first_login_data["refresh_token"]))

        old_login = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": "ali_artist", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(old_login.status_code, 401)
        self.assertEqual(old_login.json()["error"]["code"], "INVALID_CREDENTIALS")

        new_login = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": "ali_artist", "password": "NewStrongPass123!"},
            format="json",
        )
        self.assertEqual(new_login.status_code, 200)
        self.assertTrue(OutboxMessage.objects.filter(event_type="PasswordChanged").exists())

    def test_password_change_validation_errors(self):
        user = User.objects.create(email="user@example.com", art_name="user-one")
        user.set_password("CurrentPass123!")
        user.save(update_fields=["password_hash", "password_changed_at", "updated_at"])
        access_token, _, _ = self.token_service.generate_tokens(user)

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "wrong",
                "new_password": "NewPass123!",
                "new_password_confirm": "NewPass123!",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_CURRENT_PASSWORD")

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "CurrentPass123!",
                "new_password": "CurrentPass123!",
                "new_password_confirm": "CurrentPass123!",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "PASSWORD_REUSE_NOT_ALLOWED")

        self.assertFalse(OutboxMessage.objects.filter(event_type="PasswordChanged", payload__data__user_id=str(user.id)).exists())
