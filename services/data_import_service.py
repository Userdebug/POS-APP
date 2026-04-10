"""Data import service for importing products, sales, and expenses from JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

IMPORT_VERSION = "1.0"


class DataImportService:
    """Service for importing database data from JSON format.

    Args:
        db_manager: Database manager instance.
    """

    def __init__(self, db_manager: Any) -> None:
        self._db_manager = db_manager

    def import_all(self, input_path: str | Path) -> dict[str, Any]:
        """Import all data from JSON file.

        Args:
            input_path: Path to the input JSON file.

        Returns:
            Dictionary with import statistics.

        Raises:
            FileNotFoundError: If the input file does not exist.
            ValueError: If the JSON format is invalid.
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {input_path}")

        with open(input_file, encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if "metadata" not in data or "produits" not in data:
            raise ValueError("Format JSON invalide: données manquantes")

        import_result = {
            "imported": {},
            "errors": [],
        }

        # Import products (upsert by nom)
        try:
            products_imported = self._import_products(data.get("produits", []))
            import_result["imported"]["produits"] = products_imported
        except Exception as e:
            logger.exception("Error importing products")
            import_result["errors"].append(f"produits: {str(e)}")

        # Import sales (append)
        try:
            sales_imported = self._import_sales(data.get("ventes", []))
            import_result["imported"]["ventes"] = sales_imported
        except Exception as e:
            logger.exception("Error importing sales")
            import_result["errors"].append(f"ventes: {str(e)}")

        # Import expenses (append)
        try:
            expenses_imported = self._import_expenses(data.get("depenses", []))
            import_result["imported"]["depenses"] = expenses_imported
        except Exception as e:
            logger.exception("Error importing expenses")
            import_result["errors"].append(f"depenses: {str(e)}")

        # Import closures
        try:
            closures_imported = self._import_closures(data.get("clotures", []))
            import_result["imported"]["clotures"] = closures_imported
        except Exception as e:
            logger.exception("Error importing closures")
            import_result["errors"].append(f"clotures: {str(e)}")

        logger.info(
            f"Imported from {input_path}: "
            f"{import_result['imported'].get('produits', 0)} products, "
            f"{import_result['imported'].get('ventes', 0)} sales, "
            f"{import_result['imported'].get('depenses', 0)} expenses"
        )

        return import_result

    def preview_import(self, input_path: str | Path) -> dict[str, Any]:
        """Preview what will be imported without committing changes.

        Args:
            input_path: Path to the input JSON file.

        Returns:
            Dictionary with preview information.
        """
        input_file = Path(input_path)
        if not input_file.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {input_path}")

        with open(input_file, encoding="utf-8") as f:
            data = json.load(f)

        preview = {
            "metadata": data.get("metadata", {}),
            "counts": {
                "produits": len(data.get("produits", [])),
                "ventes": len(data.get("ventes", [])),
                "depenses": len(data.get("depenses", [])),
                "clotures": len(data.get("clotures", [])),
            },
            "sample": {
                "produits": data.get("produits", [])[:3],
                "ventes": data.get("ventes", [])[:3],
                "depenses": data.get("depenses", [])[:3],
            },
        }

        return preview

    def _import_products(self, produits: list[dict[str, Any]]) -> int:
        """Import products using upsert (by nom).

        Args:
            produits: List of product dictionaries.

        Returns:
            Number of products imported.
        """
        if not produits:
            return 0

        products_to_upsert = []
        for p in produits:
            nom = p.get("nom", "").strip()
            if not nom:
                continue

            products_to_upsert.append(
                {
                    "nom": nom,
                    "pv": int(p.get("pv", 0) or 0),
                    "pa": int(p.get("pa", 0) or 0),
                    "stock_boutique": int(p.get("stock_boutique", 0) or 0),
                    "stock_reserve": int(p.get("stock_reserve", 0) or 0),
                    "dlv_dlc": p.get("dlv_dlc"),
                    "description": p.get("description"),
                    "sku": p.get("sku"),
                    "en_promo": int(p.get("en_promo", 0) or 0),
                    "prix_promo": int(p.get("prix_promo", 0) or 0),
                }
            )

        if products_to_upsert:
            self._db_manager.upsert_products(products_to_upsert)

        return len(products_to_upsert)

    def _import_sales(self, ventes: list[dict[str, Any]]) -> int:
        """Import sales by appending (no duplicate check).

        Args:
            ventes: List of sale dictionaries.

        Returns:
            Number of sales imported.
        """
        if not ventes:
            return 0

        # For sales, we need to get the current session or create one
        # Get active session or use a dummy one for import
        try:
            sessions = list(self._db_manager.sessions.get_active_sessions())
            if sessions:
                session_id = sessions[0].get("id")
            else:
                # Open a system session for imports
                session_id, _ = self._db_manager.open_db_session("system_import", "admin")
        except Exception:
            session_id = 1  # Fallback

        imported = 0
        for v in ventes:
            try:
                self._db_manager.record_sale(
                    produit_id=int(v.get("produit_id", 0) or 0),
                    produit_nom=str(v.get("produit_nom", "")),
                    quantite=int(v.get("quantite", 0) or 0),
                    prix_unitaire=int(v.get("prix_unitaire", 0) or 0),
                    session_id=session_id,
                )
                imported += 1
            except Exception as e:
                logger.warning(f"Skipping sale import error: {e}")
                continue

        return imported

    def _import_expenses(self, depenses: list[dict[str, Any]]) -> int:
        """Import expenses by appending.

        Args:
            depenses: List of expense dictionaries.

        Returns:
            Number of expenses imported.
        """
        imported = 0
        for d in depenses:
            try:
                self._db_manager.add_expense(
                    designation=str(d.get("designation", "")),
                    valeur=int(d.get("valeur", 0) or 0),
                    remarque=d.get("remarque"),
                    date_depense=d.get("date_depense"),
                )
                imported += 1
            except Exception as e:
                logger.warning(f"Skipping expense import error: {e}")
                continue

        return imported

    def _import_closures(self, clotures: list[dict[str, Any]]) -> int:
        """Import closure data.

        Args:
            clotures: List of closure dictionaries.

        Returns:
            Number of closures imported.
        """
        if not clotures:
            return 0

        values = []
        for c in clotures:
            values.append(
                {
                    "categorie": c.get("categorie", ""),
                    "ca_ttc_final": int(c.get("ca_ttc_final", 0) or 0),
                }
            )

        if values:
            # Get the day from the first closure or use today
            jour = clotures[0].get("jour", "")
            if not jour:
                from datetime import datetime

                from core.constants import DATE_FORMAT_DAY

                jour = datetime.now().strftime(DATE_FORMAT_DAY)

            self._db_manager.upsert_daily_closure_by_category(jour, values)

        return len(values)
