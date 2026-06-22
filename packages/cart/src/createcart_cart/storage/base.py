"""The storage contract every cart backend implements."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ..models import CartData


@runtime_checkable
class CartStore(Protocol):
    """Loads, persists and deletes carts by id."""

    def load(self, cart_id: str) -> Optional[CartData]:
        """Return the persisted cart, or ``None`` if it doesn't exist yet."""
        ...

    def save(self, cart: CartData) -> None:
        """Persist the cart, overwriting any previous state."""
        ...

    def delete(self, cart_id: str) -> None:
        """Remove the cart. No-op if it doesn't exist."""
        ...
