# createcart-registry — Menu Registry SDK

The **headless menu engine** for CreateCart apps. It owns everything menu-related —
items (photo, price, availability, stock), categories and combos — behind one clean
Python API, with a **pluggable storage backend**. No UI, no framework. Your API
imports it; your frontend consumes the JSON it produces.

- **Language:** Python ≥ 3.10 · **Models:** pydantic v2 · **Money:** `Decimal`
- **Distribution name:** `createcart-registry` · **Import:** `createcart_registry`

---

## What's inside

```
packages/registry/
├─ pyproject.toml
├─ src/createcart_registry/
│  ├─ __init__.py            # public exports
│  ├─ models.py              # MenuItem, Category, Combo, MenuCatalog, slugify()
│  ├─ registry.py            # MenuRegistry — every operation
│  ├─ exceptions.py          # RegistryError, ItemNotFoundError, DuplicateItemError, OutOfStockError
│  ├─ py.typed
│  └─ storage/
│     ├─ base.py             # MenuStore protocol (load/save)
│     ├─ memory.py           # InMemoryStore
│     └─ jsonfile.py         # JSONFileStore (atomic writes)
├─ tests/test_registry.py    # 14 tests
└─ examples/seed_brahmana.py # builds a real menu.json
```

## What it can do

| Area | Methods |
|------|---------|
| **Items CRUD** | `add_item`, `get_item`, `find_item`, `update_item`, `remove_item` |
| **Listing & search** | `list_items` (filter by `category` / `tag` / `available_only` / `in_stock_only`), `search`, `count` |
| **Pricing** | `set_price` |
| **Availability & stock** | `set_available`, `is_available`, `set_stock`, `adjust_stock` (raises `OutOfStockError`) |
| **Categories** | `add_category`, `list_categories`, `remove_category`, `items_by_category` |
| **Combos** | `add_combo`, `list_combos`, `remove_combo` (validates item refs; cleans up on item delete) |
| **Bulk / export** | `import_items`, `to_dict`, `to_json` |

## Data model

```python
MenuItem(
  id, name, name_localized,      # e.g. English + Telugu
  description, price (Decimal), currency,
  image_url, icon,               # photo URL or emoji fallback
  category, tags,                # e.g. ["SPECIAL", "SWEET"]
  available, stock,              # stock=None means untracked/unlimited
  sort_order, metadata,
)                                # .in_stock -> available AND (stock is None or > 0)

Category(id, name, sort_order, metadata)
Combo(id, name, price, currency, description, item_ids, tags, available, sort_order, metadata)
MenuCatalog(tenant, currency, items[], categories[], combos[])   # the persisted aggregate
```

IDs auto-derive from the name as a unique slug (`"Ghee Masala Dosa"` → `ghee-masala-dosa`).

## Quick start

```python
from createcart_registry import MenuRegistry
from createcart_registry.storage import JSONFileStore

reg = MenuRegistry(store=JSONFileStore("menu.json"), tenant="brahmana-naivedyam")

reg.add_item(name="Plain Dosa", price="60", category="dosa", icon="🫓",
             tags=["SPECIAL"], stock=40)

reg.set_price("plain-dosa", "65")        # change price
reg.adjust_stock("plain-dosa", -1)       # one sold
reg.set_available("plain-dosa", False)   # 86 it for the night

menu     = reg.list_items(available_only=True)
results  = reg.search("dosa")
payload  = reg.to_dict()                 # JSON-ready for an API response
```

## Storage backends

| Backend | Use |
|---------|-----|
| `InMemoryStore` | tests, prototypes |
| `JSONFileStore` | single-tenant sites; atomic temp-file + replace writes |
| *Supabase/Postgres (planned)* | implement `load`/`save` against a DB — no other changes |

**Add your own backend** — implement two methods:

```python
class MyStore:
    def load(self) -> MenuCatalog: ...
    def save(self, catalog: MenuCatalog) -> None: ...
```

## Test & seed

```powershell
# from the monorepo venv (createcart-sdks/.venv)
.\.venv\Scripts\pytest packages/registry -q
.\.venv\Scripts\python packages/registry/examples/seed_brahmana.py   # -> brahmana-menu.json
```
