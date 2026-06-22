"""SQLite MenuStore — normalized per-tenant tables menu_items_<id> etc."""

from __future__ import annotations

import json
from contextlib import closing

from createcart_registry.models import Category, Combo, MenuCatalog, MenuItem

from .db import Database


class SqliteMenuStore:
    """Implements the registry's MenuStore protocol (load/save) for one tenant."""

    def __init__(self, db: Database, tenant: str) -> None:
        self.db = db
        self.tenant = tenant
        self.tid = db.get_or_create_tenant(tenant)

    def load(self) -> MenuCatalog:
        with closing(self.db.connect()) as conn:
            items = [
                MenuItem(
                    id=r["id"], name=r["name"], name_localized=r["name_localized"],
                    description=r["description"] or "", price=r["price"] or "0",
                    currency=r["currency"] or "INR", image_url=r["image_url"],
                    icon=r["icon"], category=r["category"],
                    tags=json.loads(r["tags"] or "[]"),
                    available=bool(r["available"]), stock=r["stock"],
                    sort_order=r["sort_order"] or 0,
                    metadata=json.loads(r["metadata"] or "{}"),
                )
                for r in conn.execute(f"SELECT * FROM menu_items_{self.tid}")
            ]
            categories = [
                Category(
                    id=r["id"], name=r["name"], sort_order=r["sort_order"] or 0,
                    metadata=json.loads(r["metadata"] or "{}"),
                )
                for r in conn.execute(f"SELECT * FROM categories_{self.tid}")
            ]
            combos = [
                Combo(
                    id=r["id"], name=r["name"], price=r["price"] or "0",
                    currency=r["currency"] or "INR", description=r["description"] or "",
                    item_ids=json.loads(r["item_ids"] or "[]"),
                    tags=json.loads(r["tags"] or "[]"),
                    available=bool(r["available"]), sort_order=r["sort_order"] or 0,
                    metadata=json.loads(r["metadata"] or "{}"),
                )
                for r in conn.execute(f"SELECT * FROM combos_{self.tid}")
            ]
        return MenuCatalog(
            tenant=self.tenant, items=items, categories=categories, combos=combos
        )

    def save(self, catalog: MenuCatalog) -> None:
        tid = self.tid
        with self.db.connect() as conn:  # transaction
            conn.execute(f"DELETE FROM menu_items_{tid}")
            conn.execute(f"DELETE FROM categories_{tid}")
            conn.execute(f"DELETE FROM combos_{tid}")
            conn.executemany(
                f"INSERT INTO menu_items_{tid} (id,name,name_localized,description,"
                f"price,currency,image_url,icon,category,tags,available,stock,"
                f"sort_order,metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        i.id, i.name, i.name_localized, i.description, str(i.price),
                        i.currency, i.image_url, i.icon, i.category,
                        json.dumps(i.tags), int(i.available), i.stock,
                        i.sort_order, json.dumps(i.metadata),
                    )
                    for i in catalog.items
                ],
            )
            conn.executemany(
                f"INSERT INTO categories_{tid} (id,name,sort_order,metadata) "
                f"VALUES (?,?,?,?)",
                [
                    (c.id, c.name, c.sort_order, json.dumps(c.metadata))
                    for c in catalog.categories
                ],
            )
            conn.executemany(
                f"INSERT INTO combos_{tid} (id,name,price,currency,description,"
                f"item_ids,tags,available,sort_order,metadata) "
                f"VALUES (?,?,?,?,?,?,?,?,?,?)",
                [
                    (
                        c.id, c.name, str(c.price), c.currency, c.description,
                        json.dumps(c.item_ids), json.dumps(c.tags),
                        int(c.available), c.sort_order, json.dumps(c.metadata),
                    )
                    for c in catalog.combos
                ],
            )
