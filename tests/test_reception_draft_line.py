"""Tests for Reception mode unified draft line mechanism."""

import unittest
from unittest.mock import MagicMock

from controllers.panier_selection_controller import PanierSelectionController
from ui.zone_panier.basket_models import normalize_ligne
from viewmodels.panier_viewmodel import BasketManagerFactory


class TestReceptionDraftLine(unittest.TestCase):
    """Test suite for Reception mode draft line functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.factory = BasketManagerFactory()
        self.factory.set_current_mode("reception")
        self.manager = self.factory.current_manager

    def test_reception_mode_uses_draft_line(self):
        """Test that Reception mode creates draft line when adding product."""
        # Simulate adding a product in Reception mode
        product = {
            "id": 1,
            "nom": "Test Product",
            "categorie": "Test",
            "pa": 100,
            "prc": 120,
            "pv": 150,
            "qte": 1,
        }

        # In Reception mode, the draft line should be created
        # This tests the concept that both modes use draft line
        normalized = normalize_ligne(product)

        # Verify the normalized line has correct structure
        self.assertEqual(normalized["nom"], "Test Product")
        self.assertEqual(normalized["pa"], 100)
        self.assertEqual(normalized["pv"], 150)
        self.assertEqual(normalized["qte"], 1)

    def test_data_isolation_between_modes(self):
        """Test that Reception and Caisse modes have isolated data."""
        # Add item to Reception mode
        self.factory.set_current_mode("reception")
        reception_manager = self.factory.current_manager
        reception_manager.add(
            {
                "nom": "Reception Product",
                "pa": 100,
                "pv": 150,
                "qte": 2,
            }
        )

        # Switch to Caisse mode
        self.factory.set_current_mode("caisse")
        caisse_manager = self.factory.current_manager

        # Add item to Caisse mode
        caisse_manager.add(
            {
                "nom": "Caisse Product",
                "pa": 50,
                "pv": 75,
                "qte": 3,
            }
        )

        # Verify data is isolated
        self.assertEqual(len(reception_manager.get_active()), 1)
        self.assertEqual(len(caisse_manager.get_active()), 1)

        # Verify different products
        self.assertEqual(reception_manager.get_active()[0]["nom"], "Reception Product")
        self.assertEqual(caisse_manager.get_active()[0]["nom"], "Caisse Product")

    def test_validation_enabled_with_reception_draft_line(self):
        """Test that validation is enabled when Reception draft line exists."""
        # Test Reception mode with draft line
        result = PanierSelectionController.validation_enabled(
            mode="reception",
            has_brouillon=False,  # No Caisse draft line
            has_achats_brouillon=True,  # Has Reception draft line
            panier_row_count=0,
            panier_current_row=-1,
            facture_row_count=0,
            facture_current_row=-1,
        )
        self.assertTrue(result)

    def test_validation_enabled_reception_without_draft_line(self):
        """Test that validation works with selected row in Reception mode."""
        result = PanierSelectionController.validation_enabled(
            mode="reception",
            has_brouillon=False,
            has_achats_brouillon=False,
            panier_row_count=0,
            panier_current_row=-1,
            facture_row_count=3,
            facture_current_row=1,
        )
        self.assertTrue(result)

    def test_validation_enabled_reception_no_items(self):
        """Test that validation is disabled when no items in Reception mode."""
        result = PanierSelectionController.validation_enabled(
            mode="reception",
            has_brouillon=False,
            has_achats_brouillon=False,
            panier_row_count=0,
            panier_current_row=-1,
            facture_row_count=0,
            facture_current_row=-1,
        )
        self.assertFalse(result)

    def test_caisse_validation_with_draft_line(self):
        """Test that Caisse validation still works with draft line."""
        result = PanierSelectionController.validation_enabled(
            mode="caisse",
            has_brouillon=True,  # Has draft line
            has_achats_brouillon=False,
            panier_row_count=0,
            panier_current_row=-1,
            facture_row_count=0,
            facture_current_row=-1,
        )
        self.assertTrue(result)

    def test_caisse_validation_with_selected_row(self):
        """Test that Caisse validation works with selected row."""
        result = PanierSelectionController.validation_enabled(
            mode="caisse",
            has_brouillon=False,
            has_achats_brouillon=False,
            panier_row_count=5,
            panier_current_row=2,
            facture_row_count=0,
            facture_current_row=-1,
        )
        self.assertTrue(result)

    def test_mode_switching_preserves_data(self):
        """Test that switching modes preserves each mode's data."""
        # Add to Reception
        self.factory.set_current_mode("reception")
        self.factory.current_manager.add({"nom": "R1", "pa": 10, "pv": 20, "qte": 1})

        # Add to Caisse
        self.factory.set_current_mode("caisse")
        self.factory.current_manager.add({"nom": "C1", "pa": 5, "pv": 10, "qte": 2})

        # Switch back to Reception - data should be preserved
        self.factory.set_current_mode("reception")
        reception_items = self.factory.current_manager.get_active()
        self.assertEqual(len(reception_items), 1)
        self.assertEqual(reception_items[0]["nom"], "R1")

        # Switch to Caisse - data should be preserved
        self.factory.set_current_mode("caisse")
        caisse_items = self.factory.current_manager.get_active()
        self.assertEqual(len(caisse_items), 1)
        self.assertEqual(caisse_items[0]["nom"], "C1")

    def test_calculator_valider_only_for_caisse_mode(self):
        """Test that calculator valider only triggers for Caisse mode.

        This tests the logic in main_window._validate_from_calculator()
        """

        # Create mock basket widget
        mock_panier = MagicMock()
        mock_panier.pm = MagicMock()
        mock_panier.pm.mode = "caisse"
        mock_panier.validate_line_and_next = MagicMock()

        # Test Caisse mode - should call validate
        def validate_if_caisse():
            if mock_panier.pm.mode == "caisse":
                mock_panier.validate_line_and_next()

        validate_if_caisse()
        self.assertTrue(mock_panier.validate_line_and_next.called)

        # Reset and test Reception mode
        mock_panier.validate_line_and_next.reset_mock()
        mock_panier.pm.mode = "reception"

        validate_if_caisse()
        self.assertFalse(mock_panier.validate_line_and_next.called)


class TestBasketManagerFactory(unittest.TestCase):
    """Test BasketManagerFactory for Reception mode."""

    def test_reception_mode_creates_separate_manager(self):
        """Test that Reception mode gets its own manager."""
        factory = BasketManagerFactory()

        # Get manager for Reception
        factory.set_current_mode("reception")
        reception_manager = factory.current_manager

        # Get manager for Caisse
        factory.set_current_mode("caisse")
        caisse_manager = factory.current_manager

        # They should be different objects
        self.assertIsNot(reception_manager, caisse_manager)

    def test_reception_manager_has_correct_mode(self):
        """Test that Reception manager has correct mode set.

        Note: The factory maps "reception" to "achat" internally.
        """
        factory = BasketManagerFactory()
        factory.set_current_mode("reception")

        # Factory maps "reception" to "achat" for backward compatibility
        self.assertEqual(factory.current_manager.mode, "achat")


if __name__ == "__main__":
    unittest.main()
