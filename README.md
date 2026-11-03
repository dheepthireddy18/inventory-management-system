# Inventory Management System

A terminal inventory system for a small hardware store, backed by SQLite.
It tracks suppliers, products, sales, and every stock movement. You can search
products with filters, add products, restock, record sales that save completely
or not at all, run four reports, and back up the database. It runs locally or
in a Docker container with the data on a volume.

## Requirements

- Python 3.14 (SQLite 3.37 or newer for STRICT tables; tested with 3.50.4 locally
  and 3.46.1 in the Docker image)
- Docker, to run it in a container

## How to run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed_db.py      # create the tables and load the sample data
python main.py         # start the menu
```

`seed_db.py` only loads data into an empty database, so running it again is safe.

## Configuration

| Variable | Meaning | Default |
|---|---|---|
| `INVENTORY_DB` | Path to the SQLite database file | `inventory.db` next to the code |

```bash
INVENTORY_DB=/tmp/test.db python main.py
```

The Docker image sets `INVENTORY_DB=/data/inventory.db`, so the database lives
on the mounted volume.

## How to run the tests

```bash
pytest -v
ruff check .
```

Each test gets a fresh in-memory database from the `conn` fixture in
`conftest.py`; `seeded_conn` adds the sample data. CI runs ruff and pytest on
every pull request, then builds the Docker image and runs the tests inside it.

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

## Deploy with Docker

### Build the image

```
$ docker build --progress=plain -t inventory:1.0.0 .

#0 building with "desktop-linux" instance using docker driver

#1 [internal] load build definition from Dockerfile
#1 transferring dockerfile: 741B done
#1 DONE 0.0s

#2 [internal] load metadata for docker.io/library/python:3.14.10-slim
#2 DONE 0.6s

#3 [internal] load .dockerignore
#3 transferring context: 293B done
#3 DONE 0.0s

#4 [internal] load build context
#4 transferring context: 9.53kB done
#4 DONE 0.0s

#5 [1/5] FROM docker.io/library/python:3.14.10-slim@sha256:3cabfd7d7aaf394e6040e79fa1eec6ca1c52b74ed9188650472695d9a9326999
#5 resolve docker.io/library/python:3.14.10-slim@sha256:3cabfd7d7aaf394e6040e79fa1eec6ca1c52b74ed9188650472695d9a9326999 0.0s done
#5 DONE 0.0s

#6 [3/5] COPY requirements.txt .
#6 CACHED

#7 [2/5] WORKDIR /app
#7 CACHED

#8 [4/5] RUN pip install --no-cache-dir -r requirements.txt
#8 CACHED

#9 [5/5] COPY . .
#9 DONE 0.0s

#10 exporting to image
#10 exporting layers 0.0s done
#10 exporting manifest sha256:4a050c435ac0c4c56cb1e63179e776ecaf98dbb55490e56c99e90c5967479d05 done
#10 exporting config sha256:401bc87cbf2450e7ca0e9c5027ccfce5bda0e4695053e2fb815d536d751d435c done
#10 exporting attestation manifest sha256:1a7bb04fddd5ea19518a8a2934bb9d35f6233af76ac7f01b660b508ccd03c858 done
#10 exporting manifest list sha256:ed2a189b3a5add59ae52d1ff6e1fef68e73f5b7fccb7d8f44d694af8c850c008 done
#10 naming to docker.io/library/inventory:1.0.0 done
#10 unpacking to docker.io/library/inventory:1.0.0 done
#10 DONE 0.0s
```

Dependencies are installed before the code is copied, so when only the code
changes, the `pip install` layer is reused (`CACHED` above) and only
`COPY . .` runs again.

### Seed and run

Load the sample data into a named volume, then run the menu:

```bash
docker run --rm -v inventory-data:/data inventory:1.0.0 python seed_db.py
docker run --rm -it -v inventory-data:/data inventory:1.0.0
```

`-it` is needed for the interactive menu; `--rm` removes the container on exit,
and the data stays in the `inventory-data` volume.

### Persistence check

The database lives on the named volume `inventory-data`, mounted at `/data`.
Each `docker run --rm` starts a new container and deletes it on exit; the data
stays in the volume. Real output:

```
$ docker run --rm -v inventory-data:/data inventory:1.0.0 python seed_db.py
Loaded sample data into /data/inventory.db
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 0

$ docker run --rm -it -v inventory-data:/data inventory:1.0.0
Choose an option: 4
Product ID: 3
Units to add: 10
Restocked. Product 3 now has 13 in stock.
Choose an option: q
Goodbye.

$ docker run --rm -v inventory-data:/data inventory:1.0.0 python seed_db.py
The database already has data; nothing was added.
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 1

$ docker run --rm -it -v inventory-data:/data inventory:1.0.0
Choose an option: 4
Product ID: 3
Units to add: 10
Restocked. Product 3 now has 23 in stock.
Choose an option: q
Goodbye.

$ docker run --rm -v inventory-data:/data inventory:1.0.0 python seed_db.py
The database already has data; nothing was added.
suppliers: 4
products: 12
sales: 5
sale_items: 12
stock_movements: 2
```

The second restock started from 13, the value written by the previous
container, which had already been deleted. Every change survives because it
is stored in the volume, not the container.

## Backup and restore

Choose **10. Back up the database** in the menu. It uses SQLite's backup API
(`connection.backup`), which copies a consistent snapshot even while the
database is open, and saves it in a `backups` folder next to the database
(`/data/backups` in Docker, so it is on the volume too).

Backup check (the copy passes `PRAGMA integrity_check` and has the same row
counts as the original):

```
$ docker run --rm -it -v inventory-data:/data inventory:1.0.0
Choose an option: 10
Backup saved to /data/backups/inventory-20261102-002403.db

$ docker run --rm -i -v inventory-data:/data inventory:1.0.0 python - <<'EOF'
from contextlib import closing
from pathlib import Path
import inventory_db

backup = sorted(Path("/data/backups").glob("*.db"))[-1]
with closing(inventory_db.connect()) as original, closing(inventory_db.connect(backup)) as copy:
    print("Backup file:     ", backup)
    print("integrity_check: ", inventory_db.integrity_check(copy))
    print("Original counts: ", inventory_db.table_row_counts(original))
    print("Backup counts:   ", inventory_db.table_row_counts(copy))
EOF
Backup file:      /data/backups/inventory-20261102-002403.db
integrity_check:  ok
Original counts:  {'suppliers': 4, 'products': 12, 'sales': 5, 'sale_items': 12, 'stock_movements': 3}
Backup counts:    {'suppliers': 4, 'products': 12, 'sales': 5, 'sale_items': 12, 'stock_movements': 3}
```

To restore, stop the program and copy the backup over the database file:

```bash
# Local
cp backups/inventory-20261101-201101.db inventory.db

# Docker
docker run --rm -v inventory-data:/data inventory:1.0.0 \
    cp /data/backups/inventory-20261102-002403.db /data/inventory.db
```

## Roll back

_Added with version 1.1.0._

## Self-review

**I would clean up old backups.** Every backup creates a new file with the date and time in its name, and old ones are never removed, so the backups folder keeps growing. Next time I would keep only the most recent few, or let the user choose which ones to delete.

**I would ask for confirmation before deleting a product.** Right now the product is deleted as soon as its ID is typed. A simple "Are you sure? (y/n)" would stop mistakes caused by typing the wrong number.

**I would show a receipt after a sale.** The menu only prints the sale number. Showing each item, its price, and the total would let the user check the sale was right before the customer leaves.