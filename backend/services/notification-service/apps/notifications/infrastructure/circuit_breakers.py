"""Circuit breaker configuration for notification-service."""

import pybreaker

from django.conf import settings

_SMS_BREAKER: pybreaker.CircuitBreaker | None = None


def get_sms_circuit_breaker() -> pybreaker.CircuitBreaker:
    global _SMS_BREAKER
    if _SMS_BREAKER is None:
        _SMS_BREAKER = pybreaker.CircuitBreaker(
            fail_max=settings.SMS_CIRCUIT_FAIL_MAX,
            reset_timeout=settings.SMS_CIRCUIT_RESET_TIMEOUT_SECONDS,
            name="sms-provider-circuit-breaker",
        )
    return _SMS_BREAKER
