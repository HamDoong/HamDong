from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.application.token_service import TokenService
from apps.identity.domain.models import RefreshToken, User
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(DEBUG=True, OTP_DEBUG_RETURN_CODE=True)
class PasswordAuthenticationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.token_service = TokenService()
        self.otp_store = RedisOtpStore()
        self.phone_number = "09120000001"

    def tearDown(self):
        self.otp_store.redis_client.flushdb()

    def _otp_login(self):
        response = self.client.post("/api/v1/auth/otp/request/", {"phone_number": self.phone_number}, format="json")
        self.assertEqual(response.status_code, 200)
        code = response.json()["debug_otp"]
        response = self.client.post("/api/v1/auth/otp/verify/", {"phone_number": self.phone_number, "code": code}, format="json")
        self.assertEqual(response.status_code, 200)
        return response.json()

    def test_otp_login_still_works(self):
        data = self._otp_login()
        self.assertIn("access_token", data)
        self.assertIn("refresh_token", data)

    def test_patch_me_sets_art_name(self):
        data = self._otp_login()
        response = self.client.patch(
            "/api/v1/users/me/",
            {"art_name": "ali_artist"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {data['access_token']}",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["art_name"], "ali_artist")

    def test_duplicate_art_name_fails(self):
        User.objects.create(phone_number="09120000001", art_name="taken_name")
        user2 = User.objects.create(phone_number="09120000002")
        access_token, _, _ = self.token_service.generate_tokens(user2)
        response = self.client.patch(
            "/api/v1/users/me/",
            {"art_name": "taken_name"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ART_NAME_ALREADY_EXISTS")

    def test_password_set_login_and_change(self):
        otp_data = self._otp_login()
        access_token = otp_data["access_token"]

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

        response = self.client.post(
            "/api/v1/auth/password/login/",
            {"art_name": "ali_artist", "password": "StrongPass123!"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        login_data = response.json()
        self.assertEqual(login_data["token_type"], "Bearer")
        self.assertEqual(login_data["user"]["art_name"], "ali_artist")

        refresh_token = login_data["refresh_token"]
        self.assertTrue(RefreshToken.objects.filter(user__phone_number=self.phone_number, revoked_at__isnull=True).exists())

        response = self.client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass123!",
                "new_password_confirm": "NewStrongPass123!",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {login_data['access_token']}",
        )
        self.assertEqual(response.status_code, 200)

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
