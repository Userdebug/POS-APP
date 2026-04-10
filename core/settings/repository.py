"""Repository for settings data access."""

from __future__ import annotations

from typing import Callable

from core.settings.models import SettingsCategory, SettingsItem


class SettingsRepository:
    """Repository for settings CRUD operations."""

    def __init__(self, connect: Callable[[], object]) -> None:
        self._connect = connect
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize the settings schema if not exists."""
        with self._connect() as conn:
            # Create categories table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings_categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom TEXT NOT NULL UNIQUE,
                    cle TEXT NOT NULL UNIQUE,
                    description TEXT,
                    display_order INTEGER NOT NULL DEFAULT 0,
                    is_visible INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            # Create items table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS settings_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    categorie_id INTEGER NOT NULL,
                    cle TEXT NOT NULL UNIQUE,
                    valeur TEXT NOT NULL,
                    type TEXT NOT NULL DEFAULT 'string',
                    description TEXT,
                    display_order INTEGER NOT NULL DEFAULT 0,
                    is_visible INTEGER NOT NULL DEFAULT 1,
                    is_sensitive INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                    FOREIGN KEY (categorie_id) REFERENCES settings_categories(id)
                )
            """)
            conn.commit()

    # === Category CRUD ===

    def list_categories(self) -> list[SettingsCategory]:
        """List all categories ordered by display_order."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM settings_categories ORDER BY display_order"
            ).fetchall()
            return [
                SettingsCategory(
                    id=row["id"],
                    nom=row["nom"],
                    cle=row["cle"],
                    description=row["description"],
                    display_order=row["display_order"],
                    is_visible=bool(row["is_visible"]),
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    def get_category_by_id(self, id: int) -> SettingsCategory | None:
        """Get category by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM settings_categories WHERE id = ?", (id,)).fetchone()
            if not row:
                return None
            return SettingsCategory(
                id=row["id"],
                nom=row["nom"],
                cle=row["cle"],
                description=row["description"],
                display_order=row["display_order"],
                is_visible=bool(row["is_visible"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def get_category_by_key(self, cle: str) -> SettingsCategory | None:
        """Get category by unique key."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM settings_categories WHERE cle = ?", (cle,)).fetchone()
            if not row:
                return None
            return SettingsCategory(
                id=row["id"],
                nom=row["nom"],
                cle=row["cle"],
                description=row["description"],
                display_order=row["display_order"],
                is_visible=bool(row["is_visible"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )

    def create_category(self, category: SettingsCategory) -> int:
        """Create a new category and return its ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO settings_categories (nom, cle, description, display_order, is_visible)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    category.nom,
                    category.cle,
                    category.description,
                    category.display_order,
                    1 if category.is_visible else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_category(self, category: SettingsCategory) -> None:
        """Update an existing category."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE settings_categories
                SET nom = ?, description = ?, display_order = ?, is_visible = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    category.nom,
                    category.description,
                    category.display_order,
                    1 if category.is_visible else 0,
                    category.id,
                ),
            )
            conn.commit()

    def delete_category(self, id: int) -> None:
        """Delete a category and all its items."""
        with self._connect() as conn:
            conn.execute("DELETE FROM settings_items WHERE categorie_id = ?", (id,))
            conn.execute("DELETE FROM settings_categories WHERE id = ?", (id,))
            conn.commit()

    def reorder_categories(self, order: list[int]) -> None:
        """Reorder categories by updating display_order."""
        with self._connect() as conn:
            for idx, cat_id in enumerate(order):
                conn.execute(
                    "UPDATE settings_categories SET display_order = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (idx, cat_id),
                )
            conn.commit()

    # === Item CRUD ===

    def list_items(self, categorie_id: int | None = None) -> list[SettingsItem]:
        """List all items, optionally filtered by category."""
        with self._connect() as conn:
            if categorie_id is not None:
                rows = conn.execute(
                    "SELECT * FROM settings_items WHERE categorie_id = ? ORDER BY display_order",
                    (categorie_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM settings_items ORDER BY display_order"
                ).fetchall()
            return [self._row_to_item(row) for row in rows]

    def _row_to_item(self, row: dict) -> SettingsItem:
        """Convert a database row to SettingsItem."""
        return SettingsItem(
            id=row["id"],
            categorie_id=row["categorie_id"],
            cle=row["cle"],
            valeur=row["valeur"],
            type=row["type"],
            description=row["description"],
            display_order=row["display_order"],
            is_visible=bool(row["is_visible"]),
            is_sensitive=bool(row["is_sensitive"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_item_by_id(self, id: int) -> SettingsItem | None:
        """Get item by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM settings_items WHERE id = ?", (id,)).fetchone()
            return self._row_to_item(row) if row else None

    def get_item_by_key(self, cle: str) -> SettingsItem | None:
        """Get item by unique key."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM settings_items WHERE cle = ?", (cle,)).fetchone()
            return self._row_to_item(row) if row else None

    def create_item(self, item: SettingsItem) -> int:
        """Create a new item and return its ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO settings_items
                (categorie_id, cle, valeur, type, description,
                 display_order, is_visible, is_sensitive)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.categorie_id,
                    item.cle,
                    item.valeur,
                    item.type,
                    item.description,
                    item.display_order,
                    1 if item.is_visible else 0,
                    1 if item.is_sensitive else 0,
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_item(self, item: SettingsItem) -> None:
        """Update an existing item."""
        with self._connect() as conn:
            # Get current item to preserve display_order
            current = conn.execute(
                "SELECT display_order FROM settings_items WHERE id = ?",
                (item.id,),
            ).fetchone()
            display_order = current["display_order"] if current else item.display_order

            conn.execute(
                """
                UPDATE settings_items
                SET categorie_id = ?, valeur = ?, type = ?, description = ?,
                    display_order = ?, is_visible = ?, is_sensitive = ?,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (
                    item.categorie_id,
                    item.valeur,
                    item.type,
                    item.description,
                    display_order,
                    1 if item.is_visible else 0,
                    1 if item.is_sensitive else 0,
                    item.id,
                ),
            )
            conn.commit()

    def upsert_item(self, item: SettingsItem) -> int:
        """Insert or update an item by key."""
        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id, display_order FROM settings_items WHERE cle = ?", (item.cle,)
            ).fetchone()
            if existing:
                display_order = existing["display_order"] if existing else 0
                conn.execute(
                    """
                    UPDATE settings_items
                    SET categorie_id = ?, valeur = ?, type = ?, description = ?,
                        display_order = ?, is_visible = ?, is_sensitive = ?,
                        updated_at = datetime('now')
                    WHERE cle = ?
                    """,
                    (
                        item.categorie_id,
                        item.valeur,
                        item.type,
                        item.description,
                        display_order,
                        1 if item.is_visible else 0,
                        1 if item.is_sensitive else 0,
                        item.cle,
                    ),
                )
                conn.commit()
                return existing["id"]
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO settings_items
                    (categorie_id, cle, valeur, type, description,
                     display_order, is_visible, is_sensitive)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.categorie_id,
                        item.cle,
                        item.valeur,
                        item.type,
                        item.description,
                        item.display_order,
                        1 if item.is_visible else 0,
                        1 if item.is_sensitive else 0,
                    ),
                )
                conn.commit()
                return cursor.lastrowid

    def delete_item(self, id: int) -> None:
        """Delete an item by ID."""
        with self._connect() as conn:
            conn.execute("DELETE FROM settings_items WHERE id = ?", (id,))
            conn.commit()

    def reorder_items(self, categorie_id: int, order: list[int]) -> None:
        """Reorder items in a category by updating display_order."""
        with self._connect() as conn:
            for idx, item_id in enumerate(order):
                conn.execute(
                    "UPDATE settings_items SET display_order = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (idx, item_id),
                )
            conn.commit()
