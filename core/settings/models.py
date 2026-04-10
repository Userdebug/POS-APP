"""Models for the settings system."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SettingsCategory:
    """Category for grouping settings items."""

    id: int | None = None
    nom: str = ""
    cle: str = ""  # unique key: "general", "financial", "display"
    description: str | None = None
    display_order: int = 0
    is_visible: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "nom": self.nom,
            "cle": self.cle,
            "description": self.description,
            "display_order": self.display_order,
            "is_visible": 1 if self.is_visible else 0,
        }


@dataclass
class SettingsItem:
    """Individual setting item with typed value support."""

    id: int | None = None
    categorie_id: int = 0
    cle: str = ""  # unique key: "tva_rate", "currency_label", "backup_dir"
    valeur: str = ""
    type: str = "string"  # "string", "int", "float", "boolean", "json"
    description: str | None = None
    display_order: int = 0
    is_visible: bool = True
    is_sensitive: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_typed_value(self) -> Any:
        """Return the value typed according to self.type."""
        if self.type == "boolean":
            return self.valeur == "1"
        if self.type == "int":
            return int(self.valeur)
        if self.type == "float":
            return float(self.valeur)
        if self.type == "json":
            return json.loads(self.valeur)
        return self.valeur

    def set_typed_value(self, value: Any) -> None:
        """Update the value as string according to type."""
        if self.type == "boolean":
            # Handle both boolean and string representations
            if isinstance(value, bool):
                self.valeur = "1" if value else "0"
            elif isinstance(value, str):
                self.valeur = "1" if value in ("1", "True", "true") else "0"
            else:
                self.valeur = "1" if value else "0"
        elif self.type == "int":
            self.valeur = str(int(value))
        elif self.type == "float":
            self.valeur = f"{float(value):.2f}"
        elif self.type == "json":
            self.valeur = json.dumps(value)
        else:
            self.valeur = str(value)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for database operations."""
        return {
            "categorie_id": self.categorie_id,
            "cle": self.cle,
            "valeur": self.valeur,
            "type": self.type,
            "description": self.description,
            "display_order": self.display_order,
            "is_visible": 1 if self.is_visible else 0,
            "is_sensitive": 1 if self.is_sensitive else 0,
        }
