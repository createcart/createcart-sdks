# CreateCart SDKs

A monorepo of **pure, headless libraries** that power CreateCart ecommerce apps.
Each package is logic-only — **no theme, no UI, no framework lock-in**. Tenants
bring their own look; these libraries bring the behaviour.

```
createcart-sdks/
└─ packages/
   ├─ registry/     # Menu SDK     (Python)  — items, categories, combos, pricing, stock
   ├─ cart/         # Cart SDK     (Python)  — line items, charges, discount, tax, totals
   ├─ payment/      # Payment SDK  (Python)  — Razorpay + Mock providers, order + verify
   ├─ js-client/    # Client SDK   (JS)      — Store (customer) + Admin (business)
   ├─ delivery/     # Delivery SDK (Python)  — order lifecycle state machine + timeline
   ├─ notify/       # Notify SDK   (Python)  — SMS/WhatsApp status follow-ups (Twilio/Console)
   ├─ auth/         # Auth SDK     (Python)  — customer Sign in with Google (+ Mock)
   └─ store-sqlite/ # Storage      (Python)  — SQLite backends, per-tenant tables (id 0..n)
```

These libraries are consumed by:
- **`createcart-api`** (separate folder) — a FastAPI service that imports the three
  Python SDKs and exposes them over HTTP, multi-tenant.
- **Each tenant's website** — imports `js-client` and builds its own themed UI.

## Packages

| Package | Lang | Distribution name | What it does | Tests |
|---------|------|-------------------|--------------|-------|
| [`packages/registry`](packages/registry/README.md) | Python | `createcart-registry` | Menu management engine | 14 |
| [`packages/cart`](packages/cart/README.md) | Python | `createcart-cart` | Shopping cart engine | 14 |
| [`packages/payment`](packages/payment/README.md) | Python | `createcart-payment` | Pluggable payments | 8 |
| [`packages/js-client`](packages/js-client/README.md) | JS | `@createcart/client` | Browser data client | — |
| [`packages/delivery`](packages/delivery/README.md) | Python | `createcart-delivery` | Order lifecycle state machine + timeline | 11 |
| [`packages/notify`](packages/notify/README.md) | Python | `createcart-notify` | SMS/WhatsApp status follow-ups (Twilio + Console) | 7 |
| [`packages/auth`](packages/auth/README.md) | Python | `createcart-auth` | Customer Sign in with Google (+ Mock) | 6 |
| [`packages/store-sqlite`](packages/store-sqlite/README.md) | Python | `createcart-store-sqlite` | SQLite storage, per-tenant tables (`tenant_id` 0..n ↔ name) | 9 |

## Design principles (shared by all packages)

- **Headless** — pure logic. No HTML/CSS/colors. The theme lives in each tenant's app.
- **Pluggable storage** — every Python SDK persists through a tiny `*Store` protocol
  (`load`/`save`). Ships in-memory + JSON-file; swap to Postgres/Supabase/Redis by
  implementing the same methods — zero SDK or app changes.
- **Pluggable providers** — payments sit behind a `PaymentProvider` interface; add
  Stripe/Cashfree by writing one class.
- **Typed & serializable** — Python models are pydantic v2 (validate + JSON in/out).
- **Money is `Decimal`** (integer paise at the gateway) — never float.
- **No cross-coupling** — the cart never imports the registry; the API is the glue.

## Develop (all Python packages in one venv)

```powershell
cd D:\createcart\createcart-sdks
python -m venv .venv
.\.venv\Scripts\pip install -e packages/registry -e packages/cart -e packages/payment pytest
.\.venv\Scripts\pytest packages/registry packages/cart packages/payment -q   # 36 passed
```

## Install into another project (no private registry yet)

```powershell
# local path (dev)
pip install -e D:\createcart\createcart-sdks\packages\registry
# or git, once pushed
pip install "git+ssh://git@github.com/createcart/createcart-sdks#subdirectory=packages/registry"
# later, with a registry:  pip install createcart-registry
```

JS client: copy `packages/js-client/createcart.js` into the tenant site (vendoring),
or publish to npm later (`npm i @createcart/client`).

## Roadmap

- ✅ registry · ✅ cart · ✅ payment · ✅ js-client · ✅ delivery · ✅ notify · ✅ store-sqlite
- Order lifecycle + phone follow-ups are shipped: `delivery` drives the state
  machine, `notify` texts the customer on every status change.
