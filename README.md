# inventory-management-system

## Sample data

`python seed_db.py` creates the tables and loads the sample data. Real output:

```
Loaded sample data into /Users/Dheepthi.Reddy/Documents/GitHub/inventory-management-system/inventory.db
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 0
```

The sample data has 4 suppliers, 12 products in 4 categories (Hand Tools,
Fasteners, Electrical, Garden), 5 sales with 12 sale items, 2 products that
were never sold (Garden Hose, Sprinkler), and 2 products at or below their
reorder level (Adjustable Wrench, Hex Bolts). `stock_movements` starts empty.

## Expected report results

Money is stored as whole cents and shown with two decimals.

**Stock value by supplier** (price × quantity, highest first)

| Supplier | Stock value |
|---|---|
| BoltCo Fasteners | 1197.90 |
| GreenThumb Garden | 659.55 |
| BrightSpark Electrical | 658.88 |
| Acme Tools | 656.07 |

**Low stock** (at or below reorder level)

| SKU | Product | In stock | Reorder level | Units short |
|---|---|---|---|---|
| WRN-001 | Adjustable Wrench | 3 | 5 | 2 |
| BLT-001 | Hex Bolts | 10 | 10 | 0 |

**Sales by product** (highest revenue first)

| SKU | Product | Units sold | Revenue |
|---|---|---|---|
| BLT-001 | Hex Bolts | 5 | 39.95 |
| BUL-001 | LED Bulb | 10 | 39.90 |
| HAM-001 | Claw Hammer | 3 | 38.97 |
| WRN-001 | Adjustable Wrench | 2 | 30.98 |
| EXT-001 | Extension Cord | 1 | 24.99 |
| SCR-001 | Screwdriver Set | 1 | 18.99 |
| GLV-001 | Garden Gloves | 2 | 17.98 |
| NAI-001 | Box of Nails | 3 | 14.97 |
| SCW-001 | Wood Screws | 2 | 12.98 |
| TAP-001 | Electrical Tape | 3 | 8.97 |

**Never sold**

| SKU | Product |
|---|---|
| HOS-001 | Garden Hose |
| SPR-001 | Sprinkler |

`tests/test_reports.py` checks each report against exactly these rows.

## What happens when a sale fails halfway

`record_sale` runs every step inside one `with conn:` transaction. In this
example the first two lines (2 hammers, 10 boxes of nails) succeed, then the
third line asks for 50 wrenches when only 3 are in stock. The CHECK constraint
on `quantity_in_stock` refuses the update, the error leaves the `with` block,
and SQLite rolls back the sale row, both sale lines, both stock reductions,
and both movements.

```
BEFORE
Row counts: {'suppliers': 4, 'products': 12, 'sales': 5, 'sale_items': 12, 'stock_movements': 0}
  product 1 Claw Hammer: 25 in stock
  product 3 Adjustable Wrench: 3 in stock
  product 4 Box of Nails: 120 in stock

CALL: record_sale(conn, [(1, 2), (4, 10), (3, 50)])
ERROR: Not enough stock for product 3.

AFTER
Row counts: {'suppliers': 4, 'products': 12, 'sales': 5, 'sale_items': 12, 'stock_movements': 0}
  product 1 Claw Hammer: 25 in stock
  product 3 Adjustable Wrench: 3 in stock
  product 4 Box of Nails: 120 in stock
```

The row counts and stock levels after the failed call are identical to
before: no sale row, no sale lines, no stock movements, and no stock change.
The test `test_sale_that_fails_halfway_changes_nothing` checks the same thing
automatically.
