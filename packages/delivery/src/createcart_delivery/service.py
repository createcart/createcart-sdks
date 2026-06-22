"""DeliveryService — create orders and drive them through the lifecycle."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

from .exceptions import DeliveryNotFoundError, InvalidTransitionError
from .models import (
    ALLOWED,
    FLOW,
    TERMINAL,
    Courier,
    Customer,
    DeliveryOrder,
    DeliveryStatus,
    OrderItem,
    StatusEvent,
)
from .storage.base import DeliveryStore
from .storage.memory import InMemoryDeliveryStore

_StatusLike = Union[DeliveryStatus, str]


def _coerce_status(s: _StatusLike) -> DeliveryStatus:
    return s if isinstance(s, DeliveryStatus) else DeliveryStatus(s)


class DeliveryService:
    """Operations on delivery orders, enforcing valid status transitions.

    A ``clock`` can be injected for deterministic timestamps in tests.
    """

    def __init__(
        self,
        store: Optional[DeliveryStore] = None,
        *,
        clock: Optional[Callable[[], datetime]] = None,
        on_event: Optional[Callable[["DeliveryOrder", "StatusEvent"], None]] = None,
    ) -> None:
        self.store: DeliveryStore = store or InMemoryDeliveryStore()
        self._now = clock or (lambda: datetime.now(timezone.utc))
        # Called after every status event (create + transitions). Stays optional
        # so the SDK has no dependency on notifications — the API wires it up.
        self._on_event = on_event

    def _emit(self, order: "DeliveryOrder", event: "StatusEvent") -> None:
        if self._on_event is not None:
            self._on_event(order, event)

    # ── create / read ────────────────────────────────────────────────────
    def create_order(
        self,
        *,
        id: Optional[str] = None,
        items: Optional[list[Union[OrderItem, dict]]] = None,
        customer: Optional[Union[Customer, dict]] = None,
        amount: Any = None,
        currency: str = "INR",
        cart_id: Optional[str] = None,
        payment_id: Optional[str] = None,
        note: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> DeliveryOrder:
        """Create a new order in the ``placed`` state with an opening timeline
        entry."""
        order_id = id or ("del_" + secrets.token_hex(8))
        if self.store.get(order_id) is not None:
            # idempotent-ish: don't clobber an existing order
            raise InvalidTransitionError(f"order {order_id!r} already exists")
        now = self._now()
        order = DeliveryOrder(
            id=order_id,
            status=DeliveryStatus.placed,
            items=[OrderItem.model_validate(i) for i in (items or [])],
            customer=Customer.model_validate(customer) if customer else None,
            amount=amount,
            currency=currency,
            cart_id=cart_id,
            payment_id=payment_id,
            timeline=[StatusEvent(status=DeliveryStatus.placed, at=now,
                                  note=note or "order placed")],
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self.store.save(order)
        self._emit(order, order.timeline[-1])
        return order

    def get(self, order_id: str) -> DeliveryOrder:
        order = self.store.get(order_id)
        if order is None:
            raise DeliveryNotFoundError(f"no delivery order {order_id!r}")
        return order

    def find(self, order_id: str) -> Optional[DeliveryOrder]:
        return self.store.get(order_id)

    def list(
        self,
        *,
        status: Optional[_StatusLike] = None,
        subject: Optional[str] = None,
    ) -> list[DeliveryOrder]:
        orders = self.store.list()
        if status is not None:
            want = _coerce_status(status)
            orders = [o for o in orders if o.status == want]
        if subject is not None:
            orders = [o for o in orders if o.customer and o.customer.subject == subject]
        # newest first (created_at may be None in odd cases -> push to end)
        return sorted(
            orders,
            key=lambda o: o.created_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

    def counts_by_status(self) -> dict[str, int]:
        """Order counts per status — handy for an admin dashboard."""
        counts = {s.value: 0 for s in DeliveryStatus}
        for order in self.store.list():
            counts[order.status.value] = counts.get(order.status.value, 0) + 1
        return counts

    # ── transitions ──────────────────────────────────────────────────────
    def set_status(
        self, order_id: str, status: _StatusLike, *, note: Optional[str] = None
    ) -> DeliveryOrder:
        order = self.get(order_id)
        target = _coerce_status(status)
        if target not in ALLOWED[order.status]:
            raise InvalidTransitionError(
                f"cannot move {order_id!r} from {order.status.value} "
                f"to {target.value}"
            )
        now = self._now()
        order.status = target
        order.updated_at = now
        event = StatusEvent(status=target, at=now, note=note)
        order.timeline.append(event)
        self.store.save(order)
        self._emit(order, event)
        return order

    def advance(self, order_id: str, *, note: Optional[str] = None) -> DeliveryOrder:
        """Move to the next status along the happy path."""
        order = self.get(order_id)
        if order.status in TERMINAL:
            raise InvalidTransitionError(
                f"order {order_id!r} is already {order.status.value}"
            )
        idx = FLOW.index(order.status)
        nxt = FLOW[idx + 1]
        return self.set_status(order_id, nxt, note=note)

    def cancel(self, order_id: str, *, reason: Optional[str] = None) -> DeliveryOrder:
        return self.set_status(order_id, DeliveryStatus.cancelled, note=reason)

    # ── courier / eta ────────────────────────────────────────────────────
    def assign_courier(
        self,
        order_id: str,
        name: str,
        *,
        phone: Optional[str] = None,
        tracking_url: Optional[str] = None,
    ) -> DeliveryOrder:
        order = self.get(order_id)
        order.courier = Courier(name=name, phone=phone, tracking_url=tracking_url)
        order.updated_at = self._now()
        self.store.save(order)
        return order

    def set_eta(self, order_id: str, eta: datetime) -> DeliveryOrder:
        order = self.get(order_id)
        order.eta = eta
        order.updated_at = self._now()
        self.store.save(order)
        return order

    # ── tracking ─────────────────────────────────────────────────────────
    def track(self, order_id: str) -> dict[str, Any]:
        """A lightweight tracking view for the customer."""
        order = self.get(order_id)
        return {
            "id": order.id,
            "status": order.status.value,
            "eta": order.eta.isoformat() if order.eta else None,
            "courier": order.courier.model_dump() if order.courier else None,
            "timeline": [
                {
                    "status": e.status.value,
                    "at": e.at.isoformat(),
                    "note": e.note,
                }
                for e in order.timeline
            ],
        }
