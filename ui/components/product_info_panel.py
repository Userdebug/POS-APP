"""Infos produit (haut gauche)."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QCalendarWidget,
    QDateEdit,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from core.formatters import (
    format_dlv_dlc_date,
    format_grouped_int,
    parse_expiry_dates,
    parse_grouped_int,
)


class ProduitInfoPanel(QGroupBox):
    """Panel affichant/éditant les informations du produit selectionne."""

    produit_modifie = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Détails du Produit")
        self.setObjectName("infoPanel")
        self._produit_actuel: dict | None = None
        self._editing = False
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #2a3142;
                border-radius: 10px;
                margin-top: 12px;
                padding: 10px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #e2e8f0;
            }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)

        top = QHBoxLayout()
        self.btn_edit = QPushButton("Editer")
        self.btn_edit.setMinimumHeight(30)
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._start_edit)
        self.btn_save = QPushButton("Enregistrer")
        self.btn_save.setMinimumHeight(30)
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self._save_edit)
        top.addWidget(self.btn_edit)
        top.addStretch(1)
        top.addWidget(self.btn_save)
        layout.addLayout(top)

        cols = QHBoxLayout()
        cols.setSpacing(12)

        self.lbl_reference = QLabel("-")
        self.lbl_stock = QLabel("-")
        self.lbl_b = QLabel("-")
        self.lbl_r = QLabel("-")
        self.lbl_prc = QLabel("-")

        self.input_nom = QLineEdit()
        self.input_categorie = QLineEdit()
        self.input_dlv = QDateEdit()
        self.input_dlv.setCalendarPopup(True)
        self.input_dlv.setDisplayFormat("dd/MM/yy")
        self.input_pa = QLineEdit()
        self.input_pv = QLineEdit()
        self.input_prix_promo = QLineEdit()
        self.input_qte_min = QLineEdit()

        for widget in (
            self.input_nom,
            self.input_categorie,
            self.input_dlv,
            self.input_pa,
            self.input_pv,
            self.input_prix_promo,
            self.input_qte_min,
        ):
            widget.setReadOnly(True)

        # En promo toggle button
        self._en_promo = False
        self.btn_en_promo = QPushButton("Hors promo")
        self.btn_en_promo.setMinimumHeight(30)
        self.btn_en_promo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_en_promo.clicked.connect(self._toggle_promo)
        self._update_promo_button()

        box_edit = QGroupBox("Editable")
        edit_grid = QGridLayout(box_edit)
        edit_grid.setHorizontalSpacing(10)
        edit_grid.setVerticalSpacing(8)
        edit_grid.addWidget(QLabel("Nom :"), 0, 0)
        edit_grid.addWidget(self.input_nom, 0, 1, 1, 3)
        # Categorie and Min on row 1 (columns 0-3)
        edit_grid.addWidget(QLabel("Categorie :"), 1, 0)
        edit_grid.addWidget(self.input_categorie, 1, 1)
        self.input_categorie.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        edit_grid.addWidget(QLabel("Min :"), 1, 2)
        edit_grid.addWidget(self.input_qte_min, 1, 3)
        self.input_qte_min.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # DLV, PA, PV on row 2 (all within columns 0-3)
        edit_grid.addWidget(QLabel("DLV/DLC :"), 2, 0)
        edit_grid.addWidget(self.input_dlv, 2, 1)
        edit_grid.setColumnStretch(1, 1)  # DLV takes remaining space in its column pair
        edit_grid.addWidget(QLabel("PA :"), 2, 2)
        edit_grid.addWidget(self.input_pa, 2, 3)
        edit_grid.addWidget(QLabel("PV :"), 3, 0)
        edit_grid.addWidget(self.input_pv, 3, 1)
        edit_grid.setColumnStretch(1, 1)  # PV takes remaining space
        edit_grid.addWidget(QLabel("Prix Promo :"), 3, 2)
        edit_grid.addWidget(self.input_prix_promo, 3, 3)
        edit_grid.addWidget(self.btn_en_promo, 4, 0, 1, 4)

        box_info = QGroupBox("Infos")
        form_info = QFormLayout(box_info)
        form_info.setSpacing(8)
        form_info.addRow("ID :", self.lbl_reference)
        form_info.addRow("PRC :", self.lbl_prc)
        form_info.addRow("Stock Total :", self.lbl_stock)
        form_info.addRow("Stock Boutique :", self.lbl_b)
        form_info.addRow("Stock Reserve :", self.lbl_r)

        cols.addWidget(box_edit, 2)
        cols.addWidget(box_info, 1)
        layout.addLayout(cols)
        layout.addStretch()

    def update_info(self, produit: dict):
        if not produit:
            self._produit_actuel = None
            self.btn_edit.setEnabled(False)
            self.btn_save.setEnabled(False)
            return
        self._produit_actuel = dict(produit)
        self.btn_edit.setEnabled(True)
        self.btn_save.setEnabled(False)
        self._editing = False
        self._set_editable(False)
        self._fill_fields(self._produit_actuel)

    def _fill_fields(self, produit: dict):
        self.lbl_reference.setText(str(produit.get("id", "-")))
        b = int(produit.get("b", 0))
        r = int(produit.get("r", 0))
        pa = int(produit.get("pa", 0))
        self.lbl_b.setText(format_grouped_int(b))
        self.lbl_r.setText(format_grouped_int(r))
        self.lbl_stock.setText(format_grouped_int(b + r))
        self.lbl_prc.setText(f"{format_grouped_int(int(produit.get('prc', round(pa * 1.2))))} Ar")
        self.input_nom.setText(str(produit.get("nom", "")))
        self.input_categorie.setText(str(produit.get("categorie", "")))
        dlv_str = str(produit.get("dlv_dlc", ""))
        parsed = parse_expiry_dates(dlv_str)
        if parsed:
            self.input_dlv.setDate(QDate(parsed.year, parsed.month, parsed.day))
        else:
            self.input_dlv.setDate(QDate())
        self.input_pa.setText(format_grouped_int(pa))
        self.input_pv.setText(format_grouped_int(int(produit.get("pv", 0))))
        self.input_prix_promo.setText(format_grouped_int(int(produit.get("prix_promo", pa))))
        self.input_qte_min.setText(str(max(0, int(produit.get("qte_min", 2)))))
        self._en_promo = bool(produit.get("en_promo", 0))
        self._update_promo_button()

    def _set_editable(self, editable: bool):
        for widget in (
            self.input_nom,
            self.input_categorie,
            self.input_dlv,
            self.input_pa,
            self.input_pv,
            self.input_prix_promo,
            self.input_qte_min,
        ):
            widget.setReadOnly(not editable)

    def _start_edit(self):
        if self._produit_actuel is None:
            return
        if self._editing:
            return
        self._editing = True
        self.btn_edit.setEnabled(False)
        self.btn_save.setEnabled(True)
        self._set_editable(True)
        self.input_nom.setFocus()

    def _save_edit(self):
        if self._produit_actuel is None or not self._editing:
            return
        pa = max(0, parse_grouped_int(self.input_pa.text().strip(), default=0))
        pv = max(0, parse_grouped_int(self.input_pv.text().strip(), default=0))
        prix_promo = max(0, parse_grouped_int(self.input_prix_promo.text().strip(), default=pa))
        qte_min = max(0, parse_grouped_int(self.input_qte_min.text().strip(), default=2))
        updated = dict(self._produit_actuel)
        updated["nom"] = self.input_nom.text().strip() or str(self._produit_actuel.get("nom", ""))
        updated["categorie"] = self.input_categorie.text().strip() or str(
            self._produit_actuel.get("categorie", "Sans categorie")
        )
        dlv_date = self.input_dlv.date()
        updated["dlv_dlc"] = dlv_date.toString("yyyy-MM-dd")
        updated["pa"] = pa
        updated["prc"] = int(round(pa * 1.2))
        updated["pv"] = pv
        updated["prix_promo"] = prix_promo
        updated["en_promo"] = 1 if self._en_promo else 0
        updated["qte_min"] = qte_min
        self._produit_actuel = updated
        self._editing = False
        self.btn_edit.setEnabled(True)
        self.btn_save.setEnabled(False)
        self._set_editable(False)
        self._fill_fields(updated)
        self.produit_modifie.emit(dict(updated))

    def _toggle_promo(self) -> None:
        """Toggle the en_promo flag, update appearance, and save to database."""
        self._en_promo = not self._en_promo
        self._update_promo_button()
        # Persist the change to database
        if self._produit_actuel:
            updated = dict(self._produit_actuel)
            updated["en_promo"] = 1 if self._en_promo else 0
            self._produit_actuel = updated
            self.produit_modifie.emit(dict(updated))

    def _update_promo_button(self) -> None:
        """Update the En promo toggle button style and text."""
        if self._en_promo:
            self.btn_en_promo.setText("En promo \u2713")
            self.btn_en_promo.setStyleSheet(
                "QPushButton {"
                "  background-color: #16a34a; color: white;"
                "  border: 1px solid #15803d; border-radius: 6px;"
                "  font-weight: bold; font-size: 12px;"
                "}"
                "QPushButton:hover { background-color: #15803d; }"
            )
        else:
            self.btn_en_promo.setText("Hors promo")
            self.btn_en_promo.setStyleSheet(
                "QPushButton {"
                "  background-color: #374151; color: #9ca3af;"
                "  border: 1px solid #4b5563; border-radius: 6px;"
                "  font-weight: bold; font-size: 12px;"
                "}"
                "QPushButton:hover { background-color: #4b5563; }"
            )
