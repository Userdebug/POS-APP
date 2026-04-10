"""Tests pour SchemaInitializer."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from core.database.schema_initializer import SchemaInitializer


class TestSchemaInitializer(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_init.db"
        self.schema_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
        self.initializer = SchemaInitializer(self.schema_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            conn.close()

    def test_init_creates_tables(self) -> None:
        """init_database doit creer toutes les tables."""
        self.initializer.init_database(self._connect)

        with self._connect() as conn:
            rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = {r[0] for r in rows}
            self.assertIn("operateurs", tables)
            self.assertIn("produits", tables)

    def test_migration_adds_promo_columns(self) -> None:
        """migrate_schema doit ajouter les colonnes promo."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE produits (id INTEGER, pa INTEGER)")

        self.initializer.migrate_schema(self._connect)

        with sqlite3.connect(self.db_path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(produits)").fetchall()}
            self.assertIn("en_promo", cols)
            self.assertIn("prix_promo", cols)

    def test_migration_idempotent(self) -> None:
        """Relancer migrate_schema ne doit pas echouer."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "CREATE TABLE produits "
                "(id INTEGER, pa INTEGER, en_promo INTEGER, prix_promo INTEGER)"
            )

        self.initializer.migrate_schema(self._connect)

        with sqlite3.connect(self.db_path) as conn:
            cols = {r[1] for r in conn.execute("PRAGMA table_info(produits)").fetchall()}
            self.assertIn("en_promo", cols)


if __name__ == "__main__":
    unittest.main()
