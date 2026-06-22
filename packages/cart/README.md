# createcart-cart — Cart SDK

The **headless shopping-cart engine** for CreateCart apps: line items
(add / increase / decrease / remove / set quantity), plus charges (e.g. parcel
fee), discounts and tax — with computed totals and **pluggable storage**.

- **Language:** Python ≥ 3.10 · **Models:** pydantic v2 · **Money:** `Decimal`
- **Distribution name:** `createcart-cart` · **Import:** `createcart_cart`

---

## Decoupled by design

The cart **never imports the menu registry** and **never trusts a client price**.
The caller (your API) looks up the authoritative price from the menu and passes it
in via `add_item(..., unit_price=...)`. This keeps the SDKs independent and blocks
price tampering.

## What's inside

```
packages/cart/
├─ pyproject.toml
├─ src/createcart_cart/
│  ├─ __init__.py            # public exports
│  ├─ models.py              # CartItem, Charge, Discount, CartData, CartTotals, to_money()
│  ├─ cart.py                # Cart — every operation + totals()
│  ├─ exceptions.py          # CartError, CartItemNotFoundError, InvalidQuantityError
│  ├─ py.typed
│  └─ storage/
│     ├─ base.py             # CartStore protocol (load/save/delete)
│     ├─ memory.py           # InMemoryCartStore
│     └─ jsonfile.py         # JSONFileCartStore (one file per cart, ids sanitized)
└─ tests/test_cart.py        # 14 tests
```

## What it can do

| Area | Methods |
|------|---------|
| **Line items** | `add_item` (merges + refreshes price), `get_item`, `find_item`, `increment`, `decrement` (auto-removes at 0), `set_quantity` (0 removes), `remove_item`, `clear` |
| **Inspect** | `list_items`, `count` (distinct lines), `total_quantity`, `is_empty` |
| **Charges** | `add_charge` (replace by code), `remove_charge`, `clear_charges` |
| **Discount** | `set_discount` (`percent` or `fixed`, never below zero), `clear_discount` |
| **Tax** | `set_tax_rate` (percent) |
| **Totals / export** | `totals`, `to_dict` (incl. per-line + grand totals), `to_json` |

## How totals are computed

```
subtotal      = Σ (unit_price × quantity)
discount      = percent of subtotal, or fixed amount (clamped so total ≥ 0)
taxable       = subtotal − discount
tax           = taxable × tax_rate%
charges       = Σ fixed charges (parcel fee, etc.)
grand_total   = taxable + tax + charges
```

## Data model

```python
CartItem(item_id, name, unit_price (Decimal), quantity, icon, image_url, metadata)
                                         # .line_total = unit_price × quantity
Charge(code, label, amount)              # fixed fee, e.g. ("parcel", "Parcel charge", 10)
Discount(kind="percent"|"fixed", value, code, label)
CartData(id, currency, items[], charges[], discount, tax_rate, metadata)   # persisted
CartTotals(currency, item_count, total_quantity,
           subtotal, discount_total, tax_total, charges_total, grand_total)
```

## Quick start

```python
from createcart_cart import Cart
from createcart_cart.storage import JSONFileCartStore

cart = Cart("sess-123", store=JSONFileCartStore("carts/"))
cart.add_item("plain-dosa", name="Plain Dosa", unit_price="60", quantity=2)
cart.increment("plain-dosa")            # qty -> 3
cart.add_charge("parcel", "Parcel charge", "10")
cart.set_discount("percent", "10")
cart.set_tax_rate("5")

print(cart.totals().grand_total)
payload = cart.to_dict()                # items + per-line totals + totals block
```

## Storage backends

| Backend | Use |
|---------|-----|
| `InMemoryCartStore` | tests, prototypes |
| `JSONFileCartStore` | one `<cart_id>.json` per cart; ids validated to be filename-safe |
| *Redis/Postgres (planned)* | implement `load` / `save` / `delete` |

**Add your own backend:**

```python
class MyCartStore:
    def load(self, cart_id: str) -> CartData | None: ...
    def save(self, cart: CartData) -> None: ...
    def delete(self, cart_id: str) -> None: ...
```

## Test

```powershell
.\.venv\Scripts\pytest packages/cart -q
```
