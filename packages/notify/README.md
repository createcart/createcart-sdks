# createcart-notify — Notify SDK

Pluggable customer notifications (SMS / WhatsApp) for order **status follow-ups**.
Providers implement one small interface; a **Twilio** provider and a **Console**
provider ship in the box. Decoupled from the other SDKs — it sends to a phone
number + status string, so anything can drive it.

- **Language:** Python ≥ 3.10 · **Import:** `createcart_notify`
- Twilio is called via its REST API (urllib) — **no `twilio` pip package**.

---

## What's inside

```
packages/notify/
├─ src/createcart_notify/
│  ├─ service.py        # NotifyService — message templates + send
│  ├─ models.py         # NotificationResult
│  ├─ exceptions.py
│  └─ providers/
│     ├─ base.py        # NotificationProvider protocol
│     ├─ console.py     # ConsoleProvider (prints + records; local/dev)
│     └─ twilio.py      # TwilioProvider (SMS + WhatsApp via REST)
└─ tests/test_notify.py # 7 tests
```

## What it can do

| Component | Capabilities |
|-----------|--------------|
| `NotifyService` | `notify_status(to, status, name, order_id, channel)` (no-op if no phone), `message_for(status, …)`, `send(to, text, channel)` |
| `ConsoleProvider` | prints + records in `.sent` — local dev, no keys |
| `TwilioProvider` | real SMS (`channel="sms"`) and WhatsApp (`channel="whatsapp"`) |

Built-in templates for `placed · confirmed · preparing · out_for_delivery ·
delivered · cancelled`, with a fallback for any other status.

## Usage

```python
from createcart_notify import NotifyService, ConsoleProvider, TwilioProvider

# local
notify = NotifyService(ConsoleProvider(), business_name="Brahmana Naivedyam")
notify.notify_status("+9198...", "out_for_delivery", name="Asha", order_id="order_ab12cd")

# production (SMS)
notify = NotifyService(
    TwilioProvider("AC...", "auth_token", from_sms="+1555..."),
    business_name="Brahmana Naivedyam",
)
# production (WhatsApp)
notify = NotifyService(
    TwilioProvider("AC...", "auth_token", from_whatsapp="+1415..."),
)
notify.notify_status("+9198...", "delivered", name="Asha", channel="whatsapp")
```

## Driving it from the delivery lifecycle

The delivery SDK's `DeliveryService(store, on_event=...)` calls a callback after
every transition. The API wires that callback to `notify_status(...)`, so each
status change automatically texts the customer's phone — no coupling between the
delivery and notify SDKs.

## Add a provider

```python
class Mseg91Provider:
    name = "msg91"
    def send(self, to, text, *, channel="sms") -> NotificationResult: ...
```

## Test

```powershell
.\.venv\Scripts\pytest packages/notify -q
```
