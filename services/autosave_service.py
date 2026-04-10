"""Autosave service for automatic backup after cash closure."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.constants import DATE_FORMAT_DAY
from services.data_export_service import DataExportService

logger = logging.getLogger(__name__)

DEFAULT_BACKUP_DIR = "backups/"
DEFAULT_RETENTION = 10


class AutosaveService:
    """Service for automatic backup after cash closure.

    Args:
        db_manager: Database manager instance.
    """

    def __init__(self, db_manager: Any) -> None:
        self._db_manager = db_manager

    def is_enabled(self) -> bool:
        """Check if autosave is enabled.

        Returns:
            True if autosave is enabled, False otherwise.
        """
        enabled = self._db_manager.get_parameter("autosave_enabled", "1")
        return enabled == "1"

    def get_backup_dir(self) -> Path:
        """Get the backup directory path.

        Returns:
            Path to the backup directory.
        """
        backup_dir = self._db_manager.get_parameter("backup_dir", DEFAULT_BACKUP_DIR)
        base_dir = Path(__file__).resolve().parent.parent.parent
        return base_dir / backup_dir

    def get_retention(self) -> int:
        """Get the backup retention count.

        Returns:
            Number of backups to keep.
        """
        retention = self._db_manager.get_parameter("backup_retention", str(DEFAULT_RETENTION))
        try:
            return int(retention)
        except ValueError:
            return DEFAULT_RETENTION

    def run_autosave(self, day: str | None = None) -> bool:
        """Run the autosave for a given day.

        Args:
            day: Day in ISO format (YYYY-MM-DD), defaults to today.

        Returns:
            True if autosave succeeded, False otherwise.
        """
        if not self.is_enabled():
            logger.debug("Autosave disabled, skipping")
            return False

        target_day = day or datetime.now().strftime(DATE_FORMAT_DAY)
        backup_dir = self.get_backup_dir()

        # Create backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"autosave_{target_day}_{timestamp}.json"

        try:
            # Ensure backup directory exists
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Export data
            export_service = DataExportService(self._db_manager)
            export_service.export_all(backup_file, day=target_day)

            logger.info(f"Autosave completed: {backup_file}")

            # Manage retention
            self._manage_retention(backup_dir, target_day)

            return True

        except Exception as e:
            logger.exception(f"Autosave failed: {e}")
            return False

    def _manage_retention(self, backup_dir: Path, target_day: str) -> None:
        """Manage backup retention by deleting old backups.

        Args:
            backup_dir: Path to the backup directory.
            target_day: The day that was just backed up.
        """
        retention = self.get_retention()

        # Find all autosave files for this day
        pattern = f"autosave_{target_day}_*.json"
        existing_backups = sorted(backup_dir.glob(pattern), reverse=True)

        # Delete old backups beyond retention
        if len(existing_backups) > retention:
            for old_backup in existing_backups[retention:]:
                try:
                    old_backup.unlink()
                    logger.info(f"Deleted old backup: {old_backup}")
                except OSError as e:
                    logger.warning(f"Failed to delete old backup {old_backup}: {e}")

    def list_backups(self, day: str | None = None) -> list[dict[str, Any]]:
        """List available backups.

        Args:
            day: Optional day to filter backups. If None, lists all backups.

        Returns:
            List of backup file information.
        """
        backup_dir = self.get_backup_dir()

        if not backup_dir.exists():
            return []

        if day:
            pattern = f"autosave_{day}_*.json"
        else:
            pattern = "autosave_*.json"

        backups = []
        for f in sorted(backup_dir.glob(pattern), reverse=True):
            stat = f.stat()
            backups.append(
                {
                    "filename": f.name,
                    "path": str(f),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        return backups
