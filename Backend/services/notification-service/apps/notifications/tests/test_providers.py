"""Tests for Email providers and provider factory."""

from django.test import SimpleTestCase

from apps.notifications.infrastructure.providers.base import (
    InvalidEmailProviderError,
)
from apps.notifications.infrastructure.providers.fake_provider import (
    FakeEmailProvider,
)
from apps.notifications.infrastructure.providers.factory import (
    get_email_provider,
)
from apps.notifications.infrastructure.providers.smtp_provider import (
    SmtpEmailProvider,
)


class EmailProviderTests(SimpleTestCase):
    def test_fake_provider_sends_email_successfully(self):
        provider = FakeEmailProvider()

        result = provider.send_email(
            "artist@example.com",
            "Test subject",
            "Test message",
        )

        self.assertTrue(result.success)
        self.assertEqual(result.provider, "fake")
        self.assertIsNotNone(result.provider_message_id)

    def test_provider_factory_returns_correct_provider(self):
        self.assertIsInstance(
            get_email_provider("fake"),
            FakeEmailProvider,
        )
        self.assertIsInstance(
            get_email_provider("smtp"),
            SmtpEmailProvider,
        )

    def test_invalid_provider_raises_controlled_error(self):
        with self.assertRaises(InvalidEmailProviderError):
            get_email_provider("unsupported-provider")