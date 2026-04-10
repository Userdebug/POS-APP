"""Business logic for product category management."""

from __future__ import annotations

from core.categories.models import Category, CategoryTreeNode
from core.categories.repository import CategoryRepository


class CategoryService:
    """Service for managing product categories with business logic."""

    def __init__(self, repository: CategoryRepository) -> None:
        self._repo = repository

    # === Read Operations ===

    def get_all_categories(self) -> list[Category]:
        """Get all categories ordered by name."""
        return self._repo.list_all()

    def get_parent_categories(self) -> list[Category]:
        """Get only parent categories."""
        return self._repo.list_parents()

    def get_child_categories(self, parent_id: int) -> list[Category]:
        """Get child categories of a parent."""
        return self._repo.list_children(parent_id)

    def get_category_by_id(self, id: int) -> Category | None:
        """Get a category by ID."""
        return self._repo.get_by_id(id)

    def get_category_by_name(self, nom: str) -> Category | None:
        """Get a category by name."""
        return self._repo.get_by_name(nom)

    def get_category_tree(self) -> list[Category]:
        """Get categories as a tree structure."""
        return self._repo.build_tree()

    def get_category_tree_flat(self) -> list[CategoryTreeNode]:
        """Get categories as a flat list with hierarchy levels."""
        tree = self._repo.build_tree()
        flat: list[CategoryTreeNode] = []

        def flatten(categories: list[Category], level: int) -> None:
            for cat in categories:
                flat.append(CategoryTreeNode(category=cat, level=level))
                if cat.children:
                    flatten(cat.children, level + 1)

        flatten(tree, 0)
        return flat

    def get_category_path(self, category_id: int) -> list[Category]:
        """Get the path from root to category."""
        return self._repo.get_path(category_id)

    def get_category_stats(self, category_id: int) -> dict:
        """Get statistics for a category."""
        product_count = self._repo.get_product_count(category_id)
        children_count = self._repo.get_children_count(category_id)
        return {
            "product_count": product_count,
            "children_count": children_count,
        }

    # === Create Operations ===

    def create_category(self, nom: str, parent_id: int | None = None) -> tuple[int, str | None]:
        """Create a new category.

        Returns:
            Tuple of (category_id, error_message)
            If error_message is not None, creation failed.
        """
        # Validate name
        if not nom or not nom.strip():
            return 0, "Le nom de la catégorie ne peut pas être vide"

        nom = nom.strip()

        # Check for duplicates
        existing = self._repo.get_by_name(nom)
        if existing:
            return 0, f'La catégorie "{nom}" existe déjà'

        # Validate parent exists if specified
        if parent_id:
            parent = self._repo.get_by_id(parent_id)
            if not parent:
                return 0, "La catégorie parente n'existe pas"

        # Create category
        category = Category(nom=nom, parent_id=parent_id)
        category_id = self._repo.create(category)
        return category_id, None

    def create_parent_category(self, nom: str) -> tuple[int, str | None]:
        """Create a new parent category."""
        return self.create_category(nom, parent_id=None)

    def create_child_category(self, nom: str, parent_id: int) -> tuple[int, str | None]:
        """Create a new child category under a parent."""
        return self.create_category(nom, parent_id=parent_id)

    # === Update Operations ===

    def update_category(
        self, category_id: int, nom: str, parent_id: int | None = None
    ) -> str | None:
        """Update a category.

        Returns:
            Error message if failed, None if successful.
        """
        # Validate name
        if not nom or not nom.strip():
            return "Le nom de la catégorie ne peut pas être vide"

        nom = nom.strip()

        # Get existing category
        category = self._repo.get_by_id(category_id)
        if not category:
            return "La catégorie n'existe pas"

        # Check for name duplicates (excluding self)
        existing = self._repo.get_by_name(nom)
        if existing and existing.id != category_id:
            return f'La catégorie "{nom}" existe déjà'

        # Validate parent exists if specified
        if parent_id and parent_id != category_id:
            parent = self._repo.get_by_id(parent_id)
            if not parent:
                return "La catégorie parente n'existe pas"

            # Prevent setting self as parent (directly or indirectly)
            if parent_id == category_id:
                return "Une catégorie ne peut pas être son propre parent"

            # Check for circular reference
            path = self._repo.get_path(category_id)
            if any(c.id == parent_id for c in path):
                return "Impossible de créer une référence circulaire"

        # Update category
        category.nom = nom
        category.parent_id = parent_id
        self._repo.update(category)
        return None

    def move_category(self, category_id: int, new_parent_id: int | None) -> str | None:
        """Move a category to a new parent."""
        category = self._repo.get_by_id(category_id)
        if not category:
            return "La catégorie n'existe pas"

        return self.update_category(category_id, category.nom, new_parent_id)

    # === Delete Operations ===

    def delete_category(self, category_id: int) -> tuple[bool, str]:
        """Delete a category.

        Returns:
            Tuple of (success, message)
        """
        category = self._repo.get_by_id(category_id)
        if not category:
            return False, "La catégorie n'existe pas"

        # Check if category has products
        product_count = self._repo.get_product_count(category_id)
        if product_count > 0:
            return False, (
                f"Impossible de supprimer: {product_count} produit(s) "
                "appartiennent à cette catégorie"
            )

        # Check if category has children
        children_count = self._repo.get_children_count(category_id)
        if children_count > 0:
            return False, (
                f"Impossible de supprimer: la catégorie a {children_count} "
                "sous-catégorie(s). Veuillez les supprimer d'abord."
            )

        # Delete
        success = self._repo.delete(category_id)
        if success:
            return True, "Catégorie supprimée avec succès"
        return False, "Erreur lors de la suppression"

    def delete_category_cascade(self, category_id: int) -> tuple[bool, str]:
        """Delete a category and all its descendants.

        Returns:
            Tuple of (success, message)
        """
        category = self._repo.get_by_id(category_id)
        if not category:
            return False, "La catégorie n'existe pas"

        # Check if category has products
        product_count = self._repo.get_product_count(category_id)
        if product_count > 0:
            return False, (
                f"Impossible de supprimer: {product_count} produit(s) "
                "appartiennent à cette catégorie"
            )

        deleted_count = self._repo.delete_cascade(category_id)
        return True, f"{deleted_count} catégorie(s) supprimée(s)"

    # === Utility Methods ===

    def can_delete(self, category_id: int) -> tuple[bool, str]:
        """Check if a category can be deleted."""
        category = self._repo.get_by_id(category_id)
        if not category:
            return False, "La catégorie n'existe pas"

        product_count = self._repo.get_product_count(category_id)
        if product_count > 0:
            return False, f"{product_count} produit(s) utilisent cette catégorie"

        children_count = self._repo.get_children_count(category_id)
        if children_count > 0:
            return False, f"{children_count} sous-catégorie(s) sous cette catégorie"

        return True, ""

    def get_category_options(self) -> list[tuple[int, str]]:
        """Get category options for dropdown (id, display_name)."""
        tree = self.get_category_tree_flat()
        return [(cat.category.id, cat.display_name) for cat in tree]

    def get_parent_options(self) -> list[tuple[int, str]]:
        """Get parent category options for dropdown."""
        parents = self.get_parent_categories()
        return [(p.id, p.nom) for p in parents if p.id is not None]
