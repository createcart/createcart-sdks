"""ShippingService — the app-facing wrapper around a ShippingProvider.

Turns raw provider calls into business-level operations: applies the flat
handling markup to quotes, derives an ETA when the provider doesn't supply
one, and builds the shipment/pickup calls from plain app data (no provider-
specific payload shapes leak past this layer).
"""

from __future__ import annotations

from typing import Optional

from .models import Address, PickupResult, Quote, Serviceability, Shipment, ShipmentItem
from .provider import ShippingProvider


def _eta_label(days: int) -> str:
    if days <= 1:
        return "~1 day"
    return f"{days}–{days + 1} days"


class ShippingService:
    def __init__(
        self,
        provider: ShippingProvider,
        *,
        origin: Address,
        default_weight_g: int,
        handling_fee: float,
    ) -> None:
        self.provider = provider
        self.origin = origin
        self.default_weight_g = default_weight_g
        self.handling_fee = handling_fee

    # ── quote ────────────────────────────────────────────────────────────
    def serviceability(self, pincode: str) -> Serviceability:
        return self.provider.serviceability(pincode)

    def quote(
        self, pincode: str, *, weight_g: Optional[int] = None, payment: str = "prepaid"
    ) -> Quote:
        svc = self.provider.serviceability(pincode)
        if not svc.serviceable:
            return Quote(serviceable=False, pincode=pincode, city=svc.city, state=svc.state)
        base, eta_days = self.provider.rate(
            pincode, weight_g=weight_g or self.default_weight_g, payment=payment
        )
        if eta_days is None:
            same_state = bool(svc.state) and bool(self.origin.state) and (
                svc.state.strip().lower() == self.origin.state.strip().lower()
            )
            eta_days = 2 if same_state else 4
        charge = round(base + self.handling_fee, 2)
        return Quote(
            serviceable=True,
            pincode=pincode,
            city=svc.city,
            state=svc.state,
            base_charge=base,
            handling_fee=self.handling_fee,
            charge=charge,
            eta=_eta_label(eta_days),
            eta_days=eta_days,
            cod_available=svc.cod,
        )

    # ── fulfillment ──────────────────────────────────────────────────────
    def ship(
        self,
        *,
        order_id: str,
        destination: Address,
        items: list[ShipmentItem],
        payment_mode: str,
        amount: float,
        weight_g: Optional[int] = None,
    ) -> Shipment:
        return self.provider.create_shipment(
            order_id=order_id,
            origin=self.origin,
            destination=destination,
            items=items,
            payment_mode=payment_mode,
            amount=amount,
            weight_g=weight_g or self.default_weight_g,
        )

    def track(self, waybill: str) -> Shipment:
        return self.provider.track(waybill)

    def cancel(self, waybill: str) -> bool:
        return self.provider.cancel(waybill)

    def schedule_pickup(self, *, date: str, time: str, package_count: int) -> PickupResult:
        return self.provider.schedule_pickup(date=date, time=time, package_count=package_count)
