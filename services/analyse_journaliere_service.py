"""Service metier pour les rapports SF et NFR base sur Tsf table."""

from __future__ import annotations

import contextlib
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from core.database import DatabaseManager

logger = logging.getLogger(__name__)


class AnalyseJournaliereService:
    """Service for SF/NFR reports using Tsf table."""

    _CATEGORY_1_NAME = "Catégorie 1 - OW (Owners)"

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def _validate_date_format(self, date_str: str) -> bool:
        """Vérifie si la date est au format YYYY-MM-DD pour éviter les crashs SQL."""
        try:
            datetime.strptime(str(date_str), "%Y-%m-%d")
            return True
        except (ValueError, TypeError):
            logger.error(f"Format de date invalide détecté : {date_str}")
            return False

    def get_sf_report(self, date_debut: str, date_fin: str) -> list[dict[str, Any]]:
        """SF Report using Tsf table (period-based aggregated data).

        Tsf table stores one row per category with:
        - si_ttc: SI from start of period (date_debut)
        - sf_ttc: SF from end of period (date_fin)
        - achats_ttc, ca_ttc, env_ttc: sums for the period
        - vente_theorique_ttc, marge_ttc: computed values
        """

        if not self._validate_date_format(date_debut) or not self._validate_date_format(date_fin):
            return []

        start = str(date_debut)
        end = str(date_fin)
        if end < start:
            start, end = end, start

        try:
            # Tsf already has aggregated data per category
            # just read from the table directly
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT 
                        c.nom AS sous_categorie,
                        t.si_ttc,
                        t.achats_ttc,
                        t.ca_ttc,
                        t.env_ttc,
                        t.sf_ttc,
                        t.vente_theorique_ttc,
                        t.marge_ttc,
                        t.marge_percent
                    FROM Tsf t
                    JOIN categories c ON t.categorie_id = c.id
                    ORDER BY c.nom
                """,
                ).fetchall()

                result = []
                for row in rows:
                    sous_cat = str(row["sous_categorie"])
                    si_ttc = int(row["si_ttc"] or 0)
                    achats_ttc = int(row["achats_ttc"] or 0)
                    ca_ttc = int(row["ca_ttc"] or 0)
                    env_ttc = int(row["env_ttc"] or 0)
                    sf_ttc = int(row["sf_ttc"] or 0)
                    vente_theo_ttc = int(row["vente_theorique_ttc"] or 0)
                    marge_ttc = int(row["marge_ttc"] or 0)
                    marge_percent = round(float(row["marge_percent"] or 0), 2)

                    result.append(
                        {
                            "jour": f"{start} - {end}",
                            "sous_categorie": sous_cat,
                            "si_ttc": si_ttc,
                            "achats_ttc": achats_ttc,
                            "ca_ttc": ca_ttc,
                            "env_ttc": env_ttc,
                            "demarque_ttc": env_ttc,
                            "sf_ttc": sf_ttc,
                            "vente_theo_ttc": vente_theo_ttc,
                            "marge_ttc": marge_ttc,
                            "marge_percent": marge_percent,
                        }
                    )
                return result

        except Exception as e:
            logger.error(f"Error in get_sf_report: {e}", exc_info=True)
            return []

    def get_sf_categories(self) -> list[str]:
        """Retourne les sous-categories avec gestion d'erreur."""
        try:
            with self._connect() as conn:
                query = """
                    SELECT c.nom AS sous_categorie
                    FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    ORDER BY c.nom
                """
                rows = conn.execute(query, (self._CATEGORY_1_NAME,)).fetchall()
                return [str(row["sous_categorie"]) for row in rows]
        except Exception as e:
            logger.error(f"Erreur get_sf_categories: {e}")
            return []

    def get_nfr_report(self, year: int, month: int) -> list[dict[str, Any]]:
        """NFR Report using Tcollecte for monthly data.

        NFR is computed monthly from Tcollecte directly.
        """
        try:
            # Compute month date range
            from datetime import date, timedelta

            start = date(year, month, 1)
            if month == 12:
                end = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end = date(year, month + 1, 1) - timedelta(days=1)
            month_start = start.strftime("%Y-%m-%d")
            month_end = end.strftime("%Y-%m-%d")

            with self._connect() as conn:
                # Query Tcollecte for monthly aggregation
                rows = conn.execute(
                    """
                    SELECT
                        c.nom AS categorie,
                        SUM(t.ca) AS ca_ttc,
                        SUM(t.vente_theorique) AS vente_theo,
                        SUM(t.marge) AS marge_ttc
                    FROM Tcollecte t
                    INNER JOIN categories c ON t.categorie_id = c.id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE t.jour BETWEEN ? AND ? AND parent.nom = ?
                    GROUP BY c.nom
                """,
                    (month_start, month_end, self._CATEGORY_1_NAME),
                ).fetchall()

                result = []
                for row in rows:
                    ca_ttc = int(row["ca_ttc"] or 0)
                    vente_theo = int(row["vente_theo"] or 0)
                    marge_ttc = int(row["marge_ttc"] or 0)
                    ca_ht = round(ca_ttc / 1.20, 2)
                    # NFR% = Marge / Vente
                    nfr_pct = round((marge_ttc / vente_theo) * 100, 2) if vente_theo > 0 else 0.0

                    result.append(
                        {
                            "categorie": str(row["categorie"]),
                            "ca_ht": ca_ht,
                            "ca_ttc": ca_ttc,
                            "marge": marge_ttc,
                            "marge_percent": nfr_pct,
                        }
                    )
                return result
        except Exception as e:
            logger.error(f"Error in get_nfr_report: {e}")
            return []

    def _connect(self) -> "contextlib.AbstractContextManager[sqlite3.Connection]":
        """Get a database connection."""
        return self.db_manager._connect()
