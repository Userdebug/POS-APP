"""Dialog for admin-confirmed sale deletion."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from styles.dialog_styles import (
    DANGER_BUTTON,
    DIALOG_BASE,
    ERROR_LABEL,
    INFO_CARD,
    INPUT_MIN_HEIGHT,
    SECONDARY_BUTTON,
    WARNING_LABEL,
)


class AdminConfirmDeleteDialog(QDialog):
    """Confirmation dialog requiring admin PIN to delete a sale."""

    def __init__(self, parent: QWidget | None, sale_info: dict[str, Any], db_manager: Any) -> None:
        """Initialize the admin confirmation dialog.

        Args:
            parent: Parent widget.
            sale_info: Dictionary with sale details (heure, produit, quantite).
            db_manager: DatabaseManager instance for PIN verification.
        """
        super().__init__(parent)
        self.setWindowTitle("Confirmer la suppression")
        self.resize(420, 280)
        self._db_manager = db_manager
        self._sale_info = sale_info

        self.setStyleSheet(DIALOG_BASE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Warning label
        warning = QLabel("ATTENTION : Suppression d'une vente")
        warning.setStyleSheet(WARNING_LABEL)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(warning)

        # Sale details
        details = QLabel(
            f"Produit : {sale_info.get('produit', '')}\n"
            f"Quantité : {sale_info.get('quantite', 0)}\n"
            f"Heure : {sale_info.get('heure', '')}"
        )
        details.setStyleSheet(f"color: {self._token('text_default')}; font-size: 14px; {INFO_CARD}")
        root.addWidget(details)

        # Admin PIN input
        lbl_pin = QLabel("Code admin requis pour confirmer")
        lbl_pin.setStyleSheet(f"color: {self._token('text_muted')}; font-size: 13px;")
        root.addWidget(lbl_pin)
        self._pin_input = QLineEdit()
        self._pin_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._pin_input.setPlaceholderText("Entrez le code admin")
        self._pin_input.setMaxLength(32)
        self._pin_input.setMinimumHeight(INPUT_MIN_HEIGHT)
        self._pin_input.textChanged.connect(self._on_pin_changed)
        root.addWidget(self._pin_input)

        # Error label
        self._error_label = QLabel("")
        self._error_label.setStyleSheet(ERROR_LABEL)
        self._error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self._error_label)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self._ok_button is not None:
            self._ok_button.setText("Supprimer")
            self._ok_button.setStyleSheet(DANGER_BUTTON)
            self._ok_button.setEnabled(False)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Annuler")
            cancel_btn.setStyleSheet(SECONDARY_BUTTON)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _token(key: str) -> str:
        """Get a design token value."""
        from styles.design_tokens import TOKENS

        return TOKENS.get(key, "")

    def _on_pin_changed(self, _text: str) -> None:
        """Enable OK button when PIN is entered."""
        self._error_label.setText("")
        if self._ok_button is not None:
            self._ok_button.setEnabled(bool(self._pin_input.text().strip()))

    def _on_accept(self) -> None:
        """Validate admin PIN before accepting."""
        pin = self._pin_input.text().strip()
        if not pin:
            self._error_label.setText("Code admin requis")
            return

        if not self._db_manager.verify_admin_pin(pin):
            self._error_label.setText("Code admin incorrect")
            self._pin_input.clear()
            return

        self.accept()

    def admin_pin(self) -> str:
        """Get the entered admin PIN."""
        return self._pin_input.text().strip()
