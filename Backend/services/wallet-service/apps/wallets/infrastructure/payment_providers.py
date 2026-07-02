from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from django.conf import settings
from django.utils import timezone

from apps.wallets.domain.models import CurrencyChoices, PaymentIntent, PaymentProviderChoices


@dataclass(frozen=True)
class ProviderPaymentRequestResult:
    payment_url: str
    provider_reference: str | None = None
    provider_status: str | None = None
    payload: dict | None = None


@dataclass(frozen=True)
class ProviderVerificationResult:
    status: str
    provider_reference: str | None
    provider_amount_minor: int | None
    currency: str | None
    provider_status: str
    payload: dict


class PaymentProviderRequestError(Exception):
    def __init__(
        self,
        message: str,
        *,
        payload: dict | None = None,
        provider_status: str | None = None,
        provider_reference: str | None = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.payload = payload or {}
        self.provider_status = provider_status
        self.provider_reference = provider_reference
        self.retryable = retryable


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

    def request_payment(self, payment_intent: PaymentIntent) -> ProviderPaymentRequestResult:
        return ProviderPaymentRequestResult(
            payment_url=self.build_payment_url(payment_intent),
            payload={
                "provider": self.provider,
                "requested_at": timezone.now().isoformat(),
            },
        )

    def verify(
        self,
        payment_intent: PaymentIntent,
        *,
        callback_payload: dict | None = None,
        provider_reference: str | None = None,
    ) -> ProviderVerificationResult:
        callback_payload = callback_payload or {}
        provider_status = str(
            callback_payload.get("result")
            or callback_payload.get("status")
            or callback_payload.get("provider_status")
            or "success"
        ).lower()
        provider_reference = (
            provider_reference
            or callback_payload.get("provider_reference")
            or callback_payload.get("ref")
            or callback_payload.get("authority")
        )
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


class ZarinpalPaymentProviderAdapter:
    provider = PaymentProviderChoices.ZARINPAL
    _SANDBOX_REQUEST_URL = "https://sandbox.zarinpal.com/pg/v4/payment/request.json"
    _SANDBOX_VERIFY_URL = "https://sandbox.zarinpal.com/pg/v4/payment/verify.json"
    _SANDBOX_STARTPAY_URL = "https://sandbox.zarinpal.com/pg/StartPay"
    _PRODUCTION_REQUEST_URL = "https://payment.zarinpal.com/pg/v4/payment/request.json"
    _PRODUCTION_VERIFY_URL = "https://payment.zarinpal.com/pg/v4/payment/verify.json"
    _PRODUCTION_STARTPAY_URL = "https://payment.zarinpal.com/pg/StartPay"

    def _is_sandbox(self) -> bool:
        return bool(getattr(settings, "ZARINPAL_SANDBOX", True))

    def _merchant_id(self) -> str:
        return str(getattr(settings, "ZARINPAL_MERCHANT_ID", "00000000-0000-0000-0000-000000000000"))

    def _timeout(self) -> float:
        return float(getattr(settings, "ZARINPAL_HTTP_TIMEOUT_SECONDS", 10))

    def _request_url(self) -> str:
        return self._SANDBOX_REQUEST_URL if self._is_sandbox() else self._PRODUCTION_REQUEST_URL

    def _verify_url(self) -> str:
        return self._SANDBOX_VERIFY_URL if self._is_sandbox() else self._PRODUCTION_VERIFY_URL

    def _startpay_url(self, authority: str) -> str:
        base = self._SANDBOX_STARTPAY_URL if self._is_sandbox() else self._PRODUCTION_STARTPAY_URL
        return f"{base}/{authority}"

    def _callback_url(self, payment_intent: PaymentIntent) -> str:
        base_url = str(getattr(settings, "ZARINPAL_CALLBACK_BASE_URL", "http://localhost:8080")).rstrip("/")
        return (
            f"{base_url}/api/v1/payments/gateway/{self.provider}/callback/"
            f"?payment_intent_id={payment_intent.id}"
        )

    def _safe_request_response(self, payload: dict | None) -> dict:
        data = payload.get("data") if isinstance(payload, dict) else {}
        errors = payload.get("errors") if isinstance(payload, dict) else []
        data = data if isinstance(data, dict) else {}
        return {
            "provider": self.provider,
            "data": {
                "code": data.get("code"),
                "message": data.get("message"),
                "authority": data.get("authority"),
            },
            "errors": errors if isinstance(errors, list) else [],
        }

    def _safe_verify_response(self, payload: dict | None) -> dict:
        data = payload.get("data") if isinstance(payload, dict) else {}
        errors = payload.get("errors") if isinstance(payload, dict) else []
        data = data if isinstance(data, dict) else {}
        return {
            "provider": self.provider,
            "data": {
                "code": data.get("code"),
                "message": data.get("message"),
                "authority": data.get("authority"),
                "ref_id": data.get("ref_id"),
                "card_pan": data.get("card_pan"),
                "card_hash": data.get("card_hash"),
                "fee": data.get("fee"),
                "fee_type": data.get("fee_type"),
            },
            "errors": errors if isinstance(errors, list) else [],
        }

    def _parse_code(self, payload: dict) -> int | None:
        code = payload.get("data", {}).get("code")
        try:
            return int(code)
        except (TypeError, ValueError):
            return None

    def request_payment(self, payment_intent: PaymentIntent) -> ProviderPaymentRequestResult:
        request_payload = {
            "merchant_id": self._merchant_id(),
            "amount": int(payment_intent.amount_minor),
            "currency": payment_intent.currency,
            "description": "HamDong wallet top-up",
            "callback_url": self._callback_url(payment_intent),
            "metadata": {"order_id": str(payment_intent.id)},
        }
        try:
            response = httpx.post(
                self._request_url(),
                json=request_payload,
                timeout=self._timeout(),
            )
        except httpx.TimeoutException as exc:
            raise PaymentProviderRequestError(
                "Zarinpal request timed out.",
                payload={"provider": self.provider, "error": "timeout"},
                provider_status="timeout",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise PaymentProviderRequestError(
                "Zarinpal request failed.",
                payload={"provider": self.provider, "error": exc.__class__.__name__},
                provider_status="request_error",
                retryable=True,
            ) from exc

        body = {}
        try:
            body = response.json()
        except ValueError:
            body = {}
        safe_body = self._safe_request_response(body)

        if response.status_code >= 500:
            raise PaymentProviderRequestError(
                "Zarinpal request failed.",
                payload={**safe_body, "http_status": response.status_code},
                provider_status=f"http_{response.status_code}",
                retryable=True,
            )
        if response.status_code >= 400:
            raise PaymentProviderRequestError(
                "Zarinpal request failed.",
                payload={**safe_body, "http_status": response.status_code},
                provider_status=f"http_{response.status_code}",
            )

        code = self._parse_code(safe_body)
        authority = safe_body["data"].get("authority")
        if code != 100 or not authority:
            raise PaymentProviderRequestError(
                "Zarinpal request failed.",
                payload=safe_body,
                provider_status=str(code) if code is not None else "invalid_response",
                provider_reference=authority,
            )

        return ProviderPaymentRequestResult(
            payment_url=self._startpay_url(str(authority)),
            provider_reference=str(authority),
            provider_status=str(code),
            payload=safe_body,
        )

    def verify(
        self,
        payment_intent: PaymentIntent,
        *,
        callback_payload: dict | None = None,
        provider_reference: str | None = None,
    ) -> ProviderVerificationResult:
        callback_payload = callback_payload or {}
        callback_status = str(
            callback_payload.get("provider_status")
            or callback_payload.get("Status")
            or callback_payload.get("status")
            or ""
        ).upper()
        reference = (
            provider_reference
            or callback_payload.get("provider_reference")
            or callback_payload.get("Authority")
            or callback_payload.get("authority")
            or payment_intent.provider_reference
        )

        if callback_status == "NOK":
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=str(reference) if reference else None,
                provider_amount_minor=int(payment_intent.amount_minor),
                currency=payment_intent.currency,
                provider_status="NOK",
                payload={
                    "provider": self.provider,
                    "data": {"code": -51, "message": "Callback reported NOK."},
                    "errors": [],
                },
            )

        if not reference:
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=None,
                provider_amount_minor=int(payment_intent.amount_minor),
                currency=payment_intent.currency,
                provider_status="missing_authority",
                payload={
                    "provider": self.provider,
                    "data": {"code": None, "message": "Missing authority."},
                    "errors": [],
                },
            )

        verify_payload = {
            "merchant_id": self._merchant_id(),
            "amount": int(payment_intent.amount_minor),
            "authority": str(reference),
        }
        try:
            response = httpx.post(
                self._verify_url(),
                json=verify_payload,
                timeout=self._timeout(),
            )
        except httpx.TimeoutException:
            return ProviderVerificationResult(
                status="RETRYABLE",
                provider_reference=str(reference),
                provider_amount_minor=None,
                currency=payment_intent.currency,
                provider_status="timeout",
                payload={"provider": self.provider, "error": "timeout"},
            )
        except httpx.RequestError as exc:
            return ProviderVerificationResult(
                status="RETRYABLE",
                provider_reference=str(reference),
                provider_amount_minor=None,
                currency=payment_intent.currency,
                provider_status="request_error",
                payload={"provider": self.provider, "error": exc.__class__.__name__},
            )

        body = {}
        try:
            body = response.json()
        except ValueError:
            body = {}
        safe_body = self._safe_verify_response(body)
        if response.status_code >= 500:
            return ProviderVerificationResult(
                status="RETRYABLE",
                provider_reference=str(reference),
                provider_amount_minor=None,
                currency=payment_intent.currency,
                provider_status=f"http_{response.status_code}",
                payload={**safe_body, "http_status": response.status_code},
            )

        code = self._parse_code(safe_body)
        if code in {100, 101}:
            return ProviderVerificationResult(
                status="SUCCEEDED",
                provider_reference=str(reference),
                provider_amount_minor=int(payment_intent.amount_minor),
                currency=payment_intent.currency,
                provider_status=str(code),
                payload=safe_body,
            )

        if code in {-50, -51, -53, -54}:
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=str(reference),
                provider_amount_minor=int(payment_intent.amount_minor),
                currency=payment_intent.currency,
                provider_status=str(code),
                payload=safe_body,
            )

        if response.status_code >= 400:
            return ProviderVerificationResult(
                status="FAILED",
                provider_reference=str(reference),
                provider_amount_minor=int(payment_intent.amount_minor),
                currency=payment_intent.currency,
                provider_status=f"http_{response.status_code}",
                payload={**safe_body, "http_status": response.status_code},
            )

        return ProviderVerificationResult(
            status="FAILED",
            provider_reference=str(reference),
            provider_amount_minor=int(payment_intent.amount_minor),
            currency=payment_intent.currency,
            provider_status=str(code) if code is not None else "invalid_response",
            payload=safe_body,
        )


def get_provider_adapter(provider: str):
    normalized = str(provider or "").upper()
    if normalized == PaymentProviderChoices.FAKE:
        return FakePaymentProviderAdapter()
    if normalized == PaymentProviderChoices.ZARINPAL:
        return ZarinpalPaymentProviderAdapter()
    raise ValueError("Unsupported payment provider.")
