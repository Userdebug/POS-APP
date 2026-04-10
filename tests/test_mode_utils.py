"""Tests for mode normalization utilities."""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.zone_panier.mode_utils import _normalize_mode, is_achat_mode, is_vente_mode


class TestModeNormalization(unittest.TestCase):
    """Test cases for mode normalization functions."""

    def test_normalize_vente(self):
        """Test that 'vente' is normalized correctly."""
        self.assertEqual(_normalize_mode("vente"), "vente")

    def test_normalize_caisse(self):
        """Test that 'caisse' is normalized to 'vente'."""
        self.assertEqual(_normalize_mode("caisse"), "vente")

    def test_normalize_achat(self):
        """Test that 'achat' is normalized correctly."""
        self.assertEqual(_normalize_mode("achat"), "achat")

    def test_normalize_reception(self):
        """Test that 'reception' is normalized to 'achat'."""
        self.assertEqual(_normalize_mode("reception"), "achat")

    def test_normalize_case_insensitive(self):
        """Test that normalization is case insensitive."""
        self.assertEqual(_normalize_mode("VENTE"), "vente")
        self.assertEqual(_normalize_mode("Caisse"), "vente")
        self.assertEqual(_normalize_mode("ACHAT"), "achat")

    def test_normalize_whitespace(self):
        """Test that whitespace is handled correctly."""
        self.assertEqual(_normalize_mode("  vente  "), "vente")

    def test_empty_mode_defaults_to_vente(self):
        """Test that empty mode defaults to 'vente'."""
        self.assertEqual(_normalize_mode(""), "vente")
        self.assertEqual(_normalize_mode(None), "vente")

    def test_is_vente_mode(self):
        """Test is_vente_mode function."""
        self.assertTrue(is_vente_mode("vente"))
        self.assertTrue(is_vente_mode("caisse"))
        self.assertTrue(is_vente_mode("VENTE"))
        self.assertFalse(is_vente_mode("achat"))
        self.assertFalse(is_vente_mode("reception"))

    def test_is_achat_mode(self):
        """Test is_achat_mode function."""
        self.assertTrue(is_achat_mode("achat"))
        self.assertTrue(is_achat_mode("reception"))
        self.assertTrue(is_achat_mode("ACHAT"))
        self.assertFalse(is_achat_mode("vente"))
        self.assertFalse(is_achat_mode("caisse"))


if __name__ == "__main__":
    unittest.main()
