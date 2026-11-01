"""
Shared pytest configuration.
"""

from contextlib import closing

import pytest

import inventory_db


@pytest.fixture
def conn():
    with closing(inventory_db.connect(":memory:")) as connection:
        inventory_db.create_schema(connection)
        yield connection
