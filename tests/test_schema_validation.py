"""Tests de validation du schema SQL."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path


class TestSchemaValidation(unittest.TestCase):
    """Validation de l'integrite du schema SQL."""

    @classmethod
    def setUpClass(cls) -> None:
        """Charge le schema SQL une seule fois pour tous les tests."""
        cls.schema_path = cls._resolve_schema_path()
        cls.schema_sql = cls.schema_path.read_text(encoding="utf-8")

    @staticmethod
    def _resolve_schema_path() -> Path:
        """Resout le chemin vers schema.sql depuis tests/ ou app/."""
        candidates = [
            Path(__file__).resolve().parent.parent / "database" / "schema.sql",
            Path(__file__).resolve().parent / "database" / "schema.sql",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        raise FileNotFoundError("schema.sql introuvable")

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_schema.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(self.schema_sql)

    def tearDown(self) -> None:
        self.conn.close()
        self.temp_dir.cleanup()

    # -- Tests de presence des tables --

    def test_all_expected_tables_exist(self) -> None:
        expected_tables = {
            "operateurs",
            "sessions_operateur",
            "categories",
            "fournisseurs",
            "parametres",
            "produits",
            "depenses",
            "ventes",
            "mouvements_stock",
            "historique_produits_enleves",
            "clotures_caisse",
            "clotures_caisse_categories",
            "analyse_journaliere_categories",
            "achats",
            "achats_lignes",
            "audit_admin_actions",
            "suivi_journalier_categories",
            "suivi_formulaire_journalier",
        }
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
        ).fetchall()
        actual_tables = {row["name"] for row in rows}
        self.assertEqual(actual_tables, expected_tables)

    # -- Tests des contraintes CHECK --

    def test_ventes_quantite_positive(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO ventes (jour, heure, produit_id, produit_nom, "
                "quantite, prix_unitaire, prix_total, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", "10:00", 1, "Test", 0, 100, 100, 1),
            )

    def test_depenses_valeur_non_negative(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO depenses (date_depense, designation, valeur) " "VALUES (?, ?, ?)",
                ("2026-01-01", "Test", -1),
            )

    def test_ventes_prix_unitaire_non_negatif(self) -> None:
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO ventes (jour, heure, produit_id, produit_nom, "
                "quantite, prix_unitaire, prix_total, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", "10:00", 1, "Test", 1, -1, 1, 1),
            )

    # -- Tests des donnees seed --

    def test_seed_categories_exist(self) -> None:
        rows = self.conn.execute("SELECT nom FROM categories ORDER BY id").fetchall()
        noms = [row["nom"] for row in rows]
        self.assertIn("Catégorie 1 - OW (Owners)", noms)
        self.assertIn("Catégorie 2 - NOW (Not owners)", noms)
        self.assertIn("Catégorie 3 - NONE", noms)

    def test_seed_tva_param_exists(self) -> None:
        row = self.conn.execute(
            "SELECT valeur FROM parametres WHERE cle = ?", ("TVA_TAUX",)
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["valeur"], "20.00")

    # -- Tests des indexes --

    def test_expected_indexes_exist(self) -> None:
        expected_indexes = {
            "idx_ventes_jour",
            "idx_ventes_session",
            "idx_depenses_date",
            "idx_clotures_caisse_jour",
            "idx_produits_categorie",
            "idx_mouvements_stock_jour",
            "idx_mouvements_stock_produit",
            "idx_achats_jour",
            "idx_achats_lignes_achat",
            "idx_historique_enleves_jour",
            "idx_fournisseurs_nom",
            "idx_suivi_journalier_categories_jour",
            "idx_analyse_journaliere_categories_jour",
            "idx_ventes_jour_heure",
        }
        rows = self.conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        actual_indexes = {row["name"] for row in rows}
        for idx in expected_indexes:
            self.assertIn(idx, actual_indexes)

    # -- Tests de l'idempotence du schema --

    def test_schema_is_idempotent(self) -> None:
        """Re-executer le schema ne doit pas lever d'erreur."""
        self.conn.executescript(self.schema_sql)
        # Les categories seed doivent toujours etre presentes (pas de doublons)
        rows = self.conn.execute("SELECT COUNT(*) as cnt FROM categories").fetchone()
        self.assertEqual(rows["cnt"], 18)  # 3 top + 10 Cat1 + 3 Cat2 + 2 Cat3

    # -- Tests des colonnes cles --

    def test_produits_has_promo_columns(self) -> None:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(produits)").fetchall()}
        self.assertIn("en_promo", columns)
        self.assertIn("prix_promo", columns)

    def test_parametres_has_updated_at(self) -> None:
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(parametres)").fetchall()}
        self.assertIn("updated_at", columns)

    def test_mouvements_stock_quantite_positive(self) -> None:
        """CHECK constraint: mouvements_stock.quantite > 0."""
        # Create prerequisite rows for foreign keys
        self.conn.execute(
            "INSERT INTO operateurs (nom, droit_acces) VALUES (?, ?)",
            ("TestOp", "admin"),
        )
        self.conn.execute(
            "INSERT INTO sessions_operateur (operateur_id, vendeur_nom) " "VALUES (?, ?)",
            (1, "TestVend"),
        )
        self.conn.execute(
            "INSERT INTO produits (nom, categorie_id) VALUES (?, ?)",
            ("TestProd", None),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO mouvements_stock "
                "(jour, produit_id, type_mouvement, quantite, valeur, "
                "stock_boutique_avant, stock_boutique_apres, "
                "stock_reserve_avant, stock_reserve_apres, "
                "operateur_id, session_id, vendeur_nom) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", 1, "RB", 0, 0, 10, 5, 0, 0, 1, 1, "Test"),
            )

    def test_mouvements_stock_type_mouvement_valid(self) -> None:
        """CHECK constraint: type_mouvement must be one of RB, BR, EB, ER, ENV."""
        # Create prerequisite rows for foreign keys
        self.conn.execute(
            "INSERT INTO operateurs (nom, droit_acces) VALUES (?, ?)",
            ("TestOp", "admin"),
        )
        self.conn.execute(
            "INSERT INTO sessions_operateur (operateur_id, vendeur_nom) " "VALUES (?, ?)",
            (1, "TestVend"),
        )
        self.conn.execute(
            "INSERT INTO produits (nom, categorie_id) VALUES (?, ?)",
            ("TestProd", None),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO mouvements_stock "
                "(jour, produit_id, type_mouvement, quantite, valeur, "
                "stock_boutique_avant, stock_boutique_apres, "
                "stock_reserve_avant, stock_reserve_apres, "
                "operateur_id, session_id, vendeur_nom) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", 1, "INVALID", 1, 0, 10, 9, 0, 0, 1, 1, "Test"),
            )

    def test_achats_lignes_quantite_non_negative(self) -> None:
        """CHECK constraint: achats_lignes.quantite >= 0."""
        # Create prerequisite rows for foreign keys
        self.conn.execute("INSERT INTO fournisseurs (nom) VALUES (?)", ("TestFournisseur",))
        self.conn.execute("INSERT INTO achats (fournisseur_id) VALUES (?)", (1,))
        self.conn.execute(
            "INSERT INTO produits (nom, categorie_id) VALUES (?, ?)", ("TestProd", None)
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO achats_lignes "
                "(achat_id, produit_id, quantite, pa_unitaire, "
                "prc_unitaire, pv_unitaire, total_ttc) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (1, 1, -1, 100, 100, 100, 0),
            )

    def test_clotures_caisse_ca_non_negative(self) -> None:
        """CHECK constraint: clotures_caisse.ca_ttc_final >= 0."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO clotures_caisse (jour, ca_ttc_final) VALUES (?, ?)",
                ("2026-01-01", -1),
            )

    def test_foreign_keys_are_enforced(self) -> None:
        """PRAGMA foreign_keys = ON must reject invalid FK references."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO ventes (jour, heure, produit_id, produit_nom, "
                "quantite, prix_unitaire, prix_total, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", "10:00", 99999, "Ghost", 1, 100, 100, 99999),
            )

    def test_historique_enleves_raison_valid(self) -> None:
        """CHECK constraint: raison must be 'abime' or 'perime'."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO historique_produits_enleves "
                "(jour, nom, categorie, quantite, valeur, raison, "
                "operateur_id, session_id, vendeur_nom) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", "Test", "Cat", 1, 100, "invalid", 1, 1, "Test"),
            )

    def test_ventes_prix_total_non_negative(self) -> None:
        """CHECK constraint: ventes.prix_total >= 0."""
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO ventes (jour, heure, produit_id, produit_nom, "
                "quantite, prix_unitaire, prix_total, session_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                ("2026-01-01", "10:00", 1, "Test", 1, 100, -1, 1),
            )

    def test_operateurs_has_required_columns(self) -> None:
        """La table operateurs doit avoir les colonnes essentielles."""
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(operateurs)").fetchall()}
        for col in ("id", "nom", "droit_acces", "actif", "created_at"):
            self.assertIn(col, columns)


if __name__ == "__main__":
    unittest.main()
