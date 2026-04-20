"""Product CRUD operations repository."""

from __future__ import annotations

import datetime
import logging
import sqlite3
from typing import Any, Callable

from core.constants import DEFAULT_CATEGORY_NAME

logger = logging.getLogger(__name__)


class ProductRepository:
    """Handles product-related database operations.

    Args:
        connect_fn: Context manager yielding a sqlite3.Connection.
        resolve_category_ids_fn: Callable to resolve category names to IDs.
    """

    def __init__(
        self,
        connect_fn: Any,
        resolve_category_ids_fn: Callable[[sqlite3.Connection, list[str]], dict[str, int]],
    ) -> None:
        self._connect = connect_fn
        self._resolve_category_ids = resolve_category_ids_fn

    def upsert_products(self, produits: list[dict[str, Any]]) -> None:
        try:
            with self._connect() as conn:
                categories = []
                for produit in produits:
                    cat_name = (
                        str(produit.get("categorie", DEFAULT_CATEGORY_NAME)).strip()
                        or DEFAULT_CATEGORY_NAME
                    )
                    categories.append(cat_name)
                category_map = self._resolve_category_ids(conn, categories)

                for produit in produits:
                    cat_name = str(produit.get("categorie", DEFAULT_CATEGORY_NAME)).strip()
                    if not cat_name:
                        cat_name = DEFAULT_CATEGORY_NAME
                    cat_id = int(category_map[cat_name])

                    product_id = produit.get("id")
                    en_promo = int(produit.get("en_promo", 0))
                    pa_val = int(produit.get("pa", produit.get("prc", 0)))
                    prix_promo = int(produit.get("prix_promo", pa_val))
                    if product_id is not None:
                        conn.execute(
                            """
                            INSERT INTO produits
                                (id, nom, categorie_id, pv, pa, stock_boutique,
                                 stock_reserve, dlv_dlc, description, sku,
                                 en_promo, prix_promo)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                nom = excluded.nom,
                                categorie_id = excluded.categorie_id,
                                pv = excluded.pv,
                                pa = excluded.pa,
                                stock_boutique = excluded.stock_boutique,
                                stock_reserve = excluded.stock_reserve,
                                dlv_dlc = excluded.dlv_dlc,
                                description = excluded.description,
                                sku = excluded.sku,
                                en_promo = excluded.en_promo,
                                prix_promo = excluded.prix_promo,
                                updated_at = datetime('now')
                            """,
                            (
                                int(product_id),
                                str(produit.get("nom", "")),
                                int(cat_id),
                                int(produit.get("pv", 0)),
                                pa_val,
                                int(produit.get("b", 0)),
                                int(produit.get("r", 0)),
                                str(produit.get("dlv_dlc", "")),
                                str(produit.get("description", "") or ""),
                                str(produit.get("sku", "") or ""),
                                en_promo,
                                prix_promo,
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            INSERT INTO produits
                                (id, nom, categorie_id, pv, pa, stock_boutique,
                                 stock_reserve, dlv_dlc, description, sku,
                                 en_promo, prix_promo)
                            VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                str(produit.get("nom", "")),
                                int(cat_id),
                                int(produit.get("pv", 0)),
                                pa_val,
                                int(produit.get("b", 0)),
                                int(produit.get("r", 0)),
                                str(produit.get("dlv_dlc", "")),
                                str(produit.get("description", "") or ""),
                                str(produit.get("sku", "") or ""),
                                en_promo,
                                prix_promo,
                            ),
                        )
        except sqlite3.Error as exc:
            raise RuntimeError(f"echec upsert_products: {exc}") from exc

    def list_products(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT
                    p.id,
                    p.nom,
                    p.pv,
                    p.pa,
                    CAST(ROUND(p.pa * 1.2, 0) AS INTEGER) AS prc,
                    p.stock_boutique AS b,
                    p.stock_reserve AS r,
                    p.dlv_dlc,
                    p.derniere_verification,
                    p.description,
                    p.sku,
                    p.en_promo,
                    p.prix_promo,
                    COALESCE(c.nom, 'Sans categorie') AS categorie
                FROM produits p
                LEFT JOIN categories c ON c.id = p.categorie_id
                ORDER BY p.id ASC
                """).fetchall()
            return [dict(row) for row in rows]

    def get_produit_by_id(self, produit_id: int) -> dict[str, Any] | None:
        """Get a single product by ID.

        Args:
            produit_id: The product ID to retrieve

        Returns:
            Dictionary with product data or None if not found
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    p.id,
                    p.nom,
                    p.pv,
                    p.pa,
                    CAST(ROUND(p.pa * 1.2, 0) AS INTEGER) AS prc,
                    p.stock_boutique AS qte_stock,
                    p.stock_reserve AS r,
                    p.dlv_dlc,
                    p.en_promo,
                    p.prix_promo,
                    COALESCE(c.nom, 'Sans categorie') AS categorie
                FROM produits p
                LEFT JOIN categories c ON c.id = p.categorie_id
                WHERE p.id = ?
                """,
                (produit_id,),
            ).fetchone()
            return dict(row) if row else None

    def update_derniere_verification(self, produit_id: int, date_verification: str) -> None:
        """Update the derniere_verification date for a product.

        Args:
            produit_id: The product ID to update
            date_verification: The verification date string (YYYY-MM-DD)
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE produits
                SET derniere_verification = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (date_verification, produit_id),
            )
            conn.commit()

    def next_product_id(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM produits"
            ).fetchone()
            return int(row["next_id"])

    def toggle_promo(self, produit_id: int, en_promo: bool) -> None:
        """Toggle the promotion flag for a product.

        Args:
            produit_id: The product ID to update
            en_promo: True to enable promotion, False to disable
        """
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE produits
                SET en_promo = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (1 if en_promo else 0, produit_id),
            )
            conn.commit()

    def list_products_en_promo(self) -> list[dict[str, Any]]:
        """List all products currently on promotion.

        Returns:
            List of dicts with id, nom, pv, prix_promo for promo products.
        """
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, nom, pv, prix_promo, en_promo, stock_boutique, stock_reserve
                FROM produits
                WHERE en_promo = 1
                ORDER BY nom
                """).fetchall()
            result = [dict(row) for row in rows]
            logger.info("Found %d promo products", len(result))
            return result

    def list_products_near_dlv(self, days: int = 30) -> list[dict[str, Any]]:
        """List products whose DLV/DLC date is within the given number of days.

        Args:
            days: Number of days threshold from today (default 30).

        Returns:
            List of dicts with id, nom, dlv_dlc, stock_boutique, stock_reserve.
        """
        today = datetime.date.today()
        limit = today + datetime.timedelta(days=days)
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, nom, dlv_dlc, stock_boutique, stock_reserve
                FROM produits
                WHERE dlv_dlc IS NOT NULL AND dlv_dlc != ''
                ORDER BY dlv_dlc ASC
                """).fetchall()
            result = []
            for row in rows:
                try:
                    # Handle multiple date formats: "1/10/2026 00:00:00" or "30/6/2026"
                    dlv_str = row["dlv_dlc"]
                    # Try first format with time, then without time
                    try:
                        dlv_date = datetime.datetime.strptime(dlv_str, "%d/%m/%Y %H:%M:%S").date()
                    except ValueError:
                        dlv_date = datetime.datetime.strptime(dlv_str, "%d/%m/%Y").date()
                    if today <= dlv_date <= limit:
                        result.append(dict(row))
                except (ValueError, TypeError):
                    continue
            logger.info("Found %d products near DLV within %d days", len(result), days)
            return result

    def list_products_to_remove(self) -> list[dict[str, Any]]:
        """List products with passed DLV date (expired products to remove).

        Returns:
            List of dicts with id, nom, dlv_dlc, stock_boutique, stock_reserve.
        """
        today = datetime.date.today()
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT id, nom, dlv_dlc, stock_boutique, stock_reserve
                FROM produits
                WHERE dlv_dlc IS NOT NULL AND dlv_dlc != ''
                ORDER BY dlv_dlc ASC
                """).fetchall()
            result = []
            for row in rows:
                try:
                    # Handle multiple date formats: "1/10/2026 00:00:00" or "30/6/2026"
                    dlv_str = row["dlv_dlc"]
                    # Try first format with time, then without time
                    try:
                        dlv_date = datetime.datetime.strptime(dlv_str, "%d/%m/%Y %H:%M:%S").date()
                    except ValueError:
                        dlv_date = datetime.datetime.strptime(dlv_str, "%d/%m/%Y").date()
                    if dlv_date < today:  # DLV has passed
                        result.append(dict(row))
                except (ValueError, TypeError):
                    continue
            logger.info("Found %d products with passed DLV to remove", len(result))
            return result

    def get_stock(self, produit_id: int) -> tuple[int, int]:
        """Récupère les stocks boutique et réserve pour un produit.

        Args:
            produit_id: ID du produit.

        Returns:
            Tuple (stock_boutique, stock_reserve). (0,0) si produit non trouvé.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT stock_boutique, stock_reserve FROM produits WHERE id = ?",
                (produit_id,),
            ).fetchone()
            if row:
                return (int(row["stock_boutique"] or 0), int(row["stock_reserve"] or 0))
            return (0, 0)
