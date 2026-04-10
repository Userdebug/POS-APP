"""Tests for stock service."""

import os
import sys
import unittest
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.stock_service import decrement_stock, validate_quantity_against_stock


class TestStockService(unittest.TestCase):
    """Test cases for stock service functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db_manager = Mock()

    def test_validate_quantity_no_product_id(self):
        """Test validation passes when no product ID provided."""
        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, None, 10)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")

    def test_validate_quantity_invalid_negative(self):
        """Test validation fails for negative quantity."""
        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, -5)
        self.assertFalse(is_valid)
        self.assertIn("positive", error_msg.lower())

    def test_validate_quantity_invalid_zero(self):
        """Test validation fails for zero quantity."""
        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, 0)
        self.assertFalse(is_valid)

    def test_validate_quantity_product_not_found(self):
        """Test validation fails when product not found."""
        self.mock_db_manager.get_produit_by_id.return_value = None

        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 999, 10)
        self.assertFalse(is_valid)
        self.assertIn("non trouvé", error_msg.lower())

    def test_validate_quantity_insufficient_stock(self):
        """Test validation fails when stock is insufficient."""
        self.mock_db_manager.get_produit_by_id.return_value = {"id": 1, "qte_stock": 5}

        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, 10)
        self.assertFalse(is_valid)
        self.assertIn("insuffisant", error_msg.lower())

    def test_validate_quantity_sufficient_stock(self):
        """Test validation passes when stock is sufficient."""
        self.mock_db_manager.get_produit_by_id.return_value = {"id": 1, "qte_stock": 20}

        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, 10)
        self.assertTrue(is_valid)
        self.assertEqual(error_msg, "")

    def test_validate_quantity_exact_stock(self):
        """Test validation passes when quantity equals stock."""
        self.mock_db_manager.get_produit_by_id.return_value = {"id": 1, "qte_stock": 10}

        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, 10)
        self.assertTrue(is_valid)

    def test_validate_quantity_db_error(self):
        """Test validation handles database errors gracefully."""
        self.mock_db_manager.get_produit_by_id.side_effect = Exception("DB Error")

        is_valid, error_msg = validate_quantity_against_stock(self.mock_db_manager, 1, 10)
        self.assertFalse(is_valid)
        self.assertIn("erreur", error_msg.lower())

    def test_decrement_stock_success(self):
        """Test successful stock decrement."""
        self.mock_db_manager.decrement_stock = Mock()

        result = decrement_stock(self.mock_db_manager, 1, 5)

        self.assertTrue(result)
        self.mock_db_manager.decrement_stock.assert_called_once_with(1, 5)

    def test_decrement_stock_invalid_product_id(self):
        """Test decrement fails with invalid product ID."""
        result = decrement_stock(self.mock_db_manager, None, 5)
        self.assertFalse(result)

        result = decrement_stock(self.mock_db_manager, 0, 5)
        self.assertFalse(result)

    def test_decrement_stock_invalid_quantity(self):
        """Test decrement fails with invalid quantity."""
        result = decrement_stock(self.mock_db_manager, 1, 0)
        self.assertFalse(result)

        result = decrement_stock(self.mock_db_manager, 1, -5)
        self.assertFalse(result)

    def test_decrement_stock_db_error(self):
        """Test decrement handles database errors gracefully."""
        self.mock_db_manager.decrement_stock = Mock(side_effect=Exception("DB Error"))

        result = decrement_stock(self.mock_db_manager, 1, 5)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
