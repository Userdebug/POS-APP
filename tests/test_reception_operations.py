"""Tests pour les operations d'achat."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TestAchatOperations(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "achats.db"
        with sqlite3.connect(self.db) as c:
            c.executescript("""
                CREATE TABLE fournisseurs (
                    id INTEGER PRIMARY KEY,
                    nom TEXT
                );
                CREATE TABLE Tachats (
                    id INTEGER PRIMARY KEY,
                    fournisseur_id INTEGER,
                    jour TEXT
                );
                CREATE TABLE Tachats_lignes (
                    id INTEGER,
                    achat_id INTEGER,
                    produit_id INTEGER,
                    quantite INTEGER
                );
            """)

    def tearDown(self):
        self.td.cleanup()

    def test_ensure_supplier(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO fournisseurs (nom) VALUES ('FournTest')")
        with sqlite3.connect(self.db) as c:
            r = c.execute("SELECT nom FROM fournisseurs WHERE nom = 'FournTest'").fetchone()
        self.assertIsNotNone(r)


if __name__ == "__main__":
    unittest.main()
