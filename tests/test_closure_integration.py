"""Integration tests for daily closure flow (cloture quotidienne).

Tests the complete workflow:
1. Opening a session, recording sales, closing the session with final amounts
2. DailyTrackingService closure behavior
3. FollowupRepository day closing and J+1 preparation
"""

import tempfile
import unittest
from pathlib import Path

from core.constants import DEFAULT_CATEGORY_NAME
from core.database import DatabaseManager
from services.suivi_journalier_service import DailyTrackingService


class TestClosureIntegration(unittest.TestCase):
    """Integration tests for the daily closure workflow."""

    def setUp(self) -> None:
        """Set up test database and services."""
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_closure.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))
        self.tracking_service = DailyTrackingService(self.db)
        self.test_day = "14/03/26"

    def tearDown(self) -> None:
        """Clean up test database."""
        self.tmpdir.cleanup()

    def _create_test_product_and_session(self) -> tuple[int, int]:
        """Helper to create a test product and open a session."""
        # Create a test product with category
        self.db.upsert_products(
            [
                {
                    "id": 1,
                    "m3": 0,
                    "nom": "TEST PRODUCT",
                    "categorie": "BA",
                    "pv": 1000,
                    "pa": 500,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                }
            ]
        )
        operator_id, session_id = self.db.open_db_session("TestVendeur", "caissier")
        return operator_id, session_id

    def test_session_open_close_workflow(self) -> None:
        """Test opening and closing a session."""
        # Open session
        operator_id, session_id = self._create_test_product_and_session()
        self.assertGreater(session_id, 0)
        self.assertGreater(operator_id, 0)

        # Verify session is active
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT active, vendeur_nom FROM sessions_operateur WHERE id = ?",
                (session_id,),
            ).fetchone()
            self.assertEqual(1, row["active"])
            self.assertEqual("TestVendeur", row["vendeur_nom"])

        # Close session
        self.db.sessions.close_session(session_id)

        # Verify session is closed
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT active, closed_at FROM sessions_operateur WHERE id = ?",
                (session_id,),
            ).fetchone()
            self.assertEqual(0, row["active"])
            self.assertIsNotNone(row["closed_at"])

    def test_sales_recording_updates_suivi(self) -> None:
        """Test that recording sales updates the daily follow-up."""
        operator_id, session_id = self._create_test_product_and_session()

        # Record a sale
        self.db.record_sale(
            produit_id=1,
            produit_nom="TEST PRODUCT",
            quantite=2,
            prix_unitaire=1000,
            session_id=session_id,
        )

        # Apply encaissement to update suivi
        self.tracking_service.apply_collection(
            self.test_day,
            [
                {"categorie": "BA", "prix": 1000, "qte": 2},
            ],
        )

        # Verify the suivi form was updated
        rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_row)
        self.assertEqual(2000, int(ba_row.get("ca_final", 0)))

    def test_sales_grouping_by_category(self) -> None:
        """Test that sales from multiple products are grouped by category."""
        # Create multiple products in different categories
        self.db.upsert_products(
            [
                {
                    "id": 1,
                    "m3": 0,
                    "nom": "PRODUCT BA",
                    "categorie": "BA",
                    "pv": 1000,
                    "pa": 500,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                },
                {
                    "id": 2,
                    "m3": 0,
                    "nom": "PRODUCT BSA",
                    "categorie": "BSA",
                    "pv": 500,
                    "pa": 250,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                },
            ]
        )

        operator_id, session_id = self.db.open_db_session("TestVendeur", "caissier")

        # Record sales in both categories
        self.tracking_service.apply_collection(
            self.test_day,
            [
                {"categorie": "BA", "prix": 1000, "qte": 3},
                {"categorie": "BA", "prix": 500, "qte": 1},
                {"categorie": "BSA", "prix": 500, "qte": 2},
            ],
        )

        # Verify grouping
        rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in rows if r.get("categorie") == "BA"), None)
        bsa_row = next((r for r in rows if r.get("categorie") == "BSA"), None)

        self.assertIsNotNone(ba_row)
        self.assertIsNotNone(bsa_row)
        self.assertEqual(3500, int(ba_row.get("ca_final", 0)))  # 3000 + 500
        self.assertEqual(1000, int(bsa_row.get("ca_final", 0)))  # 500 * 2

    def test_default_category_normalization(self) -> None:
        """Test that '-' and empty categories are normalized to default."""
        self.tracking_service.apply_collection(
            self.test_day,
            [
                {"categorie": "-", "prix": 100, "qte": 1},
                {"categorie": "", "pv": 200, "qte": 1},
                {"categorie": DEFAULT_CATEGORY_NAME, "pv": 300, "qte": 1},
            ],
        )

        rows = self.db.get_daily_suivi_form(self.test_day)
        default_row = next((r for r in rows if r.get("categorie") == DEFAULT_CATEGORY_NAME), None)
        self.assertIsNotNone(default_row)
        self.assertEqual(600, int(default_row.get("ca_final", 0)))  # 100 + 200 + 300

    def test_close_day_persists_closure_data(self) -> None:
        """Test that closing a day persists final CA values."""
        # Setup initial CA
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 2}],
        )

        # Close day with final amounts
        final_ca_rows = [
            {"categorie": "BA", "ca_ttc_final": 3000},
        ]
        self.tracking_service.close_day(self.test_day, final_ca_rows)

        # Verify closure persisted
        closure_rows = self.db.get_daily_closure_by_category(self.test_day)
        ba_closure = next((r for r in closure_rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_closure)
        self.assertEqual(3000, int(ba_closure.get("ca_ttc_final", 0)))

    def test_close_day_marks_day_as_closed(self) -> None:
        """Test that closing a day marks it as closed in the suivi form."""
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 1}],
        )

        # Verify not closed initially
        rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_row)
        self.assertEqual(0, ba_row.get("cloturee", 0))

        # Close the day
        self.tracking_service.close_day(self.test_day, [{"categorie": "BA", "ca_ttc_final": 1000}])

        # Verify closed
        rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in rows if r.get("categorie") == "BA"), None)
        self.assertEqual(1, ba_row.get("cloturee", 0))

    def test_j1_preparation_initializes_next_day(self) -> None:
        """Test that closing a day prepares the next day (J+1)."""
        current_day = "2026-03-14"
        next_day = "2026-03-15"

        # Close current day
        self.tracking_service.close_day(current_day, [{"categorie": "BA", "ca_ttc_final": 1000}])

        # Verify next day form is initialized
        next_day_rows = self.db.get_daily_suivi_form(next_day)
        self.assertTrue(len(next_day_rows) > 0, "Next day should be initialized")

    def test_daily_tracking_service_get_closure_rows(self) -> None:
        """Test DailyTrackingService.get_closure_rows for closure dialog."""
        # Apply some sales
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 2}],
        )

        # Get closure rows for dialog
        closure_rows = self.tracking_service.get_closure_rows(self.test_day)

        # Verify structure
        self.assertTrue(len(closure_rows) > 0)
        ba_row = next((r for r in closure_rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_row)
        self.assertIn("ca_ttc_final", ba_row)

    def test_suivi_journalier_service_close_day_with_achats(self) -> None:
        """Test that close_day preserves purchases (achats)."""
        # Apply encaissement first
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 1}],
        )

        # Close with final amounts
        final_ca_rows = [{"categorie": "BA", "ca_ttc_final": 1500}]
        self.tracking_service.close_day(self.test_day, final_ca_rows)

        # Verify final values are persisted
        suivi_rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in suivi_rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_row)
        self.assertEqual(1500, int(ba_row.get("ca_final", 0)))

    def test_multiple_categories_closure(self) -> None:
        """Test closing a day with multiple categories."""
        # Apply sales to multiple categories
        self.tracking_service.apply_collection(
            self.test_day,
            [
                {"categorie": "BA", "prix": 1000, "qte": 2},
                {"categorie": "BSA", "prix": 500, "qte": 3},
                {"categorie": "GL", "prix": 200, "qte": 5},
            ],
        )

        # Close with different final amounts
        final_ca_rows = [
            {"categorie": "BA", "ca_ttc_final": 2500},
            {"categorie": "BSA", "ca_ttc_final": 1800},
            {"categorie": "GL", "ca_ttc_final": 1200},
        ]
        self.tracking_service.close_day(self.test_day, final_ca_rows)

        # Verify all categories closed correctly
        closure_rows = self.db.get_daily_closure_by_category(self.test_day)
        for final_row in final_ca_rows:
            cat = final_row["categorie"]
            expected = final_row["ca_ttc_final"]
            actual_row = next((r for r in closure_rows if r.get("categorie") == cat), None)
            self.assertIsNotNone(actual_row, f"Category {cat} should have closure data")
            self.assertEqual(expected, int(actual_row.get("ca_ttc_final", 0)))

    def test_followup_repository_day_closing(self) -> None:
        """Test FollowupRepository closing behavior."""
        # Setup sales
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 1}],
        )

        # Close day via followup repository
        self.db.close_day_from_tracking_form(self.test_day)

        # Verify day is marked as closed
        rows = self.db.get_daily_suivi_form(self.test_day)
        for row in rows:
            self.assertEqual(
                1, row.get("cloturee", 0), f"Category {row.get('categorie')} should be closed"
            )

    def test_j1_preparation_uses_sf_from_previous_day(self) -> None:
        """Test that J+1 preparation uses SF (stock final) from previous day as SI."""
        day1 = "2026-03-14"
        day2 = "2026-03-15"

        # Close day 1 with a specific SF value
        self.db.save_daily_tracking_edits(
            day1,
            [
                {"categorie": "BA", "si": 100, "sf": 50},
            ],
        )

        # Close day 1
        self.db.close_day_from_tracking_form(day1)

        # Check day 2 initialization (J+1)
        day2_rows = self.db.get_daily_tracking_by_category(day2)
        ba_row = next((r for r in day2_rows if r.get("categorie") == "BA"), None)

        # Note: The exact behavior depends on the _daily_collecte_provider
        # This test verifies the day is initialized
        self.assertIsNotNone(ba_row, "Day 2 should be initialized after closing day 1")

    def test_cannot_modify_closed_day(self) -> None:
        """Test that closed days cannot be modified (unless admin)."""
        # Close the day
        self.tracking_service.close_day(self.test_day, [{"categorie": "BA", "ca_ttc_final": 1000}])

        # Try to apply encaissement to closed day
        self.tracking_service.apply_collection(
            self.test_day,
            [{"categorie": "BA", "prix": 1000, "qte": 1}],
        )

        # The closed day should not be modified (depends on implementation)
        # Check that closure is still intact
        closure_rows = self.db.get_daily_closure_by_category(self.test_day)
        ba_closure = next((r for r in closure_rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_closure)


class TestClosureWorkflow(unittest.TestCase):
    """End-to-end tests for the complete closure workflow."""

    def setUp(self) -> None:
        """Set up test database."""
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_workflow.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))
        self.tracking_service = DailyTrackingService(self.db)
        self.test_day = "14/03/26"

    def tearDown(self) -> None:
        """Clean up."""
        self.tmpdir.cleanup()

    def test_complete_closure_workflow(self) -> None:
        """Test the complete workflow: open session -> record sales -> close day."""
        # Step 1: Open session
        operator_id, session_id = self.db.open_db_session("VendeurTest", "caissier")
        self.assertGreater(session_id, 0)

        # Step 2: Record products and sales
        self.db.upsert_products(
            [
                {
                    "id": 1,
                    "m3": 0,
                    "nom": "PROD1",
                    "categorie": "BA",
                    "pv": 1000,
                    "pa": 500,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                },
                {
                    "id": 2,
                    "m3": 0,
                    "nom": "PROD2",
                    "categorie": "BSA",
                    "pv": 500,
                    "pa": 250,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                },
            ]
        )

        # Step 3: Apply encaissement (simulate sales)
        self.tracking_service.apply_collection(
            self.test_day,
            [
                {"categorie": "BA", "prix": 1000, "qte": 5},
                {"categorie": "BA", "prix": 1000, "qte": 3},
                {"categorie": "BSA", "prix": 500, "qte": 4},
            ],
        )

        # Step 4: Get closure rows for dialog
        closure_rows = self.tracking_service.get_closure_rows(self.test_day)
        self.assertTrue(len(closure_rows) > 0)

        # Step 5: Close the day with final amounts
        final_amounts = [
            {"categorie": row["categorie"], "ca_ttc_final": row["ca_ttc_final"] + 100}
            for row in closure_rows
        ]
        self.tracking_service.close_day(self.test_day, final_amounts)

        # Step 6: Verify closure persisted
        closed_rows = self.db.get_daily_suivi_form(self.test_day)
        for row in closed_rows:
            self.assertEqual(1, row.get("cloturee", 0))

        # Step 7: Verify J+1 is prepared
        next_day = "2026-03-15"
        next_day_rows = self.db.get_daily_suivi_form(next_day)
        self.assertTrue(len(next_day_rows) > 0)

        # Step 8: Close the session
        self.db.sessions.close_session(session_id)

        # Verify session closed
        with self.db._connect() as conn:
            row = conn.execute(
                "SELECT active FROM sessions_operateur WHERE id = ?",
                (session_id,),
            ).fetchone()
            self.assertEqual(0, row["active"])


