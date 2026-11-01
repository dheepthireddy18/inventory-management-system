# Inventory Management System Plan

## Overview
A terminal inventory system for a small hardware store, backed by SQLite.

## Tables

### suppliers
Stores each supplier once so products can point to it and reports can manage stock by supplier.

| Column | Type | Constraints | Why |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | number that products use to refer to a supplier |
| name | TEXT | NOT NULL, UNIQUE | Every supplier needs a name, the same supplier entered twice would split reports |
| email | TEXT | optional | Contact details are not always known |

### products
Stores everything the store sells, with its current price and how many units are on the shelf.

| Column | Type | Constraints | Why |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | Stable number that sale lines and movements use to refer to a product |
| sku | TEXT | NOT NULL, UNIQUE | The store's product code, two products with one SKU would make lookups difficult |
| name | TEXT | NOT NULL | A product must be identifiable in search and reports |
| category | TEXT | NOT NULL | Needed for the category filter |
| supplier_id | INTEGER | NOT NULL, REFERENCES suppliers(id) | Every product must come from a supplier that exists |
| unit_price_cents | INTEGER | NOT NULL, CHECK (unit_price_cents >= 0) | Whole cents avoid float rounding, a price cannot be negative |
| quantity_in_stock | INTEGER | NOT NULL, CHECK (quantity_in_stock >= 0) | A shelf cannot hold less than zero units |
| reorder_level | INTEGER | NOT NULL, CHECK (reorder_level >= 0) | threshold for the low stock report, negative would never trigger |

### sales
One row per checkout, recording when it happened, like the header of a receipt.

| Column | Type | Constraints | Why |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | Groups the lines that were bought together |
| sold_at | TEXT | NOT NULL | Every sale happened at a time, stored as ISO-8601 text |

### sale_items
One row per product in a sale, keeping the price charged at that moment so later when prices changes do not rewrite history.

| Column | Type | Constraints | Why |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | Identifies one line |
| sale_id | INTEGER | NOT NULL, REFERENCES sales(id) | A line must belong to a sale that exists |
| product_id | INTEGER | NOT NULL, REFERENCES products(id) ON DELETE RESTRICT | A line must point at a real product, and a sold product cannot be deleted |
| quantity | INTEGER | NOT NULL, CHECK (quantity > 0) | A line must sell at least one unit |
| unit_price_cents | INTEGER | NOT NULL, CHECK (unit_price_cents >= 0) | The price actually charged, kept even if the product's price changes later |
| (sale_id, product_id) | | UNIQUE | The same product cannot appear twice in one sale, buying more means a higher quantity |

### stock_movements
A log of every change to stock, so the store can say exactly what changed, when, and why.

| Column | Type | Constraints | Why |
|---|---|---|---|
| id | INTEGER | PRIMARY KEY | Identifies one movement |
| product_id | INTEGER | NOT NULL, REFERENCES products(id) ON DELETE CASCADE | A movement belongs to a real product, deleting a never-sold product removes its log too |
| change | INTEGER | NOT NULL, CHECK (change <> 0) | Signed: positive adds stock, negative removes it, a change of zero is not a movement |
| reason | TEXT | NOT NULL, CHECK (reason IN ('restock', 'adjustment', 'sale')) | Only the three allowed reasons, so reports can trust the value |
| moved_at | TEXT | NOT NULL | Every movement happened at a time |

## Relationships
- suppliers: one - many :products (products.supplier_id)
- sales: one - many :sale_items (sale_items.sale_id)
- products one - many sale_items (sale_items.product_id)
- products one - many stock_movements (stock_movements.product_id)

Foreign keys are enforced on every connection with PRAGMA foreign_keys = ON
inside connect(), because SQLite leaves them off by default.

## Public functions (inventory_db.py)
All functions take the connection as the first parameter, so tests can pass an in-memory database. 
Rule violations raise InventoryError (a custom exception) with a readable message, the menu catches it and prints a friendly message.

