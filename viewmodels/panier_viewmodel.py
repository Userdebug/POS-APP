"""Gestionnaire simple des paniers actifs."""

from __future__ import annotations

from typing import Any


class BasketManager:
    """Stocke les lignes de panier et l'etat courant (panier actif + mode)."""

    _PANIER_IDS = ("P1", "P2", "N/P")

    def __init__(self) -> None:
        self.baskets: dict[str, list[dict[str, Any]]] = {key: [] for key in self._PANIER_IDS}
        self.active: str = "P1"
        self.mode: str = "vente"  # ou "achat"

    # Alias for backward compatibility
    @property
    def paniers(self) -> dict[str, list[dict[str, Any]]]:
        """Alias for baskets - returns all baskets."""
        return self.baskets

    # Alias for backward compatibility
    @property
    def actif(self) -> str:
        return self.active

    @actif.setter
    def actif(self, value: str) -> None:
        self.active = value

    def get_actif(self) -> list[dict[str, Any]]:
        """Alias for get_active - returns active basket items."""
        return self.get_active()

    def switch_basket(self, nom: str) -> None:
        """Switch to a different basket by name.

        Args:
            nom: The basket name (e.g., 'P1', 'P2', 'N/P')

        Raises:
            ValueError: If the basket name is not valid.
        """
        if nom not in self._PANIER_IDS:
            raise ValueError(f"Invalid basket name: {nom}. Must be one of {self._PANIER_IDS}")
        self.active = str(nom)

    def set_mode(self, mode: str) -> None:
        # Normalize mode to internal standard (vente/achat)
        if mode == "caisse":
            mode = "vente"
        elif mode == "reception":
            mode = "achat"
        self.mode = str(mode)

    def add(self, product: dict[str, Any]) -> None:
        self.baskets[self.active].append(product)

    def clear_active(self) -> None:
        self.baskets[self.active] = []

    def get_active(self) -> list[dict[str, Any]]:
        return self.baskets[self.active]

    def update_item(self, item: dict[str, Any]) -> None:
        """Update an item in the active basket (by matching 'id' or index)."""
        items = self.baskets[self.active]
        # Try to find by id first
        item_id = item.get("id")
        if item_id is not None:
            for i, existing in enumerate(items):
                if existing.get("id") == item_id:
                    items[i] = item
                    return
        # If no id match, do nothing (or could update by index if needed)


class BasketManagerFactory:
    """Factory for creating and managing mode-specific BasketManager instances.

    Each mode (VENTE, ACHAT) gets its own independent BasketManager,
    ensuring complete data isolation between modes.
    """

    # Mode constants - standard internal names
    MODE_VENTE = "vente"
    MODE_ACHAT = "achat"

    # Backward compatibility mapping
    _LEGACY_MODE_MAP = {
        "caisse": MODE_VENTE,
        "reception": MODE_ACHAT,
    }

    def __init__(self):
        self._managers: dict[str, BasketManager] = {}
        self._current_mode: str = self.MODE_VENTE

    def get_manager(self, mode: str | None = None) -> BasketManager:
        """Get or create a BasketManager for the specified mode.

        Args:
            mode: The mode name (vente, achat). If None, returns current mode's manager.

        Returns:
            BasketManager instance for the mode
        """
        # Resolve legacy mode names
        if mode:
            mode = self._LEGACY_MODE_MAP.get(mode, mode)
        else:
            mode = self._current_mode

        if mode not in self._managers:
            self._managers[mode] = BasketManager()
            # Set the mode on the new manager
            self._managers[mode].set_mode(mode)

        return self._managers[mode]

    def set_current_mode(self, mode: str) -> None:
        """Set the current active mode.

        Args:
            mode: The mode to activate (vente, achat)
        """
        resolved = self._LEGACY_MODE_MAP.get(mode, mode)
        self._current_mode = resolved
        # Ensure manager exists for this mode
        self.get_manager(resolved)

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def current_manager(self) -> BasketManager:
        """Get the BasketManager for the current mode."""
        return self.get_manager(self._current_mode)
