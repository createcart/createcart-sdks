import pytest

from createcart_shipping import (
    Address,
    MockShippingProvider,
    NotServiceableError,
    ShipmentItem,
    ShippingService,
)

ORIGIN = Address(
    name="Brahmana Naivedyam", phone="+919999999999", address="Gachibowli",
    pincode="500032", city="Hyderabad", state="Telangana",
)


def make_service():
    return ShippingService(
        MockShippingProvider(origin_pin="500032"),
        origin=ORIGIN,
        default_weight_g=500,
        handling_fee=40.0,
    )


def test_serviceability_valid_pincode():
    svc = make_service()
    s = svc.serviceability("560001")
    assert s.serviceable is True
    assert s.pincode == "560001"


def test_serviceability_rejects_bad_pincode():
    svc = make_service()
    assert svc.serviceability("012345").serviceable is False


def test_quote_applies_handling_fee_and_eta():
    svc = make_service()
    q = svc.quote("560001")
    assert q.serviceable is True
    assert q.charge == round(q.base_charge + 40.0, 2)
    assert q.eta_days is not None
    assert q.eta


def test_quote_unserviceable_pincode_has_no_charge():
    svc = make_service()
    q = svc.quote("012345")
    assert q.serviceable is False
    assert q.charge == 0.0


def test_ship_creates_a_waybill():
    svc = make_service()
    dest = Address(name="Priya", phone="+919000000000", address="MG Road",
                    pincode="560001", city="Bengaluru", state="Karnataka")
    shipment = svc.ship(
        order_id="ord_1", destination=dest,
        items=[ShipmentItem(description="Mango Pickle 250g", quantity=2)],
        payment_mode="prepaid", amount=170,
    )
    assert shipment.waybill.startswith("MOCK")
    assert shipment.status == "manifested"
    assert shipment.tracking_url


def test_ship_rejects_unserviceable_destination():
    svc = make_service()
    dest = Address(name="X", phone="+919000000000", address="?",
                    pincode="012345")
    with pytest.raises(NotServiceableError):
        svc.ship(order_id="ord_2", destination=dest, items=[],
                 payment_mode="prepaid", amount=100)


def test_track_returns_the_shipment_status():
    svc = make_service()
    dest = Address(name="Priya", phone="+919000000000", address="MG Road", pincode="560001")
    shipment = svc.ship(order_id="ord_3", destination=dest, items=[],
                         payment_mode="prepaid", amount=100)
    tracked = svc.track(shipment.waybill)
    assert tracked.waybill == shipment.waybill
    assert tracked.status == "manifested"


def test_track_unknown_waybill():
    svc = make_service()
    assert svc.track("NOPE").status == "unknown"


def test_cancel_marks_shipment_cancelled():
    svc = make_service()
    dest = Address(name="Priya", phone="+919000000000", address="MG Road", pincode="560001")
    shipment = svc.ship(order_id="ord_4", destination=dest, items=[],
                         payment_mode="prepaid", amount=100)
    assert svc.cancel(shipment.waybill) is True
    assert svc.track(shipment.waybill).status == "cancelled"


def test_cancel_unknown_waybill_returns_false():
    svc = make_service()
    assert svc.cancel("NOPE") is False


def test_schedule_pickup():
    svc = make_service()
    result = svc.schedule_pickup(date="2026-08-07", time="15:00", package_count=3)
    assert result.ok is True
    assert result.pickup_id
