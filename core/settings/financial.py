"""Financial settings service for TVA, Currency, and Billetage management."""

from __future__ import annotations

from core.constants import BILLETAGE_DENOMINATIONS, CURRENCY_LABEL
from core.formatters import format_grouped_int, parse_grouped_int
from core.settings.service import SettingsService


class FinancialSettingsService:
    """Service for specialized financial settings."""

    DEFAULT_CURRENCY = CURRENCY_LABEL
    DEFAULT_TVA_RATE = 20.0
    DEFAULT_PRECISION = 0  # Ariary has no decimal places

    def __init__(self, settings_service: SettingsService) -> None:
        self._settings = settings_service

    # === TVA Management ===

    def get_tva_rate(self, default: float = DEFAULT_TVA_RATE) -> float:
        """Return the TVA rate."""
        value = self._settings.get_item_value("tva_rate", default, "float")
        return float(value) if value is not None else default

    def set_tva_rate(self, rate: float) -> None:
        """Update the TVA rate."""
        self._settings.set_item(
            key="tva_rate",
            value=rate,
            value_type="float",
            description="Taux de TVA en pourcentage",
            category_key="financial",
        )

    def calculate_ttc(self, ht: int) -> int:
        """Calculate TTC from HT using current TVA rate."""
        tva_rate = self.get_tva_rate() / 100
        return int(ht * (1 + tva_rate))

    def calculate_ht(self, ttc: int) -> int:
        """Calculate HT from TTC using current TVA rate."""
        tva_rate = self.get_tva_rate() / 100
        return int(ttc / (1 + tva_rate))

    def calculate_tva_from_ttc(self, ttc: int) -> int:
        """Calculate TVA amount from TTC."""
        ht = self.calculate_ht(ttc)
        return ttc - ht

    # === Currency/Monetary Settings ===

    def get_currency_label(self) -> str:
        """Return the currency label."""
        return self._settings.get_item_value("currency_label", self.DEFAULT_CURRENCY, "string")

    def set_currency_label(self, label: str) -> None:
        """Update the currency label."""
        self._settings.set_item(
            key="currency_label",
            value=label,
            value_type="string",
            description="Symbole de la devise",
            category_key="display",
        )

    def get_currency_precision(self) -> int:
        """Return the currency precision (0 for Ariary)."""
        return self._settings.get_item_value("currency_precision", self.DEFAULT_PRECISION, "int")

    def set_currency_precision(self, precision: int) -> None:
        """Update the currency precision."""
        self._settings.set_item(
            key="currency_precision",
            value=precision,
            value_type="int",
            description="Précision décimale de la devise",
            category_key="display",
        )

    def format_money(self, amount: int) -> str:
        """Format an amount with the currency symbol."""
        formatted = format_grouped_int(amount)
        currency = self.get_currency_label()
        return f"{formatted} {currency}"

    def format_money_ht(self, amount: int) -> str:
        """Format an amount as HT without TTC suffix."""
        formatted = format_grouped_int(amount)
        currency = self.get_currency_label()
        return f"{formatted} {currency} HT"

    def format_money_ttc(self, amount: int) -> str:
        """Format an amount as TTC without TTC suffix."""
        formatted = format_grouped_int(amount)
        currency = self.get_currency_label()
        return f"{formatted} {currency} TTC"

    def parse_money(self, text: str) -> int:
        """Parse a formatted money string."""
        return parse_grouped_int(text)

    # === Billetage/Coupures Management ===

    def get_billetage_denominations(self) -> tuple[int, ...]:
        """Return the bill denominations."""
        value = self._settings.get_item_value("billetage_denominations", None, "json")
        if value is None:
            return BILLETAGE_DENOMINATIONS
        if isinstance(value, list):
            return tuple(sorted(value, reverse=True))
        return BILLETAGE_DENOMINATIONS

    def set_billetage_denominations(self, denominations: list[int]) -> None:
        """Update the bill denominations."""
        if not self.validate_denominations(denominations):
            raise ValueError(
                "Invalid denominations: must be positive, unique, and sorted descending"
            )
        sorted_denoms = sorted(denominations, reverse=True)
        self._settings.set_item(
            key="billetage_denominations",
            value=sorted_denoms,
            value_type="json",
            description="Coupures de billets",
            category_key="display",
        )

    def validate_denominations(self, denominations: list[int]) -> bool:
        """Validate denominations (sorted, positive, unique)."""
        if not denominations:
            return False
        # All positive
        if any(d <= 0 for d in denominations):
            return False
        # All unique
        if len(denominations) != len(set(denominations)):
            return False
        # Sorted descending
        return denominations == sorted(denominations, reverse=True)

    # === Calculate total from denominations ===

    def calculate_billetage_total(self, denominations: list[int], quantities: list[int]) -> int:
        """Calculate total from denominations and their quantities."""
        if len(denominations) != len(quantities):
            raise ValueError("Denominations and quantities must have same length")
        return sum(d * q for d, q in zip(denominations, quantities))

    def calculate_billetage_breakdown(self, amount: int) -> dict[int, int]:
        """Calculate optimal breakdown for an amount."""
        denominations = list(self.get_billetage_denominations())
        breakdown: dict[int, int] = {d: 0 for d in denominations}
        remaining = amount

        for denom in denominations:
            if remaining >= denom:
                count = remaining // denom
                breakdown[denom] = count
                remaining -= count * denom

        return breakdown
