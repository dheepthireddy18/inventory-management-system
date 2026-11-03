"""Tests for backup_database."""

from contextlib import closing

import inventory_db


def test_backup_passes_integrity_check_and_has_same_row_counts(seeded_conn, tmp_path):
    backup_path = tmp_path / "backup.db"
    inventory_db.backup_database(seeded_conn, backup_path)

    with closing(inventory_db.connect(backup_path)) as backup:
        assert inventory_db.integrity_check(backup) == "ok"
        assert inventory_db.table_row_counts(backup) == inventory_db.table_row_counts(
            seeded_conn
        )
