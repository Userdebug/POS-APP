"""Business logic for settings management."""

from __future__ import annotations

from typing import Any

from core.settings.models import SettingsCategory, SettingsItem
from core.settings.repository import SettingsRepository


class SettingsService:
    """Service for managing settings with business logic."""

    def __init__(self, repository: SettingsRepository) -> None:
        self._repo = repository

    # === Category Management ===

    def get_categories(self) -> list[SettingsCategory]:
        """Return visible categories ordered by display_order."""
        categories = self._repo.list_categories()
        return [c for c in categories if c.is_visible]

    def get_all_categories(self) -> list[SettingsCategory]:
        """Return all categories (including hidden)."""
        return self._repo.list_categories()

    def get_category_by_key(self, cle: str) -> SettingsCategory | None:
        """Get category by its unique key."""
        return self._repo.get_category_by_key(cle)

    def add_category(self, nom: str, cle: str, description: str | None = None) -> int:
        """Add a new category."""
        categories = self._repo.list_categories()
        display_order = max((c.display_order for c in categories), default=-1) + 1
        category = SettingsCategory(
            nom=nom,
            cle=cle,
            description=description,
            display_order=display_order,
            is_visible=True,
        )
        return self._repo.create_category(category)

    def update_category(self, id: int, nom: str, description: str | None) -> None:
        """Update a category."""
        category = self._repo.get_category_by_id(id)
        if category:
            category.nom = nom
            category.description = description
            self._repo.update_category(category)

    def delete_category(self, id: int) -> None:
        """Delete a category and all its items."""
        self._repo.delete_category(id)

    def reorder_categories(self, category_ids: list[int]) -> None:
        """Reorder categories by list of IDs."""
        self._repo.reorder_categories(category_ids)

    # === Item Management ===

    def get_items(self, category_key: str | None = None) -> list[SettingsItem]:
        """Get items for a category or all items."""
        if category_key:
            category = self._repo.get_category_by_key(category_key)
            if category:
                return [i for i in self._repo.list_items(category.id) if i.is_visible]
            return []
        return [i for i in self._repo.list_items() if i.is_visible]

    def get_all_items(self, category_key: str | None = None) -> list[SettingsItem]:
        """Get all items (including hidden)."""
        if category_key:
            category = self._repo.get_category_by_key(category_key)
            if category:
                return self._repo.list_items(category.id)
            return []
        return self._repo.list_items()

    def get_item(self, key: str) -> SettingsItem | None:
        """Get an item by its key."""
        return self._repo.get_item_by_key(key)

    def get_item_value(self, key: str, default: Any = None, value_type: str = "string") -> Any:
        """Get typed value of an item with fallback."""
        item = self._repo.get_item_by_key(key)
        if item is None:
            return default
        try:
            return item.get_typed_value()
        except (ValueError, TypeError):
            return default

    def set_item(
        self,
        key: str,
        value: Any,
        value_type: str = "string",
        description: str | None = None,
        category_key: str = "general",
        is_sensitive: bool = False,
    ) -> None:
        """Set or create an item."""
        category = self._repo.get_category_by_key(category_key)
        if not category:
            raise ValueError(f"Category '{category_key}' not found")

        existing = self._repo.get_item_by_key(key)
        display_order = existing.display_order if existing else 0

        item = SettingsItem(
            id=existing.id if existing else None,
            categorie_id=category.id,
            cle=key,
            valeur="",
            type=value_type,
            description=description,
            display_order=display_order,
            is_visible=True,
            is_sensitive=is_sensitive,
        )
        item.set_typed_value(value)

        if existing:
            self._repo.update_item(item)
        else:
            self._repo.upsert_item(item)

    def delete_item(self, key: str) -> None:
        """Delete an item by key."""
        item = self._repo.get_item_by_key(key)
        if item and item.id:
            self._repo.delete_item(item.id)

    def reorder_items(self, category_key: str, item_keys: list[str]) -> None:
        """Reorder items in a category."""
        category = self._repo.get_category_by_key(category_key)
        if not category:
            return

        items = self._repo.list_items(category.id)
        key_to_id = {item.cle: item.id for item in items}
        order = [key_to_id[k] for k in item_keys if k in key_to_id]
        self._repo.reorder_items(category.id, order)

    # === Initialization ===

    def initialize_default_categories(self) -> None:
        """Create default categories if they don't exist."""
        defaults = [
            ("General", "general", "Paramètres généraux de l'application", 1),
            ("Financial", "financial", "Paramètres financiers et fiscaux", 2),
            ("Display", "display", "Paramètres d'affichage", 3),
        ]
        for nom, cle, desc, order in defaults:
            existing = self._repo.get_category_by_key(cle)
            if not existing:
                category = SettingsCategory(
                    nom=nom,
                    cle=cle,
                    description=desc,
                    display_order=order,
                    is_visible=True,
                )
                self._repo.create_category(category)
