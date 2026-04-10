"""Unit tests for DailyResetService."""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from services.daily_reset_service import (
    DailyResetError,
    DailyResetService,
    PreviousDayNotClosedError,
)


class TestDailyResetService(unittest.TestCase):
    """Unit tests for DailyResetService."""

    def setUp(self) -> None:
        """Set up test mocks."""
        self.mock_db = MagicMock()
        self.service = DailyResetService(self.mock_db)

    def test_get_current_date(self) -> None:
        """Test getting current date in ISO format."""
        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4, 10, 30, 0)
            mock_dt.strptime = datetime.strptime
            result = self.service.get_current_date()
            self.assertEqual(result, "2026-04-04")

    def test_get_previous_date(self) -> None:
        """Test getting previous date."""
        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.strptime = datetime.strptime
            mock_dt.side_effect = lambda d, f: datetime.strptime(d, f)
            result = self.service.get_previous_date("2026-04-04")
            self.assertEqual(result, "2026-04-03")

    def test_get_previous_date_default_today(self) -> None:
        """Test getting previous date defaults to today."""
        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4, 10, 30, 0)
            mock_dt.strptime = datetime.strptime
            result = self.service.get_previous_date()
            self.assertEqual(result, "2026-04-03")

    def test_get_last_closed_date(self) -> None:
        """Test getting last closed date from parameters."""
        self.mock_db.get_parameter.return_value = "2026-03-31"
        result = self.service.get_last_closed_date()
        self.assertEqual(result, "2026-03-31")
        self.mock_db.get_parameter.assert_called_once_with("LAST_CLOSED_DATE")

    def test_get_last_closed_date_none(self) -> None:
        """Test getting last closed date when not set."""
        self.mock_db.get_parameter.return_value = None
        result = self.service.get_last_closed_date()
        self.assertIsNone(result)

    def test_set_last_closed_date(self) -> None:
        """Test setting last closed date."""
        self.service.set_last_closed_date("2026-03-31")
        self.mock_db.set_parameter.assert_called_once_with("LAST_CLOSED_DATE", "2026-03-31")

    def test_is_reset_pending(self) -> None:
        """Test checking reset pending flag."""
        self.mock_db.get_parameter.return_value = "1"
        result = self.service.is_reset_pending()
        self.assertTrue(result)

        self.mock_db.get_parameter.return_value = "0"
        result = self.service.is_reset_pending()
        self.assertFalse(result)

    def test_set_reset_pending(self) -> None:
        """Test setting reset pending flag."""
        self.service.set_reset_pending(True)
        self.mock_db.set_parameter.assert_called_once_with("DAILY_RESET_PENDING", "1")

        self.service.set_reset_pending(False)
        self.mock_db.set_parameter.assert_called_with("DAILY_RESET_PENDING", "0")

    def test_is_previous_day_closed_true(self) -> None:
        """Test checking previous day closure returns True."""
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 5}
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.is_previous_day_closed()
            self.assertTrue(result)

    def test_is_previous_day_closed_false(self) -> None:
        """Test checking previous day closure returns False."""
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 0}
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.is_previous_day_closed()
            self.assertFalse(result)

    def test_validate_startup_no_previous_closure(self) -> None:
        """Test startup validation allows first run."""
        self.mock_db.get_parameter.return_value = None

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            can_proceed, error = self.service.validate_startup()
            self.assertTrue(can_proceed)
            self.assertIsNone(error)

    def test_validate_startup_previous_day_closed(self) -> None:
        """Test startup validation allows when previous day is closed."""
        self.mock_db.get_parameter.return_value = "2026-04-02"
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 1}
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            can_proceed, error = self.service.validate_startup()
            self.assertTrue(can_proceed)
            self.assertIsNone(error)

    def test_validate_startup_previous_day_not_closed(self) -> None:
        """Test startup validation blocks when previous day is not closed."""
        self.mock_db.get_parameter.return_value = "2026-04-02"
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 0}
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            can_proceed, error = self.service.validate_startup()
            self.assertFalse(can_proceed)
            self.assertIsNotNone(error)
            self.assertIn("est requise", error)

    def test_check_can_operate_true(self) -> None:
        """Test quick check returns True."""
        self.mock_db.get_parameter.return_value = None

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.check_can_operate()
            self.assertTrue(result)

    def test_check_can_operate_false(self) -> None:
        """Test quick check returns False when blocked."""
        self.mock_db.get_parameter.return_value = "2026-04-02"
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 0}
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.check_can_operate()
            self.assertFalse(result)

    def test_execute_reset(self) -> None:
        """Test executing daily reset."""
        self.mock_db.get_parameter.return_value = "15000"

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.execute_reset("2026-04-03")

        self.assertEqual(result["closed_date"], "2026-04-03")
        self.assertEqual(result["coffre_before"], 15000)
        self.assertEqual(result["coffre_after"], 0)

        # Verify parameters were set
        self.mock_db.set_parameter.assert_any_call("LAST_CLOSED_DATE", "2026-04-03")
        self.mock_db.set_parameter.assert_any_call("COFFRE_TOTAL", "0")
        self.mock_db.set_parameter.assert_any_call("DAILY_RESET_PENDING", "0")

    def test_execute_reset_no_coffre_value(self) -> None:
        """Test executing reset with no existing coffre value."""
        self.mock_db.get_parameter.return_value = None

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.execute_reset("2026-04-03")

        self.assertEqual(result["coffre_before"], 0)
        self.assertEqual(result["coffre_after"], 0)

    def test_on_cloture_complete(self) -> None:
        """Test handling cloture completion."""
        self.mock_db.get_parameter.return_value = "5000"

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.on_cloture_complete("2026-04-03")

        self.assertEqual(result["closed_date"], "2026-04-03")

    def test_get_reset_status(self) -> None:
        """Test getting reset status."""
        self.mock_db.get_parameter.return_value = "2026-04-02"
        mock_ctx = MagicMock()
        mock_ctx.execute.return_value.fetchone.return_value = {"n": 1}
        self.mock_db._connect.return_value = mock_ctx

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            status = self.service.get_reset_status()

        self.assertEqual(status["current_date"], "2026-04-04")
        self.assertEqual(status["previous_date"], "2026-04-03")
        self.assertEqual(status["last_closed_date"], "2026-04-02")
        self.assertTrue(status["previous_day_closed"])

    def test_exception_hierarchy(self) -> None:
        """Test exception hierarchy."""
        self.assertTrue(issubclass(DailyResetError, Exception))
        self.assertTrue(issubclass(PreviousDayNotClosedError, DailyResetError))
        err = PreviousDayNotClosedError("2026-03-31", "2026-04-04")
        self.assertEqual(err.last_closed_date, "2026-03-31")
        self.assertEqual(err.current_date, "2026-04-04")


class TestDailyResetServiceEdgeCases(unittest.TestCase):
    """Edge case tests for DailyResetService."""

    def setUp(self) -> None:
        """Set up test mocks."""
        self.mock_db = MagicMock()
        self.service = DailyResetService(self.mock_db)

    def test_is_previous_day_closed_exception(self) -> None:
        """Test handling exception in previous day check."""
        self.mock_db._connect.return_value.__enter__ = MagicMock()
        self.mock_db._connect.return_value.__enter__.return_value.execute.side_effect = Exception(
            "DB Error"
        )
        self.mock_db._connect.return_value.__exit__ = MagicMock()

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.is_previous_day_closed()
            # Should return False on exception
            self.assertFalse(result)

    def test_execute_reset_invalid_coffre(self) -> None:
        """Test executing reset with invalid coffre value."""
        self.mock_db.get_parameter.return_value = "invalid"

        with patch("services.daily_reset_service.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 4, 4)
            mock_dt.strptime = datetime.strptime
            result = self.service.execute_reset("2026-04-03")

        # Should default to 0
        self.assertEqual(result["coffre_before"], 0)


if __name__ == "__main__":
    unittest.main()
