import unittest
from unittest.mock import Mock

from core.constants import DEFAULT_CATEGORY_NAME
from services.reception_persistence_service import ReceptionPersistenceService


class TestReceptionPersistenceService(unittest.TestCase):
    def test_save_reception_row_rejects_blank_name(self) -> None:
        db = Mock()

        result = ReceptionPersistenceService.save_reception_row(
            raw_line={"nom": "   ", "pa": 100, "qte": 2},
            db_manager=db,
            fournisseur={"nom": "F"},
            day="2026-03-06",
            numero_facture=None,
        )

        self.assertEqual({}, result.line)
        self.assertIsNone(result.payload)
        self.assertEqual(0, result.total)
        db.next_product_id.assert_not_called()

    def test_save_reception_row_with_db_persists_payload(self) -> None:
        db = Mock()
        db.next_product_id.return_value = 42

        result = ReceptionPersistenceService.save_reception_row(
            raw_line={"nom": "Produit X", "categorie": "-", "pa": 1000, "qte": 3, "m3": 2},
            db_manager=db,
            fournisseur={"nom": "F-1"},
            day="2026-03-06",
            numero_facture="FACT-TEST",
        )

        self.assertEqual(3000, result.total)
        self.assertIsNotNone(result.payload)
        self.assertEqual(42, result.line["id"])
        self.assertEqual(DEFAULT_CATEGORY_NAME, result.line["categorie"])

        db.next_product_id.assert_called_once()
        db.upsert_products.assert_called_once()
        db.record_reception_line.assert_called_once()

    def test_save_reception_row_without_db_keeps_line_only(self) -> None:
        result = ReceptionPersistenceService.save_reception_row(
            raw_line={"id": 7, "nom": "Produit Y", "categorie": "EPICERIE", "pa": 200, "qte": 2},
            db_manager=None,
            fournisseur={"nom": "F-2"},
            day="2026-03-06",
            numero_facture=None,
        )

        self.assertEqual(400, result.total)
        self.assertEqual(7, result.line["id"])
        self.assertEqual("EPICERIE", result.line["categorie"])
        self.assertIsNone(result.payload)


if __name__ == "__main__":
    unittest.main()
