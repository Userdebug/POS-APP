"""Tests for DraftManager."""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ui.zone_panier.draft_manager import DraftManager


class TestDraftManager(unittest.TestCase):
    """Test cases for DraftManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.dm = DraftManager()

    def test_initial_state(self):
        """Test that DraftManager initializes with empty drafts."""
        self.assertIsNone(self.dm.get_draft("vente"))
        self.assertIsNone(self.dm.get_draft("achat"))
        self.assertFalse(self.dm.has_draft("vente"))
        self.assertFalse(self.dm.has_draft("achat"))

    def test_set_and_get_draft_vente(self):
        """Test setting and getting draft for vente mode."""
        draft = {"id": 1, "nom": "Test Product", "qte": 5}
        self.dm.set_draft(draft, "vente")

        self.assertEqual(self.dm.get_draft("vente"), draft)
        self.assertTrue(self.dm.has_draft("vente"))

    def test_set_and_get_draft_achat(self):
        """Test setting and getting draft for achat mode."""
        draft = {"id": 2, "nom": "Test Product 2", "qte": 10}
        self.dm.set_draft(draft, "achat")

        self.assertEqual(self.dm.get_draft("achat"), draft)
        self.assertTrue(self.dm.has_draft("achat"))

    def test_clear_draft(self):
        """Test clearing a draft."""
        draft = {"id": 1, "nom": "Test Product", "qte": 5}
        self.dm.set_draft(draft, "vente")
        self.assertTrue(self.dm.has_draft("vente"))

        self.dm.clear_draft("vente")
        self.assertIsNone(self.dm.get_draft("vente"))
        self.assertFalse(self.dm.has_draft("vente"))

    def test_clear_all(self):
        """Test clearing all drafts."""
        self.dm.set_draft({"id": 1}, "vente")
        self.dm.set_draft({"id": 2}, "achat")

        self.dm.clear_all()

        self.assertFalse(self.dm.has_draft("vente"))
        self.assertFalse(self.dm.has_draft("achat"))

    def test_mode_normalization(self):
        """Test that mode normalization works correctly."""
        draft = {"id": 1, "nom": "Test Product"}

        # Test with legacy mode names
        self.dm.set_draft(draft, "caisse")
        self.assertEqual(self.dm.get_draft("vente"), draft)

        self.dm.clear_draft("vente")

        self.dm.set_draft(draft, "reception")
        self.assertEqual(self.dm.get_draft("achat"), draft)

    def test_default_mode(self):
        """Test that default mode is 'vente' when None is passed."""
        draft = {"id": 1, "nom": "Test Product"}
        self.dm.set_draft(draft, None)

        self.assertEqual(self.dm.get_draft(), draft)
        self.assertEqual(self.dm.get_draft("vente"), draft)


if __name__ == "__main__":
    unittest.main()
