"""Service metier pour la persistance d'une ligne de reception."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from core.constants import DEFAULT_CATEGORY_NAME
from services.panier_transactions_service import PanierTransactionsService


class DbReceptionLike(Protocol):
    def next_product_id(self) -> int: ...

    def upsert_products(self, produits: list[dict[str, Any]]) -> None: ...

    def record_reception_line(
        self,
        *,
        jour: str,
        fournisseur: dict[str, Any] | None,
        numero_facture: str,
        produit_id: int,
        quantite: int,
        pa_unitaire: int,
        prc_unitaire: int,
        pv_unitaire: int,
    ) -> int: ...


@dataclass(frozen=True)
class ReceptionRowSaveResult:
    line: dict[str, Any]
    payload: dict[str, Any] | None
    total: int


class ReceptionPersistenceService:
    """Normalise et persiste une ligne de reception produit."""

    @staticmethod
    def _sanitize_line(raw_line: dict[str, Any]) -> dict[str, Any]:
        nom = str(raw_line.get("nom", "")).strip()
        if not nom:
            return {}

        categorie = str(raw_line.get("categorie", "")).strip()
        if not categorie or categorie == "-":
            categorie = DEFAULT_CATEGORY_NAME

        pa = max(0, int(raw_line.get("pa", 0) or 0))
        prc = max(0, int(raw_line.get("prc", pa) or 0))
        pv = max(0, int(raw_line.get("pv", pa) or pa))
        qte = max(1, int(raw_line.get("qte", 1) or 1))

        return {
            "id": raw_line.get("id"),
            "nom": nom,
            "categorie": categorie,
            "pa": pa,
            "prc": prc,
            "pv": pv,
            "prix": pa,
            "qte": qte,
            "dlv_dlc": str(raw_line.get("dlv_dlc", "")),
            "nouveau": False,
        }

    @classmethod
    def save_reception_row(
        cls,
        *,
        raw_line: dict[str, Any],
        db_manager: DbReceptionLike | None,
        fournisseur: dict[str, Any] | None,
        day: str,
        numero_facture: str | None,
    ) -> ReceptionRowSaveResult:
        line = cls._sanitize_line(raw_line)
        if not line:
            return ReceptionRowSaveResult(line={}, payload=None, total=0)

        next_id = int(line["id"]) if line.get("id") is not None else None
        payload: dict[str, Any] | None = None

        if db_manager is not None:
            if next_id is None:
                next_id = db_manager.next_product_id()

            payload = {
                "id": int(next_id),
                "nom": str(line.get("nom", "")),
                "pv": int(line.get("pv", 0)),
                "prc": int(line.get("prc", 0)),
                "pa": int(line.get("pa", 0)),
                "b": int(line.get("qte", 1)),
                "r": 0,
                "dlv_dlc": str(line.get("dlv_dlc", "")),
                "categorie": str(line.get("categorie", DEFAULT_CATEGORY_NAME)),
            }
            db_manager.upsert_products([payload])
            db_manager.record_reception_line(
                jour=day,
                fournisseur=fournisseur,
                numero_facture=numero_facture or PanierTransactionsService.build_invoice_number(),
                produit_id=int(next_id),
                quantite=int(line.get("qte", 1)),
                pa_unitaire=int(line.get("pa", 0)),
                prc_unitaire=int(line.get("prc", 0)),
                pv_unitaire=int(line.get("pv", 0)),
            )

        line["id"] = next_id
        total = int(line.get("pa", 0)) * int(line.get("qte", 1))
        return ReceptionRowSaveResult(line=line, payload=payload, total=total)
