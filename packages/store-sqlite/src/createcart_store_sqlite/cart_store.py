"""SQLite CartStore — per-tenant carts_<id> table (one row per cart)."""

from __future__ import annotations

from contextlib import closing
from typing import Optional

from createcart_cart.models import CartData

from .db import Database


class SqliteCartStore:
    """Implements the cart's CartStore protocol (load/save/delete) for one tenant.

    The cart aggregate is stored as JSON in ``carts_<tenant_id>``; carts are
    transient and read/written whole, so a JSON column keeps it simple and exact.
    """

    def __init__(self, db: Database, tenant: str) -> None:
        self.db = db
        self.tenant = tenant
        self.tid = db.get_or_create_tenant(tenant)

    def load(self, cart_id: str) -> Optional[CartData]:
        with closing(self.db.connect()) as conn:
            row = conn.execute(
                f"SELECT data FROM carts_{self.tid} WHERE cart_id=?", (cart_id,)
            ).fetchone()
        return CartData.model_validate_json(row["data"]) if row else None

    def save(self, cart: CartData) -> None:
        with self.db.connect() as conn:
            conn.execute(
                f"INSERT INTO carts_{self.tid} (cart_id, data) VALUES (?, ?) "
                f"ON CONFLICT(cart_id) DO UPDATE SET data=excluded.data",
                (cart.id, cart.model_dump_json()),
            )

    def delete(self, cart_id: str) -> None:
        with self.db.connect() as conn:
            conn.execute(f"DELETE FROM carts_{self.tid} WHERE cart_id=?", (cart_id,))
