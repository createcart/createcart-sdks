from datetime import datetime, timezone

import pytest

from createcart_delivery import (
    DeliveryNotFoundError,
    DeliveryService,
    DeliveryStatus,
    InvalidTransitionError,
)
from createcart_delivery.storage import InMemoryDeliveryStore, JSONFileDeliveryStore

# deterministic clock
_T = [datetime(2026, 6, 20, 10, 0, 0, tzinfo=timezone.utc)]


def _clock():
    _T[0] = _T[0].replace(second=_T[0].second + 1)
    return _T[0]


def make_service(store=None):
    return DeliveryService(store or InMemoryDeliveryStore(), clock=_clock)


def test_create_starts_placed_with_timeline():
    svc = make_service()
    o = svc.create_order(
        items=[{"item_id": "pulihora", "name": "Pulihora", "quantity": 2,
                "unit_price": "50"}],
        customer={"name": "Asha", "phone": "98...", "address": "Gachibowli"},
        amount="100", cart_id="sess-1", payment_id="pay_1",
    )
    assert o.status == DeliveryStatus.placed
    assert len(o.timeline) == 1
    assert o.timeline[0].status == DeliveryStatus.placed
    assert o.items[0].line_total.compare(o.items[0].unit_price * 2) == 0
    assert o.customer.name == "Asha"


def test_advance_through_happy_path():
    svc = make_service()
    o = svc.create_order()
    for expected in ["confirmed", "preparing", "out_for_delivery", "delivered"]:
        o = svc.advance(o.id)
        assert o.status.value == expected
    assert o.is_terminal
    assert [e.status.value for e in o.timeline] == [
        "placed", "confirmed", "preparing", "out_for_delivery", "delivered"]


def test_cannot_advance_past_delivered():
    svc = make_service()
    o = svc.create_order()
    for _ in range(4):
        svc.advance(o.id)
    with pytest.raises(InvalidTransitionError):
        svc.advance(o.id)


def test_invalid_skip_transition_rejected():
    svc = make_service()
    o = svc.create_order()
    with pytest.raises(InvalidTransitionError):
        svc.set_status(o.id, "delivered")   # placed -> delivered not allowed


def test_cancel_from_non_terminal_then_locked():
    svc = make_service()
    o = svc.create_order()
    svc.advance(o.id)                        # confirmed
    o = svc.cancel(o.id, reason="customer request")
    assert o.status == DeliveryStatus.cancelled
    assert o.timeline[-1].note == "customer request"
    with pytest.raises(InvalidTransitionError):
        svc.advance(o.id)


def test_get_missing_raises():
    svc = make_service()
    with pytest.raises(DeliveryNotFoundError):
        svc.get("nope")


def test_list_and_filter_by_status():
    svc = make_service()
    a = svc.create_order(id="a")
    b = svc.create_order(id="b")
    svc.advance(b.id)                        # b -> confirmed
    assert {o.id for o in svc.list()} == {"a", "b"}
    assert [o.id for o in svc.list(status="confirmed")] == ["b"]
    assert [o.id for o in svc.list(status=DeliveryStatus.placed)] == ["a"]


def test_courier_eta_and_track():
    svc = make_service()
    o = svc.create_order(id="o1")
    svc.assign_courier("o1", "Ravi", phone="90...", tracking_url="http://t/o1")
    svc.set_eta("o1", datetime(2026, 6, 20, 12, 0, tzinfo=timezone.utc))
    svc.advance("o1")
    view = svc.track("o1")
    assert view["status"] == "confirmed"
    assert view["courier"]["name"] == "Ravi"
    assert view["eta"].startswith("2026-06-20T12:00")
    assert len(view["timeline"]) == 2


def test_duplicate_id_rejected():
    svc = make_service()
    svc.create_order(id="dup")
    with pytest.raises(InvalidTransitionError):
        svc.create_order(id="dup")


def test_list_by_customer_subject():
    svc = make_service()
    svc.create_order(id="a", customer={"name": "Asha", "subject": "g-1"})
    svc.create_order(id="b", customer={"name": "Ravi", "subject": "g-2"})
    svc.create_order(id="c", customer={"name": "Asha2", "subject": "g-1"})
    mine = svc.list(subject="g-1")
    assert {o.id for o in mine} == {"a", "c"}
    assert svc.list(subject="g-2")[0].id == "b"
    assert svc.list(subject="nobody") == []


def test_counts_by_status():
    svc = make_service()
    svc.create_order(id="a")
    svc.create_order(id="b")
    svc.advance("b")               # b -> confirmed
    counts = svc.counts_by_status()
    assert counts["placed"] == 1
    assert counts["confirmed"] == 1
    assert counts["delivered"] == 0


def test_on_event_hook_fires_on_create_and_transition():
    events = []
    svc = DeliveryService(
        InMemoryDeliveryStore(), clock=_clock,
        on_event=lambda order, ev: events.append((order.id, ev.status.value)),
    )
    o = svc.create_order(id="h1")        # placed
    svc.advance("h1")                     # confirmed
    svc.cancel("h1")                      # cancelled
    assert events == [("h1", "placed"), ("h1", "confirmed"), ("h1", "cancelled")]


def test_json_file_round_trip(tmp_path):
    store = JSONFileDeliveryStore(tmp_path)
    svc = make_service(store)
    o = svc.create_order(id="ord-1", amount="250")
    svc.advance("ord-1")

    svc2 = DeliveryService(JSONFileDeliveryStore(tmp_path), clock=_clock)
    reloaded = svc2.get("ord-1")
    assert reloaded.status == DeliveryStatus.confirmed
    assert len(reloaded.timeline) == 2
    assert [o.id for o in svc2.list()] == ["ord-1"]
