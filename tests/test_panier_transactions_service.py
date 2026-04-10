import unittest
from datetime import datetime
from unittest.mock import Mock

from core.constants import DEFAULT_CATEGORY_NAME
from services.panier_transactions_service import PanierTransactionsService


class TestPanierTransactionsService(unittest.TestCase):
    def test_compute_encaissement_summary(self) -> None:
        items = [
            {"prix": 100, "qte": 2},
            {"prix": 50, "qte": 3},
        ]

        summary = PanierTransactionsService.compute_collection_summary(items)

        self.assertEqual(350, summary.total)
        self.assertEqual(2, summary.nb_lignes)
        self.assertEqual(5, summary.nb_articles)

    def test_apply_tracking_collection_with_tracking_service(self) -> None:
        tracking = Mock()

        PanierTransactionsService.apply_tracking_collection(
            "2026-03-06",
            [{"categorie": "EPICERIE", "prix": 100, "qte": 1}],
            db_manager=None,
            tracking_service=tracking,
        )

        tracking.apply_collection.assert_called_once()

    def test_apply_tracking_collection_without_tracking_service(self) -> None:
        db = Mock()
        db.get_daily_suivi_form.return_value = [
            {"categorie": "BOISSONS", "achats_ttc": 10, "ca_final": 100},
            {"categorie": DEFAULT_CATEGORY_NAME, "achats_ttc": 5, "ca_final": 20},
        ]

        PanierTransactionsService.apply_tracking_collection(
            "2026-03-06",
            [
                {"categorie": "BOISSONS", "prix": 100, "qte": 2},
                {"categorie": "-", "prix": 50, "qte": 1},
            ],
            db_manager=db,
            tracking_service=None,
        )

        db.save_daily_tracking_form_edits.assert_called_once()
        args, _ = db.save_daily_tracking_form_edits.call_args
        self.assertEqual("2026-03-06", args[0])
        by_cat = {row["categorie"]: row for row in args[1]}
        self.assertEqual(300, by_cat["BOISSONS"]["ca_final"])
        self.assertEqual(70, by_cat[DEFAULT_CATEGORY_NAME]["ca_final"])

    def test_build_helpers(self) -> None:
        sales_rows = PanierTransactionsService.build_sales_rows(
            [{"id": 1, "nom": "P", "qte": 2, "prix": 300}],
            day="2026-03-06",
            heure="12:00:00",
        )

        self.assertEqual(1, len(sales_rows))
        self.assertEqual(300, sales_rows[0]["prix_unitaire"])

        invoice = PanierTransactionsService.build_invoice_number(datetime(2026, 3, 6, 12, 34, 56))
        self.assertTrue(invoice.startswith("FACT-"))
        self.assertIn("20260306-123456", invoice)


if __name__ == "__main__":
    unittest.main()
