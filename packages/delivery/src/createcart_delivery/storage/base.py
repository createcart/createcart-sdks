"""The storage contract every delivery backend implements."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ..models import DeliveryOrder


@runtime_checkable
class DeliveryStore(Protocol):
    """Persists delivery orders by id and lists them."""

    def get(self, order_id: str) -> Optional[DeliveryOrder]:
        """Return the order, or ``None`` if unknown."""
        ...

    def save(self, order: DeliveryOrder) -> None:
        """Persist (insert or update) the order."""
        ...

    def list(self) -> list[DeliveryOrder]:
        """Return all orders (the service filters/sorts as needed)."""
        ...
