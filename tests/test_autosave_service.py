"""Tests for autosave service."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, patch


class TestAutosaveService(TestCase):
    """Tests for AutosaveService."""

    def setUp(self):
        self.db_manager = MagicMock()
        from services.autosave_service import AutosaveService

        self.service = AutosaveService(self.db_manager)

    def test_is_enabled_default(self):
        """Autosave should be enabled by default."""
        self.db_manager.get_parameter.return_value = "1"
        self.assertTrue(self.service.is_enabled())

    def test_is_enabled_disabled(self):
        """Autosave should respect disabled setting."""
        self.db_manager.get_parameter.return_value = "0"
        self.assertFalse(self.service.is_enabled())

    def test_get_backup_dir_default(self):
        """Backup dir should default to backups/."""
        self.db_manager.get_parameter.return_value = "backups/"
        backup_dir = self.service.get_backup_dir()
        self.assertTrue(str(backup_dir).endswith("backups"))

    def test_get_retention_default(self):
        """Retention should default to 10."""
        self.db_manager.get_parameter.return_value = "10"
        self.assertEqual(self.service.get_retention(), 10)

    def test_get_retention_invalid(self):
        """Retention should fallback to 10 for invalid values."""
        self.db_manager.get_parameter.return_value = "invalid"
        self.assertEqual(self.service.get_retention(), 10)

    def test_run_autosave_disabled(self):
        """Autosave should skip when disabled."""
        self.db_manager.get_parameter.return_value = "0"
        result = self.service.run_autosave("2024-01-15")
        self.assertFalse(result)

    @patch("services.autosave_service.DataExportService")
    def test_run_autosave_success(self, mock_export_cls):
        """Autosave should create backup file when enabled."""
        self.db_manager.get_parameter.side_effect = lambda key, default: {
            "autosave_enabled": "1",
            "backup_dir": "backups/",
            "backup_retention": "10",
        }.get(key, default)

        mock_export = MagicMock()
        mock_export_cls.return_value = mock_export

        result = self.service.run_autosave("2024-01-15")

        self.assertTrue(result)
        mock_export.export_all.assert_called_once()

    def test_list_backups_empty(self):
        """List backups should return empty list when no backups exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.db_manager.get_parameter.return_value = tmpdir
            backups = self.service.list_backups()
            self.assertEqual(backups, [])

    def test_list_backups_with_files(self):
        """List backups should return backup file info."""
        with tempfile.TemporaryDirectory() as tmpdir:
            self.db_manager.get_parameter.return_value = tmpdir

            # Create fake backup files
            Path(tmpdir, "autosave_2024-01-15_120000.json").touch()
            Path(tmpdir, "autosave_2024-01-15_130000.json").touch()

            backups = self.service.list_backups("2024-01-15")

            self.assertEqual(len(backups), 2)
            self.assertTrue(backups[0]["filename"].startswith("autosave_"))
