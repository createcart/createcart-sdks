"""JSON-file storage backend — persists the catalog to disk atomically."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from ..models import MenuCatalog


class JSONFileStore:
    """Persists the catalog as pretty-printed JSON at ``path``.

    Writes are atomic (temp file + replace) so a crash mid-save can never
    leave a half-written, corrupt menu file.
    """

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def load(self) -> MenuCatalog:
        if not self.path.exists():
            return MenuCatalog()
        data = self.path.read_text(encoding="utf-8")
        if not data.strip():
            return MenuCatalog()
        return MenuCatalog.model_validate_json(data)

    def save(self, catalog: MenuCatalog) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = catalog.model_dump_json(indent=2)
        # Atomic write: dump to a temp file in the same dir, then replace.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, self.path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
