"""Pydantic models for the menu registry.

Money is stored as :class:`decimal.Decimal` (never float) to avoid rounding
errors. Every model is fully JSON-serializable via ``model_dump_json`` so the
same objects can flow straight from the SDK to a FastAPI response to the JS
frontend.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

_SLUG_STRIP = re.compile(r"[^\w\s-]")
_SLUG_DASH = re.compile(r"[\s_-]+")


def slugify(text: str) -> str:
    """Turn a human name into a url/id-safe slug (``"Ghee Masala Dosa"`` ->
    ``"ghee-masala-dosa"``)."""
    text = _SLUG_STRIP.sub("", text.strip().lower())
    text = _SLUG_DASH.sub("-", text)
    return text.strip("-")


def _to_money(value: Any) -> Decimal:
    """Coerce ints, floats and strings into a 2-dp Decimal."""
    if isinstance(value, Decimal):
        d = value
    else:
        # str() first so float inputs like 70.1 don't carry binary noise.
        d = Decimal(str(value))
    return d.quantize(Decimal("0.01"))


class MenuItem(BaseModel):
    """A single sellable menu item."""

    id: str
    name: str
    name_localized: Optional[str] = None  # e.g. Telugu / regional name
    description: str = ""
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = "INR"
    image_url: Optional[str] = None
    icon: Optional[str] = None  # emoji fallback when there's no photo
    category: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    available: bool = True
    stock: Optional[int] = None  # None = unlimited / not tracked
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("price", mode="before")
    @classmethod
    def _coerce_price(cls, v: Any) -> Decimal:
        return _to_money(v)

    @property
    def in_stock(self) -> bool:
        """True when the item can currently be ordered."""
        if not self.available:
            return False
        return self.stock is None or self.stock > 0


class Category(BaseModel):
    """A grouping of menu items (e.g. ``dosa``, ``rice``, ``sweets``)."""

    id: str
    name: str
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class Combo(BaseModel):
    """A bundle sold at a single price (e.g. *any three rice items*)."""

    id: str
    name: str
    price: Decimal = Field(default=Decimal("0.00"), ge=0)
    currency: str = "INR"
    description: str = ""
    item_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    available: bool = True
    sort_order: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("price", mode="before")
    @classmethod
    def _coerce_price(cls, v: Any) -> Decimal:
        return _to_money(v)


class MenuCatalog(BaseModel):
    """The complete menu for one tenant — the unit the storage layer loads and
    saves as a whole."""

    tenant: Optional[str] = None
    currency: str = "INR"
    items: list[MenuItem] = Field(default_factory=list)
    categories: list[Category] = Field(default_factory=list)
    combos: list[Combo] = Field(default_factory=list)
