"""Logique metier de comptage billets."""

from dataclasses import dataclass


@dataclass
class CashCountResult:
    subtotals: dict[int, int]
    total_billets: int


class CashCounterService:
    """Service pur pour calculer les sous-totaux et total billets."""

    @staticmethod
    def compute(
        coupures: list[int],
        quantities: dict[int, int],
    ) -> CashCountResult:
        subtotals: dict[int, int] = {}
        total = 0
        for value in coupures:
            qty = max(0, int(quantities.get(value, 0)))
            subtotal = int(value) * qty
            subtotals[value] = subtotal
            total += subtotal
        return CashCountResult(
            subtotals=subtotals,
            total_billets=total,
        )
