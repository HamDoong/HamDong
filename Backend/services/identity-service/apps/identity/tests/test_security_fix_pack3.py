from __future__ import annotations

import jwt
from django.test import TestCase, override_settings

from apps.identity.application.otp_service import OtpService
from apps.identity.application.token_service import ACCESS_TOKEN_KID, TokenService
from apps.identity.domain.models import *
from apps.identity.infrastructure.redis_otp_store import RedisOtpStore
from apps.identity.infrastructure.repositories import RefreshTokenRepository


@override_settings(REDIS_HOST="fakeredis")
class IdentitySecurityFixPack3Tests(TestCase):
    def setUp(self):
        RedisOtpStore._shared_client = None
        self.user = User.objects.create(email="artist@example.com")
        self.otp_store = RedisOtpStore()
        self.otp_store.redis_client.flushdb()

    def tearDown(self):
        self.otp_store.redis_client.flushdb()
        User.objects.all().delete()
        RedisOtpStore._shared_client = None

    def test_refresh_token_is_stored_hashed(self):
        token_service = TokenService()
        _, refresh_token, _ = token_service.generate_tokens(self.user)
        stored = RefreshTokenRepository.get_by_token_hash(
            RefreshTokenRepository.hash_token(refresh_token)
        )
        assert stored is not None
        assert stored.token_hash != refresh_token

    def test_access_token_has_required_claims_and_rs256_kid(self):
        token_service = TokenService()
        access_token, _, _ = token_service.generate_tokens(self.user)
        payload = token_service.verify_access_token(access_token)
        assert payload is not None
        assert payload["aud"] == "hamdong.services"
        assert payload["iss"] == "hamdong.identity-service"
        assert payload["type"] == "access"
        unverified_header = jwt.get_unverified_header(access_token)
        assert unverified_header["alg"] == "RS256"
        assert unverified_header["kid"] == ACCESS_TOKEN_KID

    def test_otp_is_hashed_in_redis(self):
        self.otp_store.store_otp("artist@example.com", "LOGIN", "123456", 120)
        otp_data = self.otp_store.get_otp_data("artist@example.com", "LOGIN")
        assert otp_data is not None
        assert otp_data["otp_hash"] != "123456"
        assert "123456" not in str(otp_data)

    @override_settings(DEBUG=False, OTP_DEBUG_RETURN_CODE=True)
    def test_debug_otp_hidden_when_debug_is_false(self):
        service = OtpService()
        success, error_code, otp_code, debug_otp = service.request_otp("artist@example.com", "LOGIN")
        assert success is True
        assert error_code is None
        assert otp_code is not None
        assert debug_otp is None

    def test_email_is_masked_in_logs(self):
        service = OtpService()
        with self.assertLogs("apps.identity.application.otp_service", level="INFO") as logs:
            success, _, otp_code, _ = service.request_otp("artist@example.com", "LOGIN")
            assert success is True
            service.verify_otp("artist@example.com", otp_code, "LOGIN")
        joined = "\n".join(logs.output)
        assert "ar***@e***.com" in joined
        assert "artist@example.com" not in joined
