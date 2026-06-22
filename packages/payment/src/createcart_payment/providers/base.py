"""The contract every payment provider implements."""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from ..models import PaymentOrder


@runtime_checkable
class PaymentProvider(Protocol):
    """A payment gateway adapter.

    Only three things are required: a public key (safe to hand the frontend),
    creating an order, and verifying a completed payment's signature.
    """

    name: str

    @property
    def public_key(self) -> str:
        """The publishable/key id the frontend checkout widget needs."""
        ...

    def create_order(
        self,
        amount: int,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[dict[str, Any]] = None,
    ) -> PaymentOrder:
        """Create a payment order for ``amount`` minor units (e.g. paise)."""
        ...

    def verify_signature(
        self, order_id: str, payment_id: str, signature: str
    ) -> bool:
        """Return True if the payment signature is authentic."""
        ...
