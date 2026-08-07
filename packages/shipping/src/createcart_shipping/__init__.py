"""CreateCart Shipping SDK.

Pincode serviceability, rate quotes, shipment manifestation, tracking,
cancellation, and pickup requests — behind a pluggable ``ShippingProvider``
(``DelhiveryProvider`` for real B2C Express shipping, ``MockShippingProvider``
for dev/tests).

    from createcart_shipping import ShippingService, MockShippingProvider, Address

    svc = ShippingService(
        MockShippingProvider(origin_pin="500032"),
        origin=Address(name="Brahmana Naivedyam", phone="+91...", address="...",
                        pincode="500032", city="Hyderabad", state="Telangana"),
        default_weight_g=500,
        handling_fee=40.0,
    )
    quote = svc.quote("560001")             # servicability + ETA + charge
    shipment = svc.ship(order_id="ord_1", destination=..., items=[...],
                        payment_mode="prepaid", amount=170)
    svc.track(shipment.waybill)
    svc.schedule_pickup(date="2026-08-07", time="15:00", package_count=1)
"""

from .delhivery import DelhiveryProvider
from .exceptions import (
    NotServiceableError,
    ShipmentCreationError,
    ShipmentNotFoundError,
    ShippingError,
)
from .mock import MockShippingProvider
from .models import (
    Address,
    PickupResult,
    Quote,
    Serviceability,
    Shipment,
    ShipmentItem,
)
from .provider import ShippingProvider
from .service import ShippingService

__all__ = [
    "ShippingService",
    "ShippingProvider",
    "DelhiveryProvider",
    "MockShippingProvider",
    "Address",
    "ShipmentItem",
    "Serviceability",
    "Quote",
    "Shipment",
    "PickupResult",
    "ShippingError",
    "NotServiceableError",
    "ShipmentCreationError",
    "ShipmentNotFoundError",
]

__version__ = "0.1.0"
