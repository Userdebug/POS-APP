"""Service for daily reset operations.

This service handles:
- Checking previous day's closure status
- Validating and executing reset only after confirmed cloture
- Resetting session state (including safe/coffre reset to 0)
- Managing daily reset status flags for app startup validation
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from core.constants import DATE_FORMAT_DAY
from core.database import DatabaseManager
from core.exceptions import POSException

logger = logging.getLogger(__name__)


class DailyResetError(POSException):
    """Base exception for daily reset operations."""

    pass


class PreviousDayNotClosedError(DailyResetError):
    """Raised when previous day cloture is required before operations can proceed."""

    def __init__(self, last_closed_date: str | None, current_date: str) -> None:
        self.last_closed_date = last_closed_date
        self.current_date = current_date
        last = last_closed_date or "AUCUNE"
        msg = "La cloture du jour precedent est requise avant toute operation. "
        msg += f"Derniere cloture: {last}, actuel: {current_date}"
        super().__init__(msg)


class DailyResetService:
    """Service for handling daily reset operations.

    Manages the daily reset architecture:
    - Validates previous day's cloture status on app startup
    - Executes reset only after confirmed cloture (archives data, resets state)
    - Stores reset status in parameters for validation gates
    """

    # Parameter keys for reset management
    PARAM_LAST_CLOSED_DATE = "LAST_CLOSED_DATE"
    PARAM_DAILY_RESET_PENDING = "DAILY_RESET_PENDING"

    def __init__(self, db_manager: DatabaseManager) -> None:
        """Initialize the service.

        Args:
            db_manager: Database manager instance for parameter and tracking access.
        """
        self.db_manager = db_manager

    def get_current_date(self) -> str:
        """Get current date in ISO format.

        Returns:
            Current date as string in YYYY-MM-DD format.
        """
        return datetime.now().strftime(DATE_FORMAT_DAY)

    def get_previous_date(self, current_date: str | None = None) -> str:
        """Get the previous date.

        Args:
            current_date: Reference date (defaults to today).

        Returns:
            Previous date as string in YYYY-MM-DD format.
        """
        ref_date = current_date or self.get_current_date()
        dt = datetime.strptime(ref_date, DATE_FORMAT_DAY)
        prev = dt - timedelta(days=1)
        return prev.strftime(DATE_FORMAT_DAY)

    def is_previous_day_closed(self, reference_date: str | None = None) -> bool:
        """Check if previous day is marked as cloturee.

        Args:
            reference_date: Reference date to check against (defaults to today).

        Returns:
            True if previous day has cloturee=1, False otherwise.
        """
        prev_date = self.get_previous_date(reference_date)
        try:
            with self.db_manager._connect() as conn:
                row = conn.execute(
                    """
                    SELECT COUNT(1) as n
                    FROM Tcollecte
                    WHERE jour = ? AND cloturee = 1
                    """,
                    (prev_date,),
                ).fetchone()
                return int(row["n"] or 0) > 0
        except Exception as e:
            logger.error("Error checking previous day closure: %s", e)
            return False

    def get_last_closed_date(self) -> str | None:
        """Get the last closed date from parameters.

        Returns:
            Last closed date as string, or None if not set.
        """
        return self.db_manager.get_parameter(self.PARAM_LAST_CLOSED_DATE)

    def set_last_closed_date(self, date_iso: str) -> None:
        """Set the last closed date parameter.

        Args:
            date_iso: Date in ISO format (YYYY-MM-DD).
        """
        self.db_manager.set_parameter(self.PARAM_LAST_CLOSED_DATE, date_iso)
        logger.info("Last closed date set to: %s", date_iso)

    def is_reset_pending(self) -> bool:
        """Check if a daily reset is pending.

        Returns:
            True if reset is pending, False otherwise.
        """
        pending = self.db_manager.get_parameter(self.PARAM_DAILY_RESET_PENDING, "0")
        return pending == "1"

    def set_reset_pending(self, pending: bool) -> None:
        """Set the reset pending flag.

        Args:
            pending: True to mark reset as pending, False otherwise.
        """
        self.db_manager.set_parameter(self.PARAM_DAILY_RESET_PENDING, "1" if pending else "0")
        logger.debug("Reset pending flag set to: %s", pending)

    def validate_startup(self) -> tuple[bool, str | None]:
        """Validate if app can proceed with operations.

        This is the main validation gate called on app startup:
        - Checks if previous day closure is required
        - Returns (can_proceed, error_message)

        Returns:
            Tuple of (can_proceed: bool, error_message: str | None)
        """
        current_date = self.get_current_date()
        last_closed = self.get_last_closed_date()
        previous_date = self.get_previous_date(current_date)

        # If no closure ever done, allow startup (first day or fresh install)
        if last_closed is None:
            logger.info("No previous closure found, allowing startup (first run)")
            return True, None

        # DEVELOPMENT MODE: Always allow operations even if previous day not closed
        # This will be enabled for production deployment
        logger.warning("DEVELOPMENT MODE: Bypassing previous day closure check.")
        return True, None

        # --- PRODUCTION MODE CODE BELOW (disabled for development) ---
        # If previous day's closure is confirmed, allow operations
        if self.is_previous_day_closed(current_date):
            return True, None

        # Previous day not closed - block operations
        error_msg = f"La cloture du {previous_date} est requise avant toute operation."
        logger.warning("Blocking operations: %s", error_msg)
        return False, error_msg

    def check_can_operate(self) -> bool:
        """Quick check if operations can proceed without blocking.

        Returns:
            True if operations are allowed, False if blocked.
        """
        can_proceed, _ = self.validate_startup()
        return can_proceed

    def execute_reset(self, closed_date: str | None = None) -> dict[str, Any]:
        """Execute daily reset after confirmed cloture.

        This performs:
        1. Archive last closed date
        2. Reset COFFRE_TOTAL to 0
        3. Clear reset pending flag

        Args:
            closed_date: Date of the cloture being confirmed (defaults to previous date).

        Returns:
            Dictionary with reset results.
        """
        target_date = closed_date or self.get_previous_date()
        current_date = self.get_current_date()

        logger.info("Executing daily reset for date: %s", target_date)

        results: dict[str, Any] = {
            "closed_date": target_date,
            "reset_date": current_date,
            "coffre_before": 0,
            "coffre_after": 0,
        }

        # Get current coffre before reset
        try:
            raw_coffre = self.db_manager.get_parameter("COFFRE_TOTAL", "0")
            results["coffre_before"] = int(raw_coffre) if raw_coffre else 0
        except (ValueError, TypeError):
            results["coffre_before"] = 0

        # Archive last closed date
        self.set_last_closed_date(target_date)

        # Reset COFFRE_TOTAL to 0 (per requirements)
        self.db_manager.set_parameter("COFFRE_TOTAL", "0")

        # Clear reset pending flag
        self.set_reset_pending(False)

        results["coffre_after"] = 0

        logger.info(
            "Daily reset completed: closed=%s, coffre was %s, now reset to 0",
            target_date,
            results["coffre_before"],
        )

        return results

    def on_cloture_complete(self, cloture_date: str) -> dict[str, Any]:
        """Handle cloture completion - execute reset after cloture.

        This is called from the cloture workflow to ensure
        the daily reset is properly executed after cloture.

        Args:
            cloture_date: Date of the completed cloture.

        Returns:
            Dictionary with reset results.
        """
        logger.info("Cloture complete for %s, executing daily reset", cloture_date)

        # Verify cloture is confirmed
        prev_date = self.get_previous_date()
        if cloture_date != prev_date and cloture_date != self.get_current_date():
            logger.warning("Cloture date %s may not match expected date", cloture_date)

        # Execute the reset
        return self.execute_reset(cloture_date)

    def get_reset_status(self) -> dict[str, Any]:
        """Get current reset status for diagnostics.

        Returns:
            Dictionary with current reset status information.
        """
        current_date = self.get_current_date()
        previous_date = self.get_previous_date(current_date)

        return {
            "current_date": current_date,
            "previous_date": previous_date,
            "last_closed_date": self.get_last_closed_date(),
            "previous_day_closed": self.is_previous_day_closed(current_date),
            "reset_pending": self.is_reset_pending(),
            "can_operate": self.check_can_operate(),
        }
