"""Compatibility wrappers for notification-service consumers."""

from apps.notifications.infrastructure.rabbitmq_consumer import RabbitMqConsumer


class IdentityOtpConsumer(RabbitMqConsumer):
    """Backward-compatible alias for the idempotent OTP consumer."""

    def start(self) -> None:
        self.start_consuming()
