"""Helpers de formatage/parsing numerique pour l'UI."""

from __future__ import annotations

from datetime import date, datetime

__all__ = [
    "format_grouped_int",
    "parse_grouped_int",
    "parse_expiry_dates",
    "format_expiry_dates",
    "format_dlv_dlc_date",
    "parse_dlv_dlc_date",
]


def format_grouped_int(value: int | float | str | None) -> str:
    """Formate un entier avec separateur de milliers par espace: 1 234 567."""
    if value is None:
        return "0"
    try:
        number = int(float(str(value).replace(" ", "").replace("\u00a0", "")))
    except (TypeError, ValueError):
        return "0"
    return f"{number:,}".replace(",", " ")


def parse_grouped_int(text: str | int | float | None, default: int = 0) -> int:
    """Parse un entier potentiellement formate avec espaces de milliers."""
    if text is None:
        return int(default)
    if isinstance(text, (int, float)):
        return int(text)
    cleaned = str(text).replace("\u00a0", " ").replace(" ", "").strip()
    if not cleaned:
        return int(default)
    try:
        return int(float(cleaned))
    except ValueError:
        return int(default)


def parse_expiry_dates(value: str | None) -> date | None:
    text = (value or "").strip()
    if not text:
        return None
    # Extract date part: handle datetime strings like "2025-04-15 00:00:00" or "2025-04-15T00:00:00"
    # Take the first part before space or T
    candidate = text.split()[0] if " " in text else text.split("T")[0]
    # Try formats: dd/mm/yy, dd/mm/yyyy (existing data), yyyy-mm-dd
    for fmt in ["%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"]:
        try:
            return datetime.strptime(candidate, fmt).date()
        except ValueError:
            continue
    return None


def format_expiry_dates(value: str | None) -> str:
    parsed = parse_expiry_dates(value)
    if parsed is None:
        return (value or "").strip()
    return parsed.strftime("%d/%m/%y")


def format_dlv_dlc_date(value: str | None) -> str:
    """Formate la date DLV/DLC (DLV = Date Limite de Vente, DLC = Date Limite de Consommation).

    Args:
        value: Date string potentially in various formats

    Returns:
        Formatted date string in YYYY-MM-DD format, or original value if invalid
    """
    return format_expiry_dates(value)


def parse_dlv_dlc_date(value: str | None) -> date | None:
    """Parse la date DLV/DLC.

    Args:
        value: Date string to parse

    Returns:
        datetime.date object or None if invalid
    """
    return parse_expiry_dates(value)
