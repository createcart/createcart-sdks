from decimal import Decimal

import pytest

from createcart_cart import (
    Cart,
    CartItemNotFoundError,
    InvalidQuantityError,
)
from createcart_cart.storage import InMemoryCartStore, JSONFileCartStore


def make_cart():
    return Cart("sess-1", store=InMemoryCartStore())


def test_add_item():
    cart = make_cart()
    item = cart.add_item("plain-dosa", name="Plain Dosa", unit_price="60", quantity=2)
    assert item.quantity == 2
    assert item.line_total == Decimal("120.00")
    assert cart.count() == 1
    assert cart.total_quantity() == 2


def test_add_merges_and_refreshes_price():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60", quantity=1)
    cart.add_item("dosa", name="Dosa", unit_price="65", quantity=2)  # price changed
    item = cart.get_item("dosa")
    assert item.quantity == 3
    assert item.unit_price == Decimal("65.00")


def test_increment_decrement():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60")
    cart.increment("dosa", 2)
    assert cart.get_item("dosa").quantity == 3
    cart.decrement("dosa", 1)
    assert cart.get_item("dosa").quantity == 2
    # decrement to zero removes the line
    result = cart.decrement("dosa", 5)
    assert result is None
    assert cart.find_item("dosa") is None


def test_set_quantity_zero_removes():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60")
    assert cart.set_quantity("dosa", 0) is None
    assert cart.is_empty


def test_invalid_quantities():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60")
    with pytest.raises(InvalidQuantityError):
        cart.add_item("x", name="X", unit_price="1", quantity=0)
    with pytest.raises(InvalidQuantityError):
        cart.increment("dosa", 0)


def test_operations_on_missing_item():
    cart = make_cart()
    with pytest.raises(CartItemNotFoundError):
        cart.increment("ghost")
    with pytest.raises(CartItemNotFoundError):
        cart.remove_item("ghost")


def test_totals_with_charge():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60", quantity=2)  # 120
    cart.add_charge("parcel", "Parcel charge", "10")
    t = cart.totals()
    assert t.subtotal == Decimal("120.00")
    assert t.charges_total == Decimal("10.00")
    assert t.grand_total == Decimal("130.00")


def test_totals_with_percent_discount_and_tax():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="100", quantity=1)  # 100
    cart.set_discount("percent", "10")   # -10 -> 90
    cart.set_tax_rate("5")               # 5% of 90 = 4.50
    t = cart.totals()
    assert t.discount_total == Decimal("10.00")
    assert t.tax_total == Decimal("4.50")
    assert t.grand_total == Decimal("94.50")


def test_fixed_discount_never_below_zero():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="50", quantity=1)
    cart.set_discount("fixed", "80")  # bigger than subtotal
    t = cart.totals()
    assert t.discount_total == Decimal("50.00")
    assert t.grand_total == Decimal("0.00")


def test_charge_replaced_by_code():
    cart = make_cart()
    cart.add_charge("parcel", "Parcel", "10")
    cart.add_charge("parcel", "Parcel", "20")  # same code -> replace
    assert len(cart.data.charges) == 1
    assert cart.data.charges[0].amount == Decimal("20.00")


def test_clear_keeps_charges():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60")
    cart.add_charge("parcel", "Parcel", "10")
    cart.clear()
    assert cart.is_empty
    assert len(cart.data.charges) == 1


def test_to_dict_has_totals_and_line_total():
    cart = make_cart()
    cart.add_item("dosa", name="Dosa", unit_price="60", quantity=2)
    d = cart.to_dict()
    assert d["items"][0]["line_total"] == "120.00"
    assert d["totals"]["grand_total"] == "120.00"


def test_json_file_persistence(tmp_path):
    store = JSONFileCartStore(tmp_path)
    cart = Cart("sess-9", store=store)
    cart.add_item("dosa", name="Dosa", unit_price="60", quantity=2)
    cart.add_charge("parcel", "Parcel", "10")

    cart2 = Cart("sess-9", store=JSONFileCartStore(tmp_path))
    assert cart2.get_item("dosa").quantity == 2
    assert cart2.totals().grand_total == Decimal("130.00")


def test_json_file_rejects_unsafe_id(tmp_path):
    store = JSONFileCartStore(tmp_path)
    with pytest.raises(ValueError):
        Cart("../escape", store=store)
