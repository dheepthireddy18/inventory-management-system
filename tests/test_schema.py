"""
tests for the database schema
"""

import pytest

import inventory_db


@pytest.fixture
def supplier_id(conn):
    """Insert one supplier and return its id."""
    cursor = conn.execute("INSERT INTO suppliers (name) VALUES (?)", ("Acme Tools",))
    return cursor.lastrowid


def test_foreign_keys_are_on(conn):
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_rows_are_readable_by_column_name(conn, supplier_id):
    row = conn.execute(
        "SELECT name FROM suppliers WHERE id = ?", (supplier_id,)
    ).fetchone()
    assert row["name"] == "Acme Tools"


def test_schema_can_run_twice_without_losing_data(conn, supplier_id):
    inventory_db.create_schema(conn)
    count = conn.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]
    assert count == 1
