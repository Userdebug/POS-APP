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
        """
        with connect() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(produits)").fetchall()}

            if "en_promo" not in columns:
                conn.execute("ALTER TABLE produits ADD COLUMN en_promo INTEGER NOT NULL DEFAULT 0")
            if "prix_promo" not in columns:
                conn.execute("ALTER TABLE produits ADD COLUMN prix_promo INTEGER DEFAULT 0")
                conn.execute("UPDATE produits SET prix_promo = pa WHERE prix_promo = 0")

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

            # Migration pour analyse_journaliere_categories
            table_exists = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='analyse_journaliere_categories'"
            ).fetchone()
            if table_exists:
                ajc_columns = {
                    row[1]
                    for row in conn.execute(
                        "PRAGMA table_info(analyse_journaliere_categories)"
                    ).fetchall()
                }

                # Check if we need to migrate column names (SQLite doesn't support RENAME COLUMN)
                needs_migration = (
                    "si_ht" in ajc_columns
                    or "achats_ttc" in ajc_columns
                    or "vente_ca_ttc" in ajc_columns
                    or "sf_ht" in ajc_columns
                    or "vente_theorique_ttc" in ajc_columns
                    or "marge_ttc" in ajc_columns
                )

                if needs_migration:
                    # Create new table with correct schema
                    conn.execute("""
                        CREATE TABLE analyse_journaliere_categories_new (
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
                        "sf",
                        "vente_theorique",
                        "marge",
                        "cloturee",
                        "created_at",
                        "updated_at",
                    ]:
                        old_col = column_mappings.get(new_col, new_col)
                        if old_col in ajc_columns:
                            select_columns.append(old_col)
                        else:
                            select_columns.append(
                                f"0 AS {new_col}" if new_col in ["env"] else f"NULL AS {new_col}"
                            )

                    # Insert data
                    conn.execute(f"""
                        INSERT INTO analyse_journaliere_categories_new
                        (id, jour, categorie_id, si, achats, ca, sf, vente_theorique, marge, cloturee, created_at, updated_at)
                        SELECT {', '.join(select_columns)}
                        FROM analyse_journaliere_categories
                    """)

                    # Replace old table
                    conn.execute("DROP TABLE analyse_journaliere_categories")
                    conn.execute(
                        "ALTER TABLE analyse_journaliere_categories_new RENAME TO analyse_journaliere_categories"
                    )

                # Add env column if missing (for databases that already had correct column names)
                if "env" not in ajc_columns:
                    # Check again after potential migration
                    ajc_columns = {
                        row[1]
                        for row in conn.execute(
                            "PRAGMA table_info(analyse_journaliere_categories)"
                        ).fetchall()
                    }
                    if "env" not in ajc_columns:
                        conn.execute(
                            "ALTER TABLE analyse_journaliere_categories ADD COLUMN env INTEGER NOT NULL DEFAULT 0"
                        )
