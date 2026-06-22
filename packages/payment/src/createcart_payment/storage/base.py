"""The storage contract for payment records."""

from __future__ import annotations

from typing import Optional, Protocol, runtime_checkable

from ..models import PaymentRecord


@runtime_checkable
class PaymentStore(Protocol):
    """Persists payment records keyed by ``order_id``."""

    def get(self, order_id: str) -> Optional[PaymentRecord]:
        """Return the record, or ``None`` if unknown."""
        ...

    def save(self, record: PaymentRecord) -> None:
        """Persist (insert or update) the record."""
        ...
