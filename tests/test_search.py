"""Tests for search_products in inventory_db.py."""

import pytest

import inventory_db
from inventory_db import search_products


def skus(rows):
    """Return the SKUs of the result rows, in order."""
    return [row["sku"] for row in rows]


@pytest.mark.parametrize(
    "text, expected",
    [
        ("CLAW", ["HAM-001"]),  # product name
        ("wrn-001", ["WRN-001"]),  # SKU
        ("brightSPARK", ["TAP-001", "EXT-001", "BUL-001"]),  # supplier name
    ],
)
def test_search_matches_name_sku_and_supplier_ignoring_case(
    seeded_conn, text, expected
):
    assert skus(search_products(seeded_conn, text)) == expected


@pytest.mark.parametrize(
    "filters, expected",
    [
        ({"category": "Garden"}, ["GLV-001", "HOS-001", "SPR-001"]),
        ({"max_price_cents": 499}, ["NAI-001", "TAP-001", "BUL-001"]),
        ({"low_stock_only": True}, ["WRN-001", "BLT-001"]),
    ],
)
def test_each_filter_works(seeded_conn, filters, expected):
    assert skus(search_products(seeded_conn, **filters)) == expected


def test_in_stock_only_hides_products_with_no_stock(seeded_conn):
    inventory_db.add_product(
        seeded_conn, "DRL-001", "Cordless Drill", "Power Tools", 1, 7999, 0, 2
    )
    assert "DRL-001" not in skus(search_products(seeded_conn, in_stock_only=True))


def test_filters_combine(seeded_conn):
    results = search_products(seeded_conn, category="Hand Tools", low_stock_only=True)
    assert skus(results) == ["WRN-001"]


def test_dangerous_text_finds_nothing_and_harms_nothing(seeded_conn):
    assert search_products(seeded_conn, "'; DROP TABLE products; --") == []
    assert inventory_db.table_row_counts(seeded_conn)["products"] == 12
