"""Repository SQL pour ventes et rapports journaliers associes.

Ce module encapsule l'acces SQL aux donnees de ventes et rapports.
Toutes les methodes sont protegees par try/except avec logging.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime
from typing import Any

from core.constants import (
    DATE_FORMAT_DAY,
    DATE_FORMAT_TIME,
    PARENT_CATEGORY_GUEST,
    PARENT_CATEGORY_OASIS,
)

logger = logging.getLogger(__name__)


class SalesRepository:
    """Persistance des ventes et rapports Oasis/Guest."""

    # Common SQL fragments for JOINs including parent category hierarchy
    _VENTES_PRODUITS_CATEGORIES_JOIN = """
        FROM ventes v
        JOIN produits p ON v.produit_id = p.id
        JOIN categories c ON p.categorie_id = c.id
        JOIN categories parent ON c.parent_id = parent.id
    """

    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        day_bounds: Callable[[str], tuple[str, str]],
    ) -> None:
        self._connect = connect
        self._day_bounds = day_bounds

    @staticmethod
    def _sql_in_placeholders(values: tuple[str, ...] | list[str]) -> str:
        return ",".join("?" for _ in values)

    def _build_parent_category_filter(self, parent_name: str) -> tuple[str, tuple[str, ...]]:
        """Build filter for subcategories with given parent category name.

        Args:
            parent_name: Name of the parent category (e.g., 'Catégorie 1 - OW (Owners)').

        Returns:
            Tuple of (filter_sql, params_tuple).
        """
        return "parent.nom = ?", (parent_name,)

    def record_sale(
        self,
        *,
        produit_id: int,
        produit_nom: str,
        quantite: int,
        prix_unitaire: int,
        session_id: int,
    ) -> dict[str, Any]:
        """Enregistre une vente dans la base de donnees et retourne la ligne de vente.

        Cette methode est atomique - en cas d'erreur, un rollback est effectué.
        """
        pid = int(produit_id)
        if pid <= 0:
            raise ValueError("produit_id invalide pour enregistrement de vente")
        qte = max(1, int(quantite))
        pu = max(0, int(prix_unitaire))
        total = qte * pu
        now = datetime.now()
        jour = now.strftime(DATE_FORMAT_DAY)
        heure = now.strftime(DATE_FORMAT_TIME)

        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO ventes
                        (jour, heure, produit_id, produit_nom,
                         quantite, prix_unitaire, prix_total, session_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (jour, heure, pid, str(produit_nom), qte, pu, total, int(session_id)),
                )
                return {
                    "heure": heure,
                    "produit": str(produit_nom),
                    "quantite": qte,
                }
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de l'enregistrement de la vente: %s", exc)
            raise

    def list_daily_sales(self, day: str) -> list[dict[str, Any]]:
        """Liste les ventes enregistrees pour un jour donne, pour affichage."""
        day_start, day_end = self._day_bounds(str(day))
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        id,
                        heure,
                        produit_nom AS produit,
                        quantite,
                        deleted
                    FROM ventes
                    WHERE jour >= ? AND jour < ?
                    ORDER BY heure DESC
                    """,
                    (day_start, day_end),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la recuperation des ventes: %s", exc)
            return []

    def delete_sale(self, vente_id: int, operateur_id: int | None = None) -> bool:
        """Marque une vente comme supprimée (soft delete) par son identifiant.

        Args:
            vente_id: Identifiant de la vente a supprimer.
            operateur_id: Identifiant de l'opérateur qui effectue la suppression.

        Returns:
            True si la suppression a reussi.
        """
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    UPDATE ventes 
                    SET deleted = 1, 
                        deleted_by = ?, 
                        deleted_at = datetime('now')
                    WHERE id = ? AND deleted = 0
                    """,
                    (operateur_id, int(vente_id)),
                )
                return cursor.rowcount > 0
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la suppression de la vente %s: %s", vente_id, exc)
            return False

    def get_oasis_stats(self, jour: str) -> list[dict[str, Any]]:
        """Stats pour le rapport Oasis (Cat 1: Alimentaire/Boissons).

        Uses parent category hierarchy to filter subcategories belonging to
        'Catégorie 1 - OW (Owners)' - includes: BA, BSA, PF, GL, Confi, EPI,
        Tabac, HS, Baz, TelC.
        """
        parent_filter, filter_params = self._build_parent_category_filter(PARENT_CATEGORY_OASIS)
        day_start, day_end = self._day_bounds(jour)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        c.nom as categorie,
                        SUM(v.quantite * CASE WHEN c.prc_disabled THEN 0 ELSE CAST(ROUND(p.pa * 1.2, 0) AS INTEGER) END) as total_prc
                    {self._VENTES_PRODUITS_CATEGORIES_JOIN}
                    WHERE v.jour >= ? AND v.jour < ? AND v.deleted = 0 AND {parent_filter}
                    GROUP BY c.nom
                    ORDER BY c.nom
                    """,
                    (day_start, day_end, *filter_params),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors du calcul des stats Oasis: %s", exc)
            return []

    def get_detailed_daily_sales(self, day: str) -> list[dict[str, Any]]:
        """Rapport detaille des ventes journalieres par categorie et produit.

        Uses parent category hierarchy to filter subcategories belonging to
        'Catégorie 1 - OW (Owners)'.
        """
        parent_filter, filter_params = self._build_parent_category_filter(PARENT_CATEGORY_OASIS)
        day_start, day_end = self._day_bounds(day)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        c.nom as categorie,
                        p.nom as produit,
                        SUM(v.quantite) as quantite_vendue,
                        SUM(v.prix_total) as total_vente,
                        (p.stock_boutique + p.stock_reserve) as stock_final
                    {self._VENTES_PRODUITS_CATEGORIES_JOIN}
                    WHERE v.jour >= ? AND v.jour < ? AND v.deleted = 0 AND {parent_filter}
                    GROUP BY c.nom, p.nom
                    ORDER BY c.nom, p.nom
                    """,
                    (day_start, day_end, *filter_params),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors du calcul des stats detaillees: %s", exc)
            return []

    def total_daily_sales(self, day: str) -> int:
        """Get total sales amount for a given day.

        Args:
            day: Date in YYYY-MM-DD format

        Returns:
            Total sales amount (sum of prix_total) for the day
        """
        day_start, day_end = self._day_bounds(str(day))
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(prix_total), 0)
                    FROM ventes
                    WHERE jour >= ? AND jour < ? AND deleted = 0
                    """,
                    (day_start, day_end),
                ).fetchone()
                return int(row[0]) if row else 0
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors du calcul du total des ventes: %s", exc)
            return 0

    def get_guest_stats(self, jour: str) -> list[dict[str, Any]]:
        """Stats pour le rapport Guest (Cat 2: Divers/Hygiene).

        Uses parent category hierarchy to filter subcategories belonging to
        'Catégorie 2 - NOW (Not owners)' - includes: Lub, Pea, Solaires.
        """
        parent_filter, filter_params = self._build_parent_category_filter(PARENT_CATEGORY_GUEST)
        day_start, day_end = self._day_bounds(jour)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    f"""
                    SELECT
                        c.nom as categorie,
                        p.nom as produit,
                        SUM(v.quantite) as qte,
                        SUM(v.prix_total) as val
                    {self._VENTES_PRODUITS_CATEGORIES_JOIN}
                    WHERE v.jour >= ? AND v.jour < ? AND v.deleted = 0 AND {parent_filter}
                    GROUP BY c.nom, p.nom
                    ORDER BY c.nom, p.nom
                    """,
                    (day_start, day_end, *filter_params),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors du calcul des stats Guest: %s", exc)
            return []
