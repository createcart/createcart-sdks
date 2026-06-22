"""Delivery models + the lifecycle state machine definition."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class DeliveryStatus(str, Enum):
    placed = "placed"
    confirmed = "confirmed"
    preparing = "preparing"
    out_for_delivery = "out_for_delivery"
    delivered = "delivered"
    cancelled = "cancelled"


# Linear happy-path used by `advance()`.
FLOW: list[DeliveryStatus] = [
    DeliveryStatus.placed,
    DeliveryStatus.confirmed,
    DeliveryStatus.preparing,
    DeliveryStatus.out_for_delivery,
    DeliveryStatus.delivered,
]

# Allowed transitions. Any non-terminal state may also be cancelled.
ALLOWED: dict[DeliveryStatus, set[DeliveryStatus]] = {
    DeliveryStatus.placed: {DeliveryStatus.confirmed, DeliveryStatus.cancelled},
    DeliveryStatus.confirmed: {DeliveryStatus.preparing, DeliveryStatus.cancelled},
    DeliveryStatus.preparing: {DeliveryStatus.out_for_delivery, DeliveryStatus.cancelled},
    DeliveryStatus.out_for_delivery: {DeliveryStatus.delivered, DeliveryStatus.cancelled},
    DeliveryStatus.delivered: set(),
    DeliveryStatus.cancelled: set(),
}

TERMINAL = {DeliveryStatus.delivered, DeliveryStatus.cancelled}


def _to_money(value: Any) -> Decimal:
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(Decimal("0.01"))


class Customer(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    email: Optional[str] = None
    subject: Optional[str] = None    # stable id of the signed-in user (e.g. Google sub)
    lat: Optional[float] = None      # delivery location (captured via geolocation)
    lng: Optional[float] = None


class OrderItem(BaseModel):
    item_id: str
    name: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(default=Decimal("0.00"), ge=0)

    @field_validator("unit_price", mode="before")
    @classmethod
    def _coerce(cls, v: Any) -> Decimal:
        return _to_money(v)

    @property
    def line_total(self) -> Decimal:
        return _to_money(self.unit_price * self.quantity)


class Courier(BaseModel):
    name: str
    phone: Optional[str] = None
    tracking_url: Optional[str] = None


class StatusEvent(BaseModel):
    status: DeliveryStatus
    at: datetime
    note: Optional[str] = None


class DeliveryOrder(BaseModel):
    id: str
    status: DeliveryStatus = DeliveryStatus.placed
    customer: Optional[Customer] = None
    items: list[OrderItem] = Field(default_factory=list)
    amount: Optional[Decimal] = None        # order total (rupees)
    currency: str = "INR"
    cart_id: Optional[str] = None           # links back to the cart
    payment_id: Optional[str] = None        # links to the payment
    timeline: list[StatusEvent] = Field(default_factory=list)
    eta: Optional[datetime] = None
    courier: Optional[Courier] = None
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @field_validator("amount", mode="before")
    @classmethod
    def _coerce_amount(cls, v: Any) -> Optional[Decimal]:
        return None if v is None else _to_money(v)

    @property
    def is_terminal(self) -> bool:
        return self.status in TERMINAL
