"""Exceptions raised by the delivery SDK."""


class DeliveryError(Exception):
    """Base class for all delivery errors."""


class DeliveryNotFoundError(DeliveryError):
    """Raised when an order id does not exist."""


class InvalidTransitionError(DeliveryError):
    """Raised when a status change isn't allowed from the current status."""
