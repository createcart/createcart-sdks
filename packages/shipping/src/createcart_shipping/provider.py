"""The ``ShippingProvider`` interface every courier integration implements.

Mirrors the pattern used elsewhere in CreateCart (``PaymentProvider``,
``NotifyProvider``): a small, pluggable surface so the app code never talks to
a specific courier directly. Add UPS/Shadowfax/Porter later by implementing
this same interface — no caller changes.
"""

from __future__ import annotations

from typing import Optional, Protocol

from .models import Address, PickupResult, Serviceability, Shipment, ShipmentItem


class ShippingProvider(Protocol):
    """A courier: check coverage, price it, ship it, track it, cancel it."""

    def serviceability(self, pincode: str) -> Serviceability: ...

    def rate(
        self, dest_pin: str, *, weight_g: int, payment: str
    ) -> tuple[float, Optional[int]]:
        """Return ``(base_charge, eta_days_or_None)`` for the destination."""
        ...

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
        """Manifest a shipment (generate a waybill/AWB) for a paid order."""
        ...

    def track(self, waybill: str) -> Shipment:
        """Re-fetch the current status for a previously created shipment."""
        ...

    def cancel(self, waybill: str) -> bool:
        """Cancel a shipment that hasn't been delivered yet."""
        ...

    def schedule_pickup(
        self, *, date: str, time: str, package_count: int
    ) -> PickupResult:
        """Request a courier pickup for ``package_count`` manifested shipments."""
        ...
