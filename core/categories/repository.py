"""Repository for product categories data access."""

from __future__ import annotations

from typing import Callable

from core.categories.models import Category


class CategoryRepository:
    """Repository for product category CRUD operations."""

    def __init__(self, connect: Callable[[], object]) -> None:
        self._connect = connect

    # === CRUD Operations ===

    def list_all(self) -> list[Category]:
        """List all categories ordered by name."""
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM categories ORDER BY nom").fetchall()
            return [self._row_to_category(dict(row)) for row in rows]

    def list_parents(self) -> list[Category]:
        """List only parent categories (no parent_id)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM categories WHERE parent_id IS NULL ORDER BY nom"
            ).fetchall()
            return [self._row_to_category(dict(row)) for row in rows]

    def list_children(self, parent_id: int) -> list[Category]:
        """List child categories of a parent."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM categories WHERE parent_id = ? ORDER BY nom",
                (parent_id,),
            ).fetchall()
            return [self._row_to_category(dict(row)) for row in rows]

    def get_by_id(self, id: int) -> Category | None:
        """Get category by ID."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE id = ?", (id,)).fetchone()
            return self._row_to_category(dict(row)) if row else None

    def get_by_name(self, nom: str) -> Category | None:
        """Get category by name."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE nom = ?", (nom,)).fetchone()
            return self._row_to_category(dict(row)) if row else None

    def get_by_name(self, nom: str) -> Category | None:
        """Get category by name."""
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM categories WHERE nom = ?", (nom,)).fetchone()
            return self._row_to_category(row) if row else None

    def create(self, category: Category) -> int:
        """Create a new category and return its ID."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO categories (nom, parent_id)
                VALUES (?, ?)
                """,
                (category.nom, category.parent_id),
            )
            conn.commit()
            return cursor.lastrowid

    def update(self, category: Category) -> None:
        """Update an existing category."""
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE categories
                SET nom = ?, parent_id = ?, updated_at = datetime('now')
                WHERE id = ?
                """,
                (category.nom, category.parent_id, category.id),
            )
            conn.commit()

    def delete(self, id: int) -> bool:
        """Delete a category. Returns False if category has products."""
        with self._connect() as conn:
            # Check if category has products
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM produits WHERE categorie_id = ?",
                (id,),
            ).fetchone()
            if count and count["cnt"] > 0:
                return False

            # Check if category has children
            child_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM categories WHERE parent_id = ?",
                (id,),
            ).fetchone()
            if child_count and child_count["cnt"] > 0:
                return False

            conn.execute("DELETE FROM categories WHERE id = ?", (id,))
            conn.commit()
            return True

    def delete_cascade(self, id: int) -> int:
        """Delete a category and all its descendants. Returns count deleted."""
        with self._connect() as conn:
            # Get all descendant IDs
            deleted_count = 0

            # Delete children first
            while True:
                children = conn.execute(
                    "SELECT id FROM categories WHERE parent_id = ?", (id,)
                ).fetchall()
                if not children:
                    break
                for child in children:
                    conn.execute("DELETE FROM categories WHERE id = ?", (child["id"],))
                    deleted_count += 1

            # Delete the category itself
            conn.execute("DELETE FROM categories WHERE id = ?", (id,))
            deleted_count += 1
            conn.commit()
            return deleted_count

    def reorder(self, category_ids: list[int]) -> None:
        """Reorder categories by updating display order."""
        # Note: Current schema doesn't have display_order for categories
        # This is a placeholder for future enhancement
        pass

    # === Helper Methods ===

    def _row_to_category(self, row: dict) -> Category:
        """Convert a database row to Category."""
        return Category(
            id=row["id"],
            nom=row["nom"],
            parent_id=row["parent_id"],
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

    def get_product_count(self, category_id: int) -> int:
        """Get the number of products in a category."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM produits WHERE categorie_id = ?",
                (category_id,),
            ).fetchone()
            return row["cnt"] if row else 0

    def get_children_count(self, category_id: int) -> int:
        """Get the number of child categories."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM categories WHERE parent_id = ?",
                (category_id,),
            ).fetchone()
            return row["cnt"] if row else 0

    def build_tree(self) -> list[Category]:
        """Build a tree structure of categories with children populated."""
        all_categories = self.list_all()

        # Create lookup
        category_map: dict[int, Category] = {}
        for cat in all_categories:
            if cat.id:
                category_map[cat.id] = cat

        # Build tree
        roots: list[Category] = []
        for cat in all_categories:
            if cat.parent_id is None:
                roots.append(cat)
            elif cat.parent_id in category_map:
                parent = category_map[cat.parent_id]
                parent.children.append(cat)

        # Sort children alphabetically
        for cat in category_map.values():
            cat.children.sort(key=lambda c: c.nom)

        return roots

    def get_path(self, category_id: int) -> list[Category]:
        """Get the path from root to this category."""
        path: list[Category] = []
        current = self.get_by_id(category_id)

        while current:
            path.insert(0, current)
            if current.parent_id:
                current = self.get_by_id(current.parent_id)
            else:
                break

        return path
