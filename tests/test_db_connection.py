"""Tests pour ConnectionManager — contexte de connexion SQLite."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.database.connection_manager import ConnectionManager


class TestConnectionManager(unittest.TestCase):
    """Validation du contexte de connexion SQLite."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_conn.db"
        self.manager = ConnectionManager(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_connect_yields_connection(self) -> None:
        """Le contexte doit fournir une connexion sqlite3."""
        with self.manager.connect() as conn:
            self.assertIsInstance(conn, sqlite3.Connection)

    def test_connect_creates_file(self) -> None:
        """Le fichier DB doit etre cree a la premiere connexion."""
        self.assertFalse(self.db_path.exists())
        with self.manager.connect() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
        self.assertTrue(self.db_path.exists())

    def test_connect_commits_on_success(self) -> None:
        """Les donnees doivent etre persistees apres le contexte."""
        with self.manager.connect() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
            conn.execute("INSERT INTO t VALUES (42)")

        # Re-ouvrir pour verifier la persistance
        with self.manager.connect() as conn:
            row = conn.execute("SELECT id FROM t").fetchone()
            self.assertEqual(row[0], 42)

    def test_connect_rollback_on_error(self) -> None:
        """Une exception doit declencher un rollback."""
        with self.assertRaises(ValueError):
            with self.manager.connect() as conn:
                conn.execute("CREATE TABLE t (id INTEGER)")
                conn.execute("INSERT INTO t VALUES (1)")
                raise ValueError("rollback test")

        # Verifier que l'insert a ete annule
        with self.manager.connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
            self.assertEqual(row[0], 0)

    def test_connect_row_factory_is_row(self) -> None:
        """Les resultats doivent etre des sqlite3.Row."""
        with self.manager.connect() as conn:
            conn.execute("CREATE TABLE t (nom TEXT)")
            conn.execute("INSERT INTO t VALUES ('test')")
            row = conn.execute("SELECT nom FROM t").fetchone()
            self.assertIsInstance(row, sqlite3.Row)

    def test_connect_foreign_keys_enabled(self) -> None:
        """PRAGMA foreign_keys doit etre ON."""
        with self.manager.connect() as conn:
            result = conn.execute("PRAGMA foreign_keys").fetchone()
            self.assertEqual(result[0], 1)

    def test_connect_closes_after_context(self) -> None:
        """La connexion doit etre fermee apres le contexte."""
        with self.manager.connect() as conn:
            conn.execute("CREATE TABLE t (id INTEGER)")
        # Apres le contexte, la connexion est fermee
        with self.assertRaises(sqlite3.ProgrammingError):
            conn.execute("SELECT 1")


if __name__ == "__main__":
    unittest.main()
