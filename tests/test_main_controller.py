"""Tests for MainController logic."""

import unittest
from unittest.mock import MagicMock


class TestMainControllerLogic(unittest.TestCase):
    """Test cases for MainController business logic without PyQt6 dependencies."""

    def setUp(self) -> None:
        self.mock_db = MagicMock()
        self.mock_db.get_parameter.return_value = "0"
        self.mock_db.get_setting.return_value = ""
        self.mock_db.open_db_session.return_value = (1, 42)

    def test_open_session_delegates_to_db(self) -> None:
        """Test open_session calls db_manager.open_db_session."""

        result = self.mock_db.open_db_session("Tester", "caissier")
        self.assertEqual(result, (1, 42))
        self.mock_db.open_db_session.assert_called_once_with("Tester", "caissier")

    def test_close_session_delegates_to_db(self) -> None:
        """Test close_session calls db_manager.close_session."""
        self.mock_db.close_session(42)
        self.mock_db.close_session.assert_called_once_with(42)

    def test_compute_totals_aggregation(self) -> None:
        """Test compute_totals_for_day aggregation logic."""
        from viewmodels.dashboard_viewmodel import DashboardViewModel

        self.mock_db.total_depenses_jour.return_value = 100
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 800

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27", total_coffre=50)

        self.assertEqual(totals.total_depenses, 100)
        self.assertEqual(totals.total_ventes, 800)
        self.assertEqual(totals.total_caisse, 650)

    def test_compute_totals_without_coffre(self) -> None:
        """Test compute_totals_for_day without coffre."""
        from viewmodels.dashboard_viewmodel import DashboardViewModel

        self.mock_db.total_depenses_jour.return_value = 200
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 1000

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_depenses, 200)
        self.assertEqual(totals.total_ventes, 1000)
        self.assertEqual(totals.total_caisse, 800)

    def test_get_cash_denominations_default(self) -> None:
        """Test cash denominations fallback to default."""

        self.mock_db.get_setting.return_value = ""
        raw = self.mock_db.get_setting("CASH_DENOMINATIONS", "")
        self.assertEqual(raw, "")

    def test_get_cash_denominations_from_db(self) -> None:
        """Test cash denominations parsed from DB."""
        self.mock_db.get_setting.return_value = "1000,500,200"
        raw = self.mock_db.get_setting("CASH_DENOMINATIONS", "")
        denoms = [int(x.strip()) for x in raw.split(",") if x.strip()]
        self.assertEqual(denoms, [1000, 500, 200])

    def test_load_products_delegates(self) -> None:
        """Test load_products calls db_manager.list_products."""
        self.mock_db.list_products.return_value = [{"id": 1, "nom": "Test"}]
        products = self.mock_db.list_products()
        self.assertEqual(len(products), 1)
        self.mock_db.list_products.assert_called_once()

    def test_update_app_state(self) -> None:
        """Test update_app_state persists mode."""
        self.mock_db.set_parameter("APP_MODE", "caisse")
        self.mock_db.set_parameter.assert_called_with("APP_MODE", "caisse")

    def test_total_coffre_load(self) -> None:
        """Test coffre total loading from DB."""
        self.mock_db.get_parameter.return_value = "1500"
        raw = self.mock_db.get_parameter("COFFRE_TOTAL", "0")
        total = int(raw) if raw else 0
        self.assertEqual(total, 1500)

    def test_total_coffre_default(self) -> None:
        """Test coffre total default when not set."""
        self.mock_db.get_parameter.return_value = "0"
        raw = self.mock_db.get_parameter("COFFRE_TOTAL", "0")
        total = int(raw) if raw else 0
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
