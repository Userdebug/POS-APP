"""Database package — re-exports DatabaseManager for backward compatibility."""

from __future__ import annotations

from core.database._manager import DatabaseManager

__all__ = ["DatabaseManager"]
