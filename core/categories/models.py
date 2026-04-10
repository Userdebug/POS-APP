"""Models for product categories."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Category:
    """Product category model with hierarchical support."""

    id: int | None = None
    nom: str = ""
    parent_id: int | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    # Runtime properties (not stored in DB)
    children: list[Category] = field(default_factory=list)
    product_count: int = 0

    def is_parent(self) -> bool:
        """Check if this is a parent category."""
        return self.parent_id is None

    def is_child(self) -> bool:
        """Check if this is a child category."""
        return self.parent_id is not None

    def to_dict(self) -> dict:
        """Convert to dictionary for database operations."""
        return {
            "nom": self.nom,
            "parent_id": self.parent_id,
        }


@dataclass
class CategoryTreeNode:
    """Tree node for hierarchical category display."""

    category: Category
    level: int = 0
    is_expanded: bool = True

    @property
    def display_name(self) -> str:
        """Get display name with indentation for hierarchy."""
        return "  " * self.level + self.category.nom
