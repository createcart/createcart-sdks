"""In-memory delivery store — for tests/prototypes."""

from __future__ import annotations

from typing import Optional

from ..models import DeliveryOrder


class InMemoryDeliveryStore:
    def __init__(self) -> None:
        self._orders: dict[str, DeliveryOrder] = {}

    def get(self, order_id: str) -> Optional[DeliveryOrder]:
        o = self._orders.get(order_id)
        return o.model_copy(deep=True) if o is not None else None

    def save(self, order: DeliveryOrder) -> None:
        self._orders[order.id] = order.model_copy(deep=True)

    def list(self) -> list[DeliveryOrder]:
        return [o.model_copy(deep=True) for o in self._orders.values()]
