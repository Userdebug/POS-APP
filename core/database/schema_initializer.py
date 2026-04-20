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
        Ajoute les colonnes de soft delete a la table ventes.
        Migre les colonnes de analyse_journaliere_categories.
        Renomme les tables analyse_journaliere_categories -> Tcollecte et achats -> Tachats.
        """
        with connect() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(produits)").fetchall()}

            if "en_promo" not in columns:
                conn.execute("ALTER TABLE produits ADD COLUMN en_promo INTEGER NOT NULL DEFAULT 0")
            if "prix_promo" not in columns:
                conn.execute("ALTER TABLE produits ADD COLUMN prix_promo INTEGER DEFAULT 0")
                conn.execute("UPDATE produits SET prix_promo = pa WHERE prix_promo = 0")

            # Migration: rename analyse_journaliere_categories to Tcollecte
            old_table = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='analyse_journaliere_categories'"
            ).fetchone()
            if old_table:
                # Check if new name doesn't exist yet
                new_table = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='Tcollecte'"
                ).fetchone()
                if not new_table:
                    conn.execute("ALTER TABLE analyse_journaliere_categories RENAME TO Tcollecte")

            # Migration: Add ca_temporaire column to Tcollecte if missing
            tcollecte_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='Tcollecte'"
            ).fetchone()
            if tcollecte_exists:
                tcollecte_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(Tcollecte)").fetchall()
                }
                if "ca_temporaire" not in tcollecte_columns:
                    conn.execute(
                        "ALTER TABLE Tcollecte ADD COLUMN ca_temporaire INTEGER NOT NULL DEFAULT 0"
                    )

            # Migration: rename achats to Tachats
            old_achats = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='achats'"
            ).fetchone()
            if old_achats:
                new_achats = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='Tachats'"
                ).fetchone()
                if not new_achats:
                    conn.execute("ALTER TABLE achats RENAME TO Tachats")

            # Migration: rename achats_lignes to Tachats_lignes
            old_lignes = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='achats_lignes'"
            ).fetchone()
            if old_lignes:
                new_lignes = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='Tachats_lignes'"
                ).fetchone()
                if not new_lignes:
                    conn.execute("ALTER TABLE achats_lignes RENAME TO Tachats_lignes")

            # Migration soft delete pour ventes
            table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='ventes'"
            ).fetchone()
            if table_exists:
                ventes_columns = {
                    row[1] for row in conn.execute("PRAGMA table_info(ventes)").fetchall()
                }

                if "deleted" not in ventes_columns:
                    conn.execute("ALTER TABLE ventes ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")
                if "deleted_by" not in ventes_columns:
                    conn.execute("ALTER TABLE ventes ADD COLUMN deleted_by INTEGER NULL")
                if "deleted_at" not in ventes_columns:
                    conn.execute("ALTER TABLE ventes ADD COLUMN deleted_at TEXT NULL")
                if "deleted_reason" not in ventes_columns:
                    conn.execute("ALTER TABLE ventes ADD COLUMN deleted_reason TEXT NULL")

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
                    # Create new table with correct schema
                    conn.execute("""
                        CREATE TABLE Tcollecte_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            jour TEXT NOT NULL,
                            categorie_id INTEGER NOT NULL,
                            si INTEGER NOT NULL DEFAULT 0,
                            achats INTEGER NOT NULL DEFAULT 0,
                            ca INTEGER NOT NULL DEFAULT 0,
                            ca_temporaire INTEGER NOT NULL DEFAULT 0,
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

                    # Copy data with column name mapping
                    column_mappings = {
                        "si": "si_ht",
                        "achats": "achats_ttc",
                        "ca": "vente_ca_ttc",
                        "sf": "sf_ht",
                        "vente_theorique": "vente_theorique_ttc",
                        "marge": "marge_ttc",
                    }

                    # Build select columns for old table
                    select_columns = []
                    for new_col in [
                        "id",
                        "jour",
                        "categorie_id",
                        "si",
                        "achats",
                        "ca",
                        "ca_temporaire",
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
                                f"0 AS {new_col}"
                                if new_col in ["env", "ca_temporaire"]
                                else f"NULL AS {new_col}"
                            )

                    # Insert data
                    conn.execute(f"""
                        INSERT INTO Tcollecte_new
                        (id, jour, categorie_id, si, achats, ca, ca_temporaire, sf, env, vente_theorique, marge, cloturee, created_at, updated_at)
                        SELECT {", ".join(select_columns)}
                        FROM Tcollecte
                    """)

                    # Replace old table
                    conn.execute("DROP TABLE Tcollecte")
                    conn.execute("ALTER TABLE Tcollecte_new RENAME TO Tcollecte")

                # Add ca_temporaire column if missing (for databases with correct column names but missing the column)
                tcollecte_columns_after = {
                    row[1] for row in conn.execute("PRAGMA table_info(Tcollecte)").fetchall()
                }
                if "ca_temporaire" not in tcollecte_columns_after:
                    conn.execute(
                        "ALTER TABLE Tcollecte ADD COLUMN ca_temporaire INTEGER NOT NULL DEFAULT 0"
                    )
