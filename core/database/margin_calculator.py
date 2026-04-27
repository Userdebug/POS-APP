"""Margin calculation operations repository."""

from __future__ import annotations

from typing import Any, Callable


class MarginCalculator:
    """Handles margin-related calculations and queries.

    Args:
        connect_fn: Context manager yielding a sqlite3.Connection.
        day_bounds_fn: Callable to get day start/end bounds.
        today_iso_fn: Callable to get today's ISO date string.
        get_daily_closure_ca_fn: Callable to get daily closure CA.
        get_daily_closure_by_category_fn: Callable to get daily closure by category.
    """

    def __init__(
        self,
        connect_fn: Any,
        day_bounds_fn: Callable[[str], tuple[str, str]],
        today_iso_fn: Callable[[], str],
        get_daily_closure_ca_fn: Callable[[str], int | None],
        get_daily_closure_by_category_fn: Callable[[str], list[dict[str, Any]]],
    ) -> None:
        self._connect = connect_fn
        self._day_bounds = day_bounds_fn
        self._today_iso = today_iso_fn
        self._get_daily_closure_ca = get_daily_closure_ca_fn
        self._get_daily_closure_by_category = get_daily_closure_by_category_fn

    @staticmethod
    def compute_margin_percent(
        reference_value: int,
        margin_value: int,
        *,
        actual_value: int | None,
        zero_if_reference_is_zero: bool = False,
    ) -> float | None:
        if reference_value > 0:
            return (float(margin_value) / float(reference_value)) * 100.0
        if zero_if_reference_is_zero:
            return 0.0
        if actual_value is None:
            return None
        return 0.0 if int(actual_value) == 0 else None

    def get_daily_theoretical_margin_by_category(
        self, jour: str | None = None
    ) -> list[dict[str, Any]]:
        target_day = jour or self._today_iso()
        day_start, day_end = self._day_bounds(target_day)
        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH day_mouv AS (
                    SELECT
                        ms.produit_id,
                        SUM(CASE WHEN ms.type_mouvement IN ('EB', 'ER') THEN ms.quantite ELSE 0 END) AS achats,
                        MIN(ms.id) AS first_id,
                        MAX(ms.id) AS last_id
                    FROM mouvements_stock ms
                    WHERE ms.jour >= ? AND ms.jour < ?
                    GROUP BY ms.produit_id
                ),
                 day_stock AS (
                     SELECT
                         p.id AS produit_id,
                         COALESCE(c.nom, 'Sans categorie') AS categorie,
                         p.pa,
                         CAST(ROUND(p.pa * 1.2, 0) AS INTEGER) AS prc,
                         COALESCE(
                             (f.stock_boutique_avant + f.stock_reserve_avant),
                             (p.stock_boutique + p.stock_reserve) - COALESCE(dm.achats, 0)
                         ) AS si,
                         COALESCE(dm.achats, 0) AS achats,
                         (p.stock_boutique + p.stock_reserve) AS sf
                     FROM produits p
                     LEFT JOIN categories c ON c.id = p.categorie_id
                     LEFT JOIN day_mouv dm ON dm.produit_id = p.id
                     LEFT JOIN mouvements_stock f ON f.id = dm.first_id
                 )
                SELECT
                    ds.categorie,
                    SUM(
                        CASE
                            WHEN (ds.si + ds.achats - ds.sf) > 0 THEN (ds.si + ds.achats - ds.sf)
                            ELSE 0
                        END
                    ) AS qte_vendue_theorique,
                    SUM(
                        CASE
                            WHEN (ds.si + ds.achats - ds.sf) > 0 THEN (ds.si + ds.achats - ds.sf) * ds.pa
                            ELSE 0
                        END
                    ) AS vente_theorique_valeur,
                    SUM(
                        CASE
                            WHEN (ds.si + ds.achats - ds.sf) > 0 THEN (ds.si + ds.achats - ds.sf) * ds.prc
                            ELSE 0
                        END
                    ) AS ca_theorique
                FROM day_stock ds
                GROUP BY ds.categorie
                ORDER BY ds.categorie ASC
                """,
                (day_start, day_end),
            ).fetchall()
            inv_rows = conn.execute(
                """
                SELECT categorie, COALESCE(SUM(valeur), 0) AS invendable_valeur
                FROM historique_produits_enleves
                WHERE jour >= ? AND jour < ?
                GROUP BY categorie
                """,
                (day_start, day_end),
            ).fetchall()
            inv_map = {str(r["categorie"]): int(r["invendable_valeur"] or 0) for r in inv_rows}
            result: list[dict[str, Any]] = []
            for row in rows:
                cat = str(row["categorie"])
                qte = int(row["qte_vendue_theorique"] or 0)
                vente_brute = int(row["vente_theorique_valeur"] or 0)
                inv = inv_map.get(cat, 0)
                vente_valeur = max(0, vente_brute - inv)
                ca_theorique = int(round(vente_valeur * 1.2))
                result.append(
                    {
                        "categorie": cat,
                        "qte_vendue_theorique": qte,
                        "vente_theorique_valeur": vente_valeur,
                        "ca_theorique": ca_theorique,
                        "marge_theorique": ca_theorique - vente_valeur,
                    }
                )
            return result

    def get_daily_margin_summary(self, jour: str | None = None) -> dict[str, int | float | None]:
        target_day = jour or self._today_iso()
        rows = self.get_daily_theoretical_margin_by_category(target_day)
        ca_theorique_total = sum(int(r.get("ca_theorique", 0)) for r in rows)
        vente_theorique_total = sum(int(r.get("vente_theorique_valeur", 0)) for r in rows)
        marge_theorique_total = sum(int(r.get("marge_theorique", 0)) for r in rows)
        ca_reel = self._get_daily_closure_ca(target_day)
        marge_reelle = None if ca_reel is None else int(ca_reel) - vente_theorique_total
        ecart_ca = None if ca_reel is None else int(ca_reel) - ca_theorique_total
        marge_percent = self.compute_margin_percent(
            vente_theorique_total,
            0 if marge_reelle is None else int(marge_reelle),
            actual_value=ca_reel,
        )
        return {
            "ca_theorique_total": ca_theorique_total,
            "vente_theorique_total": vente_theorique_total,
            "marge_theorique_total": marge_theorique_total,
            "ca_reel_ttc": ca_reel,
            "marge_reelle": marge_reelle,
            "ecart_ca_reel_vs_theorique": ecart_ca,
            "marge_percent": marge_percent,
        }

    def get_daily_margin_by_category(self, jour: str | None = None) -> list[dict[str, Any]]:
        target_day = jour or self._today_iso()
        theorique = self.get_daily_theoretical_margin_by_category(target_day)
        real_map = {
            str(row.get("categorie", "")): int(row.get("ca_ttc_final", 0))
            for row in self._get_daily_closure_by_category(target_day)
        }
        result: list[dict[str, Any]] = []
        for row in theorique:
            cat = str(row.get("categorie", ""))
            vente_valeur = int(row.get("vente_theorique_valeur", 0))
            ca_theorique = int(row.get("ca_theorique", 0))
            ca_reel = real_map.get(cat)
            marge_reelle = None if ca_reel is None else int(ca_reel) - vente_valeur
            ecart_ca = None if ca_reel is None else int(ca_reel) - ca_theorique
            marge_percent = self.compute_margin_percent(
                vente_valeur,
                0 if marge_reelle is None else int(marge_reelle),
                actual_value=ca_reel,
            )
            item = dict(row)
            item["ca_reel_ttc"] = ca_reel
            item["marge_reelle"] = marge_reelle
            item["ecart_ca"] = ecart_ca
            item["marge_percent"] = marge_percent
            result.append(item)
        return result

    def get_daily_category_collecte(self, jour: str | None = None) -> list[dict[str, Any]]:
        """Collecte journaliere par categorie:
        Jour, categorie, SI, Achats, Invendable, Vente, SF, Marge.
        Toutes les valeurs sont monetaires (Ar) sauf `jour`/`categorie`.
        """
        target_day = jour or self._today_iso()
        day_start, day_end = self._day_bounds(target_day)
        with self._connect() as conn:
            rows = conn.execute(
                """
                WITH day_mouv_prod AS (
                    SELECT
                        ms.produit_id,
                        SUM(CASE WHEN ms.type_mouvement IN ('EB', 'ER') THEN ms.quantite ELSE 0 END) AS achats_qty,
                        MIN(ms.id) AS first_id,
                        MAX(ms.id) AS last_id
                    FROM mouvements_stock ms
                    WHERE ms.jour >= ? AND ms.jour < ?
                    GROUP BY ms.produit_id
                ),
                stocks_val_cat AS (
                    SELECT
                        COALESCE(c.nom, 'Sans categorie') AS categorie,
                        SUM(
                            COALESCE(
                                (f.stock_boutique_avant + f.stock_reserve_avant),
                                (p.stock_boutique + p.stock_reserve) - COALESCE(dmp.achats_qty, 0)
                            ) * p.pa
                        ) AS si_valeur,
                        SUM(COALESCE(dmp.achats_qty, 0) * p.pa) AS achats_valeur,
                        SUM(
                            COALESCE(
                                (l.stock_boutique_apres + l.stock_reserve_apres),
                                (p.stock_boutique + p.stock_reserve)
                            ) * p.pa
                        ) AS sf_valeur
                    FROM produits p
                    LEFT JOIN categories c ON c.id = p.categorie_id
                    LEFT JOIN day_mouv_prod dmp ON dmp.produit_id = p.id
                    LEFT JOIN mouvements_stock f ON f.id = dmp.first_id
                    LEFT JOIN mouvements_stock l ON l.id = dmp.last_id
                    GROUP BY COALESCE(c.nom, 'Sans categorie')
                ),
                inv_cat AS (
                    SELECT
                        h.categorie AS categorie,
                        SUM(h.valeur) AS invendable_valeur
                    FROM historique_produits_enleves h
                    WHERE h.jour >= ? AND h.jour < ?
                    GROUP BY h.categorie
                ),
                vente_cat AS (
                    SELECT
                        cc.categorie AS categorie,
                        SUM(cc.ca_ttc_final) AS vente_reelle
                    FROM clotures_caisse_categories cc
                    WHERE cc.jour = ?
                    GROUP BY cc.categorie
                ),
                all_cat AS (
                    SELECT categorie FROM stocks_val_cat
                    UNION
                    SELECT categorie FROM inv_cat
                    UNION
                    SELECT categorie FROM vente_cat
                )
                SELECT
                    ? AS jour,
                    ac.categorie,
                    COALESCE(s.si_valeur, 0) AS si,
                    COALESCE(s.achats_valeur, 0) AS achats,
                    COALESCE(i.invendable_valeur, 0) AS invendable,
                    COALESCE(v.vente_reelle, 0) AS vente,
                    COALESCE(s.sf_valeur, 0) AS sf
                FROM all_cat ac
                LEFT JOIN stocks_val_cat s ON s.categorie = ac.categorie
                LEFT JOIN inv_cat i ON i.categorie = ac.categorie
                LEFT JOIN vente_cat v ON v.categorie = ac.categorie
                ORDER BY ac.categorie ASC
                """,
                (day_start, day_end, day_start, day_end, target_day, target_day),
            ).fetchall()

            result: list[dict[str, Any]] = []
            for row in rows:
                si = int(row["si"] or 0)
                achats = int(row["achats"] or 0)
                inv = int(row["invendable"] or 0)
                vente = int(row["vente"] or 0)
                sf = int(row["sf"] or 0)
                vente_theorique = max(0, si + achats - inv - sf)
                marge = vente - vente_theorique
                marge_percent = self.compute_margin_percent(
                    vente_theorique,
                    marge,
                    actual_value=vente,
                )
                result.append(
                    {
                        "jour": str(row["jour"]),
                        "categorie": str(row["categorie"]),
                        "si": si,
                        "achats": achats,
                        "invendable": inv,
                        "vente": vente,
                        "sf": sf,
                        "vente_theorique": vente_theorique,
                        "marge": marge,
                        "marge_percent": marge_percent,
                    }
                )
            return result
