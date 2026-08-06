# createcart-shipping — Shipping SDK

Pincode serviceability, rate quotes, shipment manifestation, tracking,
cancellation, and pickup requests — behind a pluggable **courier provider**.

- **Language:** Python ≥ 3.10 · no runtime dependencies (stdlib `urllib`)
- **Import:** `createcart_shipping`

## Providers

| Provider | Use |
|---|---|
| `DelhiveryProvider` | Delhivery **B2C Express** (parcel/courier) — the right family for a business shipping individual orders to end customers. **Not** Delhivery's B2B API, which is freight/part-truckload between businesses. |
| `MockShippingProvider` | Deterministic stand-in for dev/tests — no network calls, no credentials needed. |

Add another courier later (Shadowfax, Porter, …) by implementing the same
`ShippingProvider` interface — nothing above it changes.

## Quick start

```python
from createcart_shipping import ShippingService, MockShippingProvider, Address, ShipmentItem

origin = Address(name="Brahmana Naivedyam", phone="+91...", address="Gachibowli",
                  pincode="500032", city="Hyderabad", state="Telangana")

svc = ShippingService(
    MockShippingProvider(origin_pin="500032"),
    origin=origin, default_weight_g=500, handling_fee=40.0,
)

quote = svc.quote("560001")                       # serviceable, ETA, charge
shipment = svc.ship(
    order_id="ord_1",
    destination=Address(name="Priya", phone="+91...", address="MG Road", pincode="560001"),
    items=[ShipmentItem(description="Mango Pickle 250g", quantity=2)],
    payment_mode="prepaid", amount=quote.charge,
)
svc.track(shipment.waybill)
svc.schedule_pickup(date="2026-08-07", time="15:00", package_count=1)
```

## Delhivery setup (one-time, outside this SDK)

Delhivery requires two things from **your** Delhivery account before
`DelhiveryProvider` can create real shipments — there is no public API for
either, so they must be done once via [Delhivery's client
dashboard](https://one.delhivery.com):

1. **API token** — Settings → API Setup (staging token first, then live).
2. **Pickup location ("warehouse") name** — your store's address must be
   registered as a named pickup location. The exact, case-sensitive name goes
   into `DelhiveryProvider(pickup_location=...)`.

```python
from createcart_shipping import DelhiveryProvider

provider = DelhiveryProvider(
    token="...",
    base="https://staging-express.delhivery.com",   # prod: https://track.delhivery.com
    origin_pin="500032",
    pickup_location="Brahmana Naivedyam - Gachibowli",   # exact registered name
    seller_name="Brahmana Naivedyam",
    seller_address="Gachibowli, Hyderabad, Telangana",
    seller_gst_tin="",     # if you have one
    hsn_code="2103",       # tariff code for your goods (pickles/spices)
)
```

> **Verification note:** the `create_shipment` / `track` / `cancel` /
> `schedule_pickup` payload shapes are built from Delhivery's public Express
> API documentation and cross-referenced third-party integration guides — this
> SDK has not been exercised against a live Delhivery account. Test each
> operation against your **staging** token before relying on it in production,
> and adjust field names in `delhivery.py` if Delhivery's actual response
> differs from what's assumed here. `serviceability` and `rate` *were*
> verified against the documented staging endpoints during development.

## What's inside

```
packages/shipping/
├─ src/createcart_shipping/
│  ├─ models.py       # Address, ShipmentItem, Serviceability, Quote, Shipment, PickupResult
│  ├─ provider.py      # ShippingProvider protocol
│  ├─ delhivery.py     # DelhiveryProvider (B2C Express)
│  ├─ mock.py          # MockShippingProvider
│  ├─ service.py       # ShippingService — handling fee + ETA on top of a provider
│  └─ exceptions.py
└─ tests/test_shipping.py
```

## Test

```bash
pip install -e packages/shipping[dev]
pytest packages/shipping -q
```
