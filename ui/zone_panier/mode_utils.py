"""Mode normalization utilities for ZonePanier."""

import logging

logger = logging.getLogger(__name__)

# Mode mapping: legacy -> standard
_MODE_MAP = {
    "vente": "vente",
    "caisse": "vente",
    "achat": "achat",
    "reception": "achat",
    "achats": "achat",
}


def _normalize_mode(mode: str) -> str:
    """Normalize mode name to standard form.

    Args:
        mode: Mode name (caisse, reception, vente, achat)

    Returns:
        Normalized mode name (vente, achat)
    """
    if not mode:
        logger.warning("Empty mode provided, defaulting to 'vente'")
        return "vente"

    normalized = str(mode).lower().strip()
    result = _MODE_MAP.get(normalized, normalized)

    if result != normalized and normalized in _MODE_MAP:
        logger.debug(f"Mode '{mode}' normalized to '{result}'")

    return result


def is_vente_mode(mode: str) -> bool:
    """Check if mode is a vente mode."""
    return _normalize_mode(mode) == "vente"


def is_achat_mode(mode: str) -> bool:
    """Check if mode is an achat mode."""
    return _normalize_mode(mode) == "achat"
