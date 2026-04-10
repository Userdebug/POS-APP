"""Tests pour ExpensesRepository."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path


class TestExpensesRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_expenses.db"

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE depenses (
                    id INTEGER PRIMARY KEY,
                    date_depense TEXT,
                    designation TEXT,
                    valeur INTEGER,
                    remarque TEXT
                );
            """)

        from repositories.expenses_repository import ExpensesRepository

        self.repo = ExpensesRepository(self._connect_factory, self._day_bounds, self._today_iso)

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

    def _today_iso(self) -> str:
        return datetime.now().strftime("%d/%m/%y")

    def test_add_expense_creates_record(self) -> None:
        from datetime import datetime

        today = datetime.now().strftime("%d/%m/%y")
        self.repo.add_expense("Test Expense", 1000, "Test note", date_depense=today)

        expenses = self.repo.list_daily_expenses()
        self.assertEqual(len(expenses), 1)
        self.assertEqual(expenses[0]["designation"], "Test Expense")

    def test_total_daily_expenses(self) -> None:
        from datetime import datetime

        today = datetime.now().strftime("%d/%m/%y")
        self.repo.add_expense("Expense 1", 500, "", date_depense=today)
        self.repo.add_expense("Expense 2", 300, "", date_depense=today)

        total = self.repo.total_daily_expenses()
        self.assertEqual(total, 800)


if __name__ == "__main__":
    unittest.main()
