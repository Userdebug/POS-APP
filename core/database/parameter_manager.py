"""Gestion des parametres de l'application."""

from __future__ import annotations


class ParameterManager:
    """Gestionnaire de parametres stockes en base SQLite.

    Args:
        connect: Function returning a sqlite3.Connection context.
    """

    def __init__(self, connect) -> None:
        self._connect = connect

    def get(self, key: str, default: str | None = None) -> str | None:
        """Recupere un parametre."""
        with self._connect() as conn:
            row = conn.execute("SELECT valeur FROM parametres WHERE cle = ?", (key,)).fetchone()
            return str(row["valeur"]) if row else default

    def set(self, key: str, value: str, description: str | None = None) -> None:
        """Met a jour un parametre."""
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO parametres (cle, valeur, description, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(cle) DO UPDATE SET
                    valeur = excluded.valeur,
                    description = COALESCE(excluded.description, parametres.description),
                    updated_at = datetime('now')
                """,
                (key, value, description),
            )
            conn.commit()

    def get_tax(self, default: float = 20.0) -> float:
        """Recupere le taux de TVA."""
        raw = self.get("TVA_TAUX")
        try:
            return float(raw) if raw else default
        except ValueError:
            return default

    def set_tax(self, rate: float) -> None:
        """Definit le taux de TVA."""
        self.set("TVA_TAUX", f"{float(rate):.2f}", "Taux de TVA en pourcentage")
