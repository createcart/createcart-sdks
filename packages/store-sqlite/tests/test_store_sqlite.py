from decimal import Decimal

import pytest

from createcart_cart import Cart
from createcart_delivery import DeliveryService, DeliveryStatus
from createcart_payment import MockProvider, PaymentService
from createcart_registry import MenuRegistry
from createcart_store_sqlite import (
    Database,
    SqliteCartStore,
    SqliteDeliveryStore,
    SqliteMenuStore,
    SqlitePaymentStore,
)


def test_tenant_ids_start_at_zero_and_increment(tmp_path):
    db = Database(tmp_path / "cc.db")
    assert db.get_or_create_tenant("brahmana-naivedyam") == 0
    assert db.get_or_create_tenant("second-tenant") == 1
    assert db.get_or_create_tenant("brahmana-naivedyam") == 0  # stable
    assert db.list_tenants() == [(0, "brahmana-naivedyam"), (1, "second-tenant")]
    assert db.tenant_name(1) == "second-tenant"
    assert db.tenant_id("second-tenant") == 1


def test_tenant_password_and_base_url(tmp_path):
    db = Database(tmp_path / "cc.db")
    db.get_or_create_tenant("acme")
    db.update_tenant("acme", password_hash="HASH", base_url="http://x")
    rec = db.get_tenant("acme")
    assert rec["id"] == 0 and rec["password_hash"] == "HASH" and rec["base_url"] == "http://x"
    assert db.list_tenants_full() == [{"id": 0, "name": "acme", "base_url": "http://x"}]


def test_explicit_tenant_id(tmp_path):
    db = Database(tmp_path / "cc.db")
    assert db.get_or_create_tenant("acme", tenant_id=7) == 7
    with pytest.raises(ValueError):
        db.get_or_create_tenant("beta", tenant_id=7)   # id already in use


def test_invalid_tenant_name_rejected(tmp_path):
    db = Database(tmp_path / "cc.db")
    for bad in ["Brahmana", "1tenant", "te nant", "tenant_", "../x"]:
        with pytest.raises(ValueError):
            db.get_or_create_tenant(bad)


def test_per_tenant_tables_created(tmp_path):
    db = Database(tmp_path / "cc.db")
    db.get_or_create_tenant("alpha")   # id 0
    db.get_or_create_tenant("beta")    # id 1
    import sqlite3
    with sqlite3.connect(db.path) as conn:
        names = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    for t in ["menu_items_0", "carts_0", "payments_0",
              "menu_items_1", "carts_1", "payments_1", "tenants"]:
        assert t in names


def test_menu_store_round_trip_and_isolation(tmp_path):
    db = Database(tmp_path / "cc.db")
    a = MenuRegistry(store=SqliteMenuStore(db, "alpha"))
    b = MenuRegistry(store=SqliteMenuStore(db, "beta"))
    a.add_item(name="Plain Dosa", price="60", tags=["SPECIAL"], icon="🫓")
    b.add_item(name="Idli", price="40")

    # reload fresh registries over the same DB
    a2 = MenuRegistry(store=SqliteMenuStore(db, "alpha"))
    assert a2.get_item("plain-dosa").price == Decimal("60.00")
    assert a2.count() == 1                       # alpha sees only its own item
    b2 = MenuRegistry(store=SqliteMenuStore(db, "beta"))
    assert [i.id for i in b2.list_items()] == ["idli"]


def test_cart_store_round_trip(tmp_path):
    db = Database(tmp_path / "cc.db")
    cart = Cart("sess-1", store=SqliteCartStore(db, "alpha"))
    cart.add_item("plain-dosa", name="Plain Dosa", unit_price="60", quantity=2)
    cart.add_charge("parcel", "Parcel", "10")

    cart2 = Cart("sess-1", store=SqliteCartStore(db, "alpha"))
    assert cart2.get_item("plain-dosa").quantity == 2
    assert cart2.totals().grand_total == Decimal("130.00")

    cart2.clear()  # uses delete-less clear (empties items) -> persisted
    assert Cart("sess-1", store=SqliteCartStore(db, "alpha")).is_empty


def test_payment_store_round_trip(tmp_path):
    db = Database(tmp_path / "cc.db")
    provider = MockProvider()
    svc = PaymentService(provider, store=SqlitePaymentStore(db, "alpha"))
    order = svc.create_order(13000, cart_id="sess-1")
    pay = provider.make_test_payment(order.id)
    svc.verify_payment(order.id, pay["payment_id"], pay["signature"])

    svc2 = PaymentService(provider, store=SqlitePaymentStore(db, "alpha"))
    rec = svc2.store.get(order.id)
    assert rec.status.value == "paid"
    assert rec.amount == 13000


def test_delivery_store_round_trip_and_list(tmp_path):
    db = Database(tmp_path / "cc.db")
    svc = DeliveryService(SqliteDeliveryStore(db, "alpha"))
    o = svc.create_order(id="ord-1", amount="250", cart_id="sess-1")
    svc.advance("ord-1")  # -> confirmed

    svc2 = DeliveryService(SqliteDeliveryStore(db, "alpha"))
    reloaded = svc2.get("ord-1")
    assert reloaded.status == DeliveryStatus.confirmed
    assert len(reloaded.timeline) == 2
    assert [o.id for o in svc2.list(status="confirmed")] == ["ord-1"]
