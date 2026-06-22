"""SQLite PaymentStore — per-tenant payments_<id> table.

Stores the full record as JSON plus denormalized columns (status, amount,
provider, …) so payments can also be queried/reconciled with plain SQL.
"""

from __future__ import annotations

from contextlib import closing
from typing import Optional

from createcart_payment.models import PaymentRecord

from .db import Database


class SqlitePaymentStore:
    """Implements the payment SDK's PaymentStore protocol (get/save) for one tenant."""

    def __init__(self, db: Database, tenant: str) -> None:
        self.db = db
        self.tenant = tenant
        self.tid = db.get_or_create_tenant(tenant)

    def get(self, order_id: str) -> Optional[PaymentRecord]:
        with closing(self.db.connect()) as conn:
            row = conn.execute(
                f"SELECT data FROM payments_{self.tid} WHERE order_id=?", (order_id,)
            ).fetchone()
        return PaymentRecord.model_validate_json(row["data"]) if row else None

    def save(self, record: PaymentRecord) -> None:
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO payments_{self.tid} "
                f"(order_id,status,amount,currency,provider,cart_id,payment_id,data) "
                f"VALUES (?,?,?,?,?,?,?,?) "
                f"ON CONFLICT(order_id) DO UPDATE SET "
                f"status=excluded.status, payment_id=excluded.payment_id, "
                f"data=excluded.data",
                (
                    record.order_id, record.status.value, record.amount,
                    record.currency, record.provider, record.cart_id,
                    record.payment_id, record.model_dump_json(),
                ),
            )
