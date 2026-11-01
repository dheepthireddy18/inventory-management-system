"""Create the tables and load sample data for the hardware store."""

from contextlib import closing

import inventory_db

# (id, name, email)
SUPPLIERS = [
    (1, "Acme Tools", "orders@acmetools.example"),
    (2, "BoltCo Fasteners", "sales@boltco.example"),
    (3, "BrightSpark Electrical", "hello@brightspark.example"),
    (4, "GreenThumb Garden", "support@greenthumb.example"),
]

# (id, sku, name, category, supplier_id, unit_price_cents, quantity_in_stock, reorder_level)
PRODUCTS = [
    (1, "HAM-001", "Claw Hammer", "Hand Tools", 1, 1299, 25, 5),
    (2, "SCR-001", "Screwdriver Set", "Hand Tools", 1, 1899, 15, 5),
    (3, "WRN-001", "Adjustable Wrench", "Hand Tools", 1, 1549, 3, 5),
    (4, "NAI-001", "Box of Nails", "Fasteners", 2, 499, 120, 30),
    (5, "SCW-001", "Wood Screws", "Fasteners", 2, 649, 80, 25),
    (6, "BLT-001", "Hex Bolts", "Fasteners", 2, 799, 10, 10),
    (7, "BUL-001", "LED Bulb", "Electrical", 3, 399, 60, 20),
    (8, "EXT-001", "Extension Cord", "Electrical", 3, 2499, 12, 4),
    (9, "TAP-001", "Electrical Tape", "Electrical", 3, 299, 40, 10),
    (10, "GLV-001", "Garden Gloves", "Garden", 4, 899, 30, 8),
    (11, "HOS-001", "Garden Hose", "Garden", 4, 3499, 6, 3),
    (12, "SPR-001", "Sprinkler", "Garden", 4, 1999, 9, 3),
]

# (id, sold_at)
SALES = [
    (1, "2026-10-01T10:15:00"),
    (2, "2026-10-02T14:30:00"),
    (3, "2026-10-03T09:45:00"),
    (4, "2026-10-04T16:00:00"),
    (5, "2026-10-05T11:20:00"),
]

# (sale_id, product_id, quantity, unit_price_cents)
SALE_ITEMS = [
    (1, 1, 2, 1299),
    (1, 4, 3, 499),
    (1, 7, 4, 399),
    (2, 2, 1, 1899),
    (2, 5, 2, 649),
    (3, 3, 2, 1549),
    (3, 6, 5, 799),
    (3, 9, 3, 299),
    (4, 8, 1, 2499),
    (4, 10, 2, 899),
    (5, 1, 1, 1299),
    (5, 7, 6, 399),
]


# Insert all sample data in one transaction; return False if data already exists.
def seed(conn):
    if inventory_db.table_row_counts(conn)["suppliers"] > 0:
        return False
    with conn:
        conn.executemany(
            "INSERT INTO suppliers (id, name, email) VALUES (?, ?, ?)", SUPPLIERS
        )
        conn.executemany(
            "INSERT INTO products (id, sku, name, category, supplier_id,"
            " unit_price_cents, quantity_in_stock, reorder_level)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            PRODUCTS,
        )
        conn.executemany("INSERT INTO sales (id, sold_at) VALUES (?, ?)", SALES)
        conn.executemany(
            "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price_cents)"
            " VALUES (?, ?, ?, ?)",
            SALE_ITEMS,
        )
    return True


def main():
    with closing(inventory_db.connect()) as conn:
        inventory_db.create_schema(conn)
        if seed(conn):
            print(f"Loaded sample data into {inventory_db.get_db_path()}")
        else:
            print("The database already has data; nothing was added.")
        for table, count in inventory_db.table_row_counts(conn).items():
            print(f"{table}: {count}")


if __name__ == "__main__":
    main()
