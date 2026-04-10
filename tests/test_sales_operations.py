"""Tests pour SalesRepository."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path


class TestSalesRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sales.db"

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
                    FOREIGN KEY(categorie_id) REFERENCES categories(id)
                );
                CREATE TABLE ventes (
                    id INTEGER PRIMARY KEY,
                    jour TEXT,
                    heure TEXT,
                    produit_id INTEGER,
                    produit_nom TEXT,
                    quantite INTEGER,
                    prix_unitaire INTEGER,
                    prix_total INTEGER,
                    session_id INTEGER,
                    deleted INTEGER DEFAULT 0
                );
                
                INSERT INTO categories (nom) VALUES ('BA');
                INSERT INTO produits (id, nom, categorie_id, pv, pa) VALUES (1, 'Product 1', 1, 1000, 500);
            """)

        from repositories.sales_repository import SalesRepository

        self.repo = SalesRepository(self._connect_factory, self._day_bounds)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @contextmanager
    def _connect_factory(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _day_bounds(self, day: str) -> tuple[str, str]:
        start = datetime.strptime(day, "%d/%m/%y")
        end = start + timedelta(days=1)
        return start.strftime("%d/%m/%y"), end.strftime("%d/%m/%y")

    def test_record_sale_creates_record(self) -> None:
        result = self.repo.record_sale(
            produit_id=1, produit_nom="Product 1", quantite=2, prix_unitaire=1000, session_id=1
        )

        self.assertIn("heure", result)
        self.assertEqual(result["quantite"], 2)

    def test_total_daily_sales(self) -> None:
        """Test that total_daily_sales returns correct total."""
        self.repo.record_sale(
            produit_id=1, produit_nom="Product 1", quantite=2, prix_unitaire=1000, session_id=1
        )
        self.repo.record_sale(
            produit_id=1, produit_nom="Product 1", quantite=1, prix_unitaire=1000, session_id=1
        )

        today = datetime.now().strftime("%d/%m/%y")
        total = self.repo.total_daily_sales(today)
        self.assertEqual(total, 3000)  # 2*1000 + 1*1000 = 3000

        # Test with no sales for tomorrow
        from datetime import date, timedelta

        tomorrow = date.today() + timedelta(days=1)
        tomorrow_str = tomorrow.isoformat()
        total_tomorrow = self.repo.total_daily_sales(tomorrow_str)
        self.assertEqual(total_tomorrow, 0)


if __name__ == "__main__":
    unittest.main()
