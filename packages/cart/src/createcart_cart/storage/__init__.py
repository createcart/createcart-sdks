"""Pluggable storage backends for carts.

A backend implements :class:`CartStore` (``load`` / ``save`` / ``delete``).
Unlike the menu (one catalog), there are many carts keyed by ``cart_id``.

* :class:`InMemoryCartStore` — ephemeral, for tests/prototypes.
* :class:`JSONFileCartStore` — one ``<cart_id>.json`` per cart in a directory.

A Redis/Postgres backend can be added later by implementing the same three
methods — no cart or app code changes required.
"""

from .base import CartStore
from .memory import InMemoryCartStore
from .jsonfile import JSONFileCartStore

__all__ = ["CartStore", "InMemoryCartStore", "JSONFileCartStore"]