| Function | Inputs | Returns |
|---|---|---|
| get_db_path | (none) | INVENTORY_DB if set, else the path of inventory.db next to the code |
| connect | db_path (default: INVENTORY_DB env var, else inventory.db next to the code) | sqlite3.Connection with foreign keys on and sqlite3.Row rows |
| create_schema | conn | None |
| add_product | conn, sku, name, category, supplier_id, unit_price_cents, quantity_in_stock, reorder_level | new product id (int) |
| get_product | conn, product_id | Row with product fields and supplier_name, or None |
| update_price | conn, product_id, new_price_cents | True if updated, False if no such product |
| delete_product | conn, product_id | True if deleted, False if no such product; InventoryError if it has sales |
| search_products | conn, text="", category=None, max_price_cents=None, in_stock_only=False, low_stock_only=False | list of Rows sorted by name |
| stock_value_by_supplier | conn | Rows (supplier_name, stock_value_cents), highest first |
| low_stock | conn | Rows (sku, name, quantity_in_stock, reorder_level, units_short) |
| sales_by_product | conn | Rows (sku, name, units_sold, revenue_cents), highest revenue first |
| never_sold | conn | Rows (sku, name) of products in no sale |
| restock | conn, product_id, amount, when=None | new quantity (int) |
| adjust_stock | conn, product_id, change, when=None | new quantity (int) |
| record_sale | conn, items (list of (product_id, quantity)), when=None | new sale id (int) |
| backup_database | conn, backup_path | None |
| format_cents | cents | string such as "12.50" |

## Transactions
Each multi-step change runs inside one `with conn:` block. If any statement or check raises, the block rolls back every step and the error is re-raised.
Helpers used inside the block (such as logging a movement) never commit.

### restock(connection, product_id, amount, now=None)
1. Refuse an amount of zero or less (amount <= 0). Nothing has been written yet.
2. Open the transaction.
3. Increase the product's stock by the amount. If the product does not exist,
   refuse it.
4. Log a restock movement for the amount.
5. If step 4 fails, the stock increase from step 3 is undone.

### adjust_stock(conn, product_id, change, when=None)
1. Refuse a change of zero (change = 0). Nothing has been written yet.
2. Open the transaction.
3. Look up the product's current stock. If the product does not exist, refuse it.
   Nothing to undo.
4. Refuse the change if stock would go below zero (stock + change < 0).
   Nothing has been written, so stock is unchanged.
5. Apply the change to the product's stock.
6. Log an adjustment movement for the change.
7. If step 6 fails, the stock change from step 5 is undone.

### record_sale(conn, items, when=None)
1. Refuse an empty list, a quantity of zero or less (quantity <= 0), or the same
   product listed twice. Nothing has been written yet.
2. Open the transaction.
3. Create the sale with the time.
4. For each product and quantity:
   - Look up the product's current price and stock. If the product does not exist, refuse the sale.
   - Refuse the sale if there is not enough stock (stock < quantity).
   - Add a sale line at the current price.
   - Reduce the product's stock by the quantity.
   - Log a sale movement for the quantity.
5. If any step in 4 fails, everything is undone: the sale from step 3, every sale line, every stock reduction, and every movement already written for earlier products. The database is left exactly as it was before the call.

## Release plan
- 1.0.0 is the version with every feature except the banner. Once
feature/menu-and-container is merged and CI is green on main, I tag v1.0.0 in
Git, push the tag, and build the image as inventory:1.0.0.

- 1.1.0 adds one change: when the menu starts, it shows how many products are low
on stock. I build it on feature/low-stock-banner, merge it, tag v1.1.0, and
build inventory:1.1.0. CHANGELOG.md gets an entry for each version.

- Before upgrading I back up the database with SQLite's backup function. To roll
back, I stop the 1.1.0 container and start inventory:1.0.0 with the same
volume. The schema is the same in both versions, so 1.0.0 reads the data
without changes. I check the row counts before and after to show nothing was
lost.

## Pull requests
1. feature/database-and-seed: schema.sql, connect, seed_db.py, CI workflow
2. feature/products-and-search: product functions and search
3. feature/reports: four reports
4. feature/stock-and-sales: restock, adjust, record_sale, backup
5. feature/menu-and-container: main.py, Dockerfile, .dockerignore, docker-build CI job, README, CHANGELOG
6. feature/low-stock-banner: the 1.1.0 banner

Tests are written before the code in each PR, using a fresh in-memory database per test.