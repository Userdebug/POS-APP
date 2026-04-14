"""Tests for ProduitsTable category filter functionality."""

import sys
import unittest

from PyQt6.QtWidgets import QApplication

from ui.components.products_table import ProduitsTable


class TestProduitsTableCategories(unittest.TestCase):
    """Tests for category filter in ProduitsTable."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv)

    def setUp(self):
        self.table = ProduitsTable()

    def test_default_categories_initialized(self):
        """Test that default categories are initialized."""
        categories = self.table.get_categories()
        self.assertIn("BA", categories)
        self.assertIn("BSA", categories)

    def test_set_categories_updates_map(self):
        """Test that set_categories updates the categories map."""
        new_categories = ["CAT1", "CAT2", "CAT3"]
        self.table.set_categories(new_categories)

        result = self.table.get_categories()
        self.assertEqual(result, {"CAT1": "CAT1", "CAT2": "CAT2", "CAT3": "CAT3"})

    def test_set_categories_with_dict(self):
        """Test that set_categories accepts a dict mapping."""
        category_map = {"B": "Boisson", "A": "Aliment"}
        self.table.set_categories(category_map)

        result = self.table.get_categories()
        self.assertEqual(result, {"B": "Boisson", "A": "Aliment"})

    def test_update_category_buttons_rebuilds_ui(self):
        """Test that update_category_buttons rebuilds button UI."""
        self.table.set_categories(["NEWCAT1", "NEWCAT2"])
        self.table.update_category_buttons()

        self.assertEqual(len(self.table._category_buttons), 3)

    def test_categories_modifiees_signal_emitted(self):
        """Test that categories_modifiees signal is emitted on category change."""
        signal_emitted = []

        def on_categories_changed(categories):
            signal_emitted.append(categories)

        self.table.categories_modifiees.connect(on_categories_changed)
        self.table.set_categories(["NEWCAT"])

        self.assertEqual(len(signal_emitted), 1)
        self.assertIn("NEWCAT", signal_emitted[0])

    def test_category_filter_works_with_dynamic_categories(self):
        """Test that filtering works with dynamically added categories."""
        products = [
            {"id": 1, "nom": "Product 1", "categorie": "BA", "b": 10, "r": 5, "pv": 1000},
            {"id": 2, "nom": "Product 2", "categorie": "BSA", "b": 20, "r": 10, "pv": 2000},
        ]
        self.table.set_produits(products)

        self.table.set_categories(["BA", "BSA"])
        self.table.update_category_buttons()

        self.table._set_category("BA")
        filtered = self.table._filtered_produits()

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["categorie"], "BA")

    def test_category_filter_works_after_category_removal(self):
        """Test that filtering works when categories are removed."""
        products = [
            {"id": 1, "nom": "Product 1", "categorie": "BA", "b": 10, "r": 5, "pv": 1000},
            {"id": 2, "nom": "Product 2", "categorie": "BSA", "b": 20, "r": 10, "pv": 2000},
        ]
        self.table.set_produits(products)

        self.table.set_categories(["BA"])
        self.table.update_category_buttons()

        self.table._set_category("BA")
        filtered = self.table._filtered_produits()

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["categorie"], "BA")

    def test_two_row_layout_with_many_categories(self):
        """Test that buttons wrap to 2 rows with many categories."""
        many_categories = [f"CAT{i}" for i in range(15)]
        self.table.set_categories(many_categories)
        self.table.update_category_buttons()

        button_count = len(self.table._category_buttons)
        self.assertEqual(button_count, 16)


if __name__ == "__main__":
    unittest.main()
