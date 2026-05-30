"""RabbitMQ consumers for group-service."""

import json
import logging
import pika
from django.conf import settings

from apps.groups.infrastructure.repositories import UserProjectionRepository

logger = logging.getLogger(__name__)


class IdentityUserConsumer:
	def __init__(self):
		self.exchange = getattr(settings, "IDENTITY_RABBITMQ_EXCHANGE", "hamdong.identity")
		self.queue = getattr(settings, "GROUP_IDENTITY_QUEUE", "group.identity.user_events")
		self.connection = None
		self.channel = None

	def _connect(self):
		credentials = pika.PlainCredentials(settings.RABBITMQ_DEFAULT_USER, settings.RABBITMQ_DEFAULT_PASS)
		params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT, credentials=credentials)
		self.connection = pika.BlockingConnection(params)
		self.channel = self.connection.channel()

	def _declare(self):
		self.channel.exchange_declare(exchange=self.exchange, exchange_type="topic", durable=True)
		self.channel.queue_declare(queue=self.queue, durable=True)
		self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.created")
		self.channel.queue_bind(queue=self.queue, exchange=self.exchange, routing_key="identity.user.updated")

	def _safe_parse(self, body: bytes):
		try:
			return json.loads(body)
		except Exception:
			logger.exception("Failed to parse message")
			return None

	def _handle_event(self, payload: dict):
		event_type = payload.get("event_type")
		data = payload.get("data") or {}
		if event_type in ("UserCreated", "UserUpdated"):
			identity_user_id = data.get("user_id")
			phone = data.get("phone_number")
			display_name = data.get("display_name")
			first_name = data.get("first_name")
			last_name = data.get("last_name")
			role = data.get("role")
			is_active = data.get("is_active", True)
			if identity_user_id and phone:
				UserProjectionRepository.create_or_update(
					identity_user_id=identity_user_id,
					phone_number=phone,
					display_name=display_name,
					first_name=first_name,
					last_name=last_name,
					role=role,
					is_active=is_active,
				)

	def _callback(self, ch, method, properties, body):
		payload = self._safe_parse(body)
		if not payload:
			ch.basic_ack(delivery_tag=method.delivery_tag)
			return

		try:
			self._handle_event(payload)
			ch.basic_ack(delivery_tag=method.delivery_tag)
		except Exception:
			logger.exception("Failed to process identity event")
			ch.basic_ack(delivery_tag=method.delivery_tag)

	def start(self):
		self._connect()
		self._declare()
		self.channel.basic_qos(prefetch_count=1)
		self.channel.basic_consume(queue=self.queue, on_message_callback=self._callback)
		logger.info("Starting identity consumer for queue=%s", self.queue)
		try:
			self.channel.start_consuming()
		except KeyboardInterrupt:
			logger.info("Consumer interrupted")
		finally:
			if self.connection and not self.connection.is_closed:
				self.connection.close()

