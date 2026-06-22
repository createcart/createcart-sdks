"""Pluggable storage backends for delivery orders.

Implement :class:`DeliveryStore` (``get`` / ``save`` / ``list``) to persist
anywhere. Ships with in-memory and JSON-file backends.
"""

from .base import DeliveryStore
from .memory import InMemoryDeliveryStore
from .jsonfile import JSONFileDeliveryStore

__all__ = ["DeliveryStore", "InMemoryDeliveryStore", "JSONFileDeliveryStore"]
