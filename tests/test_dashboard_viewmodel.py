"""Tests for DashboardViewModel."""

import unittest
from unittest.mock import MagicMock

from viewmodels.dashboard_viewmodel import DashboardTotals, DashboardViewModel


class TestDashboardViewModel(unittest.TestCase):
    """Test cases for DashboardViewModel."""

    def setUp(self) -> None:
        self.mock_db = MagicMock()
        self.mock_tracking = MagicMock()

    def test_compute_totals_basic(self) -> None:
        """Test basic totals computation."""
        self.mock_db.total_depenses_jour.return_value = 100
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 800

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_depenses, 100)
        self.assertEqual(totals.total_ventes, 800)
        self.assertEqual(totals.total_caisse, 700)

    def test_compute_totals_with_coffre(self) -> None:
        """Test totals with coffre deduction."""
        self.mock_db.total_depenses_jour.return_value = 200
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 1000

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27", total_coffre=150)

        self.assertEqual(totals.total_depenses, 200)
        self.assertEqual(totals.total_ventes, 1000)
        self.assertEqual(totals.total_caisse, 650)

    def test_compute_totals_empty_tracking(self) -> None:
        """Test totals with no tracking data."""
        self.mock_db.total_depenses_jour.return_value = 0
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 0

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_depenses, 0)
        self.assertEqual(totals.total_ventes, 0)
        self.assertEqual(totals.total_caisse, 0)

    def test_compute_totals_without_tracking_service(self) -> None:
        """Test totals using DB fallback when no tracking service."""
        self.mock_db.total_depenses_jour.return_value = 50
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 300

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_depenses, 50)
        self.assertEqual(totals.total_ventes, 300)
        self.assertEqual(totals.total_caisse, 250)

    def test_compute_totals_handles_none_ca_final(self) -> None:
        """Test totals handles None ca_final values."""
        self.mock_db.total_depenses_jour.return_value = 0
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 100

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_ventes, 100)

    def test_compute_totals_handles_missing_ca_final(self) -> None:
        """Test totals handles missing ca_final key."""
        self.mock_db.total_depenses_jour.return_value = 0
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 200

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_ventes, 200)

    def test_dashboard_totals_dataclass(self) -> None:
        """Test DashboardTotals dataclass creation."""
        totals = DashboardTotals(total_depenses=100, total_ventes=500, total_caisse=400)
        self.assertEqual(totals.total_depenses, 100)
        self.assertEqual(totals.total_ventes, 500)
        self.assertEqual(totals.total_caisse, 400)

    def test_compute_totals_negative_caisse(self) -> None:
        """Test totals when expenses exceed sales."""
        self.mock_db.total_depenses_jour.return_value = 500
        self.mock_db.total_factures_jour.return_value = 0
        self.mock_db.total_ventes_jour.return_value = 100

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        self.assertEqual(totals.total_depenses, 500)
        self.assertEqual(totals.total_ventes, 100)
        self.assertEqual(totals.total_caisse, -400)

    def test_compute_totals_with_factures(self) -> None:
        """Test that daily invoices are added to total_depenses."""
        self.mock_db.total_depenses_jour.return_value = 100
        self.mock_db.total_factures_jour.return_value = 50
        self.mock_db.total_ventes_jour.return_value = 800

        vm = DashboardViewModel(self.mock_db, tracking_service=None)
        totals = vm.compute_totals_for_day("2026-03-27")

        # total_depenses should be expenses + invoices
        self.assertEqual(totals.total_depenses, 150)
        self.assertEqual(totals.total_ventes, 800)
        # caisse = ventes - total_depenses - coffre
        self.assertEqual(totals.total_caisse, 650)


if __name__ == "__main__":
    unittest.main()
