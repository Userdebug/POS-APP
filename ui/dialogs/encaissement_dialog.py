"""Dialog for handling cash payment and change calculation during encaissement."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_grouped_int, parse_grouped_int
from styles.dialog_styles import (
    CHANGE_NEGATIVE,
    CHANGE_POSITIVE,
    DIALOG_BASE,
    ERROR_LABEL,
    HEADER_LABEL,
    MONEY_INPUT,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SEPARATOR,
)


class EncaissementDialog(QDialog):
    """Dialog for handling cash payment and change calculation."""

    def __init__(self, parent: QWidget | None, total: int, panier_name: str = "actif") -> None:
        """Initialize the encaissement dialog.

        Args:
            parent: Parent widget.
            total: Total amount to pay in Ariary.
            panier_name: Name of the active basket (default: "actif").
        """
        super().__init__(parent)
        self.setWindowTitle(f"Encaissement - Panier {panier_name}")
        self.resize(420, 300)
        self._total = total

        self.setStyleSheet(DIALOG_BASE)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel(f"Paiement - Panier {panier_name}")
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        # Total display
        total_container = QHBoxLayout()
        lbl_title = QLabel("Total à payer")
        lbl_title.setStyleSheet(f"color: {self._token('text_muted')}; font-size: 13px;")
        total_container.addWidget(lbl_title)
        total_container.addStretch()
        self.lbl_total = QLabel(f"{format_grouped_int(total)} Ar")
        self.lbl_total.setStyleSheet(TOTAL_DISPLAY_STYLE)
        total_container.addWidget(self.lbl_total)
        root.addLayout(total_container)

        # Money given input
        lbl_given = QLabel("Montant donné")
        muted = self._token("text_muted")
        lbl_given.setStyleSheet(f"color: {muted}; font-size: 13px; margin-top: 8px;")
        root.addWidget(lbl_given)
        input_layout = QHBoxLayout()
        self.montant_input = QLineEdit()
        self.montant_input.setPlaceholderText("Entrez le montant...")
        self.montant_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.montant_input.setStyleSheet(MONEY_INPUT)
        self.montant_input.textChanged.connect(self._on_given_amount_changed)
        input_layout.addWidget(self.montant_input, 1)
        lbl_currency = QLabel("Ar")
        lbl_currency.setStyleSheet(
            f"font-size: 18px; font-weight: 600;" f" color: {muted}; margin-left: 8px;"
        )
        input_layout.addWidget(lbl_currency)
        root.addLayout(input_layout)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(SEPARATOR)
        separator.setFixedHeight(1)
        root.addWidget(separator)

        # Change display
        self.lbl_rendu = QLabel("Rendu: 0 Ar")
        self.lbl_rendu.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.lbl_rendu.setStyleSheet(CHANGE_POSITIVE)
        root.addWidget(self.lbl_rendu)

        # Error message
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet(ERROR_LABEL)
        self.lbl_error.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(self.lbl_error)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if self._ok_button is not None:
            self._ok_button.setText("Confirmer")
            self._ok_button.setStyleSheet(PRIMARY_BUTTON)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Annuler")
            cancel_btn.setStyleSheet(SECONDARY_BUTTON)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    @staticmethod
    def _token(key: str) -> str:
        """Get a design token value."""
        from styles.design_tokens import TOKENS

        return TOKENS.get(key, "")

    def _on_given_amount_changed(self, text: str) -> None:
        """Handle changes to the given amount input."""
        given_amount = parse_grouped_int(text, default=0)
        remaining = given_amount - self._total

        if given_amount < self._total:
            self.lbl_rendu.setText(f"Rendu: {format_grouped_int(remaining)} Ar (insuffisant)")
            self.lbl_rendu.setStyleSheet(CHANGE_NEGATIVE)
            self.lbl_error.setText(
                f"Montant insuffisant de {format_grouped_int(self._total - given_amount)} Ar"
            )
        else:
            self.lbl_rendu.setText(f"Rendu: {format_grouped_int(remaining)} Ar")
            self.lbl_rendu.setStyleSheet(CHANGE_POSITIVE)
            self.lbl_error.setText("")

    def given_amount(self) -> int:
        """Get the amount given by the client.

        Returns:
            The amount given as an integer in Ariary.
        """
        return parse_grouped_int(self.montant_input.text(), default=0)

    def change(self) -> int:
        """Get the change to be given back.

        Returns:
            The change amount as an integer in Ariary.
        """
        return max(0, self.given_amount() - self._total)


# Inline style for total display to avoid circular import
TOTAL_DISPLAY_STYLE = (
    "font-size: 24px; font-weight: 700; color: #f5f3ff;"
    "background-color: #7c3aed; border: 2px solid #a78bfa;"
    "border-radius: 10px; padding: 14px 20px;"
)
