"""Simple placeholder for circuit breaker utilities used by infra clients."""


class NoopCircuitBreaker:
    def call(self, func, *args, **kwargs):
        return func(*args, **kwargs)
