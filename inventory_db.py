import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DEFAULT_DB_PATH = BASE_DIR / "inventory.db"


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
