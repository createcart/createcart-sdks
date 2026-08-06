"""Data models for the shipping SDK — plain dataclasses (no pydantic dependency),
mirroring the shape of what a courier's REST API returns after normalization."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Address:
    """A pickup or delivery address."""

    name: str
    phone: str
    address: str
    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"


@dataclass
class ShipmentItem:
    """One line of what's inside the parcel (courier manifests want a description,
    not a full menu — SKUs/prices/quantities collapse into this)."""

    description: str
    quantity: int = 1
    hsn_code: str = ""


@dataclass
class Serviceability:
    serviceable: bool
    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None
    cod: bool = False
    prepaid: bool = False


@dataclass
class Quote:
    """A priced, ETA'd delivery quote for a destination pincode."""

    serviceable: bool
    pincode: str
    city: Optional[str] = None
    state: Optional[str] = None
    base_charge: float = 0.0        # provider's own charge
    handling_fee: float = 0.0       # flat markup on top
    charge: float = 0.0             # total = base + handling
    currency: str = "INR"
    eta: Optional[str] = None       # human label, e.g. "1-2 days"
    eta_days: Optional[int] = None
    cod_available: bool = False


# Normalized shipment lifecycle — courier-agnostic. Providers map their own
# vocabulary (e.g. Delhivery's "Manifested"/"In Transit"/"Pending") onto this.
SHIPMENT_STATUSES = (
    "manifested",     # waybill created, not yet picked up
    "in_transit",     # picked up, moving through the courier network
    "out_for_delivery",
    "delivered",
    "failed",         # NDR / delivery attempt failed
    "cancelled",
    "unknown",
)


@dataclass
class Shipment:
    """A courier's view of one order: a waybill (AWB) plus its current status."""

    waybill: str
    order_id: str
    status: str = "manifested"          # normalized (SHIPMENT_STATUSES)
    raw_status: Optional[str] = None    # provider's own status text, for display
    courier_name: str = "Delhivery"
    tracking_url: Optional[str] = None
    remarks: Optional[str] = None       # provider's message (e.g. why creation failed)


@dataclass
class PickupResult:
    ok: bool
    pickup_id: Optional[str] = None
    remarks: Optional[str] = None
