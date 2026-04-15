"""Service metier pour les rapports SF et NFR base sur analyse_journaliere_categories."""

from __future__ import annotations

import contextlib
import logging
import sqlite3
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from core.database import DatabaseManager

# Configuration du logging pour attraper les erreurs silencieuses
logger = logging.getLogger(__name__)


class AnalyseJournaliereService:
    """Service pour gerer les rapports analytiques base sur le suivi journalier."""

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
        """Rapport SF sécurisé contre les erreurs de format et de types."""

        # 1. Validation de sécurité : évite d'envoyer n'importe quoi au driver C++
        if not self._validate_date_format(date_debut) or not self._validate_date_format(date_fin):
            return []

        start = str(date_debut)
        end = str(date_fin)
        if end < start:
            start, end = end, start

        try:
            with self._connect() as conn:
                # Utilisation de row_factory pour s'assurer que l'accès par nom est sûr
                conn.row_factory = sqlite3.Row

                # --- SI Query ---
                si_query = """
                    SELECT c.nom AS sous_categorie, a.si AS si_ttc
                    FROM analyse_journaliere_categories a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE a.jour = ? AND parent.nom = ?
                """
                si_rows = conn.execute(si_query, (start, self._CATEGORY_1_NAME)).fetchall()
                si_map = {str(row["sous_categorie"]): float(row["si_ttc"] or 0) for row in si_rows}

                # --- SF Query ---
                sf_query = """
                    SELECT c.nom AS sous_categorie, a.sf AS sf_ttc
                    FROM analyse_journaliere_categories a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE a.jour = ? AND parent.nom = ?
                """
                sf_rows = conn.execute(sf_query, (end, self._CATEGORY_1_NAME)).fetchall()
                sf_map = {str(row["sous_categorie"]): float(row["sf_ttc"] or 0) for row in sf_rows}

                # --- Aggr Query ---
                aggr_query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM(a.achats) AS achats_ttc,
                        SUM(a.ca) AS ca_ttc,
                        SUM(a.ca_temporaire) AS ca_temporaire,
                        SUM(a.env) AS env_ttc,
                        SUM(a.vente_theorique) AS vente_theo_ttc,
                        SUM(a.marge) AS marge_ttc
                    FROM analyse_journaliere_categories a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE a.jour BETWEEN ? AND ? AND parent.nom = ?
                    GROUP BY c.nom
                """
                aggr_rows = conn.execute(aggr_query, (start, end, self._CATEGORY_1_NAME)).fetchall()

                # --- Demarque Query ---
                demarque_query = """
                    SELECT categorie, SUM(valeur) AS demarque
                    FROM historique_produits_enleves
                    WHERE jour BETWEEN ? AND ?
                    GROUP BY categorie
                """
                demarque_rows = conn.execute(demarque_query, (start, end)).fetchall()
                demarque_map = {
                    str(row["categorie"]): float(row["demarque"] or 0) for row in demarque_rows
                }

                result: list[dict[str, Any]] = []
                for row in aggr_rows:
                    sous_cat = str(row["sous_categorie"])
                    ca = float(row["ca_ttc"] or 0)
                    ca_temporaire = (
                        float(row["ca_temporaire"]) if "ca_temporaire" in row.keys() else 0.0
                    )
                    ca_temporaire = ca_temporaire or 0.0
                    if ca == 0:
                        ca = ca_temporaire
                    vente_theo = float(row["vente_theo_ttc"] or 0)
                    marge = vente_theo - ca

                    # Calcul sécurisé du pourcentage (évite DivisionByZero)
                    marge_percent = round((marge / ca) * 100, 2) if ca > 0 else 0.0

                    result.append(
                        {
                            "jour": f"{start} - {end}",
                            "sous_categorie": sous_cat,
                            "si_ttc": si_map.get(sous_cat, 0.0),
                            "achats_ttc": float(row["achats_ttc"] or 0),
                            "ca_ttc": ca,
                            "env_ttc": float(row["env_ttc"] or 0),
                            "demarque_ttc": demarque_map.get(sous_cat, 0.0),
                            "sf_ttc": sf_map.get(sous_cat, 0.0),
                            "vente_theo_ttc": float(row["vente_theo_ttc"] or 0),
                            "marge_ttc": marge,
                            "marge_percent": marge_percent,
                        }
                    )
                return result

        except Exception as e:
            logger.critical(f"Erreur fatale dans get_sf_report: {e}", exc_info=True)
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
        """Rapport NFR sécurisé."""
        try:
            month_start = f"{year:04d}-{month:02d}-01"
            # Fin du mois simplifiée pour SQL
            month_end = f"{year:04d}-{month:02d}-31"

            with self._connect() as conn:
                query = """
                    SELECT
                        c.nom AS categorie,
                        SUM(ac.ca) AS ca_ttc,
                        SUM(ac.marge) AS marge
                    FROM analyse_journaliere_categories ac
                    INNER JOIN categories c ON c.id = ac.categorie_id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE ac.jour BETWEEN ? AND ? AND parent.nom = ?
                    GROUP BY c.nom
                """
                rows = conn.execute(
                    query, (month_start, month_end, self._CATEGORY_1_NAME)
                ).fetchall()

                result = []
                for row in rows:
                    ca_ttc = float(row["ca_ttc"] or 0)
                    marge = float(row["marge"] or 0)
                    ca_ht = round(ca_ttc / 1.20, 2)
                    m_percent = round((marge / ca_ttc) * 100, 2) if ca_ttc > 0 else 0.0

                    result.append(
                        {
                            "categorie": str(row["categorie"]),
                            "ca_ht": ca_ht,
                            "ca_ttc": ca_ttc,
                            "marge": marge,
                            "marge_percent": m_percent,
                        }
                    )
                return result
        except Exception as e:
            logger.error(f"Erreur get_nfr_report: {e}")
            return []

    def _connect(self) -> "contextlib.AbstractContextManager[sqlite3.Connection]":
        """Get a database connection."""
        return self.db_manager._connect()

    def compute_temporary_ca(self, jour: str) -> dict[str, int]:
        """Compute temporary CA from sales for a given day using PA * 1.2.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            Dictionary mapping category names to temporary CA values.
        """
        if not self._validate_date_format(jour):
            return {}

        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM(v.quantite * CAST(ROUND(p.pa * 1.2, 0) AS INTEGER)) AS ca_temporaire
                    FROM ventes v
                    JOIN produits p ON v.produit_id = p.id
                    JOIN categories c ON p.categorie_id = c.id
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE v.jour = ? AND v.deleted = 0 AND parent.nom = ?
                    GROUP BY c.nom
                """
                rows = conn.execute(query, (jour, self._CATEGORY_1_NAME)).fetchall()

                return {str(row["sous_categorie"]): int(row["ca_temporaire"] or 0) for row in rows}

        except Exception as e:
            logger.error(f"Erreur compute_temporary_ca pour {jour}: {e}", exc_info=True)
            return {}

    def update_temporary_ca(self, jour: str) -> None:
        """Compute and update temporary CA from sales for a given day.

        Creates rows in analyse_journaliere_categories if they don't exist.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).
        """
        if not self._validate_date_format(jour):
            return

        ca_by_category = self.compute_temporary_ca(jour)
        if not ca_by_category:
            return

        try:
            with self._connect() as conn:
                for categorie_nom, ca_temporaire in ca_by_category.items():
                    cat_id_row = conn.execute(
                        "SELECT id FROM categories WHERE nom = ?", (categorie_nom,)
                    ).fetchone()

                    if not cat_id_row:
                        continue

                    categorie_id = cat_id_row["id"]

                    existing = conn.execute(
                        "SELECT id FROM analyse_journaliere_categories WHERE jour = ? AND categorie_id = ?",
                        (jour, categorie_id),
                    ).fetchone()

                    if existing:
                        conn.execute(
                            "UPDATE analyse_journaliere_categories SET ca_temporaire = ? WHERE jour = ? AND categorie_id = ?",
                            (ca_temporaire, jour, categorie_id),
                        )
                    else:
                        conn.execute(
                            """INSERT INTO analyse_journaliere_categories
                               (jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee)
                               VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)""",
                            (jour, categorie_id),
                        )
                        conn.execute(
                            "UPDATE analyse_journaliere_categories SET ca_temporaire = ? WHERE jour = ? AND categorie_id = ?",
                            (ca_temporaire, jour, categorie_id),
                        )

        except Exception as e:
            logger.error(f"Erreur update_temporary_ca pour {jour}: {e}", exc_info=True)
