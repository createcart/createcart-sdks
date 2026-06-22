"""Payment models.

Amounts are integer **minor units** (paise for INR) — the unit every payment
gateway expects — never floats.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class PaymentStatus(str, Enum):
    created = "created"
    paid = "paid"
    failed = "failed"


class PaymentOrder(BaseModel):
    """An order created with the provider, ready for the customer to pay."""

    id: str                       # provider order id (e.g. Razorpay "order_...")
    amount: int = Field(ge=0)     # minor units (paise)
    currency: str = "INR"
    provider: str = "mock"
    receipt: Optional[str] = None
    status: PaymentStatus = PaymentStatus.created
    notes: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, Any] = Field(default_factory=dict)  # provider's raw response


class PaymentRecord(BaseModel):
    """Our own record of a payment's lifecycle (created -> paid/failed)."""

    order_id: str
    amount: int
    currency: str = "INR"
    provider: str = "mock"
    status: PaymentStatus = PaymentStatus.created
    payment_id: Optional[str] = None
    receipt: Optional[str] = None
    cart_id: Optional[str] = None
    notes: dict[str, Any] = Field(default_factory=dict)
