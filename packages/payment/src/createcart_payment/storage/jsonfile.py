"""JSON-file payment record store — one file per order, written atomically."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Optional

from ..models import PaymentRecord

_SAFE_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class JSONFilePaymentStore:
    def __init__(self, directory: str | os.PathLike[str]) -> None:
        self.dir = Path(directory)

    def _path(self, order_id: str) -> Path:
        if not _SAFE_ID.match(order_id):
            raise ValueError(f"unsafe order id {order_id!r}")
        return self.dir / f"{order_id}.json"

    def get(self, order_id: str) -> Optional[PaymentRecord]:
        path = self._path(order_id)
        if not path.exists():
            return None
        return PaymentRecord.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, record: PaymentRecord) -> None:
        path = self._path(record.order_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = record.model_dump_json(indent=2)
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
