"""Tests for seed_db.py: the sample data matches the assignment's requirements."""

import seed_db
from inventory_db import table_row_counts


def test_seed_loads_expected_row_counts(conn):
    seed_db.seed(conn)
    assert table_row_counts(conn) == {
        "suppliers": 4,
        "products": 12,
        "sales": 5,
        "sale_items": 12,
        "stock_movements": 0,
    }


def test_seed_twice_does_not_duplicate_data(conn):
    seed_db.seed(conn)
    assert seed_db.seed(conn) is False
    assert table_row_counts(conn)["products"] == 12


def test_seed_has_at_least_three_categories(conn):
    seed_db.seed(conn)
    count = conn.execute("SELECT COUNT(DISTINCT category) FROM products").fetchone()[0]
    assert count >= 3
