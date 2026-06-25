
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

from django.conf import settings
from django.utils import timezone

from apps.wallets.domain.models import CurrencyChoices, PaymentIntent, PaymentProviderChoices


@dataclass(frozen=True)
class ProviderVerificationResult:
    status: str
    provider_reference: str | None
    provider_amount_minor: int | None
    currency: str | None
    provider_status: str
    payload: dict


class FakePaymentProviderAdapter:
    provider = PaymentProviderChoices.FAKE

    def build_payment_url(self, payment_intent: PaymentIntent) -> str:
        base_url = str(
            getattr(settings, "FAKE_PAYMENT_PROVIDER_BASE_URL", "https://fake-gateway/pay")
        ).rstrip("/")
        query = urlencode(
            {
                "payment_intent_id": str(payment_intent.id),
                "amount_minor": int(payment_intent.amount_minor),
                "currency": payment_intent.currency,
                "purpose": payment_intent.purpose,
            }
        )
        return f"{base_url}/{payment_intent.id}?{query}"

    def verify(self, payment_intent: PaymentIntent, *, callback_payload: dict | None = None, provider_reference: str | None = None) -> ProviderVerificationResult:
        callback_payload = callback_payload or {}
        provider_status = str(
            callback_payload.get("result")
            or callback_payload.get("status")
            or callback_payload.get("provider_status")
            or "success"
        ).lower()
        provider_reference = provider_reference or callback_payload.get("provider_reference") or callback_payload.get("ref") or callback_payload.get("authority")
        provider_amount = callback_payload.get("amount_minor")
        if provider_amount is None:
            provider_amount = callback_payload.get("amount")
        provider_currency = callback_payload.get("currency") or payment_intent.currency or CurrencyChoices.IRR

        if provider_reference and str(provider_reference).startswith("timeout"):
            provider_status = "timeout"

        if provider_status in {"timeout", "retry", "retryable"}:
            return ProviderVerificationResult(
                status="RETRYABLE",
                provider_reference=str(provider_reference) if provider_reference else None,
                provider_amount_minor=int(provider_amount) if provider_amount not in (None, "") else None,
                currency=provider_currency,
                provider_status="timeout",
                payload={
                    "provider": self.provider,
                    "provider_status": "timeout",
                    "verified_at": timezone.now().isoformat(),
                },
            )

        parsed_amount = int(provider_amount) if provider_amount not in (None, "") else None
        if parsed_amount is not None and parsed_amount != int(payment_intent.amount_minor):
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=str(provider_reference) if provider_reference else None,
                provider_amount_minor=parsed_amount,
                currency=provider_currency,
                provider_status="amount_mismatch",
                payload={
                    "provider": self.provider,
                    "provider_status": "amount_mismatch",
                    "expected_amount_minor": int(payment_intent.amount_minor),
                    "actual_amount_minor": parsed_amount,
                    "verified_at": timezone.now().isoformat(),
                },
            )

        if provider_status in {"fail", "failed", "cancelled", "canceled"}:
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=str(provider_reference) if provider_reference else None,
                provider_amount_minor=parsed_amount,
                currency=provider_currency,
                provider_status=provider_status,
                payload={
                    "provider": self.provider,
                    "provider_status": provider_status,
                    "verified_at": timezone.now().isoformat(),
                },
            )

        return ProviderVerificationResult(
            status="SUCCEEDED",
            provider_reference=str(provider_reference) if provider_reference else None,
            provider_amount_minor=parsed_amount if parsed_amount is not None else int(payment_intent.amount_minor),
            currency=provider_currency,
            provider_status="success",
            payload={
                "provider": self.provider,
                "provider_status": "success",
                "verified_at": timezone.now().isoformat(),
            },
        )


def get_provider_adapter(provider: str):
    normalized = str(provider or "").upper()
    if normalized == PaymentProviderChoices.FAKE:
        return FakePaymentProviderAdapter()
    raise ValueError("Unsupported payment provider.")
