"""Initialisation du schema SQLite et migrations."""

from __future__ import annotations

from pathlib import Path


class SchemaInitializer:
    """Initialise le schema SQLite et applique les migrations.

    Args:
        schema_path: Chemin vers le fichier schema.sql.
    """

    def __init__(self, schema_path: Path) -> None:
        self.schema_path = schema_path

    def init_database(self, connect) -> None:
        """Execute le schema SQL et applique les migrations.

        Args:
            connect: Function returning a sqlite3.Connection context.
        """
        schema = self.schema_path.read_text(encoding="utf-8")
        with connect() as conn:
            conn.executescript(schema)
        self.migrate_schema(connect)

    def migrate_schema(self, connect) -> None:
        """Applique les migrations incrementales.

        Ajoute les colonnes en_promo et prix_promo a la table produits
        si elles n'existent pas deja.
        Migre les colonnes de analyse_journaliere_categories.
        Renomme les tables analyse_journaliere_categories -> Tcollecte et achats -> Tachats.
        Migre et nettoie Tcollecte, cree table Tsf pour rapports.
        """
        with connect() as conn:
            # ... existing migrations for produits and ventes ...

            # Migration pour Tcollecte (renamed from analyse_journaliere_categories)
            tcollecte_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='Tcollecte'"
            ).fetchone()
            if tcollecte_exists:
                tcollecte_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(Tcollecte)").fetchall()
                }

                # Check if we need to migrate column names (from old suffix format)
                needs_migration = (
                    "si_ht" in tcollecte_columns
                    or "achats_ttc" in tcollecte_columns
                    or "vente_ca_ttc" in tcollecte_columns
                    or "sf_ht" in tcollecte_columns
                    or "vente_theorique_ttc" in tcollecte_columns
                    or "marge_ttc" in tcollecte_columns
                )

                if needs_migration:
                    # Create new table with correct schema (no ca_temporaire)
                    conn.execute("""
                        CREATE TABLE Tcollecte_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            jour TEXT NOT NULL,
                            categorie_id INTEGER NOT NULL,
                            si INTEGER NOT NULL DEFAULT 0,
                            achats INTEGER NOT NULL DEFAULT 0,
                            ca INTEGER NOT NULL DEFAULT 0,
                            sf INTEGER NOT NULL DEFAULT 0,
                            env INTEGER NOT NULL DEFAULT 0,
                            vente_theorique INTEGER NOT NULL DEFAULT 0,
                            marge INTEGER NOT NULL DEFAULT 0,
                            cloturee INTEGER NOT NULL DEFAULT 0,
                            created_at TEXT NOT NULL DEFAULT (datetime('now')),
                            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                            UNIQUE(jour, categorie_id),
                            FOREIGN KEY (categorie_id) REFERENCES categories(id)
                        )
                    """)

                    column_mappings = {
                        "si": "si_ht",
                        "achats": "achats_ttc",
                        "ca": "vente_ca_ttc",
                        "sf": "sf_ht",
                        "vente_theorique": "vente_theorique_ttc",
                        "marge": "marge_ttc",
                    }

                    select_columns = []
                    for new_col in [
                        "id",
                        "jour",
                        "categorie_id",
                        "si",
                        "achats",
                        "ca",
                        "sf",
                        "env",
                        "vente_theorique",
                        "marge",
                        "cloturee",
                        "created_at",
                        "updated_at",
                    ]:
                        old_col = column_mappings.get(new_col, new_col)
                        if old_col in tcollecte_columns:
                            select_columns.append(old_col)
                        else:
                            select_columns.append(
                                f"0 AS {new_col}" if new_col == "env" else f"NULL AS {new_col}"
                            )

                    conn.execute(f"""
                        INSERT INTO Tcollecte_new
                        (id, jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee, created_at, updated_at)
                        SELECT {", ".join(select_columns)}
                        FROM Tcollecte
                    """)

                    conn.execute("DROP TABLE Tcollecte")
                    conn.execute("ALTER TABLE Tcollecte_new RENAME TO Tcollecte")

            # Migration: soft delete for ventes
            # ... existing code unchanged ...

            # ---- NEW MIGRATION: Tcollecte cleanup and Tsf creation ----
            # Check if already migrated to avoid re-running
            migration_key = "TCOLLECTE_MIGRATION_V2_DONE"
            param_val = conn.execute(
                "SELECT valeur FROM parametres WHERE cle = ?", (migration_key,)
            ).fetchone()
            if param_val and param_val["valeur"] == "1":
                # Already done, skip
                pass
            else:
                # Re-run schema.sql to add new tables/indexes (Tsf, indexes)
                schema_path = self.schema_path
                schema_sql = schema_path.read_text(encoding="utf-8")
                conn.executescript(schema_sql)

                # Step 1: Preserve CA from ca_temporaire (legacy column)
                tcols = [r[1] for r in conn.execute("PRAGMA table_info(Tcollecte)").fetchall()]
                if "ca_temporaire" in tcols:
                    conn.execute("""
                        UPDATE Tcollecte
                        SET ca = ca_temporaire
                        WHERE ca = 0 AND ca_temporaire > 0
                    """)
                    conn.execute("UPDATE Tcollecte SET ca_temporaire = 0")

                # Step 2: Ensure all days have rows for all OW categories
                days = [
                    r["jour"]
                    for r in conn.execute(
                        "SELECT DISTINCT jour FROM Tcollecte ORDER BY jour"
                    ).fetchall()
                ]
                # OW categories
                ow_categories = [
                    r["nom"]
                    for r in conn.execute(
                        """
                        SELECT c.nom FROM categories c
                        JOIN categories parent ON c.parent_id = parent.id
                        WHERE parent.nom = 'Catégorie 1 - OW (Owners)'
                        """
                    ).fetchall()
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
                                        (jour, categorie_id, si, achats, ca, sf, env, vente_theorique, marge, cloturee)
                                    VALUES (?, ?, 0, 0, 0, 0, 0, 0, 0, 0)
                                    """,
                                    (jour, cat_id),
                                )

                # Step 3: Remove duplicate rows (keep lowest id)
                conn.execute("""
                    DELETE FROM Tcollecte
                    WHERE id NOT IN (
                        SELECT MIN(id) FROM Tcollecte
                        GROUP BY jour, categorie_id
                    )
                """)

                # Step 4: Recompute derived fields once
                rows = conn.execute("SELECT id, si, achats, sf, env, ca FROM Tcollecte").fetchall()
                for row in rows:
                    si = row["si"] or 0
                    achats = row["achats"] or 0
                    sf = row["sf"] or 0
                    env = row["env"] or 0
                    ca = row["ca"] or 0
                    vente_theo = max(0, si + achats - sf - env)
                    marge = ca - vente_theo
                    conn.execute(
                        "UPDATE Tcollecte SET vente_theorique = ?, marge = ? WHERE id = ?",
                        (vente_theo, marge, row["id"]),
                    )

                # Step 5: Drop legacy tables if they exist
                conn.execute("DROP TABLE IF EXISTS suivi_journalier_categories")
                conn.execute("DROP TABLE IF EXISTS suivi_formulaire_journalier")

                # Step 6: Populate Tsf for all historical dates
                tcollecte_rows = conn.execute("""
                    SELECT t.jour, t.categorie_id, c.nom AS categorie,
                           t.si, t.achats, t.ca, t.env, t.cloturee
                    FROM Tcollecte t
                    JOIN categories c ON t.categorie_id = c.id
                    ORDER BY t.jour, c.nom
                """).fetchall()

                if tcollecte_rows:
                    # Compute current SF snapshot per category from produits
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
                        ca_ttc = int(r["ca"] or 0)
                        sf_ttc = sf_map.get(categorie, 0)
                        vente_theo_ttc = max(0, si_ttc + achats_ttc - sf_ttc - env_ttc)
                        marge_ttc = ca_ttc - vente_theo_ttc
                        marge_pct = (
                            (marge_ttc / vente_theo_ttc * 100.0) if vente_theo_ttc > 0 else 0.0
                        )
                    tsf_inserts.append(
                        (
                            categorie_id,
                            si_ttc,
                            achats_ttc,
                            ca_ttc,
                            env_ttc,
                            sf_ttc,
                            vente_theo_ttc,
                            marge_ttc,
                            marge_pct,
                        )
                    )

                    conn.executemany(
                        """
                        INSERT INTO Tsf (
                            categorie_id, si_ttc, achats_ttc, ca_ttc, env_ttc,
                            sf_ttc, vente_theorique_ttc, marge_ttc, marge_percent, refreshed_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                        ON CONFLICT(categorie_id) DO UPDATE SET
                            si_ttc = excluded.si_ttc,
                            achats_ttc = excluded.achats_ttc,
                            ca_ttc = excluded.ca_ttc,
                            env_ttc = excluded.env_ttc,
                            sf_ttc = excluded.sf_ttc,
                            vente_theorique_ttc = excluded.vente_theorique_ttc,
                            marge_ttc = excluded.marge_ttc,
                            marge_percent = excluded.marge_percent,
                            refreshed_at = datetime('now')
                        """,
                        tsf_inserts,
                    )

                # Step 7: Mark migration as done
                conn.execute(
                    "INSERT OR REPLACE INTO parametres (cle, valeur, description) VALUES (?, ?, ?)",
                    (migration_key, "1", "Tcollecte/Tsf migration v2 applied"),
                )

            # Step 8: Rebuild Tsf to remove jour column if present (new schema: one row per category)
            tsf_info = conn.execute("PRAGMA table_info(Tsf)").fetchall()
            tsf_columns = {row["name"] for row in tsf_info}
            if "jour" in tsf_columns:
                # Drop old Tsf (data is cache; safe to lose)
                conn.execute("DROP TABLE IF EXISTS Tsf")
                # Recreate Tsf with new schema (no jour)
                conn.execute(
                    """
                    CREATE TABLE Tsf (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        categorie_id INTEGER NOT NULL,
                        si_ttc INTEGER NOT NULL DEFAULT 0,
                        achats_ttc INTEGER NOT NULL DEFAULT 0,
                        ca_ttc INTEGER NOT NULL DEFAULT 0,
                        env_ttc INTEGER NOT NULL DEFAULT 0,
                        sf_ttc INTEGER NOT NULL DEFAULT 0,
                        vente_theorique_ttc INTEGER NOT NULL DEFAULT 0,
                        marge_ttc INTEGER NOT NULL DEFAULT 0,
                        marge_percent REAL NOT NULL DEFAULT 0.0,
                        refreshed_at TEXT NOT NULL DEFAULT (datetime('now')),
                        UNIQUE(categorie_id),
                        FOREIGN KEY (categorie_id) REFERENCES categories(id) ON DELETE CASCADE
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tsf_categorie ON Tsf(categorie_id)")
                conn.execute(
                    "INSERT OR REPLACE INTO parametres (cle, valeur, description) VALUES (?, ?, ?)",
                    (
                        "TSF_NO_JOUR_MIGRATION",
                        "1",
                        "Tsf jour column removed; table now category-aggregated",
                    ),
                )

            # Step 9: Add ca_temporaire column to Tcollecte (refactoring for live CA separation)
            tcollecte_columns = {
                row[1] for row in conn.execute("PRAGMA table_info(Tcollecte)").fetchall()
            }
            if "ca_temporaire" not in tcollecte_columns:
                conn.execute(
                    "ALTER TABLE Tcollecte ADD COLUMN ca_temporaire INTEGER NOT NULL DEFAULT 0"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO parametres (cle, valeur, description) VALUES (?, ?, ?)",
                    (
                        "TCOLLECTE_CA_TEMPORAIRE_MIGRATION",
                        "1",
                        "Added ca_temporaire column to Tcollecte for live CA separation",
                    ),
                )
            else:
                # Migration for existing data: clear ca_temporaire for closed days
                # Closed days should only have ca (definitive CA), not ca_temporaire
                conn.execute(
                    "UPDATE Tcollecte SET ca_temporaire = 0 WHERE cloturee = 1 AND ca_temporaire > 0"
                )
                conn.execute(
                    "INSERT OR REPLACE INTO parametres (cle, valeur, description) VALUES (?, ?, ?)",
                    (
                        "TCOLLECTE_CA_TEMPORAIRE_CLEANUP",
                        "1",
                        "Cleared ca_temporaire for closed days",
                    ),
                )
