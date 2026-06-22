"""Postgres DeliveryStore — per-tenant deliveries_<id> table.

Stores the order as JSON text plus denormalized ``status`` / ``created_at``
columns so deliveries can be listed/filtered with plain SQL.
"""

from __future__ import annotations

from typing import Optional

from createcart_delivery.models import DeliveryOrder

from .db import PgDatabase


class PgDeliveryStore:
    """Implements the delivery SDK's DeliveryStore protocol for one tenant."""

    def __init__(self, db: PgDatabase, tenant: str) -> None:
        self.db = db
        self.tenant = tenant
        self.tid = db.get_or_create_tenant(tenant)

    def get(self, order_id: str) -> Optional[DeliveryOrder]:
        with self.db.connect() as conn:
            row = conn.execute(
                f"SELECT data FROM deliveries_{self.tid} WHERE order_id=%s",
                (order_id,),
            ).fetchone()
        return DeliveryOrder.model_validate_json(row["data"]) if row else None

    def save(self, order: DeliveryOrder) -> None:
        created = order.created_at.isoformat() if order.created_at else None
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO deliveries_{self.tid} "
                f"(order_id, status, created_at, data) VALUES (%s,%s,%s,%s) "
                f"ON CONFLICT (order_id) DO UPDATE SET "
                f"status=excluded.status, data=excluded.data",
                (order.id, order.status.value, created, order.model_dump_json()),
            )

    def list(self) -> list[DeliveryOrder]:
        with self.db.connect() as conn:
            rows = conn.execute(
                f"SELECT data FROM deliveries_{self.tid}"
            ).fetchall()
        return [DeliveryOrder.model_validate_json(r["data"]) for r in rows]
