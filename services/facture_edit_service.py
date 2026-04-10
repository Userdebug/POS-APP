"""Service metier pour l'edition d'une ligne facture."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.formatters import format_grouped_int, parse_grouped_int


@dataclass(frozen=True)
class FactureCellEditResult:
    handled: bool
    line: dict[str, Any]
    formatted_cell_value: str | None
    formatted_prc_value: str | None
    formatted_total_value: str | None


from core.utils import calculate_line_total


class FactureLineEditService:
    """Applique une modification de cellule facture et retourne les valeurs d'affichage."""

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
    def apply_cell_edit(
        cls,
        line: dict[str, Any],
        *,
        col: int,
        text: str,
    ) -> FactureCellEditResult:
        updated = dict(line)
        raw_text = str(text or "").strip()

        if col == 0:
            updated["nom"] = raw_text
            return FactureCellEditResult(
                handled=True,
                line=updated,
                formatted_cell_value=None,
                formatted_prc_value=None,
                formatted_total_value=format_grouped_int(cls._line_total(updated)),
            )

        if col == 1:
            updated["categorie"] = raw_text
            return FactureCellEditResult(
                handled=True,
                line=updated,
                formatted_cell_value=None,
                formatted_prc_value=None,
                formatted_total_value=format_grouped_int(cls._line_total(updated)),
            )

        if col in (2, 4):
            value = max(0, parse_grouped_int(raw_text))
            if col == 2:
                updated["pa"] = value
                updated["prc"] = int(round(value * 1.2))
                updated["prix"] = value
                prc_fmt = format_grouped_int(updated["prc"])
            else:
                updated["pv"] = value
                prc_fmt = None

            return FactureCellEditResult(
                handled=True,
                line=updated,
                formatted_cell_value=format_grouped_int(value),
                formatted_prc_value=prc_fmt,
                formatted_total_value=format_grouped_int(cls._line_total(updated)),
            )

        return FactureCellEditResult(
            handled=False,
            line=dict(line),
            formatted_cell_value=None,
            formatted_prc_value=None,
            formatted_total_value=None,
        )
