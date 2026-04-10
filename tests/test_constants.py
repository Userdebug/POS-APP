"""Tests pour les constantes metier."""

from __future__ import annotations

import unittest

from core.constants import (
    BILLETAGE_DENOMINATIONS,
    CURRENCY_LABEL,
    DATE_FORMAT_DAY,
    DATE_FORMAT_FACTURE_REF,
    DATE_FORMAT_MONTH,
    DATE_FORMAT_TIME,
    DEFAULT_CATEGORY_NAME,
    DEFAULT_SUPPLIER_NAME,
    FACTURE_NUMBER_PREFIX,
    GUEST_CATEGORIES,
    OASIS_CATEGORIES,
)


class TestConstants(unittest.TestCase):
    """Verification que les constantes sont presentes et valides."""

    def test_default_category_name(self) -> None:
        self.assertEqual(DEFAULT_CATEGORY_NAME, "Sans categorie")

    def test_default_supplier_name(self) -> None:
        self.assertEqual(DEFAULT_SUPPLIER_NAME, "FOURNISSEUR PAR DEFAUT")

    def test_currency_label(self) -> None:
        self.assertEqual(CURRENCY_LABEL, "Ar")

    def test_facture_number_prefix(self) -> None:
        self.assertEqual(FACTURE_NUMBER_PREFIX, "FACT")

    def test_billetage_denominations_are_ints(self) -> None:
        for denom in BILLETAGE_DENOMINATIONS:
            self.assertIsInstance(denom, int)
            self.assertGreater(denom, 0)

    def test_billetage_denominations_descending(self) -> None:
        """Les denominations doivent etre en ordre decroissant."""
        for i in range(len(BILLETAGE_DENOMINATIONS) - 1):
            self.assertGreater(
                BILLETAGE_DENOMINATIONS[i],
                BILLETAGE_DENOMINATIONS[i + 1],
            )

    def test_oasis_categories_not_empty(self) -> None:
        self.assertGreater(len(OASIS_CATEGORIES), 0)

    def test_guest_categories_not_empty(self) -> None:
        self.assertGreater(len(GUEST_CATEGORIES), 0)

    def test_oasis_and_guest_disjoint(self) -> None:
        """Aucune categorie ne doit etre a la fois Oasis et Guest."""
        overlap = set(OASIS_CATEGORIES) & set(GUEST_CATEGORIES)
        self.assertEqual(overlap, set())

    def test_date_format_day(self) -> None:
        self.assertEqual(DATE_FORMAT_DAY, "%Y-%m-%d")

    def test_date_format_month(self) -> None:
        self.assertEqual(DATE_FORMAT_MONTH, "%Y-%m")

    def test_date_format_time(self) -> None:
        self.assertEqual(DATE_FORMAT_TIME, "%H:%M:%S")

    def test_date_format_facture_ref(self) -> None:
        self.assertEqual(DATE_FORMAT_FACTURE_REF, "%Y%m%d-%H%M%S")

    def test_all_exports_every_public_constant(self) -> None:
        """Chaque constante publique du module doit figurer dans __all__."""
        import core.constants as mod

        public_names = [name for name in dir(mod) if not name.startswith("_") and name.isupper()]
        for name in public_names:
            self.assertIn(name, mod.__all__, f"{name!r} absent de __all__")

    def test_billetage_contains_expected_denominations(self) -> None:
        expected = {20000, 10000, 5000, 2000, 1000, 500, 200, 100}
        self.assertEqual(set(BILLETAGE_DENOMINATIONS), expected)

    def test_oasis_categories_expected_names(self) -> None:
        expected = {"BA", "BSA", "Confi", "EPI", "Tabac"}
        self.assertEqual(set(OASIS_CATEGORIES), expected)

    def test_date_formats_parseable(self) -> None:
        """Les formats de date doivent etre compatibles avec datetime."""
        from datetime import datetime

        dt = datetime(2025, 6, 15, 14, 30, 45)
        day_str = dt.strftime(DATE_FORMAT_DAY)
        self.assertEqual(day_str, "2025-06-15")
        time_str = dt.strftime(DATE_FORMAT_TIME)
        self.assertEqual(time_str, "14:30:45")


if __name__ == "__main__":
    unittest.main()
