class NoopCircuitBreaker:
    def call(self, func, *args, **kwargs):
        return func(*args, **kwargs)
