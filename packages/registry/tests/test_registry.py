from decimal import Decimal

import pytest

from createcart_registry import (
    DuplicateItemError,
    ItemNotFoundError,
    MenuRegistry,
    OutOfStockError,
)
from createcart_registry.storage import InMemoryStore, JSONFileStore


def test_add_and_get_item():
    reg = MenuRegistry()
    item = reg.add_item(name="Plain Dosa", price="60", category="dosa", icon="🫓")
    assert item.id == "plain-dosa"
    assert reg.get_item("plain-dosa").price == Decimal("60.00")
    assert reg.count() == 1


def test_price_is_decimal_not_float():
    reg = MenuRegistry()
    item = reg.add_item(name="X", price=70.1)
    assert item.price == Decimal("70.10")
    assert isinstance(item.price, Decimal)


def test_unique_id_collision():
    reg = MenuRegistry()
    a = reg.add_item(name="Dosa")
    b = reg.add_item(name="Dosa")
    assert a.id == "dosa"
    assert b.id == "dosa-2"


def test_duplicate_explicit_id_raises():
    reg = MenuRegistry()
    reg.add_item(name="Dosa", id="dosa")
    with pytest.raises(DuplicateItemError):
        reg.add_item(name="Other", id="dosa")


def test_update_and_set_price():
    reg = MenuRegistry()
    reg.add_item(name="Dosa", price="60")
    reg.set_price("dosa", "75")
    assert reg.get_item("dosa").price == Decimal("75.00")


def test_availability_and_stock():
    reg = MenuRegistry()
    reg.add_item(name="Dosa", stock=2)
    assert reg.is_available("dosa") is True
    reg.adjust_stock("dosa", -2)
    assert reg.get_item("dosa").stock == 0
    assert reg.is_available("dosa") is False
    with pytest.raises(OutOfStockError):
        reg.adjust_stock("dosa", -1)


def test_untracked_stock_adjust_is_noop():
    reg = MenuRegistry()
    reg.add_item(name="Dosa")  # stock=None
    reg.adjust_stock("dosa", -5)
    assert reg.get_item("dosa").stock is None
    assert reg.is_available("dosa") is True


def test_remove_item_cleans_combo_refs():
    reg = MenuRegistry()
    reg.add_item(name="Pulihora", id="pulihora")
    reg.add_item(name="Upma", id="upma")
    reg.add_combo(name="Combo", price="100", item_ids=["pulihora", "upma"])
    reg.remove_item("pulihora")
    assert reg.list_combos()[0].item_ids == ["upma"]


def test_combo_rejects_unknown_item():
    reg = MenuRegistry()
    with pytest.raises(ItemNotFoundError):
        reg.add_combo(name="Combo", item_ids=["nope"])


def test_list_filters_and_search():
    reg = MenuRegistry()
    reg.add_item(name="Plain Dosa", category="dosa", tags=["SPECIAL"])
    reg.add_item(name="Pulihora", category="rice", available=False)
    assert len(reg.list_items(category="dosa")) == 1
    assert len(reg.list_items(available_only=True)) == 1
    assert len(reg.list_items(tag="SPECIAL")) == 1
    assert reg.search("pulihora")[0].id == "pulihora"


def test_categories_grouping_and_removal():
    reg = MenuRegistry()
    reg.add_category("Dosa", id="dosa")
    reg.add_item(name="Plain Dosa", category="dosa")
    grouped = reg.items_by_category()
    assert "dosa" in grouped
    reg.remove_category("dosa")
    assert reg.get_item("plain-dosa").category is None


def test_import_items_bulk():
    reg = MenuRegistry()
    created = reg.import_items(
        [
            {"name": "A", "price": "10"},
            {"name": "B", "price": "20", "tags": ["SWEET"]},
        ]
    )
    assert len(created) == 2
    assert reg.count() == 2


def test_json_file_round_trip(tmp_path):
    path = tmp_path / "menu.json"
    reg = MenuRegistry(store=JSONFileStore(path), tenant="brahmana")
    reg.add_item(name="Pulihora", price="50", tags=["SPECIAL"], icon="🍚")

    # Fresh registry over the same file should see the persisted item.
    reg2 = MenuRegistry(store=JSONFileStore(path))
    assert reg2.get_item("pulihora").price == Decimal("50.00")
    assert reg2.catalog.tenant == "brahmana"


def test_inmemory_store_isolation():
    store = InMemoryStore()
    reg = MenuRegistry(store=store)
    reg.add_item(name="Dosa")
    # load() returns a copy; mutating it must not corrupt the registry.
    loaded = store.load()
    loaded.items.clear()
    assert reg.count() == 1
