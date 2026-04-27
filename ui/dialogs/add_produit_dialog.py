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
        category_rules: dict[int, dict] | None = None,
        produit: dict | None = None,
    ):
        """
        Args:
            parent: Parent widget
            categories: List of (id, name) tuples for category dropdown
            category_rules: Dict mapping category_id to rule flags
            produit: Existing product data for edit mode
        """
        super().__init__(parent)
        self.categories = categories or []
        self.category_rules = category_rules or {}
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

        # Pre-select category if in edit mode
        if self.produit and self.produit.get("categorie_id"):
            cat_id = self.produit["categorie_id"]
            for i in range(self.input_categorie.count()):
                if self.input_categorie.itemData(i) == cat_id:
                    self.input_categorie.setCurrentIndex(i)
                    break
        elif self.categories:
            self.input_categorie.setCurrentIndex(0)

        # Connect category change to update UI based on rules
        self.input_categorie.currentIndexChanged.connect(self._on_category_changed)
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
        self.input_pa.valueChanged.connect(self._on_pa_changed)
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
        self.input_pv.valueChanged.connect(self._on_pv_changed)
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
        self.input_dlv_dlc.setDisplayFormat("dd/MM/yy")
        self.input_dlv_dlc.setDate(QDate.currentDate())
        self.input_dlv_dlc.setMinimumHeight(INPUT_MIN_HEIGHT)
        if produit and produit.get("dlv_dlc"):
            date_str = produit.get("dlv_dlc", "")
            if date_str:
                # Parse from dd/mm/yy format
                parts = date_str.split("/")
                if len(parts) == 3:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                    # Handle 2-digit year (assume 2000s for years < 50, 1900s otherwise)
                    if year < 50:
                        year += 2000
                    else:
                        year += 1900
                    self.input_dlv_dlc.setDate(QDate(year, month, day))
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

        # Apply initial category-based UI rules
        self._on_category_changed()

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

    def _get_current_category_id(self) -> int | None:
        """Get the currently selected category ID."""
        index = self.input_categorie.currentIndex()
        if index >= 0:
            return self.input_categorie.itemData(index)
        return None

    def _get_category_rules(self) -> dict:
        """Get rules for the currently selected category."""
        cat_id = self._get_current_category_id()
        if cat_id is not None:
            return self.category_rules.get(cat_id, {})
        return {}

    def _on_category_changed(self) -> None:
        """Handle category selection change to apply category-specific rules."""
        rules = self._get_category_rules()

        # Handle PA = PV rule: sync values
        if rules.get("pa_equals_pv"):
            # Set PA to equal PV (or vice versa) to maintain equality
            pv_value = self.input_pv.value()
            self.input_pa.blockSignals(True)
            self.input_pa.setValue(pv_value)
            self.input_pa.blockSignals(False)
            # Also update PRC display which depends on PA
            self._update_prc_display()

        # Update PRC display based on prc_disabled rule
        self._update_prc_display()

        # Handle DLV/DLC field: disable if not required for this category
        if rules.get("dlv_disabled"):
            self.input_dlv_dlc.setEnabled(False)
        else:
            self.input_dlv_dlc.setEnabled(True)

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

    def _on_pa_changed(self, value: int) -> None:
        """Handle PA value change to sync with PV if category requires."""
        rules = self._get_category_rules()
        if rules.get("pa_equals_pv"):
            # Sync PV to match PA
            self.input_pv.blockSignals(True)
            self.input_pv.setValue(value)
            self.input_pv.blockSignals(False)
        self._update_prc_display()

    def _on_pv_changed(self, value: int) -> None:
        """Handle PV value change to sync with PA if category requires."""
        rules = self._get_category_rules()
        if rules.get("pa_equals_pv"):
            # Sync PA to match PV
            self.input_pa.blockSignals(True)
            self.input_pa.setValue(value)
            self.input_pa.blockSignals(False)

    def _update_prc_display(self) -> None:
        """Update the PRC display label based on current PA value and category rules."""
        pa = self.input_pa.value()
        rules = self._get_category_rules()

        if rules.get("prc_disabled"):
            display_text = "-"
        else:
            from core.utils import calculate_prc

            prc = calculate_prc(pa, prc_disabled=False)
            from core.formatters import format_grouped_int

            display_text = f"{format_grouped_int(prc)} Ar" if prc is not None else "-"

        self.lbl_prc.setText(display_text)

    def get_produit(self) -> dict:
        """Return the product data as a dictionary."""
        categorie_index = self.input_categorie.currentIndex()
        categorie_id = (
            self.input_categorie.itemData(categorie_index) if categorie_index >= 0 else None
        )

        # Get category rules for PA=PV enforcement
        rules = self.category_rules.get(categorie_id, {}) if categorie_id else {}

        pa = self.input_pa.value()
        pv = self.input_pv.value()

        # Enforce PA = PV if category rule applies
        if rules.get("pa_equals_pv"):
            pa = pv  # Force PA to equal PV

        result = {
            "nom": self.input_nom.text().strip(),
            "categorie": self.input_categorie.currentText().strip(),
            "categorie_id": categorie_id,
            "pa": pa,
            "prc": int(round(pa * 1.2)) if not rules.get("prc_disabled") else None,
            "pv": pv,
            "dlv_dlc": "" if rules.get("dlv_disabled") else self.input_dlv_dlc.date().toString("dd/MM/yy"),
            "description": self.input_description.toPlainText().strip(),
            "sku": self.input_sku.text().strip(),
            "en_promo": 1 if self._en_promo else 0,
            "prix_promo": self.input_prix_promo.value(),
        }

        # Include ID when editing
        if self.produit and self.produit.get("id"):
            result["id"] = self.produit["id"]

        return result
