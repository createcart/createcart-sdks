"""Console provider — prints messages instead of sending (local/dev, no keys).

Records everything in ``.sent`` so tests can assert what would have gone out.
"""

from __future__ import annotations

from ..models import NotificationResult


class ConsoleProvider:
    name = "console"

    def __init__(self) -> None:
        self.sent: list[dict] = []

    def send(self, to: str, text: str, *, channel: str = "sms") -> NotificationResult:
        self.sent.append({"to": to, "text": text, "channel": channel})
        print(f"[notify:console] {channel} -> {to}: {text}")
        return NotificationResult(
            provider=self.name, to=to, channel=channel, status="logged"
        )
