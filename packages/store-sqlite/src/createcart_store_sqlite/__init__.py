"""SQLite storage backends for the CreateCart SDKs.

Implements the menu / cart / payment storage protocols against a single SQLite
database that uses **separate tables per tenant**, suffixed by a numeric
``tenant_id`` assigned ``0..n``. A ``tenants`` table maps each english
``name`` to its ``tenant_id``.

    from createcart_store_sqlite import Database, SqliteMenuStore
    from createcart_registry import MenuRegistry

    db  = Database("createcart.db")
    reg = MenuRegistry(store=SqliteMenuStore(db, "brahmana-naivedyam"))
    # -> tenant 'brahmana-naivedyam' gets id 0 and tables menu_items_0, ...
"""

from .db import Database
from .menu_store import SqliteMenuStore
from .cart_store import SqliteCartStore
from .payment_store import SqlitePaymentStore
from .delivery_store import SqliteDeliveryStore

__all__ = [
    "Database",
    "SqliteMenuStore",
    "SqliteCartStore",
    "SqlitePaymentStore",
    "SqliteDeliveryStore",
]

__version__ = "0.1.0"
