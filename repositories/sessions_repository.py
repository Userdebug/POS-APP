"""Repository SQL pour sessions operateur."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager


class SessionsRepository:
    """Gestion des ouvertures/fermetures de session operateur."""

    def __init__(self, connect: Callable[[], AbstractContextManager[sqlite3.Connection]]) -> None:
        self._connect = connect

    def open_session(self, seller_name: str, access_right: str) -> tuple[int, int]:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO operateurs (nom, droit_acces)
                    VALUES (?, ?)
                    ON CONFLICT(nom) DO UPDATE SET droit_acces = excluded.droit_acces, actif = 1
                    """,
                    (seller_name, access_right),
                )
                operator_id = conn.execute(
                    "SELECT id FROM operateurs WHERE nom = ?",
                    (seller_name,),
                ).fetchone()["id"]
                cursor = conn.execute(
                    """
                    INSERT INTO sessions_operateur (operateur_id, vendeur_nom, active)
                    VALUES (?, ?, 1)
                    """,
                    (operator_id, seller_name),
                )
                session_id = cursor.lastrowid
                return int(operator_id), int(session_id)
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec open_session: {exc}") from exc

    def close_session(self, session_id: int) -> None:
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    UPDATE sessions_operateur
                    SET active = 0, closed_at = datetime('now')
                    WHERE id = ?
                    """,
                    (session_id,),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec close_session: {exc}") from exc
