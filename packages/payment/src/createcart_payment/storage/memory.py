"""In-memory payment record store — for tests/prototypes."""

from __future__ import annotations

from typing import Optional

from ..models import PaymentRecord


class InMemoryPaymentStore:
    def __init__(self) -> None:
        self._records: dict[str, PaymentRecord] = {}

    def get(self, order_id: str) -> Optional[PaymentRecord]:
        rec = self._records.get(order_id)
        return rec.model_copy(deep=True) if rec is not None else None

    def save(self, record: PaymentRecord) -> None:
        self._records[record.order_id] = record.model_copy(deep=True)
