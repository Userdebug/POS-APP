"""Dialog for confirming transfer of billetage to coffre (safe)."""

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

from core.formatters import format_grouped_int
from styles.design_tokens import TOKENS
from styles.dialog_styles import (
    DIALOG_BASE,
    INFO_CARD,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    WARNING_LABEL,
)

__all__ = ["CoffreConfirmationDialog"]


class CoffreConfirmationDialog(QDialog):
    """Confirmation dialog for transferring billetage total to the safe.

    Displays the amount to transfer, current safe balance, and new total.
    Requires explicit user confirmation before the transfer executes.
    """

    def __init__(
        self,
        parent: QWidget | None,
        total_billetage: int,
        current_coffre: int,
    ) -> None:
        """Initialize the coffre confirmation dialog.

        Args:
            parent: Parent widget.
            total_billetage: Amount to transfer to safe.
            current_coffre: Current safe balance.
        """
        super().__init__(parent)
        self.setWindowTitle("Confirmer transfert coffre")
        self.setMinimumWidth(380)
        self.setModal(True)

        self.setStyleSheet(DIALOG_BASE)

        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(24, 24, 24, 24)

        # Warning header
        warning = QLabel("Confirmer le transfert au coffre")
        warning.setStyleSheet(WARNING_LABEL)
        warning.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(warning)

        # Info card with transfer details
        nouveau_total = current_coffre + total_billetage
        info_text = (
            f"Montant à transférer: {format_grouped_int(total_billetage)} Ar\n"
            f"Solde actuel du coffre: {format_grouped_int(current_coffre)} Ar\n"
            f"Nouveau solde: {format_grouped_int(nouveau_total)} Ar"
        )
        info = QLabel(info_text)
        info.setStyleSheet(f"{INFO_CARD} color: {TOKENS['text_default']}; font-size: 14px;")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(info)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        btn_confirm = QPushButton("Confirmer")
        btn_confirm.setStyleSheet(PRIMARY_BUTTON)
        btn_confirm.clicked.connect(self.accept)
        btn_layout.addWidget(btn_confirm)

        btn_cancel = QPushButton("Annuler")
        btn_cancel.setStyleSheet(SECONDARY_BUTTON)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        root.addLayout(btn_layout)
