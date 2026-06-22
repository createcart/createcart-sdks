"""NotifyService — builds status-update messages and sends them via a provider.

Decoupled from the delivery SDK: it takes a phone number + status string, so any
caller can use it.
"""

from __future__ import annotations

from typing import Optional

from .models import NotificationResult
from .providers.base import NotificationProvider
from .providers.console import ConsoleProvider

# Message templates per delivery status.
_TEMPLATES = {
    "placed": "Hi {name}, your {biz} order {ref} is placed. We'll text you updates.",
    "confirmed": "Hi {name}, your {biz} order {ref} is confirmed. ✅",
    "preparing": "Good news {name}! Your {biz} order {ref} is being prepared. 🍳",
    "out_for_delivery": "Your {biz} order {ref} is out for delivery. 🛵",
    "delivered": "Your {biz} order {ref} has been delivered. Enjoy! 🙏",
    "cancelled": "Your {biz} order {ref} has been cancelled.",
}


class NotifyService:
    """Sends customer notifications through a pluggable provider."""

    def __init__(
        self,
        provider: Optional[NotificationProvider] = None,
        *,
        business_name: str = "CreateCart",
    ) -> None:
        self.provider = provider or ConsoleProvider()
        self.business_name = business_name

    def send(
        self, to: str, text: str, *, channel: str = "sms"
    ) -> NotificationResult:
        return self.provider.send(to, text, channel=channel)

    def message_for(
        self, status: str, *, name: Optional[str] = None, order_id: Optional[str] = None
    ) -> str:
        template = _TEMPLATES.get(
            status, "Your {biz} order {ref} status is now: " + status + "."
        )
        ref = f"#{order_id[-6:]}" if order_id else ""
        return template.format(
            name=name or "there", biz=self.business_name, ref=ref
        ).replace("  ", " ").strip()

    def notify_status(
        self,
        to: Optional[str],
        status: str,
        *,
        name: Optional[str] = None,
        order_id: Optional[str] = None,
        channel: str = "sms",
    ) -> Optional[NotificationResult]:
        """Send a status-update message. Returns ``None`` (no-op) if ``to`` is
        empty — so callers don't have to guard on a missing phone number."""
        if not to:
            return None
        text = self.message_for(status, name=name, order_id=order_id)
        return self.send(to, text, channel=channel)
