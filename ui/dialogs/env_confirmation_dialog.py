"""Dialog for ENV removal confirmation with location selection."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from styles.design_tokens import TOKENS


class EnvConfirmationDialog(QDialog):
    """Dialog to confirm ENV removal and select location (Boutique or Reserve)."""

    def __init__(
        self,
        parent: QWidget | None,
        produit_nom: str,
        quantite: int,
        stock_b: int,
        stock_r: int,
        env_type: str,
    ) -> None:
        """Initialize the ENV confirmation dialog.

        Args:
            parent: Parent widget.
            produit_nom: Product name.
            quantite: Quantity to remove.
            stock_b: Current boutique stock.
            stock_r: Current reserve stock.
            env_type: Either "DLV" (perime) or "Abime" (damaged).
        """
        super().__init__(parent)
        self._location: str | None = None

        type_label = "DLV (Périmé)" if env_type == "DLV" else "Abimé"
        self.setWindowTitle(f"Confirmer retrait - {type_label}")
        self.setMinimumWidth(420)
        self.setModal(True)

        self.setStyleSheet(f"QDialog {{ background-color: {TOKENS['bg_sidebar']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 24, 24, 24)

        # Header warning
        warning = QLabel(f"Confirmer retrait {type_label}")
        warning.setStyleSheet(
            f"color: {TOKENS['danger']}; font-weight: 700; font-size: 18px;"
            f"padding: 14px; background-color: rgba(239, 68, 68, 0.1);"
            f"border-radius: 10px;"
        )
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(warning)

        # Info card
        info = QLabel(f"Produit: {produit_nom}\nQuantité: {quantite}")
        info.setStyleSheet(
            f"padding: 14px; background-color: {TOKENS['bg_card']};"
            f"border: 1px solid {TOKENS['border_primary']};"
            f"border-radius: 10px; font-size: 14px; color: {TOKENS['text_default']};"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(info)

        # Stock info
        stock_info = QLabel(f"Stock Boutique: {stock_b} | Stock Réserve: {stock_r}")
        stock_info.setStyleSheet(
            f"color: {TOKENS['text_muted']}; font-weight: 600; font-size: 13px;" f"padding: 6px;"
        )
        stock_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(stock_info)

        prompt = QLabel("Sélectionner l'emplacement du retrait:")
        prompt.setStyleSheet(f"color: {TOKENS['text_default']}; font-weight: 600; font-size: 13px;")
        root.addWidget(prompt)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._btn_b = QPushButton(f"Boutique ({stock_b})")
        self._btn_b.setMinimumHeight(48)
        self._btn_b.setEnabled(stock_b > 0)
        self._btn_b.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {TOKENS['bg_card']};"
            f"  border: 2px solid #3b82f6;"
            f"  color: #3b82f6;"
            f"  font-weight: 700;"
            f"  font-size: 14px;"
            f"  border-radius: 10px;"
            f"  padding: 10px 16px;"
            f"}}"
            f"QPushButton:hover {{ background-color: #3b82f6; color: #0f172a; }}"
            f"QPushButton:disabled {{"
            f"  border-color: {TOKENS['button_disabled_border']};"
            f"  color: {TOKENS['text_muted']};"
            f"}}"
        )
        self._btn_b.clicked.connect(lambda: self._select_location("B"))
        btn_layout.addWidget(self._btn_b)

        self._btn_r = QPushButton(f"Réserve ({stock_r})")
        self._btn_r.setMinimumHeight(48)
        self._btn_r.setEnabled(stock_r > 0)
        self._btn_r.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {TOKENS['bg_card']};"
            f"  border: 2px solid #f59e0b;"
            f"  color: #f59e0b;"
            f"  font-weight: 700;"
            f"  font-size: 14px;"
            f"  border-radius: 10px;"
            f"  padding: 10px 16px;"
            f"}}"
            f"QPushButton:hover {{ background-color: #f59e0b; color: #0f172a; }}"
            f"QPushButton:disabled {{"
            f"  border-color: {TOKENS['button_disabled_border']};"
            f"  color: {TOKENS['text_muted']};"
            f"}}"
        )
        self._btn_r.clicked.connect(lambda: self._select_location("R"))
        btn_layout.addWidget(self._btn_r)

        root.addLayout(btn_layout)

        self._btn_cancel = QPushButton("Annuler")
        self._btn_cancel.setMinimumHeight(42)
        self._btn_cancel.setStyleSheet(
            f"QPushButton {{"
            f"  background-color: {TOKENS['bg_button']};"
            f"  color: {TOKENS['text_default']};"
            f"  border: 1px solid {TOKENS['border_button']};"
            f"  border-radius: 8px;"
            f"  font-weight: 600;"
            f"  font-size: 13px;"
            f"  padding: 10px 16px;"
            f"}}"
            f"QPushButton:hover {{ background-color: {TOKENS['bg_button_hover']}; }}"
        )
        self._btn_cancel.clicked.connect(self.reject)
        root.addWidget(self._btn_cancel)

    def _select_location(self, location: str) -> None:
        """Handle location selection.

        Args:
            location: Selected location code ("B" or "R").
        """
        self._location = location
        self.accept()

    def location(self) -> str | None:
        """Return selected location ('B' or 'R') or None if cancelled.

        Returns:
            Selected location code or None.
        """
        return self._location
