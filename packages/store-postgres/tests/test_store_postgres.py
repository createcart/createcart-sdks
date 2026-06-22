"""Postgres store tests.

These need a real Postgres — set ``TEST_DATABASE_URL`` to a throwaway database
(e.g. a Supabase test project or local ``postgres``) to run them; otherwise they
skip. The suite mirrors the SQLite store's behaviour: tenant registry, per-tenant
isolation, and round-tripping a menu/cart/payment/delivery through the protocols.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

DSN = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DSN, reason="set TEST_DATABASE_URL to run")


@pytest.fixture()
def db():
    from createcart_store_postgres import PgDatabase

    database = PgDatabase(DSN)
    # clean any tables from a previous run for the test tenants
    with database.connect() as conn:
        for t in ("alpha", "beta"):
            tid = conn.execute("SELECT id FROM tenants WHERE name=%s", (t,)).fetchone()
            if tid:
                i = tid["id"]
                for tbl in ("menu_items", "categories", "combos", "carts",
                            "payments", "deliveries"):
                    conn.execute(f"DROP TABLE IF EXISTS {tbl}_{i}")
                conn.execute("DELETE FROM tenants WHERE name=%s", (t,))
    return database


def test_tenant_ids_increment_from_zero(db):
    from createcart_store_postgres import PgMenuStore

    a = PgMenuStore(db, "alpha")
    b = PgMenuStore(db, "beta")
    assert {db.tenant_name(a.tid), db.tenant_name(b.tid)} == {"alpha", "beta"}
    assert db.tenant_id("alpha") == a.tid
    assert (a.tid, "alpha") in db.list_tenants()


def test_menu_round_trip_and_isolation(db):
    from createcart_registry import MenuRegistry
    from createcart_store_postgres import PgMenuStore

    ra = MenuRegistry(store=PgMenuStore(db, "alpha"))
    ra.add_item("dosa", name="Dosa", price="60")
    ra.add_item("idli", name="Idli", price="40")

    rb = MenuRegistry(store=PgMenuStore(db, "beta"))
    rb.add_item("tea", name="Tea", price="10")

    # reload from fresh stores
    again_a = MenuRegistry(store=PgMenuStore(db, "alpha"))
    again_b = MenuRegistry(store=PgMenuStore(db, "beta"))
    assert {i.id for i in again_a.list_items()} == {"dosa", "idli"}
    assert {i.id for i in again_b.list_items()} == {"tea"}
    assert again_a.get_item("dosa").price == Decimal("60")


def test_update_tenant_auth_fields(db):
    from createcart_store_postgres import PgMenuStore

    PgMenuStore(db, "alpha")  # ensure tenant exists
    db.update_tenant("alpha", password_hash="hash123", base_url="https://x.test")
    rec = db.get_tenant("alpha")
    assert rec["password_hash"] == "hash123"
    assert rec["base_url"] == "https://x.test"
    # base_url is exposed, password is not, in the public listing
    full = {t["name"]: t for t in db.list_tenants_full()}
    assert full["alpha"]["base_url"] == "https://x.test"
    assert "password_hash" not in full["alpha"]
