"""Daily closure and tracking operations repository."""

from __future__ import annotations

from typing import Any, Callable


class DailyOperations:
    """Handles daily closure and tracking operations.

    Args:
        connect_fn: Context manager yielding a sqlite3.Connection.
        day_bounds_fn: Callable to get day start/end bounds.
        month_bounds_fn: Callable to get month start/end bounds.
        today_iso_fn: Callable to get today's ISO date string.
        current_month_iso_fn: Callable to get current month ISO string.
        get_tax_fn: Callable to get tax rate.
    """

    def __init__(
        self,
        connect_fn: Any,
        day_bounds_fn: Callable[[str], tuple[str, str]],
        month_bounds_fn: Callable[[str], tuple[str, str]],
        today_iso_fn: Callable[[], str],
        current_month_iso_fn: Callable[[], str],
        get_tax_fn: Callable[[float], float],
    ) -> None:
        self._connect = connect_fn
        self._day_bounds = day_bounds_fn
        self._month_bounds = month_bounds_fn
        self._today_iso = today_iso_fn
        self._current_month_iso = current_month_iso_fn
        self._get_tax = get_tax_fn

    def set_daily_closure_revenue(self, day: str, ca_ttc_final: int, note: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clotures_caisse (jour, ca_ttc_final, note, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(jour) DO UPDATE SET
                    ca_ttc_final = excluded.ca_ttc_final,
                    note = excluded.note,
                    updated_at = datetime('now')
                """,
                (str(day), int(ca_ttc_final), str(note)),
            )

    def upsert_daily_closure_by_category(self, jour: str, values: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            # Get valid OW subcategories
            valid_cats = set(
                row["nom"]
                for row in conn.execute("""
                    SELECT c.nom FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                    """).fetchall()
            )

            conn.execute("DELETE FROM clotures_caisse_categories WHERE jour = ?", (str(jour),))
            for row in values:
                categorie = str(row.get("categorie", "")).strip()
                if not categorie or categorie not in valid_cats:
                    continue
                ca_ttc_final = max(0, int(row.get("ca_ttc_final", 0)))
                conn.execute(
                    """
                    INSERT INTO clotures_caisse_categories (jour, categorie, ca_ttc_final, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(jour, categorie) DO UPDATE SET
                        ca_ttc_final = excluded.ca_ttc_final,
                        updated_at = datetime('now')
                    """,
                    (str(jour), categorie, ca_ttc_final),
                )

            row = conn.execute(
                """
                SELECT COALESCE(SUM(ca_ttc_final), 0) AS total
                FROM clotures_caisse_categories
                WHERE jour = ?
                """,
                (str(jour),),
            ).fetchone()
            total = int(row["total"] or 0)
            conn.execute(
                """
                INSERT INTO clotures_caisse (jour, ca_ttc_final, note, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(jour) DO UPDATE SET
                    ca_ttc_final = excluded.ca_ttc_final,
                    note = excluded.note,
                    updated_at = datetime('now')
                """,
                (str(jour), total, "auto-sum categories"),
            )

    def get_daily_closure_by_category(self, jour: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT categorie, ca_ttc_final
                FROM clotures_caisse_categories
                WHERE jour = ?
                ORDER BY categorie ASC
                """,
                (str(jour),),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_daily_closure_ca(self, jour: str) -> int | None:
        by_cat = self.get_daily_closure_by_category(jour)
        if by_cat:
            return sum(int(row.get("ca_ttc_final", 0)) for row in by_cat)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ca_ttc_final
                FROM clotures_caisse
                WHERE jour = ?
                """,
                (str(jour),),
            ).fetchone()
            if row is None:
                return None
            return int(row["ca_ttc_final"])
