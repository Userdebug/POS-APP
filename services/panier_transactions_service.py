"""Services metier pour les transactions de panier (caisse/reception)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from core.constants import DATE_FORMAT_FACTURE_REF, DEFAULT_CATEGORY_NAME, FACTURE_NUMBER_PREFIX


@dataclass(frozen=True)
class EncaissementSummary:
    total: int
    nb_lignes: int
    nb_articles: int


class TrackingServiceLike(Protocol):
    def apply_collection(self, jour: str, basket_rows: list[dict[str, Any]]) -> None: ...


class DbFollowupLike(Protocol):
    def get_daily_suivi_form(self, jour: str) -> list[dict[str, Any]]: ...

    def save_daily_tracking_form_edits(self, jour: str, rows: list[dict[str, Any]]) -> None: ...


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
    def apply_tracking_collection(
        cls,
        day: str,
        items: list[dict[str, Any]],
        *,
        db_manager: DbFollowupLike | None,
        tracking_service: TrackingServiceLike | None,
    ) -> None:
        if not items:
            return

        summary = cls.compute_collection_summary(items)
        if summary.total <= 0:
            return

        if tracking_service is not None:
            tracking_service.apply_collection(day, items)
            return

        if db_manager is None:
            return

        current_rows = db_manager.get_daily_suivi_form(day)
        current_map = {str(r.get("categorie", "")): dict(r) for r in current_rows}
        increments: dict[str, int] = {}

        for ligne in items:
            categorie = str(ligne.get("categorie", "")).strip()
            if not categorie or categorie == "-":
                categorie = DEFAULT_CATEGORY_NAME
            increments[categorie] = increments.get(categorie, 0) + cls.line_total(ligne)

        edits: list[dict[str, Any]] = []
        for categorie, montant in increments.items():
            base = current_map.get(categorie, {})
            edits.append(
                {
                    "categorie": categorie,
                    "achats_ttc": int(base.get("achats_ttc", 0) or 0),
                    "ca_final": int(base.get("ca_final", 0) or 0) + int(montant),
                }
            )

        if edits:
            db_manager.save_daily_tracking_form_edits(day, edits)

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
