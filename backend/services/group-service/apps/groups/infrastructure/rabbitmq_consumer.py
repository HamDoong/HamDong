"""Compatibility wrapper for the group-service RabbitMQ consumer.

This module exposes `IdentityUserConsumer` for management commands or external callers.
"""

from apps.groups.infrastructure.consumers import IdentityUserConsumer

# Re-export the consumer class under this module name for compatibility
IdentityUserConsumer = IdentityUserConsumer
