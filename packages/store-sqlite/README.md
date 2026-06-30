# createcart-store-sqlite — SQLite storage backends

DB-backed storage for the CreateCart SDKs. One SQLite database, **separate tables
per tenant**, with a `tenants` registry mapping a numeric `tenant_id` (`0..n`) to
an english `name`. Implements the menu / cart / payment storage protocols, so the
SDKs gain a database with **no SDK code changes** — just swap the store.

- **Language:** Python ≥ 3.10 · stdlib `sqlite3` (no extra deps)
- **Import:** `createcart_store_sqlite`

---

## Schema

```
tenants(id INTEGER PK 0..n, name TEXT UNIQUE,         -- name → id mapping
        password_hash TEXT, base_url TEXT)            -- tenant admin auth + stored API base url

-- created on demand, one set per tenant (suffix = tenant_id):
menu_items_<id>(id, name, name_localized, description, price, currency,
                image_url, icon, category, tags, available, stock, sort_order, metadata)
categories_<id>(id, name, sort_order, metadata)
combos_<id>(id, name, price, currency, description, item_ids, tags, available, sort_order, metadata)
carts_<id>(cart_id PK, data)                          -- cart aggregate as JSON
payments_<id>(order_id PK, status, amount, currency, provider, cart_id, payment_id, data)
deliveries_<id>(order_id PK, status, created_at, data) -- delivery order + timeline as JSON
```

The `password_hash` / `base_url` columns are added automatically to older
databases via a lightweight migration on open (opaque hash — the API hashes and
verifies; this layer only stores it).

`tenant_id` starts at **0** and increments. Tenant names must be lowercase
english words/slugs (`brahmana-naivedyam`) — validated, which also keeps the
generated table names safe.

## What's inside

```
packages/store-sqlite/
├─ src/createcart_store_sqlite/
│  ├─ db.py             # Database — tenants registry + per-tenant table DDL
│  ├─ menu_store.py     # SqliteMenuStore     (implements MenuStore)
│  ├─ cart_store.py     # SqliteCartStore     (implements CartStore)
│  ├─ payment_store.py  # SqlitePaymentStore  (implements PaymentStore)
│  └─ delivery_store.py # SqliteDeliveryStore (implements DeliveryStore)
├─ tests/test_store_sqlite.py
└─ examples/migrate_json_to_sqlite.py
```

## Usage

```python
from createcart_store_sqlite import (
    Database, SqliteMenuStore, SqliteCartStore, SqlitePaymentStore, SqliteDeliveryStore
)
from createcart_registry import MenuRegistry
from createcart_cart import Cart
from createcart_payment import PaymentService, MockProvider

db = Database("createcart.db")          # shared DB handle (thread-safe)

# 'brahmana-naivedyam' -> id 0, creates menu_items_0, carts_0, payments_0, ...
reg  = MenuRegistry(store=SqliteMenuStore(db, "brahmana-naivedyam"))
cart = Cart("sess-1", store=SqliteCartStore(db, "brahmana-naivedyam"))
pay  = PaymentService(MockProvider(), store=SqlitePaymentStore(db, "brahmana-naivedyam"))

db.list_tenants()      # [(0, 'brahmana-naivedyam'), ...]
db.tenant_id("brahmana-naivedyam")   # 0
```

## Tenant registry API (`Database`)

| Method | Returns |
|--------|---------|
| `get_or_create_tenant(name, *, tenant_id=None)` | `int` — id, creating tenant + tables if new |
| `update_tenant(name, *, password_hash=None, base_url=None)` | `None` — set auth/base-url fields |
| `get_tenant(name)` | `dict \| None` — full record `{id, name, password_hash, base_url}` |
| `delete_tenant(name)` | `bool` — delete the tenant row and **DROP all its per-tenant tables** (destructive) |
| `tenant_id(name)` | `int \| None` |
| `tenant_name(id)` | `str \| None` |
| `list_tenants()` | `list[(id, name)]` ordered by id |
| `list_tenants_full()` | `list[dict]` — `{id, name, base_url}` (no password) |

## Migrate an existing JSON menu

```bash
python examples/migrate_json_to_sqlite.py \
  ../registry/examples/brahmana-menu.json \
  ../../createcart-api/data/createcart.db \
  brahmana-naivedyam
```

## Test

```powershell
.\.venv\Scripts\pytest packages/store-sqlite -q
```

## Swapping to Postgres later

The same protocols apply — write `PgMenuStore` / `PgCartStore` / `PgPaymentStore`
against Postgres (e.g. Supabase) with the same method signatures. No SDK or API
changes; just point the API at the Postgres stores.
