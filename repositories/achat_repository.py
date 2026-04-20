"""Repository SQL pour achats fournisseurs."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

from core.constants import DEFAULT_SUPPLIER_NAME, FACTURE_NUMBER_PREFIX


class AchatRepository:
    """Gestion des fournisseurs, achats et agregats d'achats."""

    def __init__(
        self,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        today_iso: Callable[[], str],
    ) -> None:
        self._connect = connect
        self._today_iso = today_iso

    def get_all_suppliers(self) -> list[dict[str, Any]]:
        """Get all active suppliers from the database."""
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """SELECT id, nom, code, nif, stat, contact, telephone, adresse, note, actif
                    FROM fournisseurs WHERE actif = 1 ORDER BY nom""",
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec get_all_suppliers: {exc}") from exc

    def update_supplier(self, supplier: dict[str, Any]) -> None:
        """Update an existing supplier."""
        data = dict(supplier or {})
        supplier_id = data.get("id")
        if not supplier_id:
            raise ValueError("Supplier ID is required for update")
        nom = str(data.get("nom", "")).strip()
        code = str(data.get("code", "")).strip() or None
        nif = str(data.get("nif", "")).strip() or None
        stat = str(data.get("stat", "")).strip() or None
        contact = str(data.get("contact", "")).strip() or None
        telephone = str(data.get("telephone", "")).strip() or None
        adresse = str(data.get("adresse", "")).strip() or None
        note = str(data.get("note", "")).strip() or None
        try:
            with self._connect() as conn:
                conn.execute(
                    """UPDATE fournisseurs SET
                        nom = ?, code = ?, nif = ?, stat = ?, contact = ?,
                        telephone = ?, adresse = ?, note = ?, updated_at = datetime('now')
                    WHERE id = ?""",
                    (nom, code, nif, stat, contact, telephone, adresse, note, supplier_id),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec update_supplier: {exc}") from exc

    def deactivate_supplier(self, supplier_id: int) -> None:
        """Soft-delete a supplier by setting actif = 0."""
        try:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE fournisseurs SET actif = 0, updated_at = datetime('now') WHERE id = ?",
                    (supplier_id,),
                )
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec deactivate_supplier: {exc}") from exc

    def get_supplier_by_code(self, code: str) -> dict[str, Any] | None:
        """Get a supplier by code."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM fournisseurs WHERE code = ? AND actif = 1",
                    (code,),
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec get_supplier_by_code: {exc}") from exc

    def ensure_supplier(self, supplier: dict[str, Any] | None) -> int:
        data = dict(supplier or {})
        nom = str(data.get("nom", "")).strip()
        if not nom:
            nom = DEFAULT_SUPPLIER_NAME
        code = str(data.get("code", "")).strip() or None
        nif = str(data.get("nif", "")).strip() or None
        stat = str(data.get("stat", "")).strip() or None
        contact = str(data.get("contact", "")).strip() or None
        telephone = str(data.get("telephone", "")).strip() or None
        adresse = str(data.get("adresse", "")).strip() or None
        note = str(data.get("note", "")).strip() or None
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    INSERT INTO fournisseurs (nom, code, nif, stat, contact, telephone, adresse, note, actif, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
                    ON CONFLICT(nom) DO UPDATE SET
                        code = COALESCE(excluded.code, fournisseurs.code),
                        nif = COALESCE(excluded.nif, fournisseurs.nif),
                        stat = COALESCE(excluded.stat, fournisseurs.stat),
                        contact = COALESCE(excluded.contact, fournisseurs.contact),
                        telephone = COALESCE(excluded.telephone, fournisseurs.telephone),
                        adresse = COALESCE(excluded.adresse, fournisseurs.adresse),
                        note = COALESCE(excluded.note, fournisseurs.note),
                        actif = 1,
                        updated_at = datetime('now')
                    """,
                    (nom, code, nif, stat, contact, telephone, adresse, note),
                )
                row = conn.execute("SELECT id FROM fournisseurs WHERE nom = ?", (nom,)).fetchone()
                return int(row["id"])
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec ensure_supplier: {exc}") from exc

    def record_achat_line(
        self,
        *,
        day: str,
        supplier: dict[str, Any] | None,
        invoice_number: str,
        product_id: int,
        quantity: int,
        unit_cost: int,
        unit_price: int,
        retail_price: int,
    ) -> int:
        target_day = str(day).strip()
        if not target_day:
            raise ValueError("day invalide pour enregistrement d'achat")
        fid = self.ensure_supplier(supplier)
        qte = max(0, int(quantity))
        pa = max(0, int(unit_cost))
        prc = max(0, int(unit_price))
        pv = max(0, int(retail_price))
        total_ttc = qte * prc
        invoice_number = (
            str(invoice_number or "").strip() or f"{FACTURE_NUMBER_PREFIX}-{target_day}-{fid}"
        )
        try:
            with self._connect() as conn:
                row = conn.execute(
                    """
                    SELECT id FROM Tachats
                    WHERE jour = ? AND fournisseur_id = ? AND COALESCE(numero_facture,'') = COALESCE(?, '')
                    """,
                    (target_day, fid, invoice_number),
                ).fetchone()
                if row is None:
                    cur = conn.execute(
                        """
                        INSERT INTO Tachats (jour, fournisseur_id, numero_facture, total_ttc, cloturee, updated_at)
                        VALUES (?, ?, ?, 0, 0, datetime('now'))
                        """,
                        (target_day, fid, invoice_number),
                    )
                    achat_id = int(cur.lastrowid)
                else:
                    achat_id = int(row["id"])

                conn.execute(
                    """
                    INSERT INTO Tachats_lignes (
                        achat_id, produit_id, quantite, pa_unitaire, prc_unitaire, pv_unitaire, total_ttc
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (achat_id, int(product_id), qte, pa, prc, pv, total_ttc),
                )
                conn.execute(
                    """
                    UPDATE Tachats
                    SET total_ttc = (
                        SELECT COALESCE(SUM(total_ttc), 0)
                        FROM Tachats_lignes
                        WHERE achat_id = Tachats.id
                    ),
                    updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (achat_id,),
                )
                return achat_id
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec record_achat_line: {exc}") from exc

    def get_purchase_achats_by_category(self, day: str | None = None) -> list[dict[str, Any]]:
        target_day = day or self._today_iso()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.nom AS categorie,
                    COALESCE(SUM(al.total_ttc), 0) AS achats_ttc
                FROM Tachats a
                INNER JOIN Tachats_lignes al ON al.achat_id = a.id
                INNER JOIN produits p ON p.id = al.produit_id
                INNER JOIN categories c ON c.id = p.categorie_id
                WHERE a.jour = ?
                GROUP BY c.nom
                ORDER BY c.nom ASC
                """,
                (str(target_day),),
            ).fetchall()
            return [dict(row) for row in rows]

    def list_daily_achats(self, day: str) -> list[dict[str, Any]]:
        """Liste les achats (factures) pour un jour donne."""
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.id,
                    a.jour,
                    a.numero_facture,
                    f.nom as fournisseur,
                    a.total_ttc
                FROM Tachats a
                LEFT JOIN fournisseurs f ON a.fournisseur_id = f.id
                WHERE a.jour = ?
                ORDER BY a.id DESC
                """,
                (str(day),),
            ).fetchall()
            return [dict(row) for row in rows]

    def total_daily_achats(self, day: str) -> int:
        """Calcule le total des achats pour un jour donne."""
        with self._connect() as conn:
            row = conn.execute(
                """
SELECT COALESCE(SUM(total_ttc), 0) as total
            FROM Tachats
            WHERE jour = ?
                """,
                (str(day),),
            ).fetchone()
            return int(row["total"]) if row else 0
