"""CreateCart Cart SDK.

Headless shopping cart: add / increase / decrease / remove line items, plus
charges (e.g. parcel fee), discounts and tax — with computed totals and a
pluggable storage layer. Decoupled from the menu registry: prices are passed
in by the caller (the API looks them up authoritatively), so the cart can never
be tricked into trusting a client-supplied price.

Quick start::

    from createcart_cart import Cart
    from createcart_cart.storage import InMemoryCartStore

    cart = Cart("sess-123", store=InMemoryCartStore())
    cart.add_item("plain-dosa", name="Plain Dosa", unit_price="60", quantity=2)
    cart.add_charge("parcel", "Parcel charge", "10")
    totals = cart.totals()        # grand_total etc.
"""

from .cart import Cart
from .models import CartData, CartItem, CartTotals, Charge, Discount
from .exceptions import (
    CartError,
    CartItemNotFoundError,
    InvalidQuantityError,
)

__all__ = [
    "Cart",
    "CartData",
    "CartItem",
    "CartTotals",
    "Charge",
    "Discount",
    "CartError",
    "CartItemNotFoundError",
    "InvalidQuantityError",
]

__version__ = "0.1.0"
