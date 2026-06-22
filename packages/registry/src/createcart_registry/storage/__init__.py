"""Pluggable storage backends for the menu registry.

A backend only has to implement :class:`MenuStore` (``load`` + ``save``).
Two are bundled:

* :class:`InMemoryStore` — ephemeral, great for tests and prototypes.
* :class:`JSONFileStore` — persists the whole catalog to a JSON file on disk.

A Supabase / Postgres backend can be added later by implementing the same
two methods — no registry or app code changes required.
"""

from .base import MenuStore
from .memory import InMemoryStore
from .jsonfile import JSONFileStore

__all__ = ["MenuStore", "InMemoryStore", "JSONFileStore"]
