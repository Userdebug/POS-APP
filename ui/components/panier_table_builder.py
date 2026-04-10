"""Builder metier des lignes d'affichage pour les tables panier/facture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.formatters import format_grouped_int
from core.utils import calculate_line_total


@dataclass(frozen=True)
class FactureCellDescriptor:
    value: str
    align_right: bool
    editable: bool


@dataclass(frozen=True)
class FactureRowDescriptor:
    cells: tuple[FactureCellDescriptor, ...]
    quantity: int


@dataclass(frozen=True)
class PanierTablesDescriptor:
    caisse_rows: list[dict[str, Any]]
    caisse_total: int
    facture_rows: list[FactureRowDescriptor]


class PanierTableBuilder:
    """Construit les donnees d'affichage independamment des widgets Qt."""

    @staticmethod
    def _safe_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return int(default)

    @staticmethod
    def _line_total(line: dict[str, Any]) -> int:
        """Calculate line total using unified utility function.

        Args:
            line: Dictionary with product line data (pa, qte fields)

        Returns:
            Total price (pa * qte)
        """
        return calculate_line_total(line, price_field="pa")

    @classmethod
    def _build_facture_row(cls, line: dict[str, Any]) -> FactureRowDescriptor:
        values = (
            str(line.get("nom", "")),
            str(line.get("categorie", "-")),
            format_grouped_int(line.get("pa", 0)),
            format_grouped_int(line.get("prc", 0)),
            format_grouped_int(line.get("pv", 0)),
            str(line.get("qte", 1)),
            format_grouped_int(cls._line_total(line)),
        )
        cells = tuple(
            FactureCellDescriptor(
                value=value,
                align_right=index in (2, 3, 4, 5, 6),
                editable=index not in (3, 5, 6),
            )
            for index, value in enumerate(values)
        )
        qte = max(1, cls._safe_int(line.get("qte", 1) or 1, default=1))
        return FactureRowDescriptor(cells=cells, quantity=qte)

    @classmethod
    def build(cls, lines: list[dict[str, Any]]) -> PanierTablesDescriptor:
        caisse_rows = [dict(line) for line in lines]
        facture_rows = [cls._build_facture_row(line) for line in lines]
        caisse_total = sum(cls._line_total(line) for line in lines)
        return PanierTablesDescriptor(
            caisse_rows=caisse_rows,
            caisse_total=caisse_total,
            facture_rows=facture_rows,
        )
