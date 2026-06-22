"""Postgres / Supabase storage backends for the CreateCart SDKs.

A faithful port of ``createcart-store-sqlite`` to Postgres: one database with
**separate tables per tenant**, suffixed by a numeric ``tenant_id`` assigned
``0..n``, and a ``tenants`` table mapping each english ``name`` to its id.
Implements the menu / cart / payment / delivery storage protocols, so the SDKs
gain a Postgres backend with **no SDK or API logic changes** — just swap the store.

    from createcart_store_postgres import PgDatabase, PgMenuStore
    from createcart_registry import MenuRegistry

    db  = PgDatabase("postgresql://user:pass@host:6543/postgres")  # Supabase pooler
    reg = MenuRegistry(store=PgMenuStore(db, "brahmana-naivedyam"))
"""

from .db import PgDatabase
from .menu_store import PgMenuStore
from .cart_store import PgCartStore
from .payment_store import PgPaymentStore
from .delivery_store import PgDeliveryStore

__all__ = [
    "PgDatabase",
    "PgMenuStore",
    "PgCartStore",
    "PgPaymentStore",
    "PgDeliveryStore",
]

__version__ = "0.1.0"
