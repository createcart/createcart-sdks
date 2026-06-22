"""In-memory storage backend — non-persistent, ideal for tests/prototypes."""

from __future__ import annotations

from ..models import MenuCatalog


class InMemoryStore:
    """Holds the catalog in process memory. Lost when the process exits."""

    def __init__(self, catalog: MenuCatalog | None = None) -> None:
        self._catalog = catalog or MenuCatalog()

    def load(self) -> MenuCatalog:
        # Return a copy so external mutation can't bypass the registry.
        return self._catalog.model_copy(deep=True)

    def save(self, catalog: MenuCatalog) -> None:
        self._catalog = catalog.model_copy(deep=True)
