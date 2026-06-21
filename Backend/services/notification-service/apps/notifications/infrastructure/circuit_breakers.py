"""Circuit breaker configuration for notification-service."""

from __future__ import annotations

import pybreaker

from django.conf import settings

_EMAIL_BREAKER: pybreaker.CircuitBreaker | None = None


def get_email_circuit_breaker() -> pybreaker.CircuitBreaker:
    global _EMAIL_BREAKER
    if _EMAIL_BREAKER is None:
        _EMAIL_BREAKER = pybreaker.CircuitBreaker(
            fail_max=settings.EMAIL_CIRCUIT_FAIL_MAX,
            reset_timeout=settings.EMAIL_CIRCUIT_RESET_TIMEOUT_SECONDS,
            name="email-provider-circuit-breaker",
        )
    return _EMAIL_BREAKER


# Backwards-compatible alias.
get_sms_circuit_breaker = get_email_circuit_breaker
