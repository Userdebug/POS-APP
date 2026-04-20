"""DailyTrackingService - application-facing API for daily tracking operations.

This service wraps DailyTrackingRepository and provides a clean API
for UI/controllers while ensuring Tsf is refreshed after mutations.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    pass

from repositories.daily_tracking_repository import DailyTrackingRepository, DailyTrack

logger = logging.getLogger(__name__)

_OW_CATEGORY_PARENT = "Catégorie 1 - OW (Owners)"


class DailyTrackingService:
    """Service layer for daily tracking operations."""

    def __init__(self, repo: DailyTrackingRepository) -> None:
        self._repo = repo

    @classmethod
    def create(
        cls,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        today_iso: Callable[[], str],
        day_bounds: Callable[[str], tuple[str, str]],
    ) -> "DailyTrackingService":
        """Factory method to create service with repository."""

        def resolve_category_names(names: list[str]) -> dict[str, int]:
            cat_id_map: dict[str, int] = {}
            with connect() as conn:
                for name in names:
                    row = conn.execute(
                        "SELECT id FROM categories WHERE nom = ?", (name,)
                    ).fetchone()
                    if row:
                        cat_id_map[name] = int(row["id"])
            return cat_id_map

        repo = DailyTrackingRepository(
            connect=connect,
            today_iso=today_iso,
            day_bounds=day_bounds,
            resolve_category_names=resolve_category_names,
        )
        return cls(repo)

    @property
    def repo(self) -> DailyTrackingRepository:
        """Access underlying repository for read operations."""
        return self._repo

    def get_dashboard_data(self, jour: str | None = None) -> list[DailyTrack]:
        """Get all tracks for a day, ensuring day is initialized."""
        target_day = jour or self._repo._today_iso()
        self._repo.ensure_day_initialized(target_day)
        self._repo.update_stock_metrics(target_day)
        self._repo.update_purchases(target_day)
        return self._repo.list_tracks(target_day)

    def record_sales(self, jour: str, increments: dict[str, int]) -> None:
        """Record sales increments for a day."""
        if not increments:
            return
        self._repo.update_live_ca(jour, increments)
        self._repo.refresh_tsf(jour, jour)

    def record_purchases(self, jour: str) -> None:
        """Record purchases for a day from Tachats."""
        self._repo.update_purchases(jour)
        self._repo.refresh_tsf(jour, jour)

    def update_stock_metrics(self, jour: str) -> None:
        """Update stock metrics (SF, ENV) for a day."""
        self._repo.update_stock_metrics(jour)
        self._repo.refresh_tsf(jour, jour)

    def set_final_ca(self, jour: str, final_ca: dict[str, int]) -> None:
        """Set final CA for closure."""
        self._repo.set_final_ca(jour, final_ca)
        self._repo.refresh_tsf(jour, jour)

    def close_day(self, jour: str) -> None:
        """Mark day as closed."""
        self._repo.close_day(jour)
        self._repo.refresh_tsf(jour, jour)

    def finalize_day(self, jour: str, final_ca: dict[str, int]) -> str:
        """Complete closure: set final CA, close day, prepare next day. Returns next_day."""
        next_day = self._repo.finalize_day(jour, final_ca)
        self._repo.refresh_tsf(jour, next_day)
        return next_day

    def initialize_day(self, jour: str, carry_si_from: str | None = None) -> None:
        """Initialize a day with SI from previous day or current stock."""
        self._repo.initialize_day(jour, carry_si_from)
        self._repo.refresh_tsf(jour, jour)

    def get_tracks(self, jour: str) -> list[DailyTrack]:
        """Get tracks for a day."""
        return self._repo.list_tracks(jour)

    def get_tracks_range(self, start: str, end: str) -> list[DailyTrack]:
        """Get tracks for a date range."""
        return self._repo.list_tracks_range(start, end)

    def get_track(self, jour: str, category_name: str) -> DailyTrack | None:
        """Get a single track."""
        return self._repo.get_track(jour, category_name)

    def is_closed(self, jour: str) -> bool:
        """Check if day is closed."""
        return self._repo.is_closed(jour)

    def get_open_days(self) -> list[str]:
        """Get list of unclosed days."""
        return self._repo.get_open_days()

    def get_last_closed_date(self) -> str | None:
        """Get most recent closed date."""
        return self._repo.get_last_closed_date()

    def refresh_tsf(self, start_date: str, end_date: str) -> None:
        """Refresh Tsf table for date range."""
        self._repo.refresh_tsf(start_date, end_date)

    def get_tsf_data(self, start_date: str, end_date: str) -> list[dict[str, Any]]:
        """Get Tsf data for reports."""
        return self._repo.get_tsf_range(start_date, end_date)

    def compute_temporary_ca(self, jour: str) -> dict[str, int]:
        """Compute temporary CA from sales for a day."""
        with self._repo._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom AS categorie,
                       SUM(v.quantite * CAST(ROUND(p.pa * 1.2, 0) AS INTEGER)) AS ca_temporaire
                FROM ventes v
                JOIN produits p ON v.produit_id = p.id
                JOIN categories c ON p.categorie_id = c.id
                JOIN categories parent ON c.parent_id = parent.id
                WHERE v.jour = ? AND v.deleted = 0 AND parent.nom = ?
                GROUP BY c.nom
            """,
                (jour, _OW_CATEGORY_PARENT),
            ).fetchall()
            return {str(r["categorie"]): int(r["ca_temporaire"] or 0) for r in rows}

    def sync_unclosed_day(self, jour: str) -> None:
        """Sync metrics for unclosed day (called from UI after sale)."""
        self._repo.ensure_day_initialized(jour)
        self._repo.update_stock_metrics(jour)
        self._repo.update_purchases(jour)

        ca_increments = self.compute_temporary_ca(jour)
        if ca_increments:
            self._repo.update_live_ca(jour, ca_increments)
        self._repo.refresh_tsf(jour, jour)

    def get_closure_rows(self, jour: str) -> list[dict[str, Any]]:
        """Get rows for closure dialog."""
        tracks = self._repo.list_tracks(jour)
        return [
            {
                "categorie": t.category_name,
                "ca_ttc_final": t.ca,
                "si": t.stock_initial,
                "achats": t.purchases,
                "sf": t.stock_final,
                "env": t.removed_value,
                "cloturee": t.is_closed,
            }
            for t in tracks
        ]

    def close_day(self, jour: str, final_ca_rows: list[dict[str, Any]]) -> None:
        """Close day with final CA values.

        Args:
            jour: The day to close (YYYY-MM-DD)
            final_ca_rows: List of dicts with 'categorie' and 'ca_ttc_final' keys
        """
        final_ca = {r.get("categorie"): r.get("ca_ttc_final", 0) for r in final_ca_rows}
        self._repo.set_final_ca(jour, final_ca)
        self._repo.close_day(jour)
        self._repo.refresh_tsf(jour, jour)
