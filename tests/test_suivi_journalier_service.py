import unittest
from unittest.mock import Mock

from core.constants import DEFAULT_CATEGORY_NAME
from services.suivi_journalier_service import DailyTrackingService


class TestDailyTrackingService(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Mock()
        self.service = DailyTrackingService(self.db)

    def test_apply_collection_groups_and_normalizes_categories(self) -> None:
        self.db.get_daily_suivi_form.return_value = [
            {"categorie": "BOISSONS", "achats_ttc": 10, "ca_final": 100},
            {"categorie": DEFAULT_CATEGORY_NAME, "achats_ttc": 5, "ca_final": 20},
        ]

        self.service.apply_collection(
            "2026-03-03",
            [
                {"categorie": "BOISSONS", "prix": 100, "qte": 2},
                {"categorie": "BOISSONS", "prix": 50, "qte": 1},
                {"categorie": "-", "prix": 30, "qte": 1},
                {"categorie": "", "pv": 40, "qte": 1},
            ],
        )

        self.db.save_daily_tracking_form_edits.assert_called_once()
        args, _ = self.db.save_daily_tracking_form_edits.call_args
        self.assertEqual("2026-03-03", args[0])

        edits = {row["categorie"]: row for row in args[1]}
        self.assertEqual(350, edits["BOISSONS"]["ca_final"])
        self.assertEqual(90, edits[DEFAULT_CATEGORY_NAME]["ca_final"])

    def test_close_day_updates_followup_and_locks_day(self) -> None:
        self.db.get_daily_suivi_form.return_value = [
            {"categorie": "EPICERIE", "achats_ttc": 200, "ca_final": 500},
            {"categorie": "HYGIENE", "achats_ttc": 100, "ca_final": 250},
        ]

        final_rows = [
            {"categorie": "EPICERIE", "ca_ttc_final": 700},
            {"categorie": "HYGIENE", "ca_ttc_final": 300},
        ]
        self.service.close_day("2026-03-03", final_rows)

        self.db.upsert_daily_closure_by_category.assert_called_once_with("2026-03-03", final_rows)
        self.db.save_daily_tracking_form_edits.assert_called_once()
        self.db.close_day_from_tracking_form.assert_called_once_with("2026-03-03")

        args, _ = self.db.save_daily_tracking_form_edits.call_args
        edits = {row["categorie"]: row for row in args[1]}
        self.assertEqual(200, edits["EPICERIE"]["achats_ttc"])
        self.assertEqual(700, edits["EPICERIE"]["ca_final"])
        self.assertEqual(100, edits["HYGIENE"]["achats_ttc"])
        self.assertEqual(300, edits["HYGIENE"]["ca_final"])


if __name__ == "__main__":
    unittest.main()
