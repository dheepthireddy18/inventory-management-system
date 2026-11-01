-- Inventory database schema.

-- One row per supplier;
CREATE TABLE IF NOT EXISTS suppliers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    EMAIL TEXT
) STRICT;

-- One row per item the store sells.
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id), 
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    quantity_in_stock INTEGER NOT NULL CHECK (quantity_in_stock >= 0),
    reorder_level INTEGER NOT NULL CHECK (reorder_level >= 0)
) STRICT;

-- One row per checkout, like the header of a receipt.
CREATE TABLE IF NOT EXISTS sales (
    id      INTEGER PRIMARY KEY,
    sold_at TEXT NOT NULL
) STRICT;

-- One row per product in a sale. The price is copied onto each line so later price changes do not rewrite past sales.
CREATE TABLE IF NOT EXISTS sale_items (
    id               INTEGER PRIMARY KEY,
    sale_id          INTEGER NOT NULL REFERENCES sales (id),
    product_id       INTEGER NOT NULL REFERENCES products (id) ON DELETE RESTRICT,
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    UNIQUE (sale_id, product_id)
) STRICT;

-- One row per change to stock: the audit log.
CREATE TABLE IF NOT EXISTS stock_movements (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products (id) ON DELETE CASCADE,
    change     INTEGER NOT NULL CHECK (change <> 0),
    reason     TEXT    NOT NULL CHECK (reason IN ('restock', 'adjustment', 'sale')),
    moved_at   TEXT    NOT NULL
) STRICT;

-- Supports the supplier join in get_product, search_products, and stock value by supplier.
CREATE INDEX IF NOT EXISTS idx_products_supplier_id
    ON products (supplier_id);

-- Supports sales by product, never sold, and the check when deleting a product.
CREATE INDEX IF NOT EXISTS idx_sale_items_product_id
    ON sale_items (product_id);

-- Supports finding a product's movements, including the cascade on delete. 
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id
    ON stock_movements (product_id);