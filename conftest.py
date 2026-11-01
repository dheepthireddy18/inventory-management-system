"""
Shared pytest configuration.
"""

from contextlib import closing
import pytest
import inventory_db

@pytest.fixture
def conn():
    with closing(inventorydb.connect(":memory:")) as connection:
        inventory_db.create_schema(connection)
        yield connection