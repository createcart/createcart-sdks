"""Exceptions raised by the cart SDK."""


class CartError(Exception):
    """Base class for all cart errors."""


class CartItemNotFoundError(CartError):
    """Raised when an operation targets a line item not in the cart."""


class InvalidQuantityError(CartError):
    """Raised when a quantity argument is invalid (e.g. negative)."""
