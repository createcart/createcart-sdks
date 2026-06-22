"""The Cart — every cart operation and the totals calculation.

A ``Cart`` wraps one cart_id and persists through its
:class:`~createcart_cart.storage.base.CartStore` after each mutation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional

from .exceptions import CartItemNotFoundError, InvalidQuantityError
from .models import (
    CartData,
    CartItem,
    CartTotals,
    Charge,
    Discount,
    to_money,
)
from .storage.base import CartStore
from .storage.memory import InMemoryCartStore

CENTS = Decimal("0.01")
HUNDRED = Decimal("100")


class Cart:
    """Operations on a single cart: line items, charges, discount, tax, totals."""

    def __init__(
        self,
        cart_id: str,
        store: Optional[CartStore] = None,
        *,
        currency: str = "INR",
    ) -> None:
        self._store: CartStore = store or InMemoryCartStore()
        self._data: CartData = self._store.load(cart_id) or CartData(
            id=cart_id, currency=currency
        )

    # ── persistence ──────────────────────────────────────────────────────
    def _persist(self) -> None:
        self._store.save(self._data)

    def reload(self) -> None:
        loaded = self._store.load(self._data.id)
        if loaded is not None:
            self._data = loaded

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def data(self) -> CartData:
        """The live cart aggregate (treat as read-only)."""
        return self._data

    @property
    def is_empty(self) -> bool:
        return not self._data.items

    # ── line items ───────────────────────────────────────────────────────
    def _find(self, item_id: str) -> Optional[CartItem]:
        for item in self._data.items:
            if item.item_id == item_id:
                return item
        return None

    def add_item(
        self,
        item_id: str,
        *,
        name: str,
        unit_price: Decimal | float | int | str,
        quantity: int = 1,
        icon: Optional[str] = None,
        image_url: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> CartItem:
        """Add ``quantity`` of an item. If it's already in the cart, the
        quantity is increased (and price/name refreshed to the latest values)."""
        if quantity < 1:
            raise InvalidQuantityError("quantity to add must be >= 1")
        existing = self._find(item_id)
        if existing is not None:
            existing.quantity += quantity
            existing.unit_price = to_money(unit_price)  # refresh to latest price
            existing.name = name
            if icon is not None:
                existing.icon = icon
            if image_url is not None:
                existing.image_url = image_url
            if metadata is not None:
                existing.metadata = metadata
            item = existing
        else:
            item = CartItem(
                item_id=item_id,
                name=name,
                unit_price=unit_price,
                quantity=quantity,
                icon=icon,
                image_url=image_url,
                metadata=metadata or {},
            )
            self._data.items.append(item)
        self._persist()
        return item

    def get_item(self, item_id: str) -> CartItem:
        item = self._find(item_id)
        if item is None:
            raise CartItemNotFoundError(f"{item_id!r} is not in the cart")
        return item

    def find_item(self, item_id: str) -> Optional[CartItem]:
        return self._find(item_id)

    def increment(self, item_id: str, by: int = 1) -> CartItem:
        if by < 1:
            raise InvalidQuantityError("increment must be >= 1")
        item = self.get_item(item_id)
        item.quantity += by
        self._persist()
        return item

    def decrement(self, item_id: str, by: int = 1) -> Optional[CartItem]:
        """Reduce quantity by ``by``. Removes the line if it reaches 0 and
        returns ``None`` in that case."""
        if by < 1:
            raise InvalidQuantityError("decrement must be >= 1")
        item = self.get_item(item_id)
        item.quantity -= by
        if item.quantity <= 0:
            self._data.items.remove(item)
            self._persist()
            return None
        self._persist()
        return item

    def set_quantity(self, item_id: str, quantity: int) -> Optional[CartItem]:
        """Set an exact quantity. ``quantity <= 0`` removes the line."""
        item = self.get_item(item_id)
        if quantity <= 0:
            self._data.items.remove(item)
            self._persist()
            return None
        item.quantity = quantity
        self._persist()
        return item

    def remove_item(self, item_id: str) -> None:
        item = self.get_item(item_id)
        self._data.items.remove(item)
        self._persist()

    def clear(self) -> None:
        """Remove all items (keeps charges/discount/tax settings)."""
        self._data.items.clear()
        self._persist()

    def list_items(self) -> list[CartItem]:
        return list(self._data.items)

    def count(self) -> int:
        """Number of distinct line items."""
        return len(self._data.items)

    def total_quantity(self) -> int:
        """Sum of quantities across all lines."""
        return sum(i.quantity for i in self._data.items)

    # ── charges / discount / tax ─────────────────────────────────────────
    def add_charge(
        self, code: str, label: str, amount: Decimal | float | int | str
    ) -> Charge:
        """Add (or replace, by ``code``) a fixed charge such as a parcel fee."""
        self._data.charges = [c for c in self._data.charges if c.code != code]
        charge = Charge(code=code, label=label, amount=amount)
        self._data.charges.append(charge)
        self._persist()
        return charge

    def remove_charge(self, code: str) -> None:
        self._data.charges = [c for c in self._data.charges if c.code != code]
        self._persist()

    def clear_charges(self) -> None:
        self._data.charges.clear()
        self._persist()

    def set_discount(
        self,
        kind: str,
        value: Decimal | float | int | str,
        *,
        code: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Discount:
        discount = Discount(kind=kind, value=value, code=code, label=label)
        self._data.discount = discount
        self._persist()
        return discount

    def clear_discount(self) -> None:
        self._data.discount = None
        self._persist()

    def set_tax_rate(self, percent: Decimal | float | int | str) -> None:
        rate = percent if isinstance(percent, Decimal) else Decimal(str(percent))
        if rate < 0:
            raise ValueError("tax rate cannot be negative")
        self._data.tax_rate = rate
        self._persist()

    # ── totals ───────────────────────────────────────────────────────────
    def _discount_total(self, subtotal: Decimal) -> Decimal:
        d = self._data.discount
        if d is None:
            return Decimal("0.00")
        if d.kind == "percent":
            amount = subtotal * d.value / HUNDRED
        else:  # fixed
            amount = d.value
        amount = min(to_money(amount), subtotal)  # never discount below zero
        return to_money(amount)

    def totals(self) -> CartTotals:
        """Compute the monetary summary.

        Order: subtotal -> minus discount -> tax on the discounted base ->
        plus charges -> grand total.
        """
        subtotal = to_money(sum((i.line_total for i in self._data.items), Decimal("0")))
        discount_total = self._discount_total(subtotal)
        taxable = subtotal - discount_total
        tax_total = to_money(taxable * self._data.tax_rate / HUNDRED)
        charges_total = to_money(
            sum((c.amount for c in self._data.charges), Decimal("0"))
        )
        grand_total = to_money(taxable + tax_total + charges_total)
        return CartTotals(
            currency=self._data.currency,
            item_count=self.count(),
            total_quantity=self.total_quantity(),
            subtotal=subtotal,
            discount_total=discount_total,
            tax_total=tax_total,
            charges_total=charges_total,
            grand_total=grand_total,
        )

    # ── serialization ────────────────────────────────────────────────────
    def to_dict(self, *, with_totals: bool = True) -> dict[str, Any]:
        """JSON-ready cart. Includes computed ``totals`` and per-line
        ``line_total`` by default (handy for a frontend)."""
        data = self._data.model_dump(mode="json")
        if with_totals:
            for raw, item in zip(data["items"], self._data.items):
                raw["line_total"] = str(item.line_total)
            data["totals"] = self.totals().model_dump(mode="json")
        return data

    def to_json(self, *, indent: int | None = 2) -> str:
        import json

        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
