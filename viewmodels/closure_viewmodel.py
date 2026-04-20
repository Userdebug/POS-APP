"""ViewModel for closure operations.

This module provides a ViewModel layer for closure operations, wrapping the
existing DailyTrackingService with additional convenience methods.

No PyQt6 dependencies - returns plain Python data structures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from core.database import DatabaseManager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClosureRow:
    """Single row for closure dialog."""

    categorie: str
    ca_ttc_final: int


@dataclass(frozen=True)
class ClosureResult:
    """Result of a closure operation."""

    success: bool
    jour: str
    message: str


class ClosureViewModel:
    """ViewModel for closure operations.

    Provides methods to prepare and execute closure operations,
    returning simple data structures suitable for UI consumption.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize ViewModel with database access.

        Args:
            db_manager: DatabaseManager instance for data access.
        """
        self._db_manager = db_manager
        self._tracking_service = db_manager.daily_tracking

    def get_closure_rows(self, jour: str) -> list[ClosureRow]:
        """Get rows to display in the closure dialog.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            List of ClosureRow objects ready for the dialog.
        """
        try:
            dialog_rows = self._tracking_service.get_closure_rows(jour)
            return [
                ClosureRow(
                    categorie=str(row.get("categorie", "")),
                    ca_ttc_final=int(row.get("ca_ttc_final", 0) or 0),
                )
                for row in dialog_rows
            ]
        except Exception as exc:
            logger.warning("Failed to get closure rows for %s: %s", jour, exc)
            return []

    def execute_closure(
        self,
        jour: str,
        ca_rows: list[dict[str, Any]],
    ) -> ClosureResult:
        """Execute closure operation for a given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).
            ca_rows: List of dicts with 'categorie' and 'ca_ttc_final' keys.

        Returns:
            ClosureResult indicating success or failure.
        """
        try:
            self._tracking_service.close_day(jour, ca_rows)
            logger.info("Cloture effectuee avec succes pour %s", jour)
            return ClosureResult(
                success=True,
                jour=jour,
                message=f"Cloture effectuee pour le {jour}",
            )
        except Exception as exc:
            logger.error("Echec de la cloture pour %s: %s", jour, exc)
            return ClosureResult(
                success=False,
                jour=jour,
                message=f"Echec de la cloture: {str(exc)}",
            )

    def get_total_closure(self, jour: str) -> int:
        """Get total CA for the day from closure data.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            Total CA in TTC.
        """
        try:
            rows = self._db_manager.get_daily_closure_by_category(jour)
            return sum(int(row.get("ca_ttc_final", 0) or 0) for row in rows)
        except Exception as exc:
            logger.warning("Failed to get closure total for %s: %s", jour, exc)
            return 0

    def is_day_closed(self, jour: str) -> bool:
        """Check if a day is already closed.

        Args:
            jour: Date in ISO format (YYYY-MM-DD).

        Returns:
            True if the day is closed, False otherwise.
        """
        try:
            rows = self._db_manager.get_daily_followup_by_category(jour)
            return any(int(row.get("cloturee", 0)) == 1 for row in rows)
        except Exception as exc:
            logger.warning("Failed to check if day is closed for %s: %s", jour, exc)
            return False
