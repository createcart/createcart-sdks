# createcart-store-postgres — Postgres / Supabase storage

DB-backed storage for the CreateCart SDKs on **Postgres** (e.g. Supabase). A
faithful port of [`createcart-store-sqlite`](../store-sqlite/README.md): one
database, **separate tables per tenant**, with a `tenants` registry mapping a
numeric `tenant_id` (`0..n`) to an english `name`. Implements the menu / cart /
payment / delivery storage protocols, so the SDKs gain Postgres with **no SDK or
API logic changes** — just swap the store.

- **Language:** Python ≥ 3.10 · `psycopg` (v3)
- **Import:** `createcart_store_postgres`

## Schema

```
tenants(id INTEGER PK 0..n, name TEXT UNIQUE,         -- name → id mapping
        password_hash TEXT, base_url TEXT)            -- tenant admin auth + stored API base url

-- created on demand, one set per tenant (suffix = tenant_id):
menu_items_<id>(id, name, name_localized, description, price, currency,
                image_url, icon, category, tags, available, stock, sort_order, metadata)
categories_<id>(id, name, sort_order, metadata)
combos_<id>(id, name, price, currency, description, item_ids, tags, available, sort_order, metadata)
carts_<id>(cart_id PK, data)                          -- cart aggregate as JSON text
payments_<id>(order_id PK, status, amount, currency, provider, cart_id, payment_id, data)
deliveries_<id>(order_id PK, status, created_at, data) -- delivery order + timeline as JSON text
```

`tenant_id` starts at **0** and increments. Tenant names must be lowercase
english words/slugs (`brahmana-naivedyam`) — validated, which keeps the generated
table names safe.

## What's inside

```
packages/store-postgres/
├─ src/createcart_store_postgres/
│  ├─ db.py             # PgDatabase — tenants registry + per-tenant table DDL
│  ├─ menu_store.py     # PgMenuStore     (implements MenuStore)
│  ├─ cart_store.py     # PgCartStore     (implements CartStore)
│  ├─ payment_store.py  # PgPaymentStore  (implements PaymentStore)
│  └─ delivery_store.py # PgDeliveryStore (implements DeliveryStore)
└─ tests/test_store_postgres.py
```

## Usage

```python
from createcart_store_postgres import (
    PgDatabase, PgMenuStore, PgCartStore, PgPaymentStore, PgDeliveryStore
)
from createcart_registry import MenuRegistry
from createcart_cart import Cart
from createcart_payment import PaymentService, MockProvider

# Supabase: use the transaction POOLER URI (port 6543) on serverless,
# or the direct connection (port 5432) on a persistent host.
db = PgDatabase("postgresql://USER:PASSWORD@HOST:6543/postgres?sslmode=require")

reg  = MenuRegistry(store=PgMenuStore(db, "brahmana-naivedyam"))   # -> id 0, tables *_0
cart = Cart("sess-1", store=PgCartStore(db, "brahmana-naivedyam"))
pay  = PaymentService(MockProvider(), store=PgPaymentStore(db, "brahmana-naivedyam"))

db.list_tenants()                      # [(0, 'brahmana-naivedyam'), ...]
db.tenant_id("brahmana-naivedyam")     # 0
```

## Tenant registry API (`PgDatabase`)

Same surface as the SQLite backend:

| Method | Returns |
|--------|---------|
| `get_or_create_tenant(name, *, tenant_id=None)` | `int` — id, creating tenant + tables if new |
| `update_tenant(name, *, password_hash=None, base_url=None)` | `None` |
| `get_tenant(name)` | `dict \| None` — `{id, name, password_hash, base_url}` |
| `tenant_id(name)` / `tenant_name(id)` | `int \| None` / `str \| None` |
| `list_tenants()` | `list[(id, name)]` |
| `list_tenants_full()` | `list[dict]` — `{id, name, base_url}` (no password) |

## Serverless / Supabase notes

- On Vercel functions (or any serverless runtime), point the DSN at Supabase's
  **transaction pooler** (`...pooler.supabase.com:6543`). A new connection is
  opened per operation, which the pooler handles efficiently.
- On a persistent host, the direct connection (`:5432`) is fine.
- Require TLS: append `?sslmode=require` to the DSN.

## Test

```bash
# needs a throwaway Postgres; skips otherwise
TEST_DATABASE_URL="postgresql://...:5432/postgres" pytest packages/store-postgres -q
```
