"""Service metier pour les rapports SF et NFR base sur Tcollecte."""

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

                # --- SI Query: Use today's SI when single day, otherwise use start date SI ---
                if start == end:
                    # Single day: use that day's SI directly
                    si_query = """
                        SELECT c.nom AS sous_categorie, a.si AS si_ttc
                        FROM Tcollecte a
                        INNER JOIN categories c ON c.id = a.categorie_id
                        INNER JOIN categories parent ON c.parent_id = parent.id
                        WHERE a.jour = ? AND parent.nom = ?
                    """
                    si_rows = conn.execute(si_query, (start, self._CATEGORY_1_NAME)).fetchall()
                else:
                    # Date range: use start date's SI (beginning inventory)
                    si_query = """
                        SELECT c.nom AS sous_categorie, a.si AS si_ttc
                        FROM Tcollecte a
                        INNER JOIN categories c ON c.id = a.categorie_id
                        INNER JOIN categories parent ON c.parent_id = parent.id
                        WHERE a.jour = ? AND parent.nom = ?
                    """
                    si_rows = conn.execute(si_query, (start, self._CATEGORY_1_NAME)).fetchall()
                si_map = {str(row["sous_categorie"]): float(row["si_ttc"] or 0) for row in si_rows}

                # --- SF Query: Compute from current stock (products table) when Tcollecte is empty ---
                # SF = PA * (stock_boutique + stock_reserve) for each category
                sf_query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS sf_ttc
                    FROM produits p
                    INNER JOIN categories c ON p.categorie_id = c.id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    GROUP BY c.nom
                """
                sf_rows = conn.execute(sf_query, (self._CATEGORY_1_NAME,)).fetchall()
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
                    FROM Tcollecte a
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

                # Compute live values from current products when Tcollecte is empty
                # This handles both single day and date range views
                live_values_map: dict[str, dict[str, float]] = {}

                # Get categories for Catégorie 1
                categories_query = """
                    SELECT c.nom AS sous_categorie
                    FROM categories c
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    ORDER BY c.nom
                """
                category_rows = conn.execute(categories_query, (self._CATEGORY_1_NAME,)).fetchall()

                # Compute SF from current products
                current_sf_query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS sf_value
                    FROM produits p
                    INNER JOIN categories c ON p.categorie_id = c.id
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    GROUP BY c.nom
                """
                current_sf_rows = conn.execute(
                    current_sf_query, (self._CATEGORY_1_NAME,)
                ).fetchall()
                current_sf_map = {
                    str(row["sous_categorie"]): float(row["sf_value"] or 0)
                    for row in current_sf_rows
                }

                # Also compute CA from sales in the date range if any
                ca_from_sales_query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM(v.quantite * CAST(ROUND(p.pa * 1.2, 0) AS INTEGER)) AS ca_temporaire
                    FROM ventes v
                    JOIN produits p ON v.produit_id = p.id
                    JOIN categories c ON p.categorie_id = c.id
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE v.jour BETWEEN ? AND ? AND v.deleted = 0 AND parent.nom = ?
                    GROUP BY c.nom
                """
                ca_sales_rows = conn.execute(
                    ca_from_sales_query, (start, end, self._CATEGORY_1_NAME)
                ).fetchall()
                ca_sales_map = {
                    str(row["sous_categorie"]): float(row["ca_temporaire"] or 0)
                    for row in ca_sales_rows
                }

                # Build live values from products for all categories if Tcollecte is empty
                if not aggr_rows:
                    for cat_row in category_rows:
                        cat = str(cat_row["sous_categorie"])
                        sf_val = current_sf_map.get(cat, 0)
                        ca_val = ca_sales_map.get(cat, 0)
                        si_val = 0.0  # SI not available from Tcollecte
                        achats_val = 0.0  # Achats not available from Tcollecte

                        # Calculate vente_theo: SF - SI - Achats
                        demarque = demarque_map.get(cat, 0)
                        vente_theo = sf_val - si_val - achats_val - demarque

                        # Calculate marge: CA - vente_theo
                        marge = ca_val - vente_theo

                        live_values_map[cat] = {
                            "si": si_val,
                            "achats": achats_val,
                            "ca": ca_val,
                            "sf": sf_val,
                            "vente_theo": vente_theo,
                            "marge": marge,
                        }
                else:
                    # Tcollecte has data - use it for live values (single day case)
                    # Get today's SI from Tcollecte (or 0 if not set)
                    live_query = """
                        SELECT
                            c.nom AS sous_categorie,
                            a.si,
                            a.achats,
                            a.ca,
                            a.ca_temporaire
                        FROM Tcollecte a
                        INNER JOIN categories c ON c.id = a.categorie_id
                        INNER JOIN categories parent ON c.parent_id = parent.id
                        WHERE a.jour = ? AND parent.nom = ?
                    """
                    live_rows = conn.execute(live_query, (start, self._CATEGORY_1_NAME)).fetchall()

                    # Compute SF from current products
                    current_sf_query = """
                        SELECT
                            c.nom AS sous_categorie,
                            SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS sf_value
                        FROM produits p
                        INNER JOIN categories c ON p.categorie_id = c.id
                        INNER JOIN categories parent ON c.parent_id = parent.id
                        WHERE parent.nom = ?
                        GROUP BY c.nom
                    """
                    current_sf_rows = conn.execute(
                        current_sf_query, (self._CATEGORY_1_NAME,)
                    ).fetchall()
                    current_sf_map = {
                        str(row["sous_categorie"]): float(row["sf_value"] or 0)
                        for row in current_sf_rows
                    }

                    # Also compute CA from today's sales if any
                    ca_from_sales_query = """
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
                    ca_sales_rows = conn.execute(
                        ca_from_sales_query, (start, self._CATEGORY_1_NAME)
                    ).fetchall()
                    ca_sales_map = {
                        str(row["sous_categorie"]): float(row["ca_temporaire"] or 0)
                        for row in ca_sales_rows
                    }

                    if live_rows:
                        # Use data from Tcollecte if available
                        for lrow in live_rows:
                            cat = str(lrow["sous_categorie"])
                            si_val = float(lrow["si"] or 0)
                            achats_val = float(lrow["achats"] or 0)
                            ca_val = float(lrow["ca"] or 0)
                            ca_temp = float(lrow["ca_temporaire"] or 0)
                            # Use current stock from products table
                            sf_val = current_sf_map.get(cat, 0)

                            # Use ca_temporaire if ca is 0
                            if ca_val == 0 and ca_temp > 0:
                                ca_val = ca_temp

                            # Calculate vente_theo: SF - SI - Achats (Stock Flux formula)
                            demarque = demarque_map.get(cat, 0)
                            vente_theo = sf_val - si_val - achats_val - demarque

                            # Calculate marge: CA - vente_theo
                            marge = ca_val - vente_theo

                            live_values_map[cat] = {
                                "si": si_val,
                                "achats": achats_val,
                                "ca": ca_val,
                                "sf": sf_val,
                                "vente_theo": vente_theo,
                                "marge": marge,
                            }
                    else:
                        # Tcollecte is empty - compute from current products and sales
                        for cat, sf_val in current_sf_map.items():
                            # Get CA from today's sales
                            ca_val = ca_sales_map.get(cat, 0)
                            # SI is 0 for new day (or could get from yesterday's closure)
                            si_val = 0.0
                            # Achats is 0 if not set
                            achats_val = 0.0

                            # Calculate vente_theo: SF - SI - Achats
                            demarque = demarque_map.get(cat, 0)
                            vente_theo = sf_val - si_val - achats_val - demarque

                            # Calculate marge: CA - vente_theo
                            marge = ca_val - vente_theo

                            live_values_map[cat] = {
                                "si": si_val,
                                "achats": achats_val,
                                "ca": ca_val,
                                "sf": sf_val,
                                "vente_theo": vente_theo,
                                "marge": marge,
                            }

                result: list[dict[str, Any]] = []

                # If no Tcollecte data but live_values_map has data (computed from products), use it
                if not aggr_rows and live_values_map:
                    for sous_cat, lv in live_values_map.items():
                        ca = lv["ca"]
                        vente_theo = lv["vente_theo"]
                        marge = lv["marge"]

                        # Calculate margin percentage
                        marge_percent = round((marge / ca) * 100, 2) if ca > 0 else 0.0

                        result.append(
                            {
                                "jour": f"{start} - {end}",
                                "sous_categorie": sous_cat,
                                "si_ttc": lv["si"],
                                "achats_ttc": lv["achats"],
                                "ca_ttc": ca,
                                "env_ttc": 0,
                                "demarque_ttc": demarque_map.get(sous_cat, 0.0),
                                "sf_ttc": lv["sf"],
                                "vente_theo_ttc": vente_theo,
                                "marge_ttc": marge,
                                "marge_percent": marge_percent,
                            }
                        )
                    return result

                # Otherwise use aggregated data from Tcollecte
                for row in aggr_rows:
                    sous_cat = str(row["sous_categorie"])

                    # Use live values if single day, otherwise use aggregated
                    if start == end and sous_cat in live_values_map:
                        lv = live_values_map[sous_cat]
                        ca = lv["ca"]
                        vente_theo = lv["vente_theo"]
                        marge = lv["marge"]
                    else:
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

                    # Get values - use live values for single day
                    if start == end and sous_cat in live_values_map:
                        lv = live_values_map[sous_cat]
                        si_val = lv["si"]
                        achats_val = lv["achats"]
                        sf_val = lv["sf"]
                        vente_theo_val = lv["vente_theo"]
                        marge_val = lv["marge"]
                    else:
                        si_val = si_map.get(sous_cat, 0.0)
                        achats_val = float(row["achats_ttc"] or 0)
                        sf_val = sf_map.get(sous_cat, 0.0)
                        vente_theo_val = float(row["vente_theo_ttc"] or 0)
                        marge_val = marge

                    result.append(
                        {
                            "jour": f"{start} - {end}",
                            "sous_categorie": sous_cat,
                            "si_ttc": si_val,
                            "achats_ttc": achats_val,
                            "ca_ttc": ca,
                            "env_ttc": float(row["env_ttc"] or 0),
                            "demarque_ttc": demarque_map.get(sous_cat, 0.0),
                            "sf_ttc": sf_val,
                            "vente_theo_ttc": vente_theo_val,
                            "marge_ttc": marge_val,
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
                    FROM Tcollecte ac
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

        Creates rows in Tcollecte if they don't exist.

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
                        "SELECT id FROM Tcollecte WHERE jour = ? AND categorie_id = ?",
                        (jour, categorie_id),
                    ).fetchone()

                    if existing:
                        conn.execute(
                            "UPDATE Tcollecte SET ca_temporaire = ? WHERE jour = ? AND categorie_id = ?",
                            (ca_temporaire, jour, categorie_id),
                        )
                    else:
                        conn.execute(
                            """INSERT INTO Tcollecte
                               (jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee)
                               VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)""",
                            (jour, categorie_id),
                        )
                        conn.execute(
                            "UPDATE Tcollecte SET ca_temporaire = ? WHERE jour = ? AND categorie_id = ?",
                            (ca_temporaire, jour, categorie_id),
                        )

        except Exception as e:
            logger.error(f"Erreur update_temporary_ca pour {jour}: {e}", exc_info=True)

    def compute_purchases_by_category(self, jour: str) -> dict[str, int]:
        """Compute purchases (total_ttc) for each category on a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            Dictionary mapping category names to total purchases (TTC).
        """
        if not self._validate_date_format(jour):
            return {}

        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM(al.total_ttc) AS total_achats
                    FROM Tachats a
                    JOIN Tachats_lignes al ON a.id = al.achat_id
                    JOIN produits p ON al.produit_id = p.id
                    JOIN categories c ON p.categorie_id = c.id
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE a.jour = ? AND parent.nom = ?
                    GROUP BY c.nom
                """
                rows = conn.execute(query, (jour, self._CATEGORY_1_NAME)).fetchall()

                return {str(row["sous_categorie"]): int(row["total_achats"] or 0) for row in rows}

        except Exception as e:
            logger.error(f"Erreur compute_purchases_by_category pour {jour}: {e}", exc_info=True)
            return {}

    def update_purchases(self, jour: str) -> None:
        """Compute and update purchases from invoices for a given day.

        Updates the 'achats' column in Tcollecte with
        total purchases (TTC) from achat invoices for each category.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).
        """
        if not self._validate_date_format(jour):
            return

        purchases = self.compute_purchases_by_category(jour)
        if not purchases:
            return

        try:
            with self._connect() as conn:
                for categorie_nom, achats_valeur in purchases.items():
                    cat_id_row = conn.execute(
                        "SELECT id FROM categories WHERE nom = ?", (categorie_nom,)
                    ).fetchone()

                    if not cat_id_row:
                        continue

                    categorie_id = cat_id_row["id"]

                    existing = conn.execute(
                        "SELECT id FROM Tcollecte WHERE jour = ? AND categorie_id = ?",
                        (jour, categorie_id),
                    ).fetchone()

                    if existing:
                        conn.execute(
                            "UPDATE Tcollecte SET achats = ? WHERE jour = ? AND categorie_id = ?",
                            (achats_valeur, jour, categorie_id),
                        )
                    else:
                        conn.execute(
                            """INSERT INTO Tcollecte
                               (jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee)
                               VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)""",
                            (jour, categorie_id),
                        )
                        conn.execute(
                            "UPDATE Tcollecte SET achats = ? WHERE jour = ? AND categorie_id = ?",
                            (achats_valeur, jour, categorie_id),
                        )

        except Exception as e:
            logger.error(f"Erreur update_purchases pour {jour}: {e}", exc_info=True)

    def compute_stock_value_by_category(self) -> dict[str, int]:
        """Compute current stock value (PA * quantite) for each category.

        Returns:
            Dictionary mapping category names to stock values (PA * quantite).
        """
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row

                query = """
                    SELECT
                        c.nom AS sous_categorie,
                        SUM(p.stock_boutique + p.stock_reserve) AS quantite_totale,
                        SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS valeur_stock
                    FROM produits p
                    JOIN categories c ON p.categorie_id = c.id
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    GROUP BY c.nom
                """
                rows = conn.execute(query, (self._CATEGORY_1_NAME,)).fetchall()

                return {str(row["sous_categorie"]): int(row["valeur_stock"] or 0) for row in rows}

        except Exception as e:
            logger.error(f"Erreur compute_stock_value_by_category: {e}", exc_info=True)
            return {}

    def update_stock_value(self, jour: str) -> None:
        """Compute and update SF stock value from current stock for a given day.

        Updates the 'sf' column in Tcollecte with current
        stock value (PA * quantite) for each category.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).
        """
        if not self._validate_date_format(jour):
            return

        stock_values = self.compute_stock_value_by_category()
        if not stock_values:
            return

        try:
            with self._connect() as conn:
                for categorie_nom, sf_valeur in stock_values.items():
                    cat_id_row = conn.execute(
                        "SELECT id FROM categories WHERE nom = ?", (categorie_nom,)
                    ).fetchone()

                    if not cat_id_row:
                        continue

                    categorie_id = cat_id_row["id"]

                    existing = conn.execute(
                        "SELECT id FROM Tcollecte WHERE jour = ? AND categorie_id = ?",
                        (jour, categorie_id),
                    ).fetchone()

                    if existing:
                        conn.execute(
                            "UPDATE Tcollecte SET sf = ? WHERE jour = ? AND categorie_id = ?",
                            (sf_valeur, jour, categorie_id),
                        )
                    else:
                        conn.execute(
                            """INSERT INTO Tcollecte
                               (jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee)
                               VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)""",
                            (jour, categorie_id),
                        )
                        conn.execute(
                            "UPDATE Tcollecte SET sf = ? WHERE jour = ? AND categorie_id = ?",
                            (sf_valeur, jour, categorie_id),
                        )

        except Exception as e:
            logger.error(f"Erreur update_stock_value pour {jour}: {e}", exc_info=True)
