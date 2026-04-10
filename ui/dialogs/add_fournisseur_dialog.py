from typing import Any

from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from styles.dialog_styles import (
    DIALOG_BASE,
    ERROR_LABEL,
    HEADER_LABEL,
    INPUT_MIN_HEIGHT,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SEPARATOR,
)


class AddFournisseurDialog(QDialog):
    """Dialog for adding or editing a supplier (fournisseur) with all relevant information."""

    def __init__(
        self,
        parent: QWidget | None = None,
        default_code: str = "F-001",
        supplier: dict | None = None,
        db_manager: Any | None = None,
    ):
        super().__init__(parent)
        self.default_code = default_code
        self.supplier = supplier
        self.db_manager = db_manager
        self.is_edit_mode = supplier is not None

        if self.is_edit_mode:
            self.setWindowTitle("Modifier le fournisseur")
        else:
            self.setWindowTitle("Nouveau fournisseur")
        self.resize(480, 420)

        self.setStyleSheet(DIALOG_BASE)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header
        header = QLabel("Modifier le fournisseur" if self.is_edit_mode else "Nouveau fournisseur")
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)

        # Supplier name (required)
        self.input_nom = QLineEdit()
        self.input_nom.setPlaceholderText("Nom du fournisseur")
        self.input_nom.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_nom.setText(supplier.get("nom", ""))
        form.addRow("Nom *", self.input_nom)

        # Code (auto-generated but editable)
        self.input_code = QLineEdit()
        self.input_code.setPlaceholderText("Code fournisseur")
        self.input_code.setMinimumHeight(INPUT_MIN_HEIGHT)
        self.input_code.setText(
            default_code if not supplier else supplier.get("code", default_code)
        )
        form.addRow("Code", self.input_code)

        # NIF
        self.input_nif = QLineEdit()
        self.input_nif.setPlaceholderText("NIF")
        self.input_nif.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_nif.setText(supplier.get("nif", ""))
        form.addRow("NIF", self.input_nif)

        # STAT
        self.input_stat = QLineEdit()
        self.input_stat.setPlaceholderText("STAT")
        self.input_stat.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_stat.setText(supplier.get("stat", ""))
        form.addRow("STAT", self.input_stat)

        # Contact
        self.input_contact = QLineEdit()
        self.input_contact.setPlaceholderText("Personne de contact")
        self.input_contact.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_contact.setText(supplier.get("contact", ""))
        form.addRow("Contact", self.input_contact)

        # Telephone
        self.input_telephone = QLineEdit()
        self.input_telephone.setPlaceholderText("Numéro de téléphone")
        self.input_telephone.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_telephone.setText(supplier.get("telephone", ""))
        form.addRow("Téléphone", self.input_telephone)

        # Address
        self.input_adresse = QLineEdit()
        self.input_adresse.setPlaceholderText("Adresse")
        self.input_adresse.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_adresse.setText(supplier.get("adresse", ""))
        form.addRow("Adresse", self.input_adresse)

        # Note
        self.input_note = QLineEdit()
        self.input_note.setPlaceholderText("Notes supplémentaires")
        self.input_note.setMinimumHeight(INPUT_MIN_HEIGHT)
        if supplier:
            self.input_note.setText(supplier.get("note", ""))
        form.addRow("Note", self.input_note)

        # Error message area
        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_LABEL)
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

        root.addLayout(form)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(SEPARATOR)
        separator.setFixedHeight(1)
        root.addWidget(separator)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn is not None:
            ok_btn.setText("Modifier" if self.is_edit_mode else "Ajouter")
            ok_btn.setStyleSheet(PRIMARY_BUTTON)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_btn is not None:
            cancel_btn.setText("Annuler")
            cancel_btn.setStyleSheet(SECONDARY_BUTTON)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        # Focus on name field
        self.input_nom.setFocus()

    def _on_accept(self):
        """Validate and accept the dialog."""
        nom = self.input_nom.text().strip()
        if not nom:
            self.input_nom.setStyleSheet("border: 2px solid #ef4444; border-radius: 8px;")
            self.error_label.setText("Le nom du fournisseur est obligatoire")
            self.error_label.setVisible(True)
            self.input_nom.setFocus()
            return

        code = self.input_code.text().strip() or self.default_code
        if self.db_manager is not None:
            existing = self.db_manager.achats.get_supplier_by_code(code)
            if existing and (
                not self.is_edit_mode
                or self.supplier is None
                or existing["id"] != self.supplier["id"]
            ):
                self.input_code.setStyleSheet("border: 2px solid #ef4444; border-radius: 8px;")
                self.error_label.setText("Le code fournisseur existe déjà")
                self.error_label.setVisible(True)
                self.input_code.setFocus()
                return

        self.accept()

    def get_fournisseur(self) -> dict:
        """Return the supplier data as a dictionary."""
        result = {
            "nom": self.input_nom.text().strip(),
            "code": self.input_code.text().strip() or self.default_code,
            "nif": self.input_nif.text().strip(),
            "stat": self.input_stat.text().strip(),
            "contact": self.input_contact.text().strip(),
            "telephone": self.input_telephone.text().strip(),
            "adresse": self.input_adresse.text().strip(),
            "note": self.input_note.text().strip(),
        }
        # Include ID when editing
        if self.supplier and self.supplier.get("id"):
            result["id"] = self.supplier["id"]
        return result
