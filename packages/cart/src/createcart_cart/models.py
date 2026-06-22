"""Pydantic models for the cart.

Money is :class:`decimal.Decimal` throughout (never float). Every model is
JSON-serializable so a cart can flow SDK -> API -> frontend unchanged.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

CENTS = Decimal("0.01")


def to_money(value: Any) -> Decimal:
    """Coerce ints/floats/strings into a 2-dp Decimal."""
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(CENTS)


class CartItem(BaseModel):
    """A single line in the cart."""

    item_id: str
    name: str
    unit_price: Decimal = Field(ge=0)
    quantity: int = Field(ge=1)
    icon: Optional[str] = None
    image_url: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce_price(cls, v: Any) -> Decimal:
        return to_money(v)

    @property
    def line_total(self) -> Decimal:
        return to_money(self.unit_price * self.quantity)


class Charge(BaseModel):
    """A fixed amount added to the order (e.g. parcel/packaging fee)."""

    code: str
    label: str
    amount: Decimal

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v: Any) -> Decimal:
        return to_money(v)


class Discount(BaseModel):
    """A cart-level discount, either a percentage or a fixed amount."""

    kind: Literal["percent", "fixed"]
    value: Decimal = Field(ge=0)
    code: Optional[str] = None
    label: Optional[str] = None

    @field_validator("value", mode="before")
    @classmethod
    def _coerce_value(cls, v: Any) -> Decimal:
        d = v if isinstance(v, Decimal) else Decimal(str(v))
        return d


class CartData(BaseModel):
    """The persisted cart aggregate — the unit storage loads and saves."""

    id: str
    currency: str = "INR"
    items: list[CartItem] = Field(default_factory=list)
    charges: list[Charge] = Field(default_factory=list)
    discount: Optional[Discount] = None
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0)  # percent, e.g. 5 = 5%
    metadata: dict[str, Any] = Field(default_factory=dict)


class CartTotals(BaseModel):
    """Computed monetary summary of a cart."""

    currency: str
    item_count: int        # distinct line items
    total_quantity: int    # sum of quantities
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    charges_total: Decimal
    grand_total: Decimal