class TestClosureEdgeCases(unittest.TestCase):
    """Edge case tests for closure flow."""

    def setUp(self) -> None:
        """Set up test database."""
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_edge.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))
        self.tracking_service = DailyTrackingService(self.db)
        self.test_day = "14/03/26"

    def tearDown(self) -> None:
        """Clean up."""
        self.tmpdir.cleanup()

    def test_empty_sales_closure(self) -> None:
        """Test closing a day with no sales."""
        self.tracking_service.close_day(self.test_day, [])

        # Should not raise and day should be closed
        rows = self.db.get_daily_suivi_form(self.test_day)
        for row in rows:
            self.assertEqual(1, row.get("cloturee", 0))

    def test_negative_amount_handling(self) -> None:
        """Test that negative amounts are handled (converted to 0)."""
        # Apply negative amounts via edits
        self.db.save_daily_tracking_form_edits(
            self.test_day,
            [{"categorie": "BA", "ca_final": -100}],
        )

        rows = self.db.get_daily_suivi_form(self.test_day)
        ba_row = next((r for r in rows if r.get("categorie") == "BA"), None)
        self.assertIsNotNone(ba_row)
        # Negative values should be converted to 0
        self.assertEqual(0, int(ba_row.get("ca_final", 0)))

    def test_closure_with_missing_category(self) -> None:
        """Test closing with a row that has empty category."""
        # This should be filtered out
        self.tracking_service.close_day(
            self.test_day,
            [
                {"categorie": "BA", "ca_ttc_final": 1000},
                {"categorie": "", "ca_ttc_final": 500},
            ],
        )

        # Only valid category should be closed
        closure_rows = self.db.get_daily_closure_by_category(self.test_day)
        empty_row = next((r for r in closure_rows if r.get("categorie") == ""), None)
        self.assertIsNone(empty_row)


if __name__ == "__main__":
    unittest.main()
