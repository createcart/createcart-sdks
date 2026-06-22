"""Razorpay provider — REST order creation + HMAC signature verification.

Uses the Razorpay REST API directly (urllib) and stdlib ``hmac`` so there is no
dependency on the ``razorpay`` pip package. Verification follows Razorpay's
documented scheme: ``HMAC_SHA256(order_id + "|" + payment_id, key_secret)``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.error
import urllib.request
from typing import Any, Optional

from ..exceptions import ProviderError
from ..models import PaymentOrder

_ORDERS_URL = "https://api.razorpay.com/v1/orders"


class RazorpayProvider:
    name = "razorpay"

    def __init__(self, key_id: str, key_secret: str, *, timeout: float = 15.0) -> None:
        if not key_id or not key_secret:
            raise ProviderError("Razorpay requires both key_id and key_secret")
        self._key_id = key_id
        self._key_secret = key_secret
        self._timeout = timeout

    @property
    def public_key(self) -> str:
        return self._key_id

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[dict[str, Any]] = None,
    ) -> PaymentOrder:
        payload = {
            "amount": amount,
            "currency": currency,
            "payment_capture": 1,
        }
        if receipt:
            payload["receipt"] = receipt
        if notes:
            payload["notes"] = notes

        token = base64.b64encode(
            f"{self._key_id}:{self._key_secret}".encode()
        ).decode()
        req = urllib.request.Request(
            _ORDERS_URL,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {token}",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            detail = exc.read().decode(errors="replace")
            raise ProviderError(f"Razorpay order failed ({exc.code}): {detail}")
        except urllib.error.URLError as exc:  # pragma: no cover - network
            raise ProviderError(f"Razorpay unreachable: {exc.reason}")

        return PaymentOrder(
            id=data["id"],
            amount=data.get("amount", amount),
            currency=data.get("currency", currency),
            provider=self.name,
            receipt=data.get("receipt"),
            notes=data.get("notes") or {},
            raw=data,
        )

    def verify_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        message = f"{order_id}|{payment_id}".encode()
        expected = hmac.new(
            self._key_secret.encode(), message, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature or "")
