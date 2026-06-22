"""CreateCart Notify SDK.

Pluggable customer notifications (SMS / WhatsApp). Providers implement a small
interface; a Twilio provider and a Console provider ship in the box. Decoupled
from the other SDKs — it sends to a phone number + status string, so anything
can drive it.

    from createcart_notify import NotifyService, ConsoleProvider
    notify = NotifyService(ConsoleProvider(), business_name="Brahmana Naivedyam")
    notify.notify_status("+9198...", "out_for_delivery", name="Asha", order_id="order_ab12")
"""

from .exceptions import NotifyError, ProviderError
from .models import NotificationResult
from .providers import ConsoleProvider, NotificationProvider, TwilioProvider
from .service import NotifyService

__all__ = [
    "NotifyService",
    "NotificationProvider",
    "TwilioProvider",
    "ConsoleProvider",
    "NotificationResult",
    "NotifyError",
    "ProviderError",
]

__version__ = "0.1.0"
