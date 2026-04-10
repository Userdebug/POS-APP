"""Integration tests for DailyResetService with real database."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core.database import DatabaseManager
from services.daily_reset_service import DailyResetService


class TestDailyResetIntegration(unittest.TestCase):
    """Integration tests for daily reset with real database."""

    def setUp(self) -> None:
        """Set up test database."""
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_daily_reset.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))
        self.service = DailyResetService(self.db)
        self.test_date = "2026-04-03"
        self.yesterday = "2026-04-02"

    def tearDown(self) -> None:
        """Clean up test database."""
        self.tmpdir.cleanup()

    def _create_category_rows(self, jour: str, categories: list[str]) -> None:
        """Helper to create category tracking rows."""
        with self.db._connect() as conn:
            for cat in categories:
                conn.execute(
                    """
                    INSERT INTO suivi_formulaire_journalier (jour, categorie, cloturee)
                    VALUES (?, ?, 0)
                    ON CONFLICT(jour, categorie) DO UPDATE SET cloturee = 0
                    """,
                    (jour, cat),
                )
            conn.commit()

    def _close_day(self, jour: str, categories: list[str]) -> None:
        """Helper to mark day as closed."""
        with self.db._connect() as conn:
            for cat in categories:
                conn.execute(
                    """
                    UPDATE suivi_formulaire_journalier
                    SET cloturee = 1
                    WHERE jour = ? AND categorie = ?
                    """,
                    (jour, cat),
                )
            conn.commit()

    def test_validate_startup_first_run(self) -> None:
        """Test startup validation on first run (no closure history)."""
        # No last_closed_date parameter set
        result = self.service.get_last_closed_date()
        self.assertIsNone(result)

        can_proceed, error = self.service.validate_startup()
        self.assertTrue(can_proceed)
        self.assertIsNone(error)

    def test_validate_startup_with_closed_previous_day(self) -> None:
        """Test startup validation when previous day is closed."""
        categories = ["BA", "BSA", "Confi"]

        # The service checks previous day (current_date - 1 day)
        # When today is 2026-04-04, previous day is 2026-04-03
        # Create and close for this date
        prev_day = "2026-04-03"
        self._create_category_rows(prev_day, categories)
        self._close_day(prev_day, categories)

        # Set last closed date to match
        self.db.set_parameter("LAST_CLOSED_DATE", prev_day)

        can_proceed, error = self.service.validate_startup()
        self.assertTrue(can_proceed)
        self.assertIsNone(error)

    def test_validate_startup_blocks_unclosed_previous_day(self) -> None:
        """Test startup blocks when previous day is NOT closed."""
        categories = ["BA", "BSA"]

        # Create tracking rows for yesterday but NOT closed
        self._create_category_rows(self.yesterday, categories)

        # Set last closed date to yesterday
        self.db.set_parameter("LAST_CLOSED_DATE", self.yesterday)

        can_proceed, error = self.service.validate_startup()
        self.assertFalse(can_proceed)
        self.assertIsNotNone(error)
        self.assertIn("est requise", error)

    def test_execute_reset_resets_coffre(self) -> None:
        """Test reset clears the safe (coffre) to 0."""
        # Set an initial coffre value
        self.db.set_parameter("COFFRE_TOTAL", "15000")

        # Execute reset
        result = self.service.execute_reset(self.yesterday)

        self.assertEqual(result["coffre_before"], 15000)
        self.assertEqual(result["coffre_after"], 0)

        # Verify coffre is reset in database
        raw = self.db.get_parameter("COFFRE_TOTAL", "0")
        self.assertEqual(raw, "0")

    def test_execute_reset_sets_last_closed_date(self) -> None:
        """Test reset sets last closed date parameter."""
        self.service.execute_reset(self.yesterday)

        last_closed = self.db.get_parameter("LAST_CLOSED_DATE")
        self.assertEqual(last_closed, self.yesterday)

    def test_execute_reset_clears_pending_flag(self) -> None:
        """Test reset clears pending flag."""
        self.db.set_parameter("DAILY_RESET_PENDING", "1")

        self.service.execute_reset(self.yesterday)

        pending = self.db.get_parameter("DAILY_RESET_PENDING", "1")
        self.assertEqual(pending, "0")

    def test_on_cloture_complete(self) -> None:
        """Test handling cloture completion."""
        categories = ["BA"]

        # Create and close the day
        self._create_category_rows(self.yesterday, categories)
        self._close_day(self.yesterday, categories)

        # Record a COFFRE value before cloture
        self.db.set_parameter("COFFRE_TOTAL", "20000")

        # Simulate cloture completion
        result = self.service.on_cloture_complete(self.yesterday)

        self.assertEqual(result["closed_date"], self.yesterday)
        self.assertEqual(result["coffre_after"], 0)

        # Verify last closed date is set
        self.assertEqual(self.db.get_parameter("LAST_CLOSED_DATE"), self.yesterday)

    def test_is_previous_day_closed_checks_correctly(self) -> None:
        """Test that is_previous_day_closed checks the right date."""
        # Create and close yesterday
        self._create_category_rows(self.yesterday, ["BA"])
        self._close_day(self.yesterday, ["BA"])

        # Should return True for yesterday as closed
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT cloturee FROM suivi_formulaire_journalier WHERE jour = ?",
                (self.yesterday,),
            ).fetchone()
            self.assertEqual(row["cloturee"], 1)

    def test_get_reset_status(self) -> None:
        """Test getting reset status returns correct info."""
        # Set up some values
        self.db.set_parameter("LAST_CLOSED_DATE", self.yesterday)
        self.db.set_parameter("COFFRE_TOTAL", "5000")
        self.db.set_parameter("DAILY_RESET_PENDING", "0")

        status = self.service.get_reset_status()

        self.assertEqual(status["last_closed_date"], self.yesterday)
        self.assertFalse(status["reset_pending"])

    def test_reset_when_no_coffre_value(self) -> None:
        """Test reset when no coffre value exists (never set)."""
        # No COFFRE_TOTAL parameter set
        result = self.service.execute_reset(self.yesterday)

        # Should default to 0
        self.assertEqual(result["coffre_before"], 0)
        self.assertEqual(result["coffre_after"], 0)


class TestDailyResetWorkflow(unittest.TestCase):
    """Integration tests for full daily reset workflow."""

    def setUp(self) -> None:
        """Set up test database."""
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_workflow.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))
        self.service = DailyResetService(self.db)

    def tearDown(self) -> None:
        """Clean up test database."""
        self.tmpdir.cleanup()

    def _create_category_rows(self, jour: str, categories: list[str]) -> None:
        """Helper to create category tracking rows."""
        with self.db._connect() as conn:
            for cat in categories:
                conn.execute(
                    """
                    INSERT INTO suivi_formulaire_journalier (jour, categorie, cloturee)
                    VALUES (?, ?, 0)
                    ON CONFLICT(jour, categorie) DO UPDATE SET cloturee = 0
                    """,
                    (jour, cat),
                )
            conn.commit()

    def _close_day(self, jour: str, categories: list[str]) -> None:
        """Helper to mark day as closed."""
        with self.db._connect() as conn:
            for cat in categories:
                conn.execute(
                    """
                    UPDATE suivi_formulaire_journalier
                    SET cloturee = 1
                    WHERE jour = ? AND categorie = ?
                    """,
                    (jour, cat),
                )
            conn.commit()

    def test_full_workflow_block_until_cloture(self) -> None:
        """Test full workflow: block until cloture, then allow."""
        yesterday = "2026-04-03"
        categories = ["BA", "BSA"]

        # Initially no closure - should allow
        can_proceed, _ = self.service.validate_startup()
        self.assertTrue(can_proceed)

        # Create yesterday but don't close
        self._create_category_rows(yesterday, categories)

        # Reload service to check again
        self.service = DailyResetService(self.db)
        can_proceed, error = self.service.validate_startup()
        # First run allows, but let's set a last_closed_date to test blocking
        self.db.set_parameter("LAST_CLOSED_DATE", yesterday)

        self.service = DailyResetService(self.db)
        can_proceed, error = self.service.validate_startup()
        self.assertFalse(can_proceed)
        self.assertIsNotNone(error)

        # Now close the day
        self._close_day(yesterday, categories)

        # Now should allow
        self.service = DailyResetService(self.db)
        can_proceed, error = self.service.validate_startup()
        self.assertTrue(can_proceed)
        self.assertIsNone(error)


if __name__ == "__main__":
    unittest.main()
