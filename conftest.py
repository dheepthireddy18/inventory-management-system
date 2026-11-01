"""
Shared pytest configuration.
"""

from contextlib import closing

import pytest

import inventory_db
import seed_db


@pytest.fixture
def conn():
    with closing(inventory_db.connect(":memory:")) as connection:
        inventory_db.create_schema(connection)
        yield connection


@pytest.fixture
def seeded_conn(conn):
    """A fresh in-memory database loaded with the sample data from seed_db."""
    seed_db.seed(conn)
    return conn
