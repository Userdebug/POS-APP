"""Tests for BasketManagerFactory data isolation."""

import unittest

from viewmodels.panier_viewmodel import BasketManagerFactory


class TestBasketManagerFactory(unittest.TestCase):
    """Tests for BasketManagerFactory data isolation."""

    def setUp(self):
        self.factory = BasketManagerFactory()

    def test_data_isolation_ventes_achat(self):
        """Items added in VENTE mode should not appear in ACHAT mode."""
        # Add items to VENTE mode
        vente_manager = self.factory.get_manager("vente")
        vente_manager.add({"nom": "Product A", "pv": 1000, "qte": 2})
        vente_manager.add({"nom": "Product B", "pv": 500, "qte": 1})

        # Get ACHAT manager
        achat_manager = self.factory.get_manager("achat")

        # Verify isolation
        self.assertEqual(len(vente_manager.get_actif()), 2)
        self.assertEqual(len(achat_manager.get_actif()), 0)

    def test_mode_switching_preserves_data(self):
        """Switching modes should preserve each mode's data."""
        # Add items in VENTE
        vente = self.factory.get_manager("vente")
        vente.add({"nom": "Vente Item", "pv": 100})

        # Switch to ACHAT and add items
        self.factory.set_current_mode("achat")
        achat = self.factory.current_manager
        achat.add({"nom": "Achat Item", "pa": 50})

        # Verify both have their own data
        self.factory.set_current_mode("vente")
        self.assertEqual(len(self.factory.current_manager.get_actif()), 1)

        self.factory.set_current_mode("achat")
        self.assertEqual(len(self.factory.current_manager.get_actif()), 1)

    def test_lazy_instantiation(self):
        """Managers should only be created when first accessed."""
        # No managers should exist initially
        self.assertEqual(len(self.factory._managers), 0)

        # Accessing a mode creates the manager
        _ = self.factory.get_manager("vente")
        self.assertEqual(len(self.factory._managers), 1)

        # Another mode creates another manager
        _ = self.factory.get_manager("achat")
        self.assertEqual(len(self.factory._managers), 2)

    def test_backward_compatibility_caisse(self):
        """Legacy 'caisse' mode should map to 'vente'."""
        manager = self.factory.get_manager("caisse")
        self.assertEqual(manager.mode, "vente")

    def test_backward_compatibility_reception(self):
        """Legacy 'reception' mode should map to 'achat'."""
        manager = self.factory.get_manager("reception")
        self.assertEqual(manager.mode, "achat")

    def test_current_manager_property(self):
        """current_manager should return manager for current mode."""
        self.factory.set_current_mode("vente")
        vente_manager = self.factory.current_manager
        self.assertEqual(vente_manager.mode, "vente")

        self.factory.set_current_mode("achat")
        achat_manager = self.factory.current_manager
        self.assertEqual(achat_manager.mode, "achat")

        # Should be different instances
        self.assertIsNot(vente_manager, achat_manager)


if __name__ == "__main__":
    unittest.main()
