"""DailyTrackingRepository - sole owner of Tcollecte CRUD + business logic.

This repository provides all database operations for Tcollecte table,
including day initialization, CA updates, purchases, stock metrics,
and closure operations.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Optional

from core.constants import DATE_FORMAT_DAY

logger = logging.getLogger(__name__)

_OW_CATEGORY_PARENT = "Catégorie 1 - OW (Owners)"


@dataclass(frozen=True, slots=True)
class DailyTrack:
    """Immutable daily tracking record for a category."""

    jour: str
    category_id: int
    category_name: str
    stock_initial: int
    purchases: int
    stock_final: int
    removed_value: int
    ca_live: int
    ca_final: int
    is_closed: bool
    updated_at: str

    @property
    def ca(self) -> int:
        """Current CA depending on closure state."""
        return self.ca_final if self.is_closed else self.ca_live

    @property
    def sales_theoretical(self) -> int:
        """Theoretical sales: SI + Achats - SF - ENV (never negative)."""
        return max(0, self.stock_initial + self.purchases - self.stock_final - self.removed_value)

    @property
    def margin(self) -> int:
        """Margin: CA - theoretical_sales."""
        return self.ca - self.sales_theoretical

    @property
    def margin_percent(self) -> Optional[float]:
        """Margin percentage."""
        theo = self.sales_theoretical
        if theo > 0:
            return (self.margin / theo) * 100.0
        return 0.0 if self.ca == 0 else None


class DailyTrackingRepository:
    """Repository for Tcollecte operations with atomic transactions."""

    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        today_iso: Callable[[], str],
        day_bounds: Callable[[str], tuple[str, str]],
        resolve_category_names: Callable[[list[str]], dict[str, int]],
    ) -> None:
        self._connect = connect
        self._today_iso = today_iso
        self._day_bounds = day_bounds
        self._resolve_categories = resolve_category_names

    def _get_category_id_map(self) -> dict[str, int]:
        """Get mapping of category names to IDs for OW categories."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.nom FROM categories c
                JOIN categories parent ON c.parent_id = parent.id
                WHERE parent.nom = ?
            """,
                (_OW_CATEGORY_PARENT,),
            ).fetchall()
            return {str(r["nom"]): int(r["id"]) for r in rows}

    def _get_all_category_id_map(self) -> dict[str, int]:
        """Get mapping of all category names to IDs."""
        with self._connect() as conn:
            rows = conn.execute("SELECT id, nom FROM categories").fetchall()
            return {str(r["nom"]): int(r["id"]) for r in rows}

    def _get_ow_categories(self) -> list[str]:
        """Get list of OW category names."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom FROM categories c
                JOIN categories parent ON c.parent_id = parent.id
                WHERE parent.nom = ?
                ORDER BY c.nom
            """,
                (_OW_CATEGORY_PARENT,),
            ).fetchall()
            return [str(r["nom"]) for r in rows]

    def get_track(self, jour: str, category_name: str) -> Optional[DailyTrack]:
        """Get a single daily track by day and category."""
        cat_id_map = self._get_category_id_map()
        cat_id = cat_id_map.get(category_name)
        if not cat_id:
            return None

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT t.jour, t.categorie_id, c.nom AS category_name,
                       t.si, t.achats, t.sf, t.env, t.ca, t.ca_temporaire,
                       t.cloturee, t.updated_at
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ? AND t.categorie_id = ?
            """,
                (jour, cat_id),
            ).fetchone()

            if not row:
                return None

            return DailyTrack(
                jour=str(row["jour"]),
                category_id=int(row["categorie_id"]),
                category_name=str(row["category_name"]),
                stock_initial=int(row["si"] or 0),
                purchases=int(row["achats"] or 0),
                stock_final=int(row["sf"] or 0),
                removed_value=int(row["env"] or 0),
                ca_live=int(row["ca_temporaire"] or 0),
                ca_final=int(row["ca"] or 0),
                is_closed=bool(row["cloturee"] == 1),
                updated_at=str(row["updated_at"] or ""),
            )

    def list_tracks(self, jour: str) -> list[DailyTrack]:
        """Get all daily tracks for a given day."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT t.jour, t.categorie_id, c.nom AS category_name,
                       t.si, t.achats, t.sf, t.env, t.ca, t.ca_temporaire,
                       t.cloturee, t.updated_at
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
                ORDER BY c.nom
            """,
                (jour,),
            ).fetchall()

            return [
                DailyTrack(
                    jour=str(r["jour"]),
                    category_id=int(r["categorie_id"]),
                    category_name=str(r["category_name"]),
                    stock_initial=int(r["si"] or 0),
                    purchases=int(r["achats"] or 0),
                    stock_final=int(r["sf"] or 0),
                    removed_value=int(r["env"] or 0),
                    ca_live=int(r["ca_temporaire"] or 0),
                    ca_final=int(r["ca"] or 0),
                    is_closed=bool(r["cloturee"] == 1),
                    updated_at=str(r["updated_at"] or ""),
                )
                for r in rows
            ]

    def list_tracks_range(self, start: str, end: str) -> list[DailyTrack]:
        """Get all daily tracks for a date range."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT t.jour, t.categorie_id, c.nom AS category_name,
                       t.si, t.achats, t.sf, t.env, t.ca, t.ca_temporaire,
                       t.cloturee, t.updated_at
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour >= ? AND t.jour <= ?
                ORDER BY t.jour, c.nom
            """,
                (start, end),
            ).fetchall()

            return [
                DailyTrack(
                    jour=str(r["jour"]),
                    category_id=int(r["categorie_id"]),
                    category_name=str(r["category_name"]),
                    stock_initial=int(r["si"] or 0),
                    purchases=int(r["achats"] or 0),
                    stock_final=int(r["sf"] or 0),
                    removed_value=int(r["env"] or 0),
                    ca_live=int(r["ca_temporaire"] or 0),
                    ca_final=int(r["ca"] or 0),
                    is_closed=bool(r["cloturee"] == 1),
                    updated_at=str(r["updated_at"] or ""),
                )
                for r in rows
            ]

    def get_open_days(self) -> list[str]:
        """Get list of unclosed days."""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT DISTINCT jour FROM Tcollecte
                WHERE cloturee = 0
                ORDER BY jour DESC
            """).fetchall()
            return [str(r["jour"]) for r in rows]

    def is_closed(self, jour: str) -> bool:
        """Check if a day is closed."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(1) as cnt FROM Tcollecte
                WHERE jour = ? AND cloturee = 1
            """,
                (jour,),
            ).fetchone()
            return (row["cnt"] or 0) > 0

    def get_last_closed_date(self) -> Optional[str]:
        """Get the most recent closed date."""
        with self._connect() as conn:
            row = conn.execute("""
                SELECT MAX(jour) as last_closed FROM Tcollecte
                WHERE cloturee = 1
            """).fetchone()
            return str(row["last_closed"]) if row and row["last_closed"] else None

    def get_category_sf(self, jour: str) -> dict[str, int]:
        """Get SF values per category for a day (for J+1 init)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom AS category, t.sf
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
            """,
                (jour,),
            ).fetchall()
            return {str(r["category"]): int(r["sf"] or 0) for r in rows}

    def initialize_day(self, jour: str, carry_si_from: Optional[str] = None) -> None:
        """Create Tcollecte rows for all OW categories for given day.

        SI = yesterday's SF from Tcollecte if carry_si_from provided;
        else compute from current produits (first day).
        All other fields zero. Ensures idempotency (no duplicates).
        """
        if carry_si_from:
            prev_tracks = self.list_tracks(carry_si_from)
            if not prev_tracks:
                raise ValueError(f"No tracking data found for previous day {carry_si_from}")
            si_by_cat = {t.category_name: t.stock_final for t in prev_tracks}
        else:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT c.nom AS categorie, SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS si
                    FROM produits p
                    JOIN categories c ON p.categorie_id = c.id
                    JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    GROUP BY c.nom
                """,
                    (_OW_CATEGORY_PARENT,),
                ).fetchall()
                si_by_cat = {str(r["categorie"]): int(r["si"] or 0) for r in rows}

        cat_id_map = self._get_category_id_map()

        with self._connect() as conn:
            for cat_name, si_val in si_by_cat.items():
                cat_id = cat_id_map.get(cat_name)
                if not cat_id:
                    continue
                conn.execute(
                    """
                    INSERT INTO Tcollecte (
                        jour, categorie_id, si, achats, ca, ca_temporaire,
                        sf, env, vente_theorique, marge, cloturee, updated_at
                    ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, 0, 0, 0, datetime('now'))
                    ON CONFLICT(jour, categorie_id) DO UPDATE SET
                        si = CASE WHEN Tcollecte.si = 0 THEN excluded.si ELSE Tcollecte.si END,
                        updated_at = datetime('now')
                """,
                    (jour, cat_id, si_val),
                )
            conn.commit()

    def update_live_ca(self, jour: str, increments: dict[str, int]) -> None:
        """Increment ca_live (ca_temporaire in DB) by amounts per category (from sales)."""
        if not increments:
            return

        cat_id_map = self._get_category_id_map()

        with self._connect() as conn:
            for cat_name, inc in increments.items():
                if inc <= 0:
                    continue
                cat_id = cat_id_map.get(cat_name)
                if cat_id:
                    conn.execute(
                        """
                        UPDATE Tcollecte
                        SET ca_temporaire = COALESCE(ca_temporaire, 0) + ?,
                            updated_at = datetime('now')
                        WHERE jour = ? AND categorie_id = ?
                    """,
                        (inc, jour, cat_id),
                    )
            conn.commit()

        self._recompute_derived_fields(jour)

    def update_purchases(self, jour: str) -> None:
        """Compute purchases from Tachats and update Tcollecte.achats."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom AS categorie, c.id AS categorie_id,
                       SUM(al.total_ttc) AS achats_ttc
                FROM Tachats a
                JOIN Tachats_lignes al ON a.id = al.achat_id
                JOIN produits p ON al.produit_id = p.id
                JOIN categories c ON p.categorie_id = c.id
                JOIN categories parent ON c.parent_id = parent.id
                WHERE a.jour = ? AND parent.nom = ?
                GROUP BY c.nom, c.id
            """,
                (jour, _OW_CATEGORY_PARENT),
            ).fetchall()

            updates = []
            for r in rows:
                if r["achats_ttc"]:
                    updates.append((int(r["achats_ttc"]), jour, int(r["categorie_id"])))

            if updates:
                conn.executemany(
                    """
                    UPDATE Tcollecte
                    SET achats = ?, updated_at = datetime('now')
                    WHERE jour = ? AND categorie_id = ?
                """,
                    updates,
                )
                conn.commit()

        self._recompute_derived_fields(jour)

    def update_stock_metrics(self, jour: str) -> None:
        """Recompute and update sf and env for all categories for the day.

        SF = current produits stock value; ENV = sum of removed products.
        """
        with self._connect() as conn:
            sf_rows = conn.execute(
                """
                SELECT c.nom AS categorie, c.id AS categorie_id,
                       SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS sf_ttc
                FROM produits p
                JOIN categories c ON p.categorie_id = c.id
                JOIN categories parent ON c.parent_id = parent.id
                WHERE parent.nom = ?
                GROUP BY c.nom, c.id
            """,
                (_OW_CATEGORY_PARENT,),
            ).fetchall()
            sf_map = {
                str(r["categorie"]): (int(r["categorie_id"]), int(r["sf_ttc"] or 0))
                for r in sf_rows
            }

            env_rows = conn.execute(
                """
                SELECT categorie, SUM(valeur) AS env_ttc
                FROM historique_produits_enleves
                WHERE jour = ?
                GROUP BY categorie
            """,
                (jour,),
            ).fetchall()
            env_map = {str(r["categorie"]): int(r["env_ttc"] or 0) for r in env_rows}

            updates = []
            for categorie, (cat_id, sf_val) in sf_map.items():
                env_val = env_map.get(categorie, 0)
                updates.append((sf_val, env_val, jour, cat_id))

            if updates:
                conn.executemany(
                    """
                    UPDATE Tcollecte
                    SET sf = ?, env = ?, updated_at = datetime('now')
                    WHERE jour = ? AND categorie_id = ?
                """,
                    updates,
                )
                conn.commit()

        self._recompute_derived_fields(jour)

    def _recompute_derived_fields(self, jour: str) -> None:
        """Recompute vente_theorique and marge for a day."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, si, achats, sf, env, ca
                FROM Tcollecte
                WHERE jour = ?
            """,
                (jour,),
            ).fetchall()

            updates = []
            for r in rows:
                si = int(r["si"] or 0)
                achats = int(r["achats"] or 0)
                sf = int(r["sf"] or 0)
                env = int(r["env"] or 0)
                ca = int(r["ca"] or 0)
                vente_theo = max(0, si + achats - sf - env)
                marge = ca - vente_theo
                updates.append((vente_theo, marge, int(r["id"])))

            if updates:
                conn.executemany(
                    """
                    UPDATE Tcollecte
                    SET vente_theorique = ?, marge = ?, updated_at = datetime('now')
                    WHERE id = ?
                """,
                    updates,
                )
                conn.commit()

    def set_final_ca(self, jour: str, final_ca: dict[str, int]) -> None:
        """Set ca_final per category during closure (overwrites previous)."""
        cat_id_map = self._get_category_id_map()

        with self._connect() as conn:
            for cat_name, ca_val in final_ca.items():
                cat_id = cat_id_map.get(cat_name)
                if cat_id:
                    conn.execute(
                        """
                        UPDATE Tcollecte
                        SET ca = ?, updated_at = datetime('now')
                        WHERE jour = ? AND categorie_id = ?
                    """,
                        (ca_val, jour, cat_id),
                    )
            conn.commit()

        self._recompute_derived_fields(jour)

    def close_day(self, jour: str) -> None:
        """Mark day as closed (set cloturee=1). Must be called after final CA set."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE Tcollecte SET cloturee = 1, updated_at = datetime('now')
                WHERE jour = ?
            """,
                (jour,),
            )
            conn.commit()

    def prepare_next_day(self, jour: str) -> str:
        """Initialize day+1 with SI = today's SF (after closure). Returns next_day."""
        from datetime import datetime, timedelta

        current = datetime.strptime(jour, DATE_FORMAT_DAY)
        next_day = (current + timedelta(days=1)).strftime(DATE_FORMAT_DAY)

        self.initialize_day(next_day, carry_si_from=jour)
        return next_day

    def finalize_day(self, jour: str, final_ca: dict[str, int]) -> str:
        """Complete closure: set final CA, close day, prepare next day. Returns next_day."""
        self.set_final_ca(jour, final_ca)
        self.close_day(jour)
        return self.prepare_next_day(jour)

    def refresh_tsf(self, start_date: str, end_date: str) -> None:
        """Repopulate Tsf table for date range with period-based aggregation.

        Tsf now stores ONE row per category (not per day) with:
        - si_ttc: SI from start_date (first day in range)
        - sf_ttc: SF from end_date (last day in range)
        - achats_ttc: SUM of achats for the period
        - ca_ttc: SUM of CA for the period
        - env_ttc: SUM of ENV for the period
        - vente_theorique_ttc: calculated (si + achats - sf - env)
        - marge_ttc: ca - vente_theorique
        - marge_percent: (marge / vente_theorique) * 100
        """
        with self._connect() as conn:
            # Get SI for start date
            si_rows = conn.execute(
                """
                SELECT c.nom, t.si
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
            """,
                (start_date,),
            ).fetchall()
            si_map = {str(r[0]): int(r[1] or 0) for r in si_rows}

            # Get SF for end date
            sf_rows = conn.execute(
                """
                SELECT c.nom, t.sf
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
            """,
                (end_date,),
            ).fetchall()
            sf_map = {str(r[0]): int(r[1] or 0) for r in sf_rows}

            # Aggregate Achats, CA, ENV for the period
            agg_rows = conn.execute(
                """
                SELECT c.nom, 
                       SUM(t.achats) as total_achats, 
                       SUM(t.ca) as total_ca,
                       SUM(t.env) as total_env
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour BETWEEN ? AND ?
                GROUP BY c.nom
            """,
                (start_date, end_date),
            ).fetchall()

            if not agg_rows:
                return

            # Clear old Tsf data
            conn.execute("DELETE FROM Tsf")

            # Build and insert aggregated data
            for r in agg_rows:
                categorie = str(r[0])
                total_achats = int(r[1] or 0)
                total_ca = int(r[2] or 0)
                total_env = int(r[3] or 0)

                si_val = si_map.get(categorie, 0)
                sf_val = sf_map.get(categorie, 0)

                # Calculate derived values
                vente_theo = max(0, si_val + total_achats - sf_val - total_env)
                marge = total_ca - vente_theo
                marge_pct = (marge / vente_theo * 100.0) if vente_theo > 0 else 0.0

                # Get categorie_id
                cat_row = conn.execute(
                    "SELECT id FROM categories WHERE nom = ?", (categorie,)
                ).fetchone()
                if cat_row:
                    # Build SQL dynamically to avoid count mismatch
                    columns = "jour, categorie_id, si_ttc, achats_ttc, ca_ttc, env_ttc, sf_ttc, vente_theorique_ttc, marge_ttc, marge_percent, is_closed"
                    placeholders = "(" + ",".join(["?" for _ in columns.split(",")]) + ")"
                    sql = f"INSERT INTO Tsf ({columns}) VALUES {placeholders}"
                    conn.execute(
                        sql,
                        (
                            end_date,  # jour = period end
                            cat_row[0],
                            si_val,
                            total_achats,
                            total_ca,
                            total_env,
                            sf_val,
                            vente_theo,
                            marge,
                            marge_pct,
                            0,
                        ),
                    )

            conn.commit()

    def get_tsf_range(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Get Tsf data for date range (for reports)."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT 
                    t.jour, t.categorie_id, c.nom AS categorie,
                    t.si_ttc, t.achats_ttc, t.ca_ttc, t.env_ttc,
                    t.sf_ttc, t.vente_theorique_ttc, t.marge_ttc, t.marge_percent,
                    t.is_closed
                FROM Tsf t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour >= ? AND t.jour <= ?
                ORDER BY t.jour, c.nom
            """,
                (start_date, end_date),
            ).fetchall()
            return [dict(row) for row in rows]

    def ensure_day_initialized(self, jour: str) -> None:
        """Ensure day has Tcollecte rows, initialize if missing."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT COUNT(1) as cnt FROM Tcollecte WHERE jour = ?", (jour,)
            ).fetchone()
            if (existing["cnt"] or 0) > 0:
                return

        last_closed = self.get_last_closed_date()
        if last_closed:
            self.initialize_day(jour, carry_si_from=last_closed)
        else:
            self.initialize_day(jour)
