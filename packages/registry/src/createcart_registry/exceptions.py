"""Exceptions raised by the menu registry."""


class RegistryError(Exception):
    """Base class for all registry errors."""


class ItemNotFoundError(RegistryError):
    """Raised when an item / category / combo id does not exist."""


class DuplicateItemError(RegistryError):
    """Raised when creating an entity whose id already exists."""


class OutOfStockError(RegistryError):
    """Raised when a stock operation would push stock below zero."""
