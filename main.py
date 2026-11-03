"""Terminal menu for the hardware store inventory."""

import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import inventory_db
from inventory_db import InventoryError, format_cents


# Ask for text; keep asking while the answer is blank if it is required.
def ask_text(prompt, required=False):
    while True:
        answer = input(prompt).strip()
        if answer or not required:
            return answer
        print("This field is required.")


# Ask for a whole number; blank returns None when allowed.
def ask_int(prompt, allow_blank=False):
    while True:
        answer = ask_text(prompt)
        if allow_blank and not answer:
            return None
        try:
            return int(answer)
        except ValueError:
            print("Please type a whole number, for example 5.")


# Ask for a price such as 12.99 and return it as whole cents.
def ask_price_cents(prompt, allow_blank=False):
    while True:
        answer = ask_text(prompt)
        if allow_blank and not answer:
            return None
        try:
            cents = Decimal(answer) * 100
            if cents == cents.to_integral_value():
                return int(cents)
        except (InvalidOperation, OverflowError):
            pass
        print("Please type a price with at most two decimals, for example 12.99.")


def ask_yes_no(prompt):
    return ask_text(prompt).lower().startswith("y")


def print_products(rows):
    if not rows:
        print("No products found.")
        return
    print(
        f"{'ID':>3}  {'SKU':<8} {'Name':<18} {'Category':<11} {'Price':>8} {'Stock':>5}  Supplier"
    )
    for row in rows:
        print(
            f"{row['id']:>3}  {row['sku']:<8} {row['name']:<18} {row['category']:<11}"
            f" {format_cents(row['unit_price_cents']):>8} {row['quantity_in_stock']:>5}"
            f"  {row['supplier_name']}"
        )


def search(conn):
    text = ask_text("Search text (blank for all): ")
    category = ask_text("Category (blank for any): ") or None
    max_price_cents = ask_price_cents(
        "Maximum price (blank for none): ", allow_blank=True
    )
    in_stock_only = ask_yes_no("In stock only? (y/n): ")
    low_stock_only = ask_yes_no("Low stock only? (y/n): ")
    print_products(
        inventory_db.search_products(
            conn, text, category, max_price_cents, in_stock_only, low_stock_only
        )
    )


def look_up_product(conn):
    product = inventory_db.get_product(conn, ask_int("Product ID: "))
    if product is None:
        print("No product has that ID.")
    else:
        print_products([product])


def add_product(conn):
    product_id = inventory_db.add_product(
        conn,
        sku=ask_text("SKU: ", required=True),
        name=ask_text("Name: ", required=True),
        category=ask_text("Category: ", required=True),
        supplier_id=ask_int("Supplier ID: "),
        unit_price_cents=ask_price_cents("Unit price: "),
        quantity_in_stock=ask_int("Quantity in stock: "),
        reorder_level=ask_int("Reorder level: "),
    )
    print(f"Added product {product_id}.")


def restock(conn):
    product_id = ask_int("Product ID: ")
    new_quantity = inventory_db.restock(conn, product_id, ask_int("Units to add: "))
    print(f"Restocked. Product {product_id} now has {new_quantity} in stock.")


def change_price(conn):
    product_id = ask_int("Product ID: ")
    if inventory_db.update_price(conn, product_id, ask_price_cents("New price: ")):
        print("Price updated.")
    else:
        print("No product has that ID.")


def delete_product(conn):
    product_id = ask_int("Product ID: ")
    if inventory_db.delete_product(conn, product_id):
        print("Product deleted.")
    else:
        print("No product has that ID.")


def record_sale(conn):
    items = []
    print("Enter each product in the sale. Leave the product ID blank to finish.")
    while (product_id := ask_int("Product ID: ", allow_blank=True)) is not None:
        items.append((product_id, ask_int("Quantity: ")))
    sale_id = inventory_db.record_sale(conn, items)
    print(f"Recorded sale {sale_id}.")


def show_stock_value(conn):
    for row in inventory_db.stock_value_by_supplier(conn):
        print(
            f"{row['supplier_name']:<24} {format_cents(row['stock_value_cents']):>10}"
        )


def show_low_stock(conn):
    rows = inventory_db.low_stock(conn)
    if not rows:
        print("No products are low on stock.")
    for row in rows:
        print(
            f"{row['sku']:<8} {row['name']:<18} stock {row['quantity_in_stock']:>3}"
            f"  reorder at {row['reorder_level']:>3}  short {row['units_short']:>3}"
        )


def show_sales_by_product(conn):
    for row in inventory_db.sales_by_product(conn):
        print(
            f"{row['sku']:<8} {row['name']:<18} sold {row['units_sold']:>4}"
            f"  revenue {format_cents(row['revenue_cents']):>9}"
        )


def show_never_sold(conn):
    for row in inventory_db.never_sold(conn):
        print(f"{row['sku']:<8} {row['name']}")


# Back up into a backups folder next to the database, so it lands on the same volume.
def back_up(conn):
    backup_dir = Path(inventory_db.get_db_path()).parent / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_path = backup_dir / f"inventory-{datetime.now():%Y%m%d-%H%M%S}.db"
    inventory_db.backup_database(conn, backup_path)
    print(f"Backup saved to {backup_path}")


MENU = {
    "1": ("Search products", search),
    "2": ("Look up a product", look_up_product),
    "3": ("Add a product", add_product),
    "4": ("Restock a product", restock),
    "5": ("Record a sale", record_sale),
    "6": ("Report: stock value by supplier", show_stock_value),
    "7": ("Report: low stock", show_low_stock),
    "8": ("Report: sales by product", show_sales_by_product),
    "9": ("Report: never sold", show_never_sold),
    "10": ("Back up the database", back_up),
    "11": ("Change a product's price", change_price),
    "12": ("Delete a product", delete_product),
}


# Version 1.1.0: warn at start-up how many products need reordering.
def show_low_stock_banner(conn):
    count = len(inventory_db.low_stock(conn))
    print(f"*** Low stock: {count} products at or below their reorder level ***")


def run_menu(conn):
    while True:
        print()
        for key, (label, _) in MENU.items():
            print(f"{key:>2}. {label}")
        print(" q. Quit")
        choice = ask_text("Choose an option: ").lower()
        if choice == "q":
            print("Goodbye.")
            return
        if choice not in MENU:
            print("Please choose one of the listed options.")
            continue
        _, action = MENU[choice]
        try:
            action(conn)
        except InventoryError as error:
            print(f"Sorry, that did not work: {error}")
        except sqlite3.Error as error:
            print(f"Sorry, the database reported a problem: {error}")


def main():
    with closing(inventory_db.connect()) as conn:
        inventory_db.create_schema(conn)
        show_low_stock_banner(conn)
        run_menu(conn)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
