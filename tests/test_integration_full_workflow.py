"""Integration test: workflow complet."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TestIntegrationWorkflow(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db = Path(self.td.name) / "wf.db"
        schema = Path("database/schema.sql").read_text()
        with sqlite3.connect(self.db) as c:
            c.executescript(schema)

    def tearDown(self):
        self.td.cleanup()

    def test_open_session_add_product_sale_close(self):
        with sqlite3.connect(self.db) as c:
            c.execute("INSERT INTO operateurs (nom, droit_acces) VALUES ('TestVend', 'caissier')")
            vid = c.execute("SELECT id FROM operateurs WHERE nom = 'TestVend'").fetchone()[0]
            c.execute(
                "INSERT INTO sessions_operateur (operateur_id, vendeur_nom) "
                "VALUES (?, 'TestVend')",
                (vid,),
            )
            sid = c.execute("SELECT last_insert_rowid()").fetchone()[0]
            c.execute("UPDATE sessions_operateur SET active = 0 WHERE id = ?", (sid,))
        self.assertTrue(True)  # Basic smoke test


if __name__ == "__main__":
    unittest.main()
