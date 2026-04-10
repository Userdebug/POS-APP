"""Tests pour ProductRepository."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


class TestProductRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_products.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE categories (id INTEGER PRIMARY KEY, nom TEXT UNIQUE);
                CREATE TABLE produits (
                    id INTEGER PRIMARY KEY, 
                    m3 INTEGER DEFAULT 0, 
                    nom TEXT, 
                    categorie_id INTEGER,
                    pv INTEGER, 
                    pa INTEGER, 
                    stock_boutique INTEGER DEFAULT 0, 
                    stock_reserve INTEGER DEFAULT 0,
                    dlv_dlc TEXT,
                    description TEXT,
                    sku TEXT,
                    en_promo INTEGER DEFAULT 0,
                    prix_promo INTEGER DEFAULT 0,
                    updated_at TEXT,
                    derniere_verification TEXT,
                    FOREIGN KEY(categorie_id) REFERENCES categories(id)
                );
                INSERT INTO categories (nom) VALUES ('Test');
            """)

        from core.database.product_repository import ProductRepository

        self.repo = ProductRepository(self._connect_factory, self._resolve_cat)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @contextmanager
    def _connect_factory(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _resolve_cat(self, conn, names):
        result = {}
        for name in names:
            row = conn.execute("SELECT id FROM categories WHERE nom = ?", (name,)).fetchone()
            if row:
                result[name] = row["id"]
        return result

    def test_upsert_creates_product(self) -> None:
        self.repo.upsert_products(
            [{"id": 1, "nom": "Test Product", "pv": 1000, "pa": 500, "categorie": "Test"}]
        )

        products = self.repo.list_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["nom"], "Test Product")


if __name__ == "__main__":
    unittest.main()
