"""Daily closure and tracking operations repository."""

from __future__ import annotations

from typing import Any, Callable


class DailyOperations:
    """Handles daily closure and tracking operations.

    Args:
        connect_fn: Context manager yielding a sqlite3.Connection.
        day_bounds_fn: Callable to get day start/end bounds.
        month_bounds_fn: Callable to get month start/end bounds.
        today_iso_fn: Callable to get today's ISO date string.
        current_month_iso_fn: Callable to get current month ISO string.
        get_tax_fn: Callable to get tax rate.
    """

    def __init__(
        self,
        connect_fn: Any,
        day_bounds_fn: Callable[[str], tuple[str, str]],
        month_bounds_fn: Callable[[str], tuple[str, str]],
        today_iso_fn: Callable[[], str],
        current_month_iso_fn: Callable[[], str],
        get_tax_fn: Callable[[float], float],
    ) -> None:
        self._connect = connect_fn
        self._day_bounds = day_bounds_fn
        self._month_bounds = month_bounds_fn
        self._today_iso = today_iso_fn
        self._current_month_iso = current_month_iso_fn
        self._get_tax = get_tax_fn

    def get_daily_category_evolution(self, jour: str | None = None) -> list[dict[str, Any]]:
        target_day = jour or self._today_iso()
        day_start, day_end = self._day_bounds(target_day)
        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH base AS (
                    SELECT
                        p.id AS produit_id,
                        COALESCE(c.nom, 'Sans categorie') AS categorie,
                        (p.stock_boutique + p.stock_reserve) AS stock_sf
                    FROM produits p
                    LEFT JOIN categories c ON c.id = p.categorie_id
                ),
                day_mouv AS (
                    SELECT
                        ms.produit_id,
                        SUM(CASE WHEN ms.type_mouvement IN ('EB', 'ER') THEN ms.quantite ELSE 0 END) AS achats,
                        MIN(ms.id) AS first_id
                    FROM mouvements_stock ms
                    WHERE ms.jour >= ? AND ms.jour < ?
                    GROUP BY ms.produit_id
                ),
                first_stock AS (
                    SELECT
                        ms.produit_id,
                        (ms.stock_boutique_avant + ms.stock_reserve_avant) AS stock_si
                    FROM mouvements_stock ms
                    INNER JOIN day_mouv dm ON dm.first_id = ms.id
                )
                SELECT
                    b.categorie,
                    SUM(
                        COALESCE(
                            fs.stock_si,
                            b.stock_sf - COALESCE(dm.achats, 0)
                        )
                    ) AS si,
                    SUM(COALESCE(dm.achats, 0)) AS achats,
                    SUM(b.stock_sf) AS sf
                FROM base b
                LEFT JOIN day_mouv dm ON dm.produit_id = b.produit_id
                LEFT JOIN first_stock fs ON fs.produit_id = b.produit_id
                GROUP BY b.categorie
                ORDER BY b.categorie ASC
                """,
                (day_start, day_end),
            ).fetchall()
            result: list[dict[str, Any]] = []
            for row in rows:
                si = int(row["si"] or 0)
                achats = int(row["achats"] or 0)
                sf = int(row["sf"] or 0)
                ventes_theoriques = si + achats - sf
                result.append(
                    {
                        "categorie": str(row["categorie"]),
                        "si": si,
                        "achats": achats,
                        "ventes_theoriques": ventes_theoriques,
                        "sf": sf,
                        "ecart_formule": si + achats - ventes_theoriques - sf,
                    }
                )
            return result

    def get_monthly_nfr_by_category(self, mois: str | None = None) -> list[dict[str, Any]]:
        """NFR mensuel par categorie: CA TTC / CA HT (base theorique)."""
        target_month = mois or self._current_month_iso()
        month_start, month_end = self._month_bounds(target_month)
        tax_rate = self._get_tax(default=20.0)
        factor = 1.0 + (float(tax_rate) / 100.0)

        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH day_mouv AS (
                    SELECT
                        ms.produit_id,
                        date(ms.jour) AS jour_key,
                        SUM(CASE WHEN ms.type_mouvement IN ('EB', 'ER') THEN ms.quantite ELSE 0 END) AS achats,
                        MIN(ms.id) AS first_id,
                        MAX(ms.id) AS last_id
                    FROM mouvements_stock ms
                    WHERE ms.jour >= ? AND ms.jour < ?
                    GROUP BY ms.produit_id, date(ms.jour)
                ),
                day_stock AS (
                    SELECT
                        dm.produit_id,
                        dm.jour_key,
                        dm.achats,
                        (f.stock_boutique_avant + f.stock_reserve_avant) AS si,
                        (l.stock_boutique_apres + l.stock_reserve_apres) AS sf
                    FROM day_mouv dm
                    INNER JOIN mouvements_stock f ON f.id = dm.first_id
                    INNER JOIN mouvements_stock l ON l.id = dm.last_id
                ),
                ventes_prod AS (
                    SELECT
                        ds.produit_id,
                        SUM(
                            CASE
                                WHEN (ds.si + ds.achats - ds.sf) > 0 THEN (ds.si + ds.achats - ds.sf)
                                ELSE 0
                            END
                        ) AS qte_ventes
                    FROM day_stock ds
                    GROUP BY ds.produit_id
                )
                SELECT
                    COALESCE(c.nom, 'Sans categorie') AS categorie,
                    SUM(vp.qte_ventes * CAST(ROUND(p.pa * 1.2, 0) AS INTEGER)) AS ca_ttc
                FROM ventes_prod vp
                INNER JOIN produits p ON p.id = vp.produit_id
                LEFT JOIN categories c ON c.id = p.categorie_id
                GROUP BY COALESCE(c.nom, 'Sans categorie')
                ORDER BY categorie ASC
                """,
                (month_start, month_end),
            ).fetchall()

            result: list[dict[str, Any]] = []
            for row in rows:
                ca_ttc = int(row["ca_ttc"] or 0)
                ca_ht = int(round(ca_ttc / factor)) if factor > 0 else ca_ttc
                result.append(
                    {
                        "categorie": str(row["categorie"]),
                        "ca_ttc": ca_ttc,
                        "ca_ht": ca_ht,
                    }
                )
            return result

    def set_daily_closure_revenue(self, day: str, ca_ttc_final: int, note: str = "") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO clotures_caisse (jour, ca_ttc_final, note, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(jour) DO UPDATE SET
                    ca_ttc_final = excluded.ca_ttc_final,
                    note = excluded.note,
                    updated_at = datetime('now')
                """,
                (str(day), int(ca_ttc_final), str(note)),
            )

    def upsert_daily_closure_by_category(self, jour: str, values: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            # Get valid OW subcategories
            valid_cats = set(row["nom"] for row in conn.execute("""
                    SELECT c.nom FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                    """).fetchall())

            conn.execute("DELETE FROM clotures_caisse_categories WHERE jour = ?", (str(jour),))
            for row in values:
                categorie = str(row.get("categorie", "")).strip()
                if not categorie or categorie not in valid_cats:
                    continue
                ca_ttc_final = max(0, int(row.get("ca_ttc_final", 0)))
                conn.execute(
                    """
                    INSERT INTO clotures_caisse_categories (jour, categorie, ca_ttc_final, updated_at)
                    VALUES (?, ?, ?, datetime('now'))
                    ON CONFLICT(jour, categorie) DO UPDATE SET
                        ca_ttc_final = excluded.ca_ttc_final,
                        updated_at = datetime('now')
                    """,
                    (str(jour), categorie, ca_ttc_final),
                )

            row = conn.execute(
                """
                SELECT COALESCE(SUM(ca_ttc_final), 0) AS total
                FROM clotures_caisse_categories
                WHERE jour = ?
                """,
                (str(jour),),
            ).fetchone()
            total = int(row["total"] or 0)
            conn.execute(
                """
                INSERT INTO clotures_caisse (jour, ca_ttc_final, note, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(jour) DO UPDATE SET
                    ca_ttc_final = excluded.ca_ttc_final,
                    note = excluded.note,
                    updated_at = datetime('now')
                """,
                (str(jour), total, "auto-sum categories"),
            )

    def get_daily_closure_by_category(self, jour: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT categorie, ca_ttc_final
                FROM clotures_caisse_categories
                WHERE jour = ?
                ORDER BY categorie ASC
                """,
                (str(jour),),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_daily_closure_ca(self, jour: str) -> int | None:
        by_cat = self.get_daily_closure_by_category(jour)
        if by_cat:
            return sum(int(row.get("ca_ttc_final", 0)) for row in by_cat)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT ca_ttc_final
                FROM clotures_caisse
                WHERE jour = ?
                """,
                (str(jour),),
            ).fetchone()
            if row is None:
                return None
            return int(row["ca_ttc_final"])
