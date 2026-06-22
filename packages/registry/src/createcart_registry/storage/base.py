"""The storage contract every backend implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import MenuCatalog


@runtime_checkable
class MenuStore(Protocol):
    """Loads and persists a whole :class:`MenuCatalog`.

    The catalog for a single menu is small, so backends work at whole-catalog
    granularity. The registry calls ``load()`` once on construction and
    ``save()`` after every mutation.
    """

    def load(self) -> MenuCatalog:
        """Return the persisted catalog (or an empty one if none exists)."""
        ...

    def save(self, catalog: MenuCatalog) -> None:
        """Persist the given catalog, overwriting any previous state."""
        ...
