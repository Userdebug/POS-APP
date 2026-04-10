"""Tests pour le calcul de marge."""

from __future__ import annotations

import unittest


class TestMarginCalculator(unittest.TestCase):
    def test_compute_margin_percent(self):
        from core.database.margin_calculator import MarginCalculator

        result = MarginCalculator.compute_margin_percent(1000, 200, actual_value=1200)
        self.assertEqual(result, 20.0)


if __name__ == "__main__":
    unittest.main()
