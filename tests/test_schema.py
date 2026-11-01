"""
tests for the database schema
"""

import sqlite3
import pytest
import inventory_db

@pytest.fixture
def supplier_id(conn):
    cursor = conn.execute("INSERT INTO suppliers (name) VALUES (?)", ("Acme Tools",))
    return cursor.lastrowid

def insert_product(conn, supplier_id, sku= "HAM-001", price_cents=1299, quantity=10):
    cursor = conn.execute(
        "INSERT INTO products (sku, name, category, supplier_id, unite_price_cents, quantity_in_stock, reorder_level)"
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (sku, "Hammer", "Tools", supplier_id, price_cents, quantity, 5)
    )
    return cursor.lastrowid

def test_foriegn_keys_are_on(conn):
    assert conn.execute("PRAGMA foriegn_keys").fetchone()[0] ==1

def test_rows_are_readable_by_column_name(conn, supplier_id):
    row = conn.execute(
        "SELECT name FROM suppliers WHERE id = ?", (supplier_id,)
    ).fetchone()
    assert row["name"] == "Acme Tools"

def test_schema_can_run_twice_without_losing_data(conn, supplier_id):
    inventory_db.create_schema(conn)
    count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count == 1

def test_duplicate_sku_is_rejected(conn, supplier_id):
    insert_product(conn, supplier_id)
    with pytest.raises(sqlite3.IntegrityError):
        insert_product(conn, supplier_id)


def test_unknown_supplier_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        insert_product(conn, supplier_id=999)

@pytest.mark.parametrize("price_cents, quantity", [(-1, 10), (1299, -1)])
def test_negative_price_or_quantity_is_rejected(
    conn, supplier_id, price_cents, quantity
):
    with pytest.raises(sqlite3.IntegrityError):
        insert_product(conn, supplier_id, price_cents=price_cents, quantity=quantity)

def test_strict_table_rejects_text_in_number_column(conn, supplier_id):
    with pytest.raises(sqlite3.IntegrityError):
        insert_product(conn, supplier_id, price_cents="twelve dollars")

def test_invalid_movement_reason_is_rejected(conn, supplier_id):
    product_id = insert_product(conn, supplier_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO stock_movements (product_id, change, reason, moved_at)"
            " VALUES (?, ?, ?, ?)",
            (product_id, 5, "theft", "2026-01-01T09:00:00"),
        )