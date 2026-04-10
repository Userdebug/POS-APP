"""Tests pour ParameterManager."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


class TestParameterManager(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_params.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS parametres (
                    cle TEXT PRIMARY KEY,
                    valeur TEXT,
                    description TEXT,
                    updated_at TEXT
                )
            """)

        @contextmanager
        def _connect():
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

        from core.database.parameter_manager import ParameterManager

        self.pm = ParameterManager(_connect)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_get_returns_default_for_missing(self) -> None:
        result = self.pm.get("INEXISTANT", "default")
        self.assertEqual(result, "default")

    def test_set_and_get_roundtrip(self) -> None:
        self.pm.set("TEST_KEY", "test_value")
        result = self.pm.get("TEST_KEY")
        self.assertEqual(result, "test_value")

    def test_tax_default_is_20(self) -> None:
        result = self.pm.get_tax()
        self.assertEqual(result, 20.0)

    def test_tax_custom_value(self) -> None:
        self.pm.set_tax(18.5)
        result = self.pm.get_tax()
        self.assertAlmostEqual(result, 18.5)


if __name__ == "__main__":
    unittest.main()
