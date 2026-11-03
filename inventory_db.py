import os
import sqlite3
from contextlib import closing
from datetime import datetime
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


# Total value of each supplier's stock (price times quantity), highest first.
def stock_value_by_supplier(conn):
    return conn.execute(
        "SELECT s.name AS supplier_name,"
        " COALESCE(SUM(p.unit_price_cents * p.quantity_in_stock), 0)"
        " AS stock_value_cents"
        " FROM suppliers AS s"
        " LEFT JOIN products AS p ON p.supplier_id = s.id"
        " GROUP BY s.id"
        " ORDER BY stock_value_cents DESC"
    ).fetchall()


# Products at or below their reorder level, with how many units short they are.
def low_stock(conn):
    return conn.execute(
        "SELECT sku, name, quantity_in_stock, reorder_level,"
        " reorder_level - quantity_in_stock AS units_short"
        " FROM products"
        " WHERE quantity_in_stock <= reorder_level"
        " ORDER BY units_short DESC, name"
    ).fetchall()


# Units sold and revenue for each product that has been sold, highest revenue first.
def sales_by_product(conn):
    return conn.execute(
        "SELECT p.sku, p.name, SUM(i.quantity) AS units_sold,"
        " SUM(i.quantity * i.unit_price_cents) AS revenue_cents"
        " FROM products AS p"
        " JOIN sale_items AS i ON i.product_id = p.id"
        " GROUP BY p.id"
        " ORDER BY revenue_cents DESC, p.name"
    ).fetchall()


# Products that appear in no sale.
def never_sold(conn):
    return conn.execute(
        "SELECT p.sku, p.name"
        " FROM products AS p"
        " LEFT JOIN sale_items AS i ON i.product_id = p.id"
        " WHERE i.id IS NULL"
        " ORDER BY p.name"
    ).fetchall()


# Show whole cents as dollars with two decimals, e.g. 1299 -> "12.99".
def format_cents(cents):
    dollars, remainder = divmod(cents, 100)
    return f"{dollars}.{remainder:02d}"


# Format the time of a change; tests pass a fixed time, otherwise use now.
def _timestamp(when):
    if when is None:
        when = datetime.now()
    return when.isoformat(timespec="seconds")


# Apply a signed stock change and log it, inside the caller's transaction.
# Never commits. Returns the new quantity.
def _change_stock(conn, product_id, change, reason, moved_at):
    try:
        row = conn.execute(
            "UPDATE products SET quantity_in_stock = quantity_in_stock + ?"
            " WHERE id = ? RETURNING quantity_in_stock",
            (change, product_id),
        ).fetchone()
    except sqlite3.IntegrityError as error:
        # The CHECK (quantity_in_stock >= 0) constraint refused the update.
        raise InventoryError(f"Not enough stock for product {product_id}.") from error
    if row is None:
        raise InventoryError(f"Product {product_id} does not exist.")
    conn.execute(
        "INSERT INTO stock_movements (product_id, change, reason, moved_at)"
        " VALUES (?, ?, ?, ?)",
        (product_id, change, reason, moved_at),
    )
    return row["quantity_in_stock"]


# Add a positive amount to stock and log a restock movement. Returns the new quantity.
def restock(conn, product_id, amount, when=None):
    if amount <= 0:
        raise InventoryError("Restock amount must be more than zero.")
    with conn:
        return _change_stock(conn, product_id, amount, "restock", _timestamp(when))


# Change stock by a signed amount (damage or recount) and log an adjustment.
# Returns the new quantity; refused if stock would go below zero.
def adjust_stock(conn, product_id, change, when=None):
    if change == 0:
        raise InventoryError("Adjustment must not be zero.")
    with conn:
        return _change_stock(conn, product_id, change, "adjustment", _timestamp(when))


# Record a sale of (product_id, quantity) pairs at current prices and return its id.
# Everything happens in one transaction: if any line fails, the whole sale is undone.
def record_sale(conn, items, when=None):
    product_ids = [product_id for product_id, _ in items]
    if not items:
        raise InventoryError("A sale needs at least one item.")
    if len(set(product_ids)) != len(product_ids):
        raise InventoryError("Each product can appear only once in a sale.")
    if any(quantity <= 0 for _, quantity in items):
        raise InventoryError("Each quantity must be more than zero.")

    sold_at = _timestamp(when)
    with conn:
        sale_id = conn.execute(
            "INSERT INTO sales (sold_at) VALUES (?)", (sold_at,)
        ).lastrowid
        for product_id, quantity in items:
            product = conn.execute(
                "SELECT unit_price_cents FROM products WHERE id = ?", (product_id,)
            ).fetchone()
            if product is None:
                raise InventoryError(f"Product {product_id} does not exist.")
            conn.execute(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price_cents)"
                " VALUES (?, ?, ?, ?)",
                (sale_id, product_id, quantity, product["unit_price_cents"]),
            )
            _change_stock(conn, product_id, -quantity, "sale", sold_at)
    return sale_id


# Copy the whole database to backup_path with SQLite's backup API.
# while the database is in use, the copy is a complete, consistent snapshot.
def backup_database(conn, backup_path):
    with closing(connect(backup_path)) as backup:
        conn.backup(backup)


# Run SQLite's own consistency check; returns "ok" for a healthy database.
def integrity_check(conn):
    return conn.execute("PRAGMA integrity_check").fetchone()[0]
