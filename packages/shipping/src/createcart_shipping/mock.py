"""A deterministic stand-in courier — used when no real provider is configured
so the whole shipping flow (quote through pickup) works end-to-end in dev, and
in tests, without ever calling out to the network."""

from __future__ import annotations

import hashlib
from typing import Optional

from .exceptions import NotServiceableError
from .models import Address, PickupResult, Serviceability, Shipment, ShipmentItem
from .provider import ShippingProvider


class MockShippingProvider(ShippingProvider):
    def __init__(self, *, origin_pin: str) -> None:
        self.origin_pin = origin_pin
        self._shipments: dict[str, Shipment] = {}

    def serviceability(self, pincode: str) -> Serviceability:
        ok = pincode.isdigit() and len(pincode) == 6 and not pincode.startswith("0")
        same_region = pincode[:2] == self.origin_pin[:2]
        return Serviceability(
            serviceable=ok,
            pincode=pincode,
            city="Hyderabad" if same_region else "Your city",
            state="Telangana" if same_region else "Other",
            cod=ok,
            prepaid=ok,
        )

    def rate(self, dest_pin: str, *, weight_g: int, payment: str) -> tuple[float, Optional[int]]:
        try:
            spread = abs(int(dest_pin[:3]) - int(self.origin_pin[:3]))
        except ValueError:
            spread = 100
        base = 45.0 + min(spread, 400) * 0.25 + max(0, weight_g - 500) // 500 * 15
        return round(base, 2), None

    def create_shipment(
        self,
        *,
        order_id: str,
        origin: Address,
        destination: Address,
        items: list[ShipmentItem],
        payment_mode: str,
        amount: float,
        weight_g: int,
    ) -> Shipment:
        svc = self.serviceability(destination.pincode)
        if not svc.serviceable:
            raise NotServiceableError(f"{destination.pincode!r} is not serviceable")
        waybill = "MOCK" + hashlib.sha1(order_id.encode()).hexdigest()[:10].upper()
        shipment = Shipment(
            waybill=waybill,
            order_id=order_id,
            status="manifested",
            raw_status="Manifested",
            tracking_url=f"https://example-tracking.test/{waybill}",
        )
        self._shipments[waybill] = shipment
        return shipment

    def track(self, waybill: str) -> Shipment:
        return self._shipments.get(waybill) or Shipment(
            waybill=waybill, order_id="", status="unknown", raw_status=None
        )

    def cancel(self, waybill: str) -> bool:
        s = self._shipments.get(waybill)
        if s is None:
            return False
        s.status = "cancelled"
        s.raw_status = "Cancelled"
        return True

    def schedule_pickup(self, *, date: str, time: str, package_count: int) -> PickupResult:
        return PickupResult(ok=True, pickup_id=f"MOCK-PICKUP-{date}-{time}".replace(":", ""))
