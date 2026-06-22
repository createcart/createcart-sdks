"""CreateCart Menu Registry SDK.

Headless, framework-agnostic menu management: items, categories, combos,
pricing, availability and stock — backed by a pluggable storage layer.

Quick start::

    from createcart_registry import MenuRegistry
    from createcart_registry.storage import JSONFileStore

    registry = MenuRegistry(store=JSONFileStore("menu.json"))
    registry.add_item(name="Plain Dosa", price="60", category="dosa", icon="🫓")
    available = registry.list_items(available_only=True)
"""

from .models import Category, Combo, MenuCatalog, MenuItem
from .registry import MenuRegistry
from .exceptions import (
    DuplicateItemError,
    ItemNotFoundError,
    OutOfStockError,
    RegistryError,
)

__all__ = [
    "MenuRegistry",
    "MenuItem",
    "Category",
    "Combo",
    "MenuCatalog",
    "RegistryError",
    "ItemNotFoundError",
    "DuplicateItemError",
    "OutOfStockError",
]

__version__ = "0.1.0"
