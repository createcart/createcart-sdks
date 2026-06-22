"""Mock provider — same signature scheme as Razorpay, no network or real keys.

Lets the entire checkout round-trip run locally. It signs with HMAC exactly
like Razorpay, and exposes :meth:`make_test_payment` so a server (which holds
the secret) can produce a valid (payment_id, signature) pair to simulate a
successful payment from the browser.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any, Optional

from ..models import PaymentOrder


class MockProvider:
    name = "mock"

    def __init__(
        self, key_id: str = "mock_key", key_secret: str = "mock_secret"
    ) -> None:
        self._key_id = key_id
        self._key_secret = key_secret

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
        order_id = "order_" + secrets.token_hex(10)
        return PaymentOrder(
            id=order_id,
            amount=amount,
            currency=currency,
            provider=self.name,
            receipt=receipt,
            notes=notes or {},
            raw={"mock": True},
        )

    def _sign(self, order_id: str, payment_id: str) -> str:
        message = f"{order_id}|{payment_id}".encode()
        return hmac.new(
            self._key_secret.encode(), message, hashlib.sha256
        ).hexdigest()

    def verify_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        return hmac.compare_digest(self._sign(order_id, payment_id), signature or "")

    def make_test_payment(self, order_id: str) -> dict[str, str]:
        """Produce a valid (payment_id, signature) pair for local simulation."""
        payment_id = "pay_" + secrets.token_hex(8)
        return {
            "payment_id": payment_id,
            "signature": self._sign(order_id, payment_id),
        }
