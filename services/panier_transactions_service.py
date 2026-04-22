"""Services metier pour les transactions de panier (caisse/reception)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.constants import DATE_FORMAT_FACTURE_REF, FACTURE_NUMBER_PREFIX


@dataclass(frozen=True)
class EncaissementSummary:
    total: int
    nb_lignes: int
    nb_articles: int


class PanierTransactionsService:
    """Regroupe les calculs et mises a jour metier lies aux transactions panier."""

    @staticmethod
    def line_total(ligne: dict[str, Any]) -> int:
        """Calculate line total (price × quantity).

        Args:
            ligne: Dictionary with product line data (prix/pv, qte fields)

        Returns:
            Total price (prix * qte)
        """
        # Check both fields to maintain compatibility
        price = int(ligne.get("prix", ligne.get("pv", 0)) or 0)
        qte = int(ligne.get("qte", 1) or 1)
        return price * qte

    @classmethod
    def compute_collection_summary(cls, items: list[dict[str, Any]]) -> EncaissementSummary:
        return EncaissementSummary(
            total=sum(cls.line_total(ligne) for ligne in items),
            nb_lignes=len(items),
            nb_articles=sum(max(1, int(ligne.get("qte", 1) or 1)) for ligne in items),
        )

    @classmethod
    def build_sales_rows(
        cls, items: list[dict[str, Any]], *, day: str, heure: str
    ) -> list[dict[str, Any]]:
        return [
            {
                "jour": day,
                "heure": heure,
                "produit_id": int(ligne.get("id", 0) or 0),
                "produit": str(ligne.get("nom", "")),
                "quantite": max(1, int(ligne.get("qte", 1) or 1)),
                "prix_unitaire": int(ligne.get("prix", ligne.get("pv", 0)) or 0),
            }
            for ligne in items
        ]

    @staticmethod
    def compute_invoice_total_preview(items: list[dict[str, Any]]) -> int:
        total = 0
        for ligne in items:
            pa = max(0, int(ligne.get("pa", 0) or 0))
            qte = max(1, int(ligne.get("qte", 1) or 1))
            total += pa * qte
        return total

    @staticmethod
    def build_invoice_number(now: datetime | None = None) -> str:
        stamp = (now or datetime.now()).strftime(DATE_FORMAT_FACTURE_REF)
        return f"{FACTURE_NUMBER_PREFIX}-{stamp}"
