import tempfile
import unittest
from pathlib import Path

from core.database import DatabaseManager


class TestDatabaseManager(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        base_dir = Path(__file__).resolve().parent.parent
        schema_path = base_dir / "database" / "schema.sql"
        db_path = Path(self.tmpdir.name) / "test_app.db"
        self.db = DatabaseManager(db_path=str(db_path), schema_path=str(schema_path))

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _create_product_and_session(self) -> tuple[int, int]:
        self.db.upsert_products(
            [
                {
                    "id": 1,
                    "m3": 0,
                    "nom": "P TEST",
                    "categorie": "CAT TEST",
                    "pv": 1200,
                    "pa": 1000,
                    "b": 1,
                    "r": 0,
                    "dlv_dlc": "",
                }
            ]
        )
        _, session_id = self.db.open_db_session("Tester", "caissier")
        return 1, session_id

    def test_admin_pin_is_hashed_and_verifiable(self) -> None:
        raw = self.db.get_param("ADMIN_PIN")
        self.assertIsNotNone(raw)
        self.assertTrue(str(raw).startswith("pbkdf2_sha256$"))
        self.assertTrue(self.db.verify_admin_pin("1234"))
        self.assertFalse(self.db.verify_admin_pin("bad-pin"))

    def test_verify_admin_pin_migrates_legacy_clear_pin(self) -> None:
        self.db.set_parameter("ADMIN_PIN", "9999", "legacy clear pin")
        self.assertTrue(self.db.verify_admin_pin("9999"))
        migrated = self.db.get_param("ADMIN_PIN")
        self.assertIsNotNone(migrated)
        self.assertNotEqual(migrated, "9999")
        self.assertTrue(str(migrated).startswith("pbkdf2_sha256$"))

    def test_depenses_are_filtered_by_day_bounds(self) -> None:
        self.db.add_expense("A", 100, date_depense="2026-03-03 10:00:00")
        self.db.add_expense("B", 50, date_depense="2026-03-03 23:59:59")
        self.db.add_expense("C", 300, date_depense="2026-03-04 00:00:00")

        rows = self.db.list_daily_expenses("2026-03-03")
        total = self.db.total_daily_expenses("2026-03-03")

        self.assertEqual(2, len(rows))
        self.assertEqual(150, total)

    def test_ventes_are_filtered_by_day_bounds(self) -> None:
        product_id, session_id = self._create_product_and_session()
        with self.db._connect() as conn:
            conn.execute(
                """
                INSERT INTO ventes (jour, heure, produit_id, produit_nom, quantite, prix_unitaire, prix_total, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-03-03 10:00:00",
                    "10:00:00",
                    product_id,
                    "P TEST",
                    1,
                    1000,
                    1000,
                    session_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO ventes (jour, heure, produit_id, produit_nom, quantite, prix_unitaire, prix_total, session_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "2026-03-04 00:00:00",
                    "00:00:00",
                    product_id,
                    "P TEST",
                    1,
                    1000,
                    1000,
                    session_id,
                ),
            )

        rows = self.db.list_daily_sales("2026-03-03")
        self.assertEqual(1, len(rows))
        self.assertEqual("10:00:00", rows[0]["heure"])


if __name__ == "__main__":
    unittest.main()
