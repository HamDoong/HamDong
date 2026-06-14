"""Tests for OTP flow."""

from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch

from apps.identity.domain.models import *
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore


@override_settings(
    OTP_LENGTH=6, OTP_TTL_SECONDS=120, OTP_DEBUG_RETURN_CODE=True, DEBUG=True
)
class OtpRequestTestCase(TestCase):
    """Test cases for OTP request endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.otp_store = RedisOtpStore()
        self.url = "/api/v1/auth/otp/request/"

    def tearDown(self):
        """Clean up Redis after each test."""
        # Clear OTP data
        self.otp_store.redis_client.flushdb()

    def test_request_otp_with_valid_email(self):
        """Test requesting OTP with a valid email address."""
        response = self.client.post(
            self.url,
            {"email": "artist@example.com"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "OTP has been requested successfully."
        assert data["expires_in"] == 120
        assert data["resend_after"] == 60
        assert "debug_otp" in data  # Should be present in debug mode
        assert len(data["debug_otp"]) == 6
        assert data["debug_otp"].isdigit()

    def test_request_otp_with_invalid_email(self):
        """Test requesting OTP with an invalid email address."""
        response = self.client.post(
            self.url,
            {"email": "12345"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "INVALID_EMAIL"

    def test_request_otp_rate_limit(self):
        """Test OTP request rate limiting."""
        url = self.url
        email = "artist@example.com"

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

        try:
            # Make 3 requests (at limit)
            for _ in range(3):
                response = self.client.post(
                    url, {"email": email}, format="json"
                )
                assert response.status_code == status.HTTP_200_OK

            # 4th request should be rate limited
            response = self.client.post(
                url, {"email": email}, format="json"
            )
            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            data = response.json()
            assert data["error"]["code"] == "OTP_RATE_LIMITED"
        finally:
            set_cooldown_patch.stop()
            cooldown_patch.stop()

    def test_request_otp_cooldown(self):
        """Test OTP request cooldown period."""
        url = self.url
        email = "artist@example.com"

        # First request
        response = self.client.post(url, {"email": email}, format="json")
        assert response.status_code == status.HTTP_200_OK

        # Second request immediately should fail cooldown
        response = self.client.post(url, {"email": email}, format="json")
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["error"]["code"] == "OTP_IN_COOLDOWN"

    def test_request_otp_without_phone(self):
        """Test requesting OTP without phone number."""
        response = self.client.post(self.url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data


class OtpVerifyTestCase(TestCase):
    """Test cases for OTP verification endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.otp_service = RedisOtpStore()
        self.url = "/api/v1/auth/otp/verify/"

    def tearDown(self):
        """Clean up after each test."""
        self.otp_service.redis_client.flushdb()
        User.objects.all().delete()

    def test_verify_otp_creates_new_user(self):
        """Test verifying OTP creates a new user."""
        email = "artist@example.com"
        otp_code = "123456"

        # Store OTP
        self.otp_service.store_otp(email, otp_code, 120)

        # Verify OTP
        response = self.client.post(
            self.url,
            {"email": email, "code": otp_code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"
        assert "user" in data
        assert data["user"]["email"] == email
        assert data["user"]["is_email_verified"] is True

        # User should be created
        user = User.objects.get(email=email)
        assert user is not None
        assert user.is_email_verified is True

    def test_verify_otp_logs_in_existing_user(self):
        """Test verifying OTP logs in existing user."""
        email = "artist@example.com"
        otp_code = "123456"

        # Create user first
        user = User.objects.create(email=email)
        assert user.is_email_verified is False

        # Store OTP
        self.otp_service.store_otp(email, otp_code, 120)

        # Verify OTP
        response = self.client.post(
            self.url,
            {"email": email, "code": otp_code},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data

        # User should be updated
        user.refresh_from_db()
        assert user.is_email_verified is True
        assert user.last_login_at is not None

    def test_verify_otp_with_wrong_code(self):
        """Test verifying OTP with wrong code."""
        email = "artist@example.com"
        correct_otp = "123456"
        wrong_otp = "000000"

        # Store correct OTP
        self.otp_service.store_otp(email, correct_otp, 120)

        # Try with wrong OTP
        response = self.client.post(
            self.url,
            {"email": email, "code": wrong_otp},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "INVALID_OTP"

    def test_verify_otp_expired(self):
        """Test verifying expired OTP."""
        email = "artist@example.com"
        otp_code = "123456"

        # Don't store OTP (simulating expired)
        response = self.client.post(
            self.url,
            {"email": email, "code": otp_code},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["error"]["code"] == "OTP_EXPIRED"

    def test_verify_otp_max_attempts(self):
        """Test max OTP verification attempts."""
        email = "artist@example.com"
        correct_otp = "123456"
        wrong_otp = "000000"

        # Store OTP
        self.otp_service.store_otp(email, correct_otp, 120)

        # Make 5 wrong attempts
        for _ in range(5):
            response = self.client.post(
                self.url,
                {"email": email, "code": wrong_otp},
                format="json",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 6th attempt should fail with max attempts exceeded
        response = self.client.post(
            self.url,
            {"email": email, "code": wrong_otp},
            format="json",
        )
        assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        data = response.json()
        assert data["error"]["code"] == "OTP_MAX_ATTEMPTS_EXCEEDED"
