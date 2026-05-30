"""Tests for SMS providers and provider factory."""

from django.test import SimpleTestCase

from apps.notifications.infrastructure.providers.base import InvalidSmsProviderError
from apps.notifications.infrastructure.providers.fake_provider import FakeSmsProvider
from apps.notifications.infrastructure.providers.factory import get_sms_provider
from apps.notifications.infrastructure.providers.kavenegar_provider import (
    KavenegarSmsProvider,
)
from apps.notifications.infrastructure.providers.melipayamak_provider import (
    MelipayamakSmsProvider,
)


class SmsProviderTests(SimpleTestCase):
    def test_fake_provider_sends_sms_successfully(self):
        provider = FakeSmsProvider()
        result = provider.send_sms("09123456789", "Test message")

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "fake")
        self.assertIsNotNone(result.provider_message_id)

    def test_provider_factory_returns_correct_provider(self):
        self.assertIsInstance(get_sms_provider("fake"), FakeSmsProvider)
        self.assertIsInstance(get_sms_provider("kavenegar"), KavenegarSmsProvider)
        self.assertIsInstance(get_sms_provider("melipayamak"), MelipayamakSmsProvider)

    def test_invalid_provider_raises_controlled_error(self):
        with self.assertRaises(InvalidSmsProviderError):
            get_sms_provider("unsupported-provider")
