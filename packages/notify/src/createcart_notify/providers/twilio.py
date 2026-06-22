"""Twilio provider — SMS and WhatsApp via the Twilio REST API.

Uses ``urllib`` + basic auth; no ``twilio`` pip package required. WhatsApp uses
Twilio's ``whatsapp:`` address prefix.
"""

from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional

from ..exceptions import ProviderError
from ..models import NotificationResult

_API = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


class TwilioProvider:
    name = "twilio"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        *,
        from_sms: Optional[str] = None,
        from_whatsapp: Optional[str] = None,
        timeout: float = 15.0,
    ) -> None:
        if not account_sid or not auth_token:
            raise ProviderError("Twilio requires account_sid and auth_token")
        self._sid = account_sid
        self._token = auth_token
        self._from_sms = from_sms
        self._from_whatsapp = from_whatsapp
        self._timeout = timeout

    def send(self, to: str, text: str, *, channel: str = "sms") -> NotificationResult:
        if channel == "whatsapp":
            if not self._from_whatsapp:
                raise ProviderError("from_whatsapp not configured")
            sender, dest = f"whatsapp:{self._from_whatsapp}", f"whatsapp:{to}"
        else:
            if not self._from_sms:
                raise ProviderError("from_sms not configured")
            sender, dest = self._from_sms, to

        data = urllib.parse.urlencode(
            {"To": dest, "From": sender, "Body": text}
        ).encode()
        token = base64.b64encode(f"{self._sid}:{self._token}".encode()).decode()
        req = urllib.request.Request(
            _API.format(sid=self._sid),
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                payload = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            detail = exc.read().decode(errors="replace")
            raise ProviderError(f"Twilio send failed ({exc.code}): {detail}")
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise ProviderError(f"Twilio unreachable: {exc.reason}")

        return NotificationResult(
            provider=self.name, to=to, channel=channel,
            status=payload.get("status", "queued"), sid=payload.get("sid"),
            raw=payload,
        )
