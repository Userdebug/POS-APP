"""Migration script for Tcollecte cleanup and Tsf initialization.

This migration:
1. Preserves CA from ca_temporaire to ca where needed
2. Ensures all OW categories have rows for all days
3. Removes duplicate Tcollecte rows
4. Recomputes derived fields (vente_theorique, marge)
5. Drops legacy tables (suivi_journalier_categories, suivi_formulaire_journalier)
6. Creates and populates Tsf table

Run once on app startup with parameter guard MIGRATION_TCOLLECTE_CLEAN_DONE.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any

logger: Any = None  # Will be set from calling module


def migrate_tcollecte_data(
    db_connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
) -> None:
    """One-time migration to clean Tcollecte and initialize Tsf."""
    with db_connect() as conn:
        # STEP 1: Preserve CA from ca_temporaire
        conn.execute("""
            UPDATE Tcollecte 
            SET ca = ca_temporaire 
            WHERE ca = 0 AND ca_temporaire > 0
        """)
        conn.execute("UPDATE Tcollecte SET ca_temporaire = 0")

        # STEP 2: Ensure all days have rows for all OW categories
        days = [r["jour"] for r in conn.execute("SELECT DISTINCT jour FROM Tcollecte").fetchall()]
        ow_categories = [
            r["nom"]
            for r in conn.execute("""
            SELECT c.nom FROM categories c
            JOIN categories parent ON c.parent_id = parent.id
            WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
        """).fetchall()
        ]
        cat_id_map = {
            row["nom"]: row["id"]
            for row in conn.execute("SELECT id, nom FROM categories").fetchall()
        }

        for jour in days:
            existing = [
                r["categorie"]
                for r in conn.execute(
                    """
                SELECT c.nom AS categorie FROM Tcollecte t
                JOIN categories c ON t.categorie_id = c.id
                WHERE t.jour = ?
            """,
                    (jour,),
                ).fetchall()
            ]
            for cat_name in ow_categories:
                if cat_name not in existing:
                    cat_id = cat_id_map.get(cat_name)
                    if cat_id:
                        conn.execute(
                            """
                            INSERT OR IGNORE INTO Tcollecte 
                            (jour, categorie_id, si, achats, ca, ca_temporaire, sf, env, vente_theorique, marge, cloturee)
                            VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0, 0)
                        """,
                            (jour, cat_id),
                        )

        # STEP 3: Remove duplicate rows (keep lowest id)
        conn.execute("""
            DELETE FROM Tcollecte
            WHERE id NOT IN (
                SELECT MIN(id) FROM Tcollecte
                GROUP BY jour, categorie_id
            )
        """)

        # STEP 4: Recompute derived fields once
        rows = conn.execute("""
            SELECT id, si, achats, sf, env, ca, cloturee 
            FROM Tcollecte
        """).fetchall()
        for row in rows:
            si = row["si"] or 0
            achats = row["achats"] or 0
            sf = row["sf"] or 0
            env = row["env"] or 0
            ca = row["ca"] or 0
            vente_theo = max(0, si + achats - sf - env)
            marge = ca - vente_theo
            conn.execute(
                """
                UPDATE Tcollecte 
                SET vente_theorique = ?, marge = ?
                WHERE id = ?
            """,
                (vente_theo, marge, row["id"]),
            )

        # STEP 5: Drop legacy tables
        conn.execute("DROP TABLE IF EXISTS suivi_journalier_categories")
        conn.execute("DROP TABLE IF EXISTS suivi_formulaire_journalier")

        # STEP 6: Create Tsf table and populate initial snapshot
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Tsf (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jour TEXT NOT NULL,
                categorie_id INTEGER NOT NULL,
                si_ttc INTEGER NOT NULL DEFAULT 0,
                achats_ttc INTEGER NOT NULL DEFAULT 0,
                ca_ttc INTEGER NOT NULL DEFAULT 0,
                env_ttc INTEGER NOT NULL DEFAULT 0,
                sf_ttc INTEGER NOT NULL DEFAULT 0,
                vente_theorique_ttc INTEGER NOT NULL DEFAULT 0,
                marge_ttc INTEGER NOT NULL DEFAULT 0,
                marge_percent REAL NOT NULL DEFAULT 0.0,
                is_closed INTEGER NOT NULL DEFAULT 0,
                refreshed_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(jour, categorie_id),
                FOREIGN KEY (categorie_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tsf_jour ON Tsf(jour)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tsf_jour_cat ON Tsf(jour, categorie_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tsf_closed ON Tsf(is_closed, jour)")

        # Populate Tsf for all historical dates from cleaned Tcollecte
        tcollecte_rows = conn.execute("""
            SELECT t.jour, t.categorie_id, c.nom AS categorie,
                   t.si, t.achats, t.ca, t.ca_temporaire, t.env, t.cloturee
            FROM Tcollecte t
            JOIN categories c ON t.categorie_id = c.id
            ORDER BY t.jour, c.nom
        """).fetchall()

        if tcollecte_rows:
            # Compute current SF snapshot per category (from current produits)
            sf_rows = conn.execute("""
                SELECT c.nom AS categorie, SUM((p.stock_boutique + p.stock_reserve) * p.pa) AS sf_ttc
                FROM produits p
                JOIN categories c ON p.categorie_id = c.id
                GROUP BY c.nom
            """).fetchall()
            sf_map = {str(r["categorie"]): int(r["sf_ttc"] or 0) for r in sf_rows}

            tsf_inserts = []
            for r in tcollecte_rows:
                jour = r["jour"]
                categorie_id = r["categorie_id"]
                categorie = str(r["categorie"])
                is_closed = r["cloturee"] == 1
                si_ttc = int(r["si"] or 0)
                achats_ttc = int(r["achats"] or 0)
                env_ttc = int(r["env"] or 0)
                ca_ttc = int(r["ca"] if is_closed else r["ca_temporaire"] or 0)
                sf_ttc = sf_map.get(categorie, 0)
                vente_theo_ttc = max(0, si_ttc + achats_ttc - sf_ttc - env_ttc)
                marge_ttc = ca_ttc - vente_theo_ttc
                marge_pct = (marge_ttc / ca_ttc * 100.0) if ca_ttc > 0 else 0.0
                tsf_inserts.append(
                    (
                        jour,
                        categorie_id,
                        si_ttc,
                        achats_ttc,
                        ca_ttc,
                        env_ttc,
                        sf_ttc,
                        vente_theo_ttc,
                        marge_ttc,
                        marge_pct,
                        int(is_closed),
                    )
                )

            conn.executemany(
                """
                INSERT INTO Tsf (
                    jour, categorie_id, si_ttc, achats_ttc, ca_ttc, env_ttc,
                    sf_ttc, vente_theorique_ttc, marge_ttc, marge_percent, is_closed, refreshed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(jour, categorie_id) DO UPDATE SET
                    si_ttc = excluded.si_ttc,
                    achats_ttc = excluded.achats_ttc,
                    ca_ttc = excluded.ca_ttc,
                    env_ttc = excluded.env_ttc,
                    sf_ttc = excluded.sf_ttc,
                    vente_theorique_ttc = excluded.vente_theorique_ttc,
                    marge_ttc = excluded.marge_ttc,
                    marge_percent = excluded.marge_percent,
                    is_closed = excluded.is_closed,
                    refreshed_at = datetime('now')
            """,
                tsf_inserts,
            )

        conn.commit()


def run_migration(
    db_connect: Callable[[], AbstractContextManager[sqlite3.Connection]],
    get_parameter: Callable[[str], str | None],
    set_parameter: Callable[[str, str], None],
) -> bool:
    """Run migration with parameter guard.

    Returns True if migration was executed, False if already done.
    """
    param_key = "MIGRATION_TCOLLECTE_CLEAN_DONE"

    if get_parameter(param_key):
        return False

    try:
        migrate_tcollecte_data(db_connect)
        set_parameter(param_key, "1")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
