"""Data export service for exporting products, sales, and expenses to JSON."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.constants import DATE_FORMAT_DAY

logger = logging.getLogger(__name__)

EXPORT_VERSION = "1.0"


class DataExportService:
    """Service for exporting database data to JSON format.

    Args:
        db_manager: Database manager instance.
    """

    def __init__(self, db_manager: Any) -> None:
        self._db_manager = db_manager

    def export_all(
        self,
        output_path: str | Path,
        day: str | None = None,
    ) -> dict[str, Any]:
        """Export all data to JSON file.

        Args:
            output_path: Path to the output JSON file.
            day: Optional day in ISO format (YYYY-MM-DD) to filter sales/expenses.
                 If None, exports all data.

        Returns:
            Dictionary with export metadata and statistics.
        """
        target_day = day or datetime.now().strftime(DATE_FORMAT_DAY)

        # Collect data
        produits = self._export_products()
        ventes = self._export_sales(target_day)
        depenses = self._export_expenses(target_day)
        clotures = self._export_closures(target_day)

        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "export_version": EXPORT_VERSION,
                "target_day": target_day,
                "record_counts": {
                    "produits": len(produits),
                    "ventes": len(ventes),
                    "depenses": len(depenses),
                    "clotures": len(clotures),
                },
            },
            "produits": produits,
            "ventes": ventes,
            "depenses": depenses,
            "clotures": clotures,
        }

        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(
            f"Exported to {output_path}: "
            f"{len(produits)} products, {len(ventes)} sales, {len(depenses)} expenses"
        )

        return export_data["metadata"]["record_counts"]

    def _export_products(self) -> list[dict[str, Any]]:
        """Export all products."""
        produits = self._db_manager.list_products()
        result = []

        for p in produits:
            result.append(
                {
                    "nom": p.get("nom"),
                    "categorie": p.get("categorie"),
                    "pv": p.get("pv"),
                    "pa": p.get("pa"),
                    "stock_boutique": p.get("stock_boutique"),
                    "stock_reserve": p.get("stock_reserve"),
                    "dlv_dlc": p.get("dlv_dlc"),
                    "description": p.get("description"),
                    "sku": p.get("sku"),
                    "en_promo": p.get("en_promo"),
                    "prix_promo": p.get("prix_promo"),
                }
            )

        return result

    def _export_sales(self, day: str) -> list[dict[str, Any]]:
        """Export sales for a specific day."""
        ventes = self._db_manager.list_daily_sales(day)
        result = []

        for v in ventes:
            result.append(
                {
                    "jour": v.get("jour"),
                    "heure": v.get("heure"),
                    "produit_id": v.get("produit_id"),
                    "produit_nom": v.get("produit_nom"),
                    "quantite": v.get("quantite"),
                    "prix_unitaire": v.get("prix_unitaire"),
                    "prix_total": v.get("prix_total"),
                }
            )

        return result

    def _export_expenses(self, day: str) -> list[dict[str, Any]]:
        """Export expenses for a specific day."""
        depenses = self._db_manager.list_daily_expenses(day)
        result = []

        for d in depenses:
            result.append(
                {
                    "date_depense": d.get("date_depense"),
                    "designation": d.get("designation"),
                    "valeur": d.get("valeur"),
                    "remarque": d.get("remarque"),
                }
            )

        return result

    def _export_closures(self, day: str) -> list[dict[str, Any]]:
        """Export closure data for a specific day."""
        clotures = self._db_manager.get_daily_closure_by_category(day)
        result = []

        for c in clotures:
            result.append(
                {
                    "jour": day,
                    "categorie": c.get("categorie"),
                    "ca_ttc_final": c.get("ca_ttc_final"),
                }
            )

        return result
