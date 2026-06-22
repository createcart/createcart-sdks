"""In-memory cart storage — non-persistent, for tests/prototypes."""

from __future__ import annotations

from typing import Optional

from ..models import CartData


class InMemoryCartStore:
    """Holds carts in a process-local dict, keyed by cart id."""

    def __init__(self) -> None:
        self._carts: dict[str, CartData] = {}

    def load(self, cart_id: str) -> Optional[CartData]:
        cart = self._carts.get(cart_id)
        return cart.model_copy(deep=True) if cart is not None else None

    def save(self, cart: CartData) -> None:
        self._carts[cart.id] = cart.model_copy(deep=True)

    def delete(self, cart_id: str) -> None:
        self._carts.pop(cart_id, None)
