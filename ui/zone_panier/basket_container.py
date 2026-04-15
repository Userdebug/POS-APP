"""BasketContainer — QStackedWidget parent holding ZoneVente and ZoneAchat.

Routes API calls to whichever zone is currently visible and forwards
child signals to the parent (main_window.py).
"""

from __future__ import annotations

import logging
from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from .zone_achat import ZoneAchat
from .zone_vente import ZoneVente

logger = logging.getLogger(__name__)


class BasketContainer(QWidget):
    """Container that holds both basket zones and routes calls to the active one.

    Signals:
        mode_change: Emitted when the mode switches ("vente" or "achat").
        transaction_finalisee: Forwarded from child zones (mode, total).
        validation_state_changed: Forwarded from child zones.
        nouveau_produit_enregistre: Forwarded from child zones.
        sales_day_recorded: Forwarded from ZoneVente only.
    """

    mode_change = pyqtSignal(str)
    transaction_finalisee = pyqtSignal(str, int)
    validation_state_changed = pyqtSignal(bool)
    nouveau_produit_enregistre = pyqtSignal(dict)
    sales_day_recorded = pyqtSignal(object)
    validation_completed = pyqtSignal()

    VENTE_INDEX = 0
    ACHAT_INDEX = 1

    def __init__(
        self,
        basket_manager_factory: Any = None,
        db_manager: Any | None = None,
        current_day_provider: Any | None = None,
        tracking_service: Any | None = None,
    ) -> None:
        """Initialize the container.

        Args:
            basket_manager_factory: Ignored (kept for backward compatibility).
            db_manager: Database manager instance.
            current_day_provider: Callable returning the current business day.
            tracking_service: Daily tracking service instance.
        """
        super().__init__()

        self.zone_vente = ZoneVente(db_manager, tracking_service, current_day_provider)
        self.zone_achat = ZoneAchat(db_manager, tracking_service, current_day_provider)

        self._stack = QStackedWidget()
        self._stack.addWidget(self.zone_vente)
        self._stack.addWidget(self.zone_achat)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)

        # Forward signals from both zones
        for zone in (self.zone_vente, self.zone_achat):
            zone.transaction_finalisee.connect(self.transaction_finalisee.emit)
            zone.validation_state_changed.connect(self.validation_state_changed.emit)
            zone.nouveau_produit_enregistre.connect(self.nouveau_produit_enregistre.emit)
            zone.mode_switch_request.connect(self._toggle_mode)
            zone.validation_completed.connect(self.validation_completed.emit)

        self.zone_vente.sales_day_recorded.connect(self.sales_day_recorded.emit)

    # ==================== Mode Routing ====================

    @property
    def mode(self) -> str:
        """Return the current mode string."""
        return "vente" if self._stack.currentIndex() == self.VENTE_INDEX else "achat"

    @property
    def active_zone(self) -> ZoneVente | ZoneAchat:
        """Return the currently visible zone widget."""
        return self._stack.currentWidget()  # type: ignore[return-value]

    def set_mode(self, mode: str) -> None:
        """Switch to the specified mode and emit mode_change."""
        normalized = mode.lower().strip()
        if normalized in ("achat", "achats", "reception"):
            idx = self.ACHAT_INDEX
        else:
            idx = self.VENTE_INDEX
        self._stack.setCurrentIndex(idx)
        self.mode_change.emit(self.mode)

    def _toggle_mode(self) -> None:
        """Toggle between vente and achat."""
        if self._stack.currentIndex() == self.VENTE_INDEX:
            self.set_mode("achat")
        else:
            self.set_mode("vente")

    # ==================== Delegated API ====================

    def add_product(self, produit: dict[str, Any]) -> None:
        """Route product addition to the active zone."""
        self.active_zone.add_product(produit)

    def validate_current_line(self) -> dict | None:
        """Route validation to the active zone."""
        return self.active_zone.validate_current_line()

    def appliquer_quantite(self, quantite: int) -> None:
        """Route quantity application to the active zone."""
        self.active_zone.appliquer_quantite(quantite)

    def current_validation_enabled(self) -> bool:
        """Return whether the Valider button should be enabled."""
        return self.active_zone.current_validation_enabled()

    def switch_basket(self, nom: str) -> None:
        """Switch P1/P2/N/P — only valid in vente mode."""
        if isinstance(self.active_zone, ZoneVente):
            self.active_zone.switch_basket(nom)

    def clear_basket(self) -> None:
        """Clear the active zone's basket."""
        self.active_zone.clear_basket()

    def refresh(self) -> None:
        """Refresh the active zone's display."""
        self.active_zone.refresh()
