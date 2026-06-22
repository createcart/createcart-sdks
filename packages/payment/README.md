# createcart-payment — Payment SDK

The **pluggable payment layer** for CreateCart apps. Payment gateways sit behind a
small `PaymentProvider` interface; a **Razorpay** provider and a **Mock** provider
ship in the box. Swapping to Stripe/Cashfree later means writing one class — no
service or app changes.

- **Language:** Python ≥ 3.10 · **Models:** pydantic v2 · **Amounts:** integer minor units (paise)
- **Distribution name:** `createcart-payment` · **Import:** `createcart_payment`

---

## Zero extra dependencies

Razorpay order creation uses the REST API via `urllib`; signature verification uses
stdlib `hmac`. **No `razorpay` pip package required.**

## What's inside

```
packages/payment/
├─ pyproject.toml
├─ src/createcart_payment/
│  ├─ __init__.py            # public exports
│  ├─ models.py              # PaymentOrder, PaymentRecord, PaymentStatus
│  ├─ service.py             # PaymentService (provider + record storage)
│  ├─ exceptions.py          # PaymentError, ProviderError, SignatureVerificationError
│  ├─ py.typed
│  ├─ providers/
│  │  ├─ base.py             # PaymentProvider protocol
│  │  ├─ razorpay.py         # RazorpayProvider (REST orders + HMAC verify)
│  │  └─ mock.py             # MockProvider (no network/keys; make_test_payment)
│  └─ storage/
│     ├─ base.py             # PaymentStore protocol (get/save)
│     ├─ memory.py           # InMemoryPaymentStore
│     └─ jsonfile.py         # JSONFilePaymentStore (one file per order)
└─ tests/test_payment.py     # 8 tests
```

## The flow

```
server   create_order(amount_minor)          -> PaymentOrder (order_id, key_id)
browser  open provider checkout widget, pay  -> payment_id, signature
server   verify_payment(order_id, ...)       -> PaymentRecord (status = paid)
```

Verification follows Razorpay's scheme: `HMAC_SHA256(order_id + "|" + payment_id, key_secret)`.

## What it can do

| Component | Capabilities |
|-----------|--------------|
| `PaymentService` | `create_order`, `verify_payment` (raises on bad signature, marks record `failed`), `public_key` |
| `RazorpayProvider(key_id, key_secret)` | real order creation + signature verify |
| `MockProvider(key_id="mock_key", key_secret="mock_secret")` | offline (args optional); `make_test_payment(order_id)` returns a valid `{payment_id, signature}` pair |
| Storage | track lifecycle `created → paid / failed`, keyed by `order_id` |

## Data model

```python
PaymentStatus(str, Enum) = created | paid | failed   # str-enum: PaymentStatus.paid == "paid"
PaymentOrder(id, amount (paise int), currency, provider, receipt, status, notes, raw)
PaymentRecord(order_id, amount, currency, provider, status, payment_id, receipt, cart_id, notes)
```

## Production usage

```python
from createcart_payment import PaymentService, RazorpayProvider
from createcart_payment.storage import JSONFilePaymentStore

svc = PaymentService(
    RazorpayProvider(key_id="rzp_live_...", key_secret="..."),
    store=JSONFilePaymentStore("payments/"),
)
order  = svc.create_order(25000, currency="INR", cart_id="sess-1")   # 250.00 INR
# ... browser pays via Razorpay checkout.js ...
record = svc.verify_payment(order.id, payment_id, signature)         # raises if invalid
```

## Local testing without real keys (Mock provider)

The mock provider signs with the same HMAC scheme, so the **entire round-trip runs
offline**:

```python
from createcart_payment import PaymentService, MockProvider
from createcart_payment.storage import InMemoryPaymentStore

provider = MockProvider()
svc = PaymentService(provider, store=InMemoryPaymentStore())
order = svc.create_order(13000)
pay   = provider.make_test_payment(order.id)        # server holds the secret
svc.verify_payment(order.id, pay["payment_id"], pay["signature"])   # -> paid
```

## Add a new provider

```python
class StripeProvider:
    name = "stripe"
    @property
    def public_key(self) -> str: ...
    def create_order(self, amount, currency="INR", receipt=None, notes=None) -> PaymentOrder: ...
    def verify_signature(self, order_id, payment_id, signature) -> bool: ...
```

## Test

```powershell
.\.venv\Scripts\pytest packages/payment -q
```
