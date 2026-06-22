"""The contract every notification provider implements."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import NotificationResult


@runtime_checkable
class NotificationProvider(Protocol):
    name: str

    def send(self, to: str, text: str, *, channel: str = "sms") -> NotificationResult:
        """Send ``text`` to phone number ``to`` over ``channel`` (sms/whatsapp)."""
        ...
