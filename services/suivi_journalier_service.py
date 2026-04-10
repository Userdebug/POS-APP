"""Service metier pour le suivi journalier et la cloture de caisse."""

from __future__ import annotations

import logging
from typing import Any

from core.constants import DATE_FORMAT_DAY, DEFAULT_CATEGORY_NAME
from core.database import DatabaseManager

logger = logging.getLogger(__name__)


class DailyTrackingService:
    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def get_tracking_rows(self, jour: str) -> list[dict[str, Any]]:
        return self.db_manager.get_daily_suivi_form(jour)

    def get_closure_rows(self, jour: str) -> list[dict[str, Any]]:
        tracking_rows = self.get_tracking_rows(jour)
        existing_map = {
            str(r.get("categorie", "")): int(r.get("ca_ttc_final", 0) or 0)
            for r in self.db_manager.get_daily_closure_by_category(jour)
        }
        dialog_rows: list[dict[str, Any]] = []
        for row in tracking_rows:
            categorie = str(row.get("categorie", "")).strip()
            if not categorie:
                continue
            dialog_rows.append(
                {
                    "categorie": categorie,
                    "ca_ttc_final": int(existing_map.get(categorie, row.get("ca_final", 0) or 0)),
                }
            )
        return dialog_rows

    def apply_collection(self, jour: str, basket_rows: list[dict[str, Any]]) -> None:
        if not basket_rows:
            return
        current_rows = self.get_tracking_rows(jour)
        current_map = {str(r.get("categorie", "")): dict(r) for r in current_rows}
        increments: dict[str, int] = {}
        for ligne in basket_rows:
            categorie = str(ligne.get("categorie", "")).strip()
            if not categorie or categorie == "-":
                categorie = DEFAULT_CATEGORY_NAME
            montant = int(ligne.get("prix", ligne.get("pv", 0)) or 0) * int(
                ligne.get("qte", 1) or 1
            )
            increments[categorie] = increments.get(categorie, 0) + max(0, montant)
        edits: list[dict[str, Any]] = []
        for categorie, montant in increments.items():
            base = current_map.get(categorie, {})
            edits.append(
                {
                    "categorie": categorie,
                    "achats_ttc": int(base.get("achats_ttc", 0) or 0),
                    "ca_final": int(base.get("ca_final", 0) or 0) + int(montant),
                }
            )
        if edits:
            self.db_manager.save_daily_tracking_form_edits(jour, edits)

    def close_day(self, jour: str, final_ca_rows: list[dict[str, Any]]) -> None:
        self.db_manager.upsert_daily_closure_by_category(jour, final_ca_rows)
        current_tracking_rows = self.get_tracking_rows(jour)
        purchases_map = {
            str(r.get("categorie", "")): int(r.get("achats_ttc", 0) or 0)
            for r in current_tracking_rows
        }
        edits = []
        for row in final_ca_rows:
            cat = str(row.get("categorie", "")).strip()
            if not cat:
                continue
            edits.append(
                {
                    "categorie": cat,
                    "achats_ttc": purchases_map.get(cat, 0),
                    "ca_final": int(row.get("ca_ttc_final", 0) or 0),
                }
            )
        if edits:
            self.db_manager.save_daily_tracking_form_edits(jour, edits)
        self.db_manager.close_day_from_tracking_form(jour)

    def create_next_day(self, jour: str, ca_final_value: int) -> str:
        """Create a new day initialized with the previous day's CA final value.

        Args:
            jour: The current day (ISO format YYYY-MM-DD).
            ca_final_value: The CA final value to initialize for the new day.

        Returns:
            The new day's date in ISO format.
        """
        from datetime import datetime, timedelta

        # Calculate next day
        for fmt in ["%d/%m/%y", "%Y-%m-%d"]:
            try:
                current_date = datetime.strptime(jour, fmt)
                next_day = current_date + timedelta(days=1)
                next_day_str = next_day.strftime(DATE_FORMAT_DAY)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Unable to parse date: {jour}")

        # Get categories from current day
        current_rows = self.get_tracking_rows(jour)

        # Create edits for next day with CA final initialized
        edits = []
        for row in current_rows:
            categorie = str(row.get("categorie", "")).strip()
            if not categorie:
                continue
            edits.append(
                {
                    "categorie": categorie,
                    "achats_ttc": 0,  # New day starts with 0 purchases
                    "ca_final": ca_final_value,  # Initialize with previous day's CA
                }
            )

        if edits:
            self.db_manager.save_daily_tracking_form_edits(next_day_str, edits)

        logger.info(
            "Created next day %s with CA final initialized to %d", next_day_str, ca_final_value
        )
        return next_day_str
