"""RabbitMQ publishers for group-service."""

import json
import logging
import pika
from django.conf import settings

logger = logging.getLogger(__name__)


class RabbitMqPublisher:
	def __init__(self):
		self.exchange = getattr(settings, "GROUP_RABBITMQ_EXCHANGE", "hamdong.group")
		self.connection = None
		self.channel = None

	def _connect(self):
		credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
		params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
		self.connection = pika.BlockingConnection(params)
		self.channel = self.connection.channel()

	def publish(self, event: dict, routing_key: str):
		try:
			if not self.channel or self.connection.is_closed:
				self._connect()

			self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
			self.channel.basic_publish(
				exchange=self.exchange,
				routing_key=routing_key,
				body=json.dumps(event),
				properties=pika.BasicProperties(content_type="application/json", delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE),
			)
			logger.info("Published group event %s", event.get("event_type"))
			return True
		except Exception:
			logger.exception("Failed to publish group event")
			return False

