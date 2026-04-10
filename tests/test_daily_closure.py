"""Tests pour les operations de cloture quotidienne."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TestDailyClosure(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "closure.db"
        with sqlite3.connect(self.db) as c:
            c.executescript("""
                CREATE TABLE clotures_caisse (
                    id INTEGER PRIMARY KEY,
                    jour TEXT UNIQUE,
                    ca_ttc_final INTEGER
                );
                """)

    def tearDown(self):
        self.td.cleanup()

    def test_set_closure(self):
        with sqlite3.connect(self.db) as c:
            c.execute(
                "INSERT OR REPLACE INTO clotures_caisse "
                "(jour, ca_ttc_final) VALUES ('2026-04-02', 50000)"
            )
        with sqlite3.connect(self.db) as c:
            r = c.execute(
                "SELECT ca_ttc_final FROM clotures_caisse WHERE jour = '2026-04-02'"
            ).fetchone()
        self.assertEqual(r[0], 50000)


if __name__ == "__main__":
    unittest.main()
