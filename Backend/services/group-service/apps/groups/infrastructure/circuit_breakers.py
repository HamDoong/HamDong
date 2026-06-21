"""Placeholder for circuit breaker configs used by providers (not used heavily in group-service)."""

def get_breaker(name: str):
    # Return a no-op placeholder
    class Dummy:
        def call(self, fn, *args, **kwargs):
            return fn(*args, **kwargs)

    return Dummy()
