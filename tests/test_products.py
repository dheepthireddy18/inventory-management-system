"""Tests for the product functions in inventory_db.py."""

import pytest

import inventory_db
from inventory_db import InventoryError

NEW_PRODUCT = {
    "sku": "DRL-001",
    "name": "Cordless Drill",
    "category": "Power Tools",
    "supplier_id": 1,
    "unit_price_cents": 7999,
    "quantity_in_stock": 8,
    "reorder_level": 2,
}


def add_new_product(conn, **changes):
    """Add NEW_PRODUCT with some fields replaced, and return its id."""
    return inventory_db.add_product(conn, **{**NEW_PRODUCT, **changes})


def test_add_product_returns_new_id(seeded_conn):
    product_id = add_new_product(seeded_conn)
    product = inventory_db.get_product(seeded_conn, product_id)
    assert product["sku"] == "DRL-001"
    assert product["supplier_name"] == "Acme Tools"


def test_duplicate_sku_is_refused(seeded_conn):
    with pytest.raises(InventoryError, match="SKU"):
        add_new_product(seeded_conn, sku="HAM-001")


def test_unknown_supplier_is_refused(seeded_conn):
    with pytest.raises(InventoryError, match="supplier"):
        add_new_product(seeded_conn, supplier_id=999)


@pytest.mark.parametrize("field", ["unit_price_cents", "quantity_in_stock"])
def test_negative_price_or_quantity_is_refused(seeded_conn, field):
    with pytest.raises(InventoryError, match="negative"):
        add_new_product(seeded_conn, **{field: -1})


def test_update_price_changes_the_price(seeded_conn):
    assert inventory_db.update_price(seeded_conn, 1, 1499) is True
    assert inventory_db.get_product(seeded_conn, 1)["unit_price_cents"] == 1499


def test_update_price_of_missing_product_returns_false(seeded_conn):
    assert inventory_db.update_price(seeded_conn, 999, 1499) is False


def test_sold_product_cannot_be_deleted(seeded_conn):
    with pytest.raises(InventoryError, match="sales history"):
        inventory_db.delete_product(seeded_conn, 1)


def test_never_sold_product_can_be_deleted(seeded_conn):
    assert inventory_db.delete_product(seeded_conn, 11) is True
    assert inventory_db.get_product(seeded_conn, 11) is None
