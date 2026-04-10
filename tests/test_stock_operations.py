"""Tests pour les operations de stock."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TestStockOperations(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "stock.db"
        with sqlite3.connect(self.db) as c:
            c.executescript("""
                CREATE TABLE produits (
                    id INTEGER PRIMARY KEY,
                    nom TEXT,
                    stock_boutique INTEGER DEFAULT 10
                );
                INSERT INTO produits (nom, stock_boutique) VALUES ('Test', 10);
            """)

    def tearDown(self):
        self.td.cleanup()

    def test_decrement_stock(self):
        with sqlite3.connect(self.db) as c:
            c.execute("UPDATE produits SET stock_boutique = stock_boutique - 3 WHERE id = 1")
        with sqlite3.connect(self.db) as c:
            r = c.execute("SELECT stock_boutique FROM produits WHERE id = 1").fetchone()
        self.assertEqual(r[0], 7)


if __name__ == "__main__":
    unittest.main()
