"""Pluggable storage for payment records (created -> paid/failed).

Implement :class:`PaymentStore` (``get`` / ``save``) to persist anywhere.
Ships with in-memory and JSON-file backends.
"""

from .base import PaymentStore
from .memory import InMemoryPaymentStore
from .jsonfile import JSONFilePaymentStore

__all__ = ["PaymentStore", "InMemoryPaymentStore", "JSONFilePaymentStore"]
