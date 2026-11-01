"""Tests for restock, adjust_stock, and record_sale: each is all or nothing."""

from datetime import datetime

import pytest

import inventory_db
from inventory_db import InventoryError

FIXED_TIME = datetime(2026, 11, 1, 9, 30)


def snapshot(conn):
    """Row counts of every table plus every product's stock, to prove nothing changed."""
    stock = conn.execute("SELECT id, quantity_in_stock FROM products ORDER BY id")
    return inventory_db.table_row_counts(conn), [tuple(row) for row in stock]


def movements(conn):
    """Every logged stock movement as a tuple, in the order written."""
    rows = conn.execute(
        "SELECT product_id, change, reason, moved_at FROM stock_movements ORDER BY id"
    )
    return [tuple(row) for row in rows]


def test_restock_increases_stock_and_logs_one_movement(seeded_conn):
    assert inventory_db.restock(seeded_conn, 3, 10, when=FIXED_TIME) == 13
    assert movements(seeded_conn) == [(3, 10, "restock", "2026-11-01T09:30:00")]


@pytest.mark.parametrize("amount", [0, -5])
def test_restock_of_zero_or_less_is_refused(seeded_conn, amount):
    before = snapshot(seeded_conn)
    with pytest.raises(InventoryError):
        inventory_db.restock(seeded_conn, 3, amount)
    assert snapshot(seeded_conn) == before


def test_adjustment_that_would_go_negative_changes_nothing(seeded_conn):
    before = snapshot(seeded_conn)
    with pytest.raises(InventoryError, match="stock"):
        inventory_db.adjust_stock(seeded_conn, 3, -4)  # only 3 wrenches in stock
    assert snapshot(seeded_conn) == before


def test_sale_records_lines_reduces_stock_and_logs_movements(seeded_conn):
    inventory_db.update_price(seeded_conn, 1, 1499)  # the sale must use this new price
    sale_id = inventory_db.record_sale(seeded_conn, [(1, 2), (4, 10)], when=FIXED_TIME)

    lines = seeded_conn.execute(
        "SELECT product_id, quantity, unit_price_cents FROM sale_items"
        " WHERE sale_id = ? ORDER BY product_id",
        (sale_id,),
    )
    assert [tuple(line) for line in lines] == [(1, 2, 1499), (4, 10, 499)]
    assert inventory_db.get_product(seeded_conn, 1)["quantity_in_stock"] == 23
    assert inventory_db.get_product(seeded_conn, 4)["quantity_in_stock"] == 110
    assert movements(seeded_conn) == [
        (1, -2, "sale", "2026-11-01T09:30:00"),
        (4, -10, "sale", "2026-11-01T09:30:00"),
    ]


def test_sale_that_fails_halfway_changes_nothing(seeded_conn):
    before = snapshot(seeded_conn)
    with pytest.raises(InventoryError, match="stock"):
        # The first two lines are fine; the third asks for 50 wrenches when there are 3.
        inventory_db.record_sale(seeded_conn, [(1, 2), (4, 10), (3, 50)])
    assert snapshot(seeded_conn) == before


def test_sale_with_unknown_product_changes_nothing(seeded_conn):
    before = snapshot(seeded_conn)
    with pytest.raises(InventoryError, match="does not exist"):
        inventory_db.record_sale(seeded_conn, [(1, 2), (999, 1)])
    assert snapshot(seeded_conn) == before
