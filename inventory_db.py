import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_DB_PATH = BASE_DIR / "inventory.db"


# Raised when a business rule is broken
class InventoryError(Exception):
    pass


# Return INVENTORY_DB if it is set, else inventory.db next to the code.
def get_db_path():
    return os.environ.get("INVENTORY_DB", str(DEFAULT_DB_PATH))


# open a connection with foreign keys on and rows readable by column name
def connect(db_path=None):
    if db_path is None:
        db_path = get_db_path()
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    return connection


# create any missing tables and indexes, existing tables and data are kept.
def create_schema(conn):
    conn.executescript(SCHEMA_PATH.read_text())


# One fixed query; table names are written here, never taken from input.
ROW_COUNTS_SQL = """
    SELECT 'suppliers' AS table_name, COUNT(*) AS row_count FROM suppliers
    UNION ALL SELECT 'products', COUNT(*) FROM products
    UNION ALL SELECT 'sales', COUNT(*) FROM sales
    UNION ALL SELECT 'sale_items', COUNT(*) FROM sale_items
    UNION ALL SELECT 'stock_movements', COUNT(*) FROM stock_movements
"""


# Return a dict of table name to row count, in schema order.
def table_row_counts(conn):
    return {row["table_name"]: row["row_count"] for row in conn.execute(ROW_COUNTS_SQL)}


# Turn a database IntegrityError from saving a product into a readable message.
def _product_error_message(error, sku):
    message = str(error)
    if "UNIQUE" in message:
        return f"A product with SKU {sku!r} already exists."
    if "FOREIGN KEY" in message:
        return "That supplier does not exist."
    if "CHECK" in message:
        return "Price and quantities cannot be negative."
    return "Every product field is required."


# Insert a product and return its new id.
def add_product(
    conn,
    sku,
    name,
    category,
    supplier_id,
    unit_price_cents,
    quantity_in_stock,
    reorder_level,
):
    try:
        with conn:
            cursor = conn.execute(
                "INSERT INTO products (sku, name, category, supplier_id,"
                " unit_price_cents, quantity_in_stock, reorder_level)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    sku,
                    name,
                    category,
                    supplier_id,
                    unit_price_cents,
                    quantity_in_stock,
                    reorder_level,
                ),
            )
    except sqlite3.IntegrityError as error:
        raise InventoryError(_product_error_message(error, sku)) from error
    return cursor.lastrowid


# Return one product with its supplier's name, or None if it does not exist.
def get_product(conn, product_id):
    return conn.execute(
        "SELECT p.id, p.sku, p.name, p.category, p.unit_price_cents,"
        " p.quantity_in_stock, p.reorder_level, s.name AS supplier_name"
        " FROM products AS p"
        " JOIN suppliers AS s ON s.id = p.supplier_id"
        " WHERE p.id = ?",
        (product_id,),
    ).fetchone()


# Change a product's price; return False if the product does not exist.
def update_price(conn, product_id, new_price_cents):
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE products SET unit_price_cents = ? WHERE id = ?",
                (new_price_cents, product_id),
            )
    except sqlite3.IntegrityError as error:
        raise InventoryError("Price cannot be negative.") from error
    return cursor.rowcount == 1


# Delete a product, return False if it does not exist.
# A product with sales history is refused by the ON DELETE RESTRICT foreign key.
def delete_product(conn, product_id):
    try:
        with conn:
            cursor = conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
    except sqlite3.IntegrityError as error:
        raise InventoryError(
            "This product has sales history and cannot be deleted."
        ) from error
    return cursor.rowcount == 1


# Find products whose name, SKU, or supplier name contains text, ignoring case.
# Optional filters combine with AND. Results are sorted by name.
def search_products(
    conn,
    text="",
    category=None,
    max_price_cents=None,
    in_stock_only=False,
    low_stock_only=False,
):
    pattern = f"%{text}%"
    conditions = ["(p.name LIKE ? OR p.sku LIKE ? OR s.name LIKE ?)"]
    params = [pattern, pattern, pattern]
    if category is not None:
        conditions.append("p.category = ?")
        params.append(category)
    if max_price_cents is not None:
        conditions.append("p.unit_price_cents <= ?")
        params.append(max_price_cents)
    if in_stock_only:
        conditions.append("p.quantity_in_stock > 0")
    if low_stock_only:
        conditions.append("p.quantity_in_stock <= p.reorder_level")
    sql = (
        "SELECT p.id, p.sku, p.name, p.category, p.unit_price_cents,"
        " p.quantity_in_stock, p.reorder_level, s.name AS supplier_name"
        " FROM products AS p"
        " JOIN suppliers AS s ON s.id = p.supplier_id"
        " WHERE " + " AND ".join(conditions) + " ORDER BY p.name"
    )
    return conn.execute(sql, params).fetchall()
