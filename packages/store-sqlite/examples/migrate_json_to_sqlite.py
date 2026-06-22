"""Import a registry menu.json into the SQLite store for a tenant.

Usage:
    python migrate_json_to_sqlite.py <menu.json> <db_path> <tenant-name>

Example:
    python migrate_json_to_sqlite.py ../../registry/examples/brahmana-menu.json \
        ../../../createcart-api/data/createcart.db brahmana-naivedyam
"""

import sys

from createcart_registry import MenuRegistry
from createcart_registry.storage import JSONFileStore
from createcart_store_sqlite import Database, SqliteMenuStore


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(1)
    json_path, db_path, tenant = sys.argv[1], sys.argv[2], sys.argv[3]

    src = MenuRegistry(store=JSONFileStore(json_path))           # read JSON
    db = Database(db_path)
    dst = MenuRegistry(store=SqliteMenuStore(db, tenant), tenant=tenant)

    # copy catalog wholesale
    dst._catalog = src.catalog.model_copy(deep=True)
    dst._catalog.tenant = tenant
    dst._persist()

    tid = db.tenant_id(tenant)
    print(f"Imported {dst.count()} items + {len(dst.list_combos())} combos "
          f"-> tenant '{tenant}' (id {tid}) in {db_path}")


if __name__ == "__main__":
    main()
