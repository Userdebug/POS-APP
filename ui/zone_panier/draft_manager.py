"""Draft line management for ZonePanier."""

import logging

from .mode_utils import _normalize_mode

logger = logging.getLogger(__name__)


class DraftManager:
    """Manages draft lines for both vente and achat modes."""

    def __init__(self):
        self._drafts: dict[str, dict | None] = {
            "vente": None,
            "achat": None,
        }

    def get_draft(self, mode: str | None = None) -> dict | None:
        """Get draft for the specified mode or current mode."""
        normalized = _normalize_mode(mode) if mode else "vente"
        return self._drafts.get(normalized)

    def set_draft(self, draft: dict | None, mode: str | None = None) -> None:
        """Set draft for the specified mode."""
        normalized = _normalize_mode(mode) if mode else "vente"
        self._drafts[normalized] = draft
        logger.debug(f"Draft set for mode '{normalized}': {draft is not None}")

    def clear_draft(self, mode: str | None = None) -> None:
        """Clear draft for the specified mode."""
        normalized = _normalize_mode(mode) if mode else "vente"
        self._drafts[normalized] = None
        logger.debug(f"Draft cleared for mode '{normalized}'")

    def has_draft(self, mode: str | None = None) -> bool:
        """Check if there's a draft for the specified mode."""
        normalized = _normalize_mode(mode) if mode else "vente"
        return self._drafts.get(normalized) is not None

    def clear_all(self) -> None:
        """Clear all drafts."""
        for key in self._drafts:
            self._drafts[key] = None
