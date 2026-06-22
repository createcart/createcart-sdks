"""JSON-file cart storage — one file per cart, written atomically."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from ..models import CartData

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def _check_id(cart_id: str) -> str:
    if not _SAFE_ID.match(cart_id):
        raise ValueError(
            f"unsafe cart id {cart_id!r}: use 1-128 chars of [A-Za-z0-9_-]"
        )
    return cart_id


class JSONFileCartStore:
    """Persists each cart as ``<dir>/<cart_id>.json`` with atomic writes."""

    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self.dir = Path(directory)

    def _path(self, cart_id: str) -> Path:
        return self.dir / f"{_check_id(cart_id)}.json"

    def load(self, cart_id: str) -> Optional[CartData]:
        path = self._path(cart_id)
        if not path.exists():
            return None
        data = path.read_text(encoding="utf-8")
        if not data.strip():
            return None
        return CartData.model_validate_json(data)

    def save(self, cart: CartData) -> None:
        path = self._path(cart.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = cart.model_dump_json(indent=2)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    def delete(self, cart_id: str) -> None:
        path = self._path(cart_id)
        if path.exists():
            path.unlink()
