"""Repository SQL pour depenses journalieres.

Ce module encapsule l'acces SQL aux donnees de depenses.
Toutes les methodes sont protegees par try/except avec logging.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

logger = logging.getLogger(__name__)


class ExpensesRepository:
    """CRUD et agregations des depenses."""

    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        day_bounds: Callable[[str], tuple[str, str]],
        today_iso: Callable[[], str],
    ) -> None:
        self._connect = connect
        self._day_bounds = day_bounds
        self._today_iso = today_iso

    def add_expense(
        self,
        designation: str,
        valeur: int,
        remarque: str = "",
        date_depense: str | None = None,
    ) -> None:
        try:
            with self._connect() as conn:
                if date_depense:
                    conn.execute(
                        """
                        INSERT INTO depenses (date_depense, designation, valeur, remarque)
                        VALUES (?, ?, ?, ?)
                        """,
                        (date_depense, str(designation), int(valeur), str(remarque)),
                    )
                    return
                conn.execute(
                    """
                    INSERT INTO depenses (designation, valeur, remarque)
                    VALUES (?, ?, ?)
                    """,
                    (str(designation), int(valeur), str(remarque)),
                )
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de l'ajout de depense: %s", exc)
            raise RuntimeError(f"echec add_expense: {exc}") from exc

    def list_daily_expenses(self, day: str | None = None) -> list[dict[str, Any]]:
        target_day = day or self._today_iso()
        day_start, day_end = self._day_bounds(target_day)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, date_depense, designation, valeur, remarque
                    FROM depenses
                    WHERE date_depense >= ? AND date_depense < ?
                    ORDER BY date_depense DESC, id DESC
                    """,
                    (day_start, day_end),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la recuperation des depenses: %s", exc)
            raise RuntimeError(f"echec list_daily_expenses: {exc}") from exc

    def total_daily_expenses(self, day: str | None = None) -> int:
        target_day = day or self._today_iso()
        day_start, day_end = self._day_bounds(target_day)
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COALESCE(SUM(valeur), 0) AS total
                    FROM depenses
                    WHERE date_depense >= ? AND date_depense < ?
                    """,
                    (day_start, day_end),
                ).fetchone()
                return int(row["total"])
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors du calcul du total des depenses: %s", exc)
            raise RuntimeError(f"echec total_daily_expenses: {exc}") from exc

    def update_expense(
        self, expense_id: int, designation: str, valeur: int, remarque: str = ""
    ) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE depenses
                    SET designation = ?, valeur = ?, remarque = ?
                    WHERE id = ?
                    """,
                    (str(designation), int(valeur), str(remarque), int(expense_id)),
                )
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la mise a jour de la depense: %s", exc)
            raise RuntimeError(f"echec update_expense: {exc}") from exc

    def delete_expense(self, expense_id: int) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    DELETE FROM depenses WHERE id = ?
                    """,
                    (int(expense_id),),
                )
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la suppression de la depense: %s", exc)
            raise RuntimeError(f"echec delete_expense: {exc}") from exc
