from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
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


class AddProduitDialog(QDialog):
    """Dialog for adding a new product with all required information."""

    def __init__(
        self,
        parent: QWidget | None = None,
        categories: list[tuple[int, str]] | None = None,
        produit: dict | None = None,
    ):
        """
        Args:
            parent: Parent widget
            categories: List of (id, name) tuples for category dropdown
            produit: Existing product data for edit mode (currently not used for edit)
        """
        super().__init__(parent)
        self.categories = categories or []
        self.produit = produit
        self.is_edit_mode = produit is not None

        if self.is_edit_mode:
            self.setWindowTitle("Modifier le produit")
        else:
            self.setWindowTitle("Nouveau produit")
        self.resize(540, 700)
        self.setModal(True)

        self.setStyleSheet(DIALOG_BASE)

        # Error labels storage
        self.error_labels = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header
        header = QLabel(
            "Informations du produit" if not self.is_edit_mode else "Modifier le produit"
        )
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Product name (required, unique)
        self.input_nom = QLineEdit()
        self.input_nom.setPlaceholderText("Nom du produit")
        self.input_nom.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit:
            self.input_nom.setText(produit.get("nom", ""))
        form.addRow("Nom *", self.input_nom)

        # Category dropdown
        self.input_categorie = QComboBox()
        self.input_categorie.setEditable(True)
        self.input_categorie.setMinimumHeight(INPUT_MIN_HEIGHT)
        for cat_id, cat_name in self.categories:
            self.input_categorie.addItem(cat_name, cat_id)
        if self.categories:
            self.input_categorie.setCurrentIndex(0)
        form.addRow("Catégorie *", self.input_categorie)

        # SKU field
        self.input_sku = QLineEdit()
        self.input_sku.setPlaceholderText("Code SKU (optionnel)")
        self.input_sku.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit:
            self.input_sku.setText(produit.get("sku", ""))
        form.addRow("SKU", self.input_sku)

        # Prix d'achat (PA - Purchase Price)
        self.input_pa = QSpinBox()
        self.input_pa.setRange(0, 999999999)
        self.input_pa.setValue(0)
        self.input_pa.setSuffix(" Ar")
        self.input_pa.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit:
            self.input_pa.setValue(produit.get("pa", 0))
        self.input_pa.valueChanged.connect(self._update_prc_display)
        form.addRow("Prix Achat (PA)", self.input_pa)

        # PRC (Prix de Revient Calculé) - read-only, auto-calculated
        self.lbl_prc = QLabel()
        self.lbl_prc.setMinimumHeight(INPUT_MIN_HEIGHT)
        self.lbl_prc.setStyleSheet(
            "QLabel {"
            "  background-color: #1f2937; color: #a855f7;"
            "  border: 1px solid #374151; border-radius: 6px;"
            "  padding: 4px 8px; font-weight: bold;"
            "}"
        )
        self._update_prc_display()
        form.addRow("PRC (PA×1.2)", self.lbl_prc)

        # Prix de vente (PV - Selling Price)
        self.input_pv = QSpinBox()
        self.input_pv.setRange(0, 999999999)
        self.input_pv.setValue(0)
        self.input_pv.setSuffix(" Ar")
        self.input_pv.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit:
            self.input_pv.setValue(produit.get("pv", 0))
        form.addRow("Prix Vente (PV)", self.input_pv)

        # Prix de promotion (defaults to PA)
        self.input_prix_promo = QSpinBox()
        self.input_prix_promo.setRange(0, 999999999)
        self.input_prix_promo.setValue(0)
        self.input_prix_promo.setSuffix(" Ar")
        self.input_prix_promo.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit:
            self.input_prix_promo.setValue(produit.get("prix_promo", produit.get("pa", 0)))
        form.addRow("Prix Promo", self.input_prix_promo)

        # En promo toggle button
        self._en_promo = bool(produit.get("en_promo", 0)) if produit else False
        self.btn_en_promo = QPushButton()
        self.btn_en_promo.setMinimumHeight(INPUT_MIN_HEIGHT)
        self.btn_en_promo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_en_promo.clicked.connect(self._toggle_promo)
        self._update_promo_button()
        form.addRow("Promotion", self.btn_en_promo)

        # Date limite de vente/conso (DLV/DLC)
        self.input_dlv_dlc = QDateEdit()
        self.input_dlv_dlc.setCalendarPopup(True)
        self.input_dlv_dlc.setDisplayFormat("yyyy-MM-dd")
        self.input_dlv_dlc.setDate(QDate.currentDate())
        self.input_dlv_dlc.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit and produit.get("dlv_dlc"):
            date_str = produit.get("dlv_dlc", "")
            if date_str:
                parts = date_str.split("-")
                if len(parts) == 3:
                    self.input_dlv_dlc.setDate(QDate(int(parts[0]), int(parts[1]), int(parts[2])))
        form.addRow("Date Limite (DLV/DLC)", self.input_dlv_dlc)

        # Description field
        self.input_description = QTextEdit()
        self.input_description.setPlaceholderText("Description du produit (optionnel)")
        self.input_description.setMinimumHeight(80)
        self.input_description.setMaximumHeight(120)
        if produit:
            self.input_description.setText(produit.get("description", ""))
        form.addRow("Description", self.input_description)

        root.addLayout(form)

        # Error message area
        self.error_label = QLabel()
        self.error_label.setStyleSheet(ERROR_LABEL)
        self.error_label.setVisible(False)
        self.error_label.setWordWrap(True)
        root.addWidget(self.error_label)

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
            ok_btn.setText("Enregistrer")
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

    def _clear_error_styles(self):
        """Clear error styling from all input fields."""
        self.input_nom.setStyleSheet("")
        self.input_categorie.setStyleSheet("")
        self.error_label.setVisible(False)

    def _set_field_error(self, field, error_message: str):
        """Set error styling on a specific field."""
        field.setStyleSheet("border: 2px solid #ef4444; border-radius: 8px;")
        self.error_label.setText(error_message)
        self.error_label.setVisible(True)

    def validate(self) -> bool:
        """
        Validate the form fields.
        Returns True if valid, False otherwise.
        """
        self._clear_error_styles()

        # Validate required fields
        nom = self.input_nom.text().strip()
        if not nom:
            self._set_field_error(self.input_nom, "Le nom du produit est obligatoire")
            self.input_nom.setFocus()
            return False

        # Validate category is selected
        categorie_index = self.input_categorie.currentIndex()
        if categorie_index < 0:
            self._set_field_error(self.input_categorie, "Veuillez sélectionner une catégorie")
            self.input_categorie.setFocus()
            return False

        return True

    def _on_accept(self):
        """Validate and accept the dialog."""
        if self.validate():
            self.accept()

    def _toggle_promo(self) -> None:
        """Toggle the en_promo flag and update button appearance."""
        self._en_promo = not self._en_promo
        self._update_promo_button()

    def _update_promo_button(self) -> None:
        """Update the En promo toggle button style and text."""
        if self._en_promo:
            self.btn_en_promo.setText("En promo \u2713")
            self.btn_en_promo.setStyleSheet(
                "QPushButton {"
                "  background-color: #16a34a; color: white;"
                "  border: 1px solid #15803d; border-radius: 6px;"
                "  font-weight: bold; font-size: 13px;"
                "}"
                "QPushButton:hover { background-color: #15803d; }"
            )
        else:
            self.btn_en_promo.setText("Hors promo")
            self.btn_en_promo.setStyleSheet(
                "QPushButton {"
                "  background-color: #374151; color: #9ca3af;"
                "  border: 1px solid #4b5563; border-radius: 6px;"
                "  font-weight: bold; font-size: 13px;"
                "}"
                "QPushButton:hover { background-color: #4b5563; }"
            )

    def _update_prc_display(self) -> None:
        """Update the PRC display label based on current PA value."""
        pa = self.input_pa.value()
        prc = int(round(pa * 1.2))
        from core.formatters import format_grouped_int

        self.lbl_prc.setText(f"{format_grouped_int(prc)} Ar")

    def get_produit(self) -> dict:
        """Return the product data as a dictionary."""
        categorie_index = self.input_categorie.currentIndex()
        categorie_id = (
            self.input_categorie.itemData(categorie_index) if categorie_index >= 0 else None
        )

        result = {
            "nom": self.input_nom.text().strip(),
            "categorie": self.input_categorie.currentText().strip(),
            "categorie_id": categorie_id,
            "pa": self.input_pa.value(),
            "prc": int(round(self.input_pa.value() * 1.2)),
            "pv": self.input_pv.value(),
            "dlv_dlc": self.input_dlv_dlc.date().toString("yyyy-MM-dd"),
            "description": self.input_description.toPlainText().strip(),
            "sku": self.input_sku.text().strip(),
            "en_promo": 1 if self._en_promo else 0,
            "prix_promo": self.input_prix_promo.value(),
        }

        # Include ID when editing
        if self.produit and self.produit.get("id"):
            result["id"] = self.produit["id"]

        return result
