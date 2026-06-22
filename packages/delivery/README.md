# createcart-delivery — Delivery SDK

The **order-lifecycle engine** for CreateCart apps. It models an order as a
validated **state machine** and records every transition in a timeline the
customer can track. Headless, with pluggable storage.

- **Language:** Python ≥ 3.10 · **Models:** pydantic v2
- **Distribution name:** `createcart-delivery` · **Import:** `createcart_delivery`

---

## The lifecycle

```
placed → confirmed → preparing → out_for_delivery → delivered
   └──────────┴───────────┴──────────────┘ → cancelled   (any non-terminal state)
```

`delivered` and `cancelled` are terminal. Illegal jumps (e.g. `placed → delivered`)
raise `InvalidTransitionError`.

## What's inside

```
packages/delivery/
├─ src/createcart_delivery/
│  ├─ models.py        # DeliveryStatus, DeliveryOrder, OrderItem, Customer, Courier, StatusEvent + state machine
│  ├─ service.py       # DeliveryService — create + transitions + tracking
│  ├─ exceptions.py    # DeliveryError, DeliveryNotFoundError, InvalidTransitionError
│  └─ storage/         # base.py · memory.py · jsonfile.py
└─ tests/test_delivery.py   # 13 tests
```

## What it can do

| Area | Methods |
|------|---------|
| **Create / read** | `create_order`, `get`, `find`, `list` (filter by `status`) |
| **Transitions** | `advance` (next happy-path step), `set_status` (validated), `cancel` |
| **Logistics** | `assign_courier`, `set_eta` |
| **Tracking** | `track` — status + ETA + courier + full timeline |

## Data model

```python
DeliveryStatus = placed | confirmed | preparing | out_for_delivery | delivered | cancelled

DeliveryOrder(
  id, status, customer, items[OrderItem], amount, currency,
  cart_id, payment_id,            # links back to cart & payment
  timeline[StatusEvent],          # every transition, timestamped
  eta, courier, notes, metadata, created_at, updated_at,
)
Customer(name, phone, address, email)
OrderItem(item_id, name, quantity, unit_price)   # .line_total
Courier(name, phone, tracking_url)
StatusEvent(status, at, note)
```

## Quick start

```python
from createcart_delivery import DeliveryService
from createcart_delivery.storage import JSONFileDeliveryStore

svc = DeliveryService(store=JSONFileDeliveryStore("deliveries/"))

order = svc.create_order(
    items=[{"item_id": "pulihora", "name": "Pulihora", "quantity": 2, "unit_price": "50"}],
    customer={"name": "Asha", "phone": "98...", "address": "Gachibowli"},
    amount="100", cart_id="sess-1", payment_id="pay_1",
)

svc.advance(order.id)                       # placed -> confirmed
svc.assign_courier(order.id, "Ravi", phone="90...")
svc.advance(order.id)                       # -> preparing
svc.set_status(order.id, "out_for_delivery")
svc.advance(order.id)                       # -> delivered

svc.track(order.id)                         # {status, eta, courier, timeline[...]}
```

## Storage backends

| Backend | Use |
|---------|-----|
| `InMemoryDeliveryStore` | tests, prototypes |
| `JSONFileDeliveryStore` | one `<order_id>.json` per order |
| *SQLite (`createcart-store-sqlite`)* | per-tenant `deliveries_<id>` table |

Add your own: implement `get(order_id)`, `save(order)`, `list()`.

## Determinism

`DeliveryService(store, clock=...)` accepts a `clock` callable for fixed
timestamps in tests; it defaults to `datetime.now(timezone.utc)`.

## Test

```powershell
.\.venv\Scripts\pytest packages/delivery -q
```
