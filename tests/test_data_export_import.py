"""Tests for data export and import services."""

from __future__ import annotations

import json
import os
import tempfile
from unittest import TestCase
from unittest.mock import MagicMock


class TestDataExportService(TestCase):
    """Tests for DataExportService."""

    def setUp(self):
        self.db_manager = MagicMock()
        from services.data_export_service import DataExportService

        self.service = DataExportService(self.db_manager)

    def test_export_all_creates_json_file(self):
        """Export all should create a valid JSON file."""
        self.db_manager.list_products.return_value = [
            {
                "nom": "Produit A",
                "categorie": "BA",
                "pv": 1000,
                "pa": 500,
                "stock_boutique": 10,
                "stock_reserve": 5,
                "dlv_dlc": None,
                "description": None,
                "sku": None,
                "en_promo": 0,
                "prix_promo": 0,
            }
        ]
        self.db_manager.list_daily_sales.return_value = [
            {
                "jour": "2024-01-15",
                "heure": "10:30",
                "produit_id": 1,
                "produit_nom": "Produit A",
                "quantite": 2,
                "prix_unitaire": 1000,
                "prix_total": 2000,
            }
        ]
        self.db_manager.list_daily_expenses.return_value = [
            {
                "date_depense": "2024-01-15",
                "designation": "Transport",
                "valeur": 500,
                "remarque": "Taxi",
            }
        ]
        self.db_manager.get_daily_closure_by_category.return_value = [
            {"categorie": "BA", "ca_ttc_final": 5000}
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            counts = self.service.export_all(output_path, day="2024-01-15")

            with open(output_path, encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("metadata", data)
            self.assertIn("produits", data)
            self.assertIn("ventes", data)
            self.assertIn("depenses", data)
            self.assertIn("clotures", data)

            self.assertEqual(counts["produits"], 1)
            self.assertEqual(counts["ventes"], 1)
            self.assertEqual(counts["depenses"], 1)
            self.assertEqual(counts["clotures"], 1)

            self.assertEqual(data["produits"][0]["nom"], "Produit A")
            self.assertEqual(data["ventes"][0]["produit_nom"], "Produit A")
            self.assertEqual(data["depenses"][0]["designation"], "Transport")
            self.assertEqual(data["clotures"][0]["categorie"], "BA")

        finally:
            os.unlink(output_path)

    def test_export_all_empty_data(self):
        """Export all should handle empty data gracefully."""
        self.db_manager.list_products.return_value = []
        self.db_manager.list_daily_sales.return_value = []
        self.db_manager.list_daily_expenses.return_value = []
        self.db_manager.get_daily_closure_by_category.return_value = []

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            output_path = f.name

        try:
            counts = self.service.export_all(output_path, day="2024-01-15")

            self.assertEqual(counts["produits"], 0)
            self.assertEqual(counts["ventes"], 0)
            self.assertEqual(counts["depenses"], 0)
            self.assertEqual(counts["clotures"], 0)

        finally:
            os.unlink(output_path)


class TestDataImportService(TestCase):
    """Tests for DataImportService."""

    def setUp(self):
        self.db_manager = MagicMock()
        from services.data_import_service import DataImportService

        self.service = DataImportService(self.db_manager)

    def test_import_all_with_valid_file(self):
        """Import all should process valid JSON file."""
        export_data = {
            "metadata": {
                "export_date": "2024-01-15T10:00:00",
                "export_version": "1.0",
                "target_day": "2024-01-15",
                "record_counts": {"produits": 1, "ventes": 1, "depenses": 1, "clotures": 1},
            },
            "produits": [
                {
                    "nom": "Produit A",
                    "categorie": "BA",
                    "pv": 1000,
                    "pa": 500,
                    "stock_boutique": 10,
                    "stock_reserve": 5,
                    "dlv_dlc": None,
                    "description": None,
                    "sku": None,
                    "en_promo": 0,
                    "prix_promo": 0,
                }
            ],
            "ventes": [
                {
                    "jour": "2024-01-15",
                    "heure": "10:30",
                    "produit_id": 1,
                    "produit_nom": "Produit A",
                    "quantite": 2,
                    "prix_unitaire": 1000,
                    "prix_total": 2000,
                }
            ],
            "depenses": [
                {
                    "date_depense": "2024-01-15",
                    "designation": "Transport",
                    "valeur": 500,
                    "remarque": "Taxi",
                }
            ],
            "clotures": [{"jour": "2024-01-15", "categorie": "BA", "ca_ttc_final": 5000}],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(export_data, f)
            input_path = f.name

        try:
            self.db_manager.sessions.get_active_sessions.return_value = [{"id": 1}]

            result = self.service.import_all(input_path)

            self.db_manager.upsert_products.assert_called_once()
            self.db_manager.record_sale.assert_called_once()
            self.db_manager.add_expense.assert_called_once()
            self.db_manager.upsert_daily_closure_by_category.assert_called_once()

            self.assertEqual(result["imported"]["produits"], 1)
            self.assertEqual(result["imported"]["ventes"], 1)
            self.assertEqual(result["imported"]["depenses"], 1)
            self.assertEqual(result["imported"]["clotures"], 1)

        finally:
            os.unlink(input_path)

    def test_import_all_file_not_found(self):
        """Import all should raise FileNotFoundError for missing file."""
        with self.assertRaises(FileNotFoundError):
            self.service.import_all("/nonexistent/path/file.json")

    def test_import_all_invalid_format(self):
        """Import all should raise ValueError for invalid JSON format."""
        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump({"invalid": "data"}, f)
            input_path = f.name

        try:
            with self.assertRaises(ValueError):
                self.service.import_all(input_path)
        finally:
            os.unlink(input_path)

    def test_preview_import(self):
        """Preview should return file info without importing."""
        export_data = {
            "metadata": {"export_date": "2024-01-15T10:00:00", "export_version": "1.0"},
            "produits": [{"nom": "Produit A"}],
            "ventes": [{"produit_nom": "Produit A"}],
            "depenses": [{"designation": "Transport"}],
            "clotures": [{"categorie": "BA"}],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(export_data, f)
            input_path = f.name

        try:
            preview = self.service.preview_import(input_path)

            self.assertEqual(preview["counts"]["produits"], 1)
            self.assertEqual(preview["counts"]["ventes"], 1)
            self.assertEqual(preview["counts"]["depenses"], 1)
            self.assertEqual(preview["counts"]["clotures"], 1)
            self.assertIn("metadata", preview)
            self.assertIn("sample", preview)

        finally:
            os.unlink(input_path)

    def test_import_empty_lists(self):
        """Import should handle empty lists gracefully."""
        export_data = {
            "metadata": {"export_date": "2024-01-15T10:00:00", "export_version": "1.0"},
            "produits": [],
            "ventes": [],
            "depenses": [],
            "clotures": [],
        }

        with tempfile.NamedTemporaryFile(
            suffix=".json", mode="w", delete=False, encoding="utf-8"
        ) as f:
            json.dump(export_data, f)
            input_path = f.name

        try:
            result = self.service.import_all(input_path)

            self.assertEqual(result["imported"]["produits"], 0)
            self.assertEqual(result["imported"]["ventes"], 0)
            self.assertEqual(result["imported"]["depenses"], 0)
            self.assertEqual(result["imported"]["clotures"], 0)

        finally:
            os.unlink(input_path)
