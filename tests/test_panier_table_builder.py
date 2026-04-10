import unittest

from ui.components.panier_table_builder import PanierTableBuilder


class TestPanierTableBuilder(unittest.TestCase):
    def test_build_empty(self) -> None:
        result = PanierTableBuilder.build([])

        self.assertEqual([], result.caisse_rows)
        self.assertEqual(0, result.caisse_total)
        self.assertEqual([], result.facture_rows)

    def test_build_populates_caisse_and_facture_rows(self) -> None:
        lines = [
            {"nom": "P1", "categorie": "CAT", "pa": 100, "prc": 120, "pv": 150, "qte": 2},
            {"nom": "P2", "categorie": "EP", "pa": 50, "prc": 60, "pv": 80, "qte": 3},
        ]

        result = PanierTableBuilder.build(lines)

        self.assertEqual(2, len(result.caisse_rows))
        self.assertEqual(350, result.caisse_total)
        self.assertEqual(2, len(result.facture_rows))

        first = result.facture_rows[0]
        self.assertEqual("P1", first.cells[0].value)
        self.assertTrue(first.cells[2].align_right)
        self.assertFalse(first.cells[3].editable)
        self.assertFalse(first.cells[5].editable)
        self.assertEqual("200", first.cells[6].value)
        self.assertEqual(2, first.quantity)

    def test_build_handles_bad_numeric_values(self) -> None:
        lines = [{"nom": "P", "categorie": "CAT", "pa": "oops", "qte": "bad"}]

        result = PanierTableBuilder.build(lines)

        self.assertEqual(0, result.caisse_total)
        self.assertEqual("0", result.facture_rows[0].cells[6].value)


if __name__ == "__main__":
    unittest.main()
