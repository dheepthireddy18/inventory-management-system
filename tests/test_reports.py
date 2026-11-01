"""Tests for the four reports, using the sample data from seed_db."""

import inventory_db


def as_tuples(rows):
    """Turn result rows into plain tuples so whole reports can be compared."""
    return [tuple(row) for row in rows]


def test_stock_value_by_supplier(seeded_conn):
    assert as_tuples(inventory_db.stock_value_by_supplier(seeded_conn)) == [
        ("BoltCo Fasteners", 119790),
        ("GreenThumb Garden", 65955),
        ("BrightSpark Electrical", 65888),
        ("Acme Tools", 65607),
    ]


def test_low_stock(seeded_conn):
    assert as_tuples(inventory_db.low_stock(seeded_conn)) == [
        ("WRN-001", "Adjustable Wrench", 3, 5, 2),
        ("BLT-001", "Hex Bolts", 10, 10, 0),
    ]


def test_sales_by_product(seeded_conn):
    assert as_tuples(inventory_db.sales_by_product(seeded_conn)) == [
        ("BLT-001", "Hex Bolts", 5, 3995),
        ("BUL-001", "LED Bulb", 10, 3990),
        ("HAM-001", "Claw Hammer", 3, 3897),
        ("WRN-001", "Adjustable Wrench", 2, 3098),
        ("EXT-001", "Extension Cord", 1, 2499),
        ("SCR-001", "Screwdriver Set", 1, 1899),
        ("GLV-001", "Garden Gloves", 2, 1798),
        ("NAI-001", "Box of Nails", 3, 1497),
        ("SCW-001", "Wood Screws", 2, 1298),
        ("TAP-001", "Electrical Tape", 3, 897),
    ]


def test_never_sold(seeded_conn):
    assert as_tuples(inventory_db.never_sold(seeded_conn)) == [
        ("HOS-001", "Garden Hose"),
        ("SPR-001", "Sprinkler"),
    ]
