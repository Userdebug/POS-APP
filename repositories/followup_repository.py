"""Repository SQL pour suivi journalier, cloture et preparation J+1.

Ce module encapsule l'acces SQL au suivi journalier.
Toutes les methodes sont protegees par try/except avec logging.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import datetime, timedelta
from typing import Any

from core.constants import DATE_FORMAT_DAY

logger = logging.getLogger(__name__)


class FollowupRepository:
    """Orchestration persistence du suivi journalier et du formulaire simplifie."""

    def __init__(
        self,
        *,
        connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
        today_iso: Callable[[], str],
        day_bounds: Callable[[str], tuple[str, str]],
        resolve_category_ids: Callable[[sqlite3.Connection, list[str]], dict[str, int]],
        daily_collecte_provider: Callable[[str], list[dict[str, Any]]],
        daily_theoretical_margin_provider: Callable[[str], list[dict[str, Any]]],
        achats_receptions_provider: Callable[[str | None], list[dict[str, Any]]],
        upsert_daily_closure_by_category: Callable[[str, list[dict[str, Any]]], None],
    ) -> None:
        self._connect = connect
        self._today_iso = today_iso
        self._day_bounds = day_bounds
        self._resolve_category_ids = resolve_category_ids
        self._daily_collecte_provider = daily_collecte_provider
        self._daily_theoretical_margin_provider = daily_theoretical_margin_provider
        self._achats_receptions_provider = achats_receptions_provider
        self._upsert_daily_closure_by_category = upsert_daily_closure_by_category

    @staticmethod
    def _compute_margin_percent(
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

    def _build_tracking_row(
        self,
        *,
        categorie: str,
        si: int,
        achats: int,
        vente_ca: int,
        sf: int,
        env: int,
        vente_theorique: int,
        cloturee: int,
    ) -> dict[str, Any]:
        marge = int(vente_ca) - int(vente_theorique)
        return {
            "categorie": str(categorie),
            "si": int(si),
            "achats": int(achats),
            "vente_ca": int(vente_ca),
            "sf": int(sf),
            "env": int(env),
            "vente_theorique": int(vente_theorique),
            "marge": marge,
            "cloturee": int(cloturee),
        }

    @staticmethod
    def _next_day_iso(day: str) -> str:
        for fmt in ["%d/%m/%y", "%Y-%m-%d"]:
            try:
                return (datetime.strptime(day, fmt) + timedelta(days=1)).strftime(DATE_FORMAT_DAY)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {day}")

    def get_daily_tracking_by_category(self, day: str | None = None) -> list[dict[str, Any]]:
        target_day = day or self._today_iso()
        self._initialize_daily_tracking_if_missing(target_day)
        self._sync_unclosed_day_metrics(target_day)
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT
                        a.jour,
                        c.nom AS categorie,
                        a.si AS si,
                        a.achats AS achats,
                        a.ca AS vente_ca,
                        a.sf AS sf,
                        a.env AS env,
                        a.vente_theorique AS vente_theorique,
                        a.marge AS marge,
                        a.cloturee
                    FROM Tcollecte a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    WHERE a.jour = ?
                    ORDER BY c.nom ASC
                    """,
                    (target_day,),
                ).fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as exc:
            logger.error("Erreur SQL lors de la recuperation du suivi journalier: %s", exc)
            return []

    def _sync_unclosed_day_metrics(self, day: str) -> None:
        """Synchronise SI/Achats/SF depuis la logique stock du jour, sans ecraser les CA saisis."""
        target_day = str(day)
        current = self.get_daily_tracking_by_category_raw(target_day)
        current_map = {str(r.get("categorie", "")): dict(r) for r in current}
        if not current_map:
            return
        if all(int(r.get("cloturee", 0) or 0) == 1 for r in current_map.values()):
            return

        # Get valid OW subcategories to filter
        with self._connect() as conn:
            valid_cats = set(
                row["nom"]
                for row in conn.execute("""
                    SELECT c.nom FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                    """).fetchall()
            )

        daily_collecte = self._daily_collecte_provider(target_day)
        achats_receptions = self._achats_receptions_provider(target_day)
        achats_map = {
            str(r.get("categorie", "")): int(r.get("achats_ttc", 0) or 0) for r in achats_receptions
        }

        env_map = {}
        with self._connect() as conn:
            env_rows = conn.execute(
                """
            SELECT c.nom as categorie, SUM(m.valeur) as env_value
            FROM mouvements_stock m
            JOIN produits p ON p.id = m.produit_id
            JOIN categories c ON c.id = p.categorie_id
            WHERE m.jour = ? AND m.type_mouvement = 'ENV'
            GROUP BY c.nom
            """,
                (target_day,),
            ).fetchall()
            env_map = {r["categorie"]: r["env_value"] for r in env_rows}

        payload: list[dict[str, Any]] = []
        for row in daily_collecte:
            cat = str(row.get("categorie", ""))
            if cat not in valid_cats:
                continue
            base = current_map.get(cat, {})
            if not base:
                continue
            # Si la ligne est cloturée, on la passe telle quelle (pas de sync)
            if int(base.get("cloturee", 0) or 0) == 1:
                payload.append(base)
                continue

            # Récupérer les valeurs calculées
            si_calc = int(row.get("si", 0) or 0)
            achats = int(achats_map.get(cat, 0))
            sf = int(row.get("sf", 0) or 0)
            env = int(env_map.get(cat, 0))

            # Préserver le SI existant s'il est déjà non nul (report de la veille ou ajustement manuel)
            existing_si = int(base.get("si", 0) or 0)
            si_val = existing_si if existing_si != 0 else si_calc

            # Pour les jours non cloturés, le CA (vente_ca) doit être 0 (saisie manuelle uniquement à clôture)
            # On conserve la valeur existante si elle est non nulle? En théorie, avant clôture, ca=0.
            # Si l'utilisateur a déjà commencé à saisir, on peut le préserver? L'exigence: sans préremplissage, donc 0.
            # On force à 0 pour les jours non cloturés.
            ca_val = 0  # pas de CA final avant clôture

            # Calculer vente_theorique avec la formule corrigée
            vente_theorique = si_val + achats - sf - env
            # Marge = CA (0) - vente_theorique → négative, ce qui est attendu pour un jour en cours
            marge = ca_val - vente_theorique

            payload.append(
                self._build_tracking_row(
                    categorie=cat,
                    si=si_val,
                    achats=achats,
                    vente_ca=ca_val,
                    sf=sf,
                    env=env,
                    vente_theorique=vente_theorique,
                    cloturee=0,
                )
            )
        self.upsert_daily_tracking(target_day, payload)

    def get_daily_tracking_by_category_raw(self, day: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    a.jour,
                    c.nom AS categorie,
                    a.si AS si,
                    a.achats AS achats,
                    a.ca AS vente_ca,
                    a.sf AS sf,
                    a.env AS env,
                    a.vente_theorique AS vente_theorique,
                    a.marge AS marge,
                    a.cloturee
                FROM Tcollecte a
                INNER JOIN categories c ON c.id = a.categorie_id
                WHERE a.jour = ?
                ORDER BY c.nom ASC
                """,
                (str(day),),
            ).fetchall()
            return [dict(row) for row in rows]

    def _initialize_daily_tracking_if_missing(self, day: str) -> None:
        # Get valid OW subcategories to filter
        with self._connect() as conn:
            valid_cats = set(
                row["nom"]
                for row in conn.execute("""
                    SELECT c.nom FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                    """).fetchall()
            )

            existing = conn.execute(
                "SELECT COUNT(1) AS n FROM Tcollecte WHERE jour = ?",
                (str(day),),
            ).fetchone()
            if int(existing["n"] or 0) > 0:
                return

        daily_collecte = self._daily_collecte_provider(day)
        theorique_rows = self._daily_theoretical_margin_provider(day)
        theorique_map = {
            str(r.get("categorie", "")): int(r.get("ca_theorique", 0) or 0) for r in theorique_rows
        }

        rows_to_insert: list[dict[str, Any]] = []
        for row in daily_collecte:
            cat = str(row.get("categorie", ""))
            if cat not in valid_cats:
                continue
            si = int(row.get("si", 0) or 0)
            achats = 0
            sf = int(row.get("sf", 0) or 0)
            vente_theorique = int(theorique_map.get(cat, 0))
            vente_ca = vente_theorique
            rows_to_insert.append(
                self._build_tracking_row(
                    categorie=cat,
                    si=si,
                    achats=achats,
                    vente_ca=vente_ca,
                    sf=sf,
                    env=0,
                    vente_theorique=vente_theorique,
                    cloturee=0,
                )
            )
        self.upsert_daily_tracking(day, rows_to_insert)

    def upsert_daily_tracking(self, day: str, rows: list[dict[str, Any]]) -> None:
        with self._connect() as conn:
            categories = []
            for row in rows:
                categorie = str(row.get("categorie", "")).strip()
                if categorie:
                    categories.append(categorie)
            category_map = self._resolve_category_ids(conn, categories)

            for row in rows:
                categorie = str(row.get("categorie", "")).strip()
                if not categorie:
                    continue
                cat_id = int(category_map[categorie])
                si = int(row.get("si", 0))
                achats = int(row.get("achats", 0))
                vente_ca = int(row.get("vente_ca", 0))
                sf = int(row.get("sf", 0))
                env = int(row.get("env", 0))
                vente_theorique = int(row.get("vente_theorique", 0))
                marge = int(row.get("marge", vente_ca - vente_theorique))
                cloturee = int(row.get("cloturee", 0))
                conn.execute(
                    """
                    INSERT INTO Tcollecte (
                        jour, categorie_id, si, achats, ca, sf, env,
                        vente_theorique, marge, cloturee, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    ON CONFLICT(jour, categorie_id) DO UPDATE SET
                        si = excluded.si,
                        achats = excluded.achats,
                        ca = excluded.ca,
                        sf = excluded.sf,
                        env = excluded.env,
                        vente_theorique = excluded.vente_theorique,
                        marge = excluded.marge,
                        cloturee = excluded.cloturee,
                        updated_at = datetime('now')
                    """,
                    (
                        str(day),
                        cat_id,
                        si,
                        achats,
                        vente_ca,
                        sf,
                        env,
                        vente_theorique,
                        marge,
                        cloturee,
                    ),
                )

    def save_daily_tracking_edits(self, day: str, rows: list[dict[str, Any]]) -> None:
        """Sauvegarde les edits manuels (SI/Achats/Vente/SF) d'un jour non cloture."""
        current = self.get_daily_tracking_by_category(day)
        current_map = {str(r.get("categorie", "")): dict(r) for r in current}
        payload: list[dict[str, Any]] = []
        for row in rows:
            cat = str(row.get("categorie", "")).strip()
            if not cat:
                continue
            base = current_map.get(cat, {})
            if int(base.get("cloturee", 0)) == 1:
                payload.append(base)
                continue
            si = int(row.get("si", base.get("si", 0)))
            achats = int(row.get("achats", base.get("achats", 0)))
            vente_ca = int(row.get("vente_ca", base.get("vente_ca", 0)))
            sf = int(row.get("sf", base.get("sf", 0)))
            env = int(base.get("env", 0))
            # Vente = SI + Achats - SF
            vente_theorique = si + achats - sf + env
            payload.append(
                self._build_tracking_row(
                    categorie=cat,
                    si=si,
                    achats=achats,
                    vente_ca=vente_ca,
                    sf=sf,
                    env=env,
                    vente_theorique=vente_theorique,
                    cloturee=0,
                )
            )
        self.upsert_daily_tracking(day, payload)

    def _initialize_daily_tracking_form_if_missing(self, day: str) -> None:
        # Get yesterday's SF for SI copying
        yesterday_sf = self._get_yesterday_sf(day)

        with self._connect() as conn:
            # Get existing data from Tcollecte
            existing_rows = conn.execute(
                """
                SELECT c.nom AS categorie, t.si, t.ca, t.cloturee
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
                """,
                (str(day),),
            ).fetchall()
            existing_map = {
                str(r["categorie"]): {
                    "si": int(r["si"] or 0),
                    "ca": int(r["ca"] or 0),
                    "cloturee": int(r["cloturee"] or 0),
                }
                for r in existing_rows
            }

            # Get OW categories
            follow_rows = conn.execute("""
                SELECT c.nom AS categorie, c.id as categorie_id
                FROM categories c
                INNER JOIN categories parent ON c.parent_id = parent.id
                WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                ORDER BY c.nom ASC
                """).fetchall()

            ca_rows = conn.execute(
                """
                SELECT categorie, ca_ttc_final
                FROM clotures_caisse_categories
                WHERE jour = ?
                """,
                (str(day),),
            ).fetchall()
            ca_map = {str(r["categorie"]): int(r["ca_ttc_final"] or 0) for r in ca_rows}

            achats_map = {
                str(r.get("categorie", "")): int(r.get("achats_ttc", 0) or 0)
                for r in self._achats_receptions_provider(str(day))
            }
            for row in follow_rows:
                cat = str(row["categorie"])
                cat_id = int(row["categorie_id"])
                # Use existing SI or copy from yesterday's SF
                si = existing_map.get(cat, {}).get("si", yesterday_sf.get(cat, 0))
                achats = int(achats_map.get(cat, 0))
                ca = int(existing_map.get(cat, {}).get("ca", ca_map.get(cat, 0)))
                cloturee = int(existing_map.get(cat, {}).get("cloturee", 0))
                conn.execute(
                    """
                    INSERT INTO Tcollecte (
                        jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee
                    )
                    VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, ?)
                    ON CONFLICT(jour, categorie_id) DO UPDATE SET
                        si = excluded.si,
                        achats = excluded.achats,
                        ca = excluded.ca,
                        cloturee = excluded.cloturee,
                        updated_at = datetime('now')
                    """,
                    (str(day), cat_id, si, achats, ca, cloturee),
                )

    def _get_yesterday_sf(self, jour: str) -> dict[str, int]:
        """Get yesterday's SF values by category."""
        from datetime import datetime, timedelta

        # Calculate yesterday
        for fmt in ["%d/%m/%y", "%Y-%m-%d"]:
            try:
                current_date = datetime.strptime(jour, fmt)
                yesterday = current_date - timedelta(days=1)
                yesterday_str = yesterday.strftime(DATE_FORMAT_DAY)
                break
            except ValueError:
                continue

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom, t.sf
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
                """,
                (yesterday_str,),
            ).fetchall()
            return {str(row[0]): int(row[1] or 0) for row in rows}

    def get_daily_tracking_form(self, day: str | None = None) -> list[dict[str, Any]]:
        target_day = day or self._today_iso()
        self._initialize_daily_tracking_form_if_missing(target_day)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.nom AS categorie, t.achats, t.ca, t.cloturee
                FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
                ORDER BY c.nom ASC
                """,
                (str(target_day),),
            ).fetchall()
            return [
                {
                    "categorie": row["categorie"],
                    "achats_ttc": int(row["achats"] or 0),
                    "ca_final": int(row["ca"] or 0),
                    "cloturee": int(row["cloturee"] or 0),
                }
                for row in rows
            ]

    def save_daily_tracking_form_edits(
        self,
        jour: str,
        rows: list[dict[str, Any]],
        force_admin: bool = False,
    ) -> None:
        target_day = str(jour)
        self._initialize_daily_tracking_form_if_missing(target_day)
        current = self.get_daily_tracking_form(target_day)
        current_map = {str(r.get("categorie", "")): dict(r) for r in current}
        with self._connect() as conn:
            # Get category ID mapping
            cat_id_map = {
                str(r["nom"]): int(r["id"])
                for r in conn.execute(
                    "SELECT id, nom FROM categories WHERE parent_id IS NOT NULL"
                ).fetchall()
            }
            for row in rows:
                cat = str(row.get("categorie", "")).strip()
                if not cat:
                    continue
                cat_id = cat_id_map.get(cat)
                if not cat_id:
                    continue
                base = current_map.get(cat, {})
                if int(base.get("cloturee", 0) or 0) == 1 and not force_admin:
                    continue
                # Get existing SI or use the one from the row
                si = int(row.get("si", base.get("si", 0)) or 0)
                # Get achats from the row (not from si!)
                achats = max(0, int(row.get("achats_ttc", base.get("achats_ttc", 0)) or 0))
                ca = max(0, int(row.get("ca_final", base.get("ca_final", 0))))
                old_achats = int(base.get("achats_ttc", 0) or 0)
                old_ca = int(base.get("ca_final", 0) or 0)
                conn.execute(
                    """
                    INSERT INTO Tcollecte (
                        jour, categorie_id, si, achats, ca, cloturee, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 0, datetime('now'))
                    ON CONFLICT(jour, categorie_id) DO UPDATE SET
                        si = excluded.si,
                        achats = excluded.achats,
                        ca = excluded.ca,
                        updated_at = datetime('now')
                    """,
                    (target_day, cat_id, si, achats, ca),
                )
                if force_admin and (old_achats != achats or old_ca != ca):
                    conn.execute(
                        """
                        INSERT INTO audit_admin_actions (action, jour, old_value, new_value, actor)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            "correction_tracking",
                            target_day,
                            f"{cat}:achats={old_achats},ca={old_ca}",
                            f"{cat}:achats={achats},ca={ca}",
                            "admin",
                        ),
                    )

    def close_day_from_tracking_form(self, day: str) -> None:
        target_day = str(day)
        rows = self.get_daily_tracking_form(target_day)
        final_ca_by_category = [
            {
                "categorie": str(r.get("categorie", "")),
                "ca_ttc_final": int(r.get("ca_final", 0) or 0),
            }
            for r in rows
            if str(r.get("categorie", "")).strip()
        ]
        self.close_day_and_prepare_next(target_day, final_ca_by_category)

        # Mark as cloturee in Tcollecte
        with self._connect() as conn:
            # Get category IDs
            cat_id_map = {
                str(r["nom"]): int(r["id"])
                for r in conn.execute(
                    "SELECT id, nom FROM categories WHERE parent_id IS NOT NULL"
                ).fetchall()
            }
            for cat, ca_info in {
                r["categorie"]: r["ca_ttc_final"] for r in final_ca_by_category
            }.items():
                cat_id = cat_id_map.get(cat)
                if cat_id:
                    conn.execute(
                        """
                        UPDATE Tcollecte
                        SET cloturee = 1, updated_at = datetime('now')
                        WHERE jour = ? AND categorie_id = ?
                        """,
                        (target_day, cat_id),
                    )

        next_day = self._next_day_iso(target_day)
        self._initialize_daily_tracking_form_if_missing(next_day)

    def close_day_and_prepare_next(
        self,
        jour: str,
        final_ca_by_category: list[dict[str, Any]],
    ) -> None:
        """Cloture le jour: ecrase le CA par categorie, fige les lignes puis prepare le jour suivant."""
        target_day = str(jour)
        self._initialize_daily_tracking_if_missing(target_day)
        self._upsert_daily_closure_by_category(target_day, final_ca_by_category)

        current = self.get_daily_tracking_by_category(target_day)
        ca_map = {
            str(row.get("categorie", "")): int(row.get("ca_ttc_final", 0))
            for row in final_ca_by_category
        }

        closed_rows: list[dict[str, Any]] = []
        for row in current:
            cat = str(row.get("categorie", ""))
            si = int(row.get("si", 0) or 0)
            achats = int(row.get("achats", 0) or 0)
            sf = int(row.get("sf", 0) or 0)
            env = int(row.get("env", 0) or 0)
            # Vente = SI + Achats - SF
            vente_theorique = si + achats - sf + env
            vente_ca = int(ca_map.get(cat, row.get("vente_ca", 0) or 0))
            closed_rows.append(
                self._build_tracking_row(
                    categorie=cat,
                    si=si,
                    achats=achats,
                    vente_ca=vente_ca,
                    sf=sf,
                    env=env,
                    vente_theorique=vente_theorique,
                    cloturee=1,
                )
            )
        self.upsert_daily_tracking(target_day, closed_rows)

        next_day = self._next_day_iso(target_day)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(1) AS n FROM Tcollecte WHERE jour = ?",
                (next_day,),
            ).fetchone()
            if int(row["n"] or 0) > 0:
                return
        next_rows: list[dict[str, Any]] = []
        for row in closed_rows:
            sf = int(row.get("sf", 0))
            next_rows.append(
                self._build_tracking_row(
                    categorie=str(row.get("categorie", "")),
                    si=sf,
                    achats=0,
                    vente_ca=0,
                    sf=sf,
                    env=0,
                    vente_theorique=0,
                    cloturee=0,
                )
            )
        self.upsert_daily_tracking(next_day, next_rows)

    def get_category_collection_interval(
        self,
        date_debut: str,
        date_fin: str,
    ) -> list[dict[str, Any]]:
        """Collecte par categorie sur un intervalle [date_debut, date_fin]."""
        start = str(date_debut)
        end = str(date_fin)
        if end < start:
            start, end = end, start
        _, end_exclusive = self._day_bounds(end)

        with self._connect() as conn:
            self._initialize_daily_tracking_if_missing(start)
            self._initialize_daily_tracking_if_missing(end)
            self._sync_unclosed_day_metrics(start)
            self._sync_unclosed_day_metrics(end)

            rows = conn.execute(
                """
                WITH cats AS (
                    SELECT DISTINCT c.nom AS categorie
                    FROM Tcollecte a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    WHERE a.jour BETWEEN ? AND ?
                ),
                deb AS (
                    SELECT c.nom AS categorie, a.si AS si
                    FROM Tcollecte a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    WHERE a.jour = ?
                ),
                fin AS (
                    SELECT c.nom AS categorie, a.sf AS sf
                    FROM Tcollecte a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    WHERE a.jour = ?
                ),
                aggr AS (
                    SELECT
                        c.nom AS categorie,
                        SUM(a.achats) AS achats,
                        SUM(a.ca) AS ca
                    FROM Tcollecte a
                    INNER JOIN categories c ON c.id = a.categorie_id
                    WHERE a.jour BETWEEN ? AND ?
                    GROUP BY c.nom
                ),
                enlevee AS (
                    SELECT
                        categorie,
                        SUM(valeur) AS demarque
                    FROM historique_produits_enleves
                    WHERE jour >= ? AND jour < ?
                    GROUP BY categorie
                )
                SELECT
                    c.categorie,
                    COALESCE(d.si, 0) AS si,
                    COALESCE(a.achats, 0) AS achats,
                    COALESCE(e.demarque, 0) AS demarque,
                    COALESCE(a.ca, 0) AS ca,
                    COALESCE(f.sf, 0) AS sf
                FROM cats c
                LEFT JOIN deb d ON d.categorie = c.categorie
                LEFT JOIN fin f ON f.categorie = c.categorie
                LEFT JOIN aggr a ON a.categorie = c.categorie
                LEFT JOIN enlevee e ON e.categorie = c.categorie
                ORDER BY c.categorie ASC
                """,
                (start, end, start, end, start, end, start, end_exclusive),
            ).fetchall()

            result: list[dict[str, Any]] = []
            for row in rows:
                si = int(row["si"] or 0)
                achats = int(row["achats"] or 0)
                demarque = int(row["demarque"] or 0)
                sf = int(row["sf"] or 0)
                result.append(
                    {
                        "date_debut": start,
                        "date_fin": end,
                        "categorie": str(row["categorie"]),
                        "si": si,
                        "achats": achats,
                        "demarque": demarque,
                        "sf": sf,
                    }
                )
            return result
