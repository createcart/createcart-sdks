"""PaymentService — orchestrates a provider with optional record storage."""

from __future__ import annotations

from typing import Any, Optional

from .exceptions import SignatureVerificationError
from .models import PaymentOrder, PaymentRecord, PaymentStatus
from .providers.base import PaymentProvider
from .storage.base import PaymentStore


class PaymentService:
    """Create orders and verify payments through a pluggable provider.

    If a :class:`PaymentStore` is supplied, every order/payment is recorded so
    its lifecycle can be reconciled later.
    """

    def __init__(
        self, provider: PaymentProvider, store: Optional[PaymentStore] = None
    ) -> None:
        self.provider = provider
        self.store = store

    @property
    def public_key(self) -> str:
        return self.provider.public_key

    def create_order(
        self,
        amount: int,
        *,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[dict[str, Any]] = None,
        cart_id: Optional[str] = None,
    ) -> PaymentOrder:
        order = self.provider.create_order(
            amount=amount, currency=currency, receipt=receipt, notes=notes
        )
        if self.store is not None:
            self.store.save(
                PaymentRecord(
                    order_id=order.id,
                    amount=order.amount,
                    currency=order.currency,
                    provider=order.provider,
                    status=PaymentStatus.created,
                    receipt=receipt,
                    cart_id=cart_id,
                    notes=notes or {},
                )
            )
        return order

    def verify_payment(
        self, order_id: str, payment_id: str, signature: str
    ) -> PaymentRecord:
        """Verify a completed payment's signature and mark it paid.

        Raises :class:`SignatureVerificationError` if the signature is invalid
        (the record, if any, is marked ``failed``).
        """
        ok = self.provider.verify_signature(order_id, payment_id, signature)
        record = self.store.get(order_id) if self.store is not None else None

        if not ok:
            if record is not None:
                record.status = PaymentStatus.failed
                self.store.save(record)
            raise SignatureVerificationError(
                f"signature verification failed for order {order_id!r}"
            )

        if record is None:
            # No store (or unknown order) — return a minimal paid record.
            record = PaymentRecord(
                order_id=order_id,
                amount=0,
                provider=self.provider.name,
            )
        record.status = PaymentStatus.paid
        record.payment_id = payment_id
        if self.store is not None:
            self.store.save(record)
        return record
