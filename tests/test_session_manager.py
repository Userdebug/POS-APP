"""Tests pour SessionsRepository."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path


class TestSessionsRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_sessions.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE operateurs (
                    id INTEGER PRIMARY KEY, 
                    nom TEXT UNIQUE, 
                    droit_acces TEXT, 
                    actif INTEGER DEFAULT 1
                );
                CREATE TABLE sessions_operateur (
                    id INTEGER PRIMARY KEY, 
                    operateur_id INTEGER, 
                    vendeur_nom TEXT,
                    opened_at TEXT DEFAULT (datetime('now')), 
                    closed_at TEXT, 
                    active INTEGER DEFAULT 1,
                    FOREIGN KEY(operateur_id) REFERENCES operateurs(id)
                );
                INSERT INTO operateurs (nom, droit_acces) VALUES ('TestUser', 'caissier');
            """)

        from repositories.sessions_repository import SessionsRepository

        self.repo = SessionsRepository(self._connect_factory)

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

    def test_open_session_creates_record(self) -> None:
        user_id, session_id = self.repo.open_session("TestUser", "caissier")
        self.assertIsInstance(user_id, int)
        self.assertIsInstance(session_id, int)
        self.assertGreater(session_id, 0)

    def test_close_session_sets_inactive(self) -> None:
        user_id, session_id = self.repo.open_session("TestUser2", "caissier")
        self.repo.close_session(session_id)

        with self._connect_factory() as conn:
            row = conn.execute(
                "SELECT active FROM sessions_operateur WHERE id = ?", (session_id,)
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["active"], 0)


if __name__ == "__main__":
    unittest.main()
