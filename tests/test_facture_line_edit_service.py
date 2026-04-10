import unittest

from services.facture_edit_service import FactureLineEditService


class TestFactureLineEditService(unittest.TestCase):
    def test_edit_nom(self) -> None:
        line = {"nom": "A", "categorie": "CAT", "pa": 100, "qte": 2}
        result = FactureLineEditService.apply_cell_edit(line, col=0, text="Produit B")

        self.assertTrue(result.handled)
        self.assertEqual("Produit B", result.line["nom"])
        self.assertEqual("200", result.formatted_total_value)

    def test_edit_categorie(self) -> None:
        line = {"nom": "A", "categorie": "CAT", "pa": 50, "qte": 4}
        result = FactureLineEditService.apply_cell_edit(line, col=1, text="EPICERIE")

        self.assertTrue(result.handled)
        self.assertEqual("EPICERIE", result.line["categorie"])
        self.assertEqual("200", result.formatted_total_value)

    def test_edit_pa_recomputes_prc_and_total(self) -> None:
        line = {"nom": "A", "categorie": "CAT", "pa": 0, "prc": 0, "prix": 0, "qte": 3}
        result = FactureLineEditService.apply_cell_edit(line, col=2, text="1 500")

        self.assertTrue(result.handled)
        self.assertEqual(1500, result.line["pa"])
        self.assertEqual(1800, result.line["prc"])
        self.assertEqual(1500, result.line["prix"])
        self.assertEqual("1 500", result.formatted_cell_value)
        self.assertEqual("1 800", result.formatted_prc_value)
        self.assertEqual("4 500", result.formatted_total_value)

    def test_edit_pv_updates_value(self) -> None:
        line = {"nom": "A", "categorie": "CAT", "pa": 200, "pv": 200, "qte": 2}
        result = FactureLineEditService.apply_cell_edit(line, col=4, text="350")

        self.assertTrue(result.handled)
        self.assertEqual(350, result.line["pv"])
        self.assertEqual("350", result.formatted_cell_value)
        self.assertIsNone(result.formatted_prc_value)
        self.assertEqual("400", result.formatted_total_value)

    def test_unsupported_col_is_ignored(self) -> None:
        line = {"nom": "A", "categorie": "CAT", "pa": 200, "qte": 2}
        result = FactureLineEditService.apply_cell_edit(line, col=6, text="999")

        self.assertFalse(result.handled)
        self.assertEqual(line, result.line)
        self.assertIsNone(result.formatted_cell_value)
        self.assertIsNone(result.formatted_total_value)


if __name__ == "__main__":
    unittest.main()
