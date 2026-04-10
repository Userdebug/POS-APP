from datetime import date, timedelta

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_dlv_dlc_date, format_grouped_int, parse_dlv_dlc_date
from styles.design_tokens import TOKENS
from ui.components.pos_tables import get_table_style


class ZoneProduits(QWidget):
    """Zone affichant la liste des produits avec recherche et ajout au panier."""

    produit_ajoute = pyqtSignal(dict)
    verification_change = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.produits = []
        self.recherche = ""
        self._mode = "vente"

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)

        # Table des produits (5 colonnes contenant: Nom & Infos, Qté, PV, DLV/DLC, +)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Nom & Infos", "Qté", "PV", "DLV/DLC", ""])
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        self.table.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)

        # Vertical header — used to display verification date DD/MM
        vert_header = self.table.verticalHeader()
        if vert_header is not None:
            vert_header.setDefaultSectionSize(60)  # chaque ligne = 80px (was 60, text was cut)
            vert_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            vert_header.setFixedWidth(40)  # enough for DD/MM
            vert_header.setSectionsClickable(True)
            vert_header.sectionClicked.connect(self._on_verification_click)

        # Ajustement horizontal des colonnes
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(4, 60)

        self.table.setStyleSheet(get_table_style("products"))

        main_layout.addWidget(self.table, 1)

        # Footer avec champ de recherche
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Rechercher un produit...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        footer.addWidget(self.search_input, 1)
        main_layout.addLayout(footer)

        self._refresh_table()

    # --- Méthodes de gestion des produits ---
    def set_mode(self, mode: str):
        """Set the mode to control button behavior.

        Args:
            mode: 'vente' (caisse) or 'achat' (reception)
        """
        normalized = mode.lower().strip()
        old_mode = self._mode
        if normalized in ("vente", "caisse"):
            self._mode = "vente"
        elif normalized in ("achat", "reception"):
            self._mode = "achat"
        else:
            self._mode = "vente"

        # Only refresh if mode actually changed AND we have products
        if self._mode != old_mode and self.produits:
            self._refresh_table()

    def set_produits(self, produits):
        new_produits = list(produits or [])
        # Only rebuild if data actually changed
        if new_produits == self.produits:
            return
        self.produits = new_produits
        self.search_text = ""
        self.search_input.clear()
        self._refresh_table()

    def _on_search_text_changed(self, text):
        self._apply_search_filter()

    def _apply_search_filter(self):
        text = self.search_input.text().strip().lower()
        if len(text) > 3 and len(set(text)) == 1:
            return
        if len(text) < 2:
            text = ""
        if text == self.search_text:
            return
        self.search_text = text
        self._refresh_table()

    def _matches_search(self, produit):
        if not self.search_text:
            return True
        nom = str(produit.get("nom", "")).lower()
        categorie = str(produit.get("categorie", "")).lower()
        base_search = f"{nom} {categorie}"
        return all(term in base_search for term in self.search_text.split())

    def _filtered_produits(self):
        return [p for p in self.produits if self._matches_search(p)]

    def _refresh_table(self):
        data = self._filtered_produits()
        self.table.setRowCount(0)

        for produit in data:
            row = self.table.rowCount()
            self.table.insertRow(row)

            b = int(produit.get("b", 0))
            r = int(produit.get("r", 0))
            pa = int(produit.get("pa", produit.get("prix", 0)))
            qte_min = 2
            nom = str(produit.get("nom", ""))
            total_qte = b + r
            pa_100 = int(pa / 100)

            # Vertical header: display verification date as DD/MM
            verification_str = str(produit.get("derniere_verification", ""))
            self._set_verification_header(row, verification_str)

            # Nom & Infos (col 0)
            is_promo = bool(produit.get("en_promo", 0))
            promo_badge = (
                " <span style='color:#22c55e; font-weight:bold;'>[P]</span>" if is_promo else ""
            )
            html_text = (
                f"<b style='color:{TOKENS['text_primary']};'>{nom}</b><br>"
                f"<span style='color:#22c55e;'>B: {format_grouped_int(b)}</span> | "
                f"<span style='color:#f59e0b;'>R: {format_grouped_int(r)}</span> | "
                f"<span style='color:#a855f7;'>Idx: {format_grouped_int(pa_100)}</span>{promo_badge}"
            )
            lbl = QLabel(html_text)
            lbl.setContentsMargins(2, 2, 2, 2)
            lbl.setWordWrap(True)

            # Get PV (prix de vente) - use promo price if en_promo
            pv = int(produit.get("pv", 0))
            if is_promo:
                pv = int(produit.get("prix_promo", pv))
            pv_formatted = format_grouped_int(pv)

            values = [
                "",  # col 0 remplacée par widget
                format_grouped_int(total_qte),
                pv_formatted,
                self._format_dlv_dlc(str(produit.get("dlv_dlc", ""))),
            ]

            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    self.table.setItem(row, col, item)
                    self.table.setCellWidget(row, col, lbl)
                else:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                    if col == 1 and total_qte < qte_min:
                        item.setForeground(QColor("#dc2626"))
                    if col == 3:
                        self._apply_dlv_color(item, str(produit.get("dlv_dlc", "")))
                    self.table.setItem(row, col, item)

            # Bouton d’ajout (col 4)
            ccontainer = QWidget()
            layout = QHBoxLayout(ccontainer)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

            btn_add = QPushButton("+")
            btn_add.setMinimumHeight(20)
            btn_add.setCursor(Qt.CursorShape.PointingHandCursor)

            # Logique métier (DLV / Stock)
            is_vente = self._mode == "vente"
            if is_vente:
                dlv_value = str(produit.get("dlv_dlc", ""))
                has_dlv = parse_dlv_dlc_date(dlv_value) is not None
                is_expired = self._is_dlv_expired(dlv_value)
                can_add = total_qte > 0 and (not has_dlv or not is_expired)
            else:
                can_add = True

            btn_add.setStyleSheet(self._add_button_style(can_add))
            btn_add.setEnabled(can_add)

            if not can_add:
                msg = "Stock épuisé" if total_qte <= 0 else "DLV/DLC dépassée"
                btn_add.setToolTip(f"{msg}: ajout désactivé")
            else:
                btn_add.setToolTip("Ajouter au panier")

            btn_add.clicked.connect(lambda _, p=produit: self._emit_add_to_cart(p))

            layout.addWidget(btn_add)
            self.table.setCellWidget(row, 4, ccontainer)

    # --- Verification date display & click ---
    def _set_verification_header(self, row: int, verification_str: str) -> None:
        """Set the vertical header item for a row to show verification date.

        Display format: two lines like "03\n/04" (DD on top, MM below).

        Args:
            row: Row index
            verification_str: ISO date string YYYY-MM-DD or empty string
        """
        label = QTableWidgetItem()
        label.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if verification_str and len(verification_str) >= 10:
            parts = verification_str[:10].split("-")
            if len(parts) == 3:
                dd = parts[2]
                mm = parts[1]
                # Two-line format: day on top, month below
                label.setText(f"{dd}\n{mm}")
                try:
                    verify_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                    today = date.today()
                    if (today - verify_date).days <= 7:
                        label.setForeground(QColor("#22c55e"))  # green
                    elif (today - verify_date).days <= 30:
                        label.setForeground(QColor("#ca8a04"))  # yellow
                    else:
                        label.setForeground(QColor("#dc2626"))  # red
                except ValueError:
                    label.setForeground(QColor("#9ca3af"))
            else:
                label.setText("--")
                label.setForeground(QColor("#6b7280"))
        else:
            label.setText("--")
            label.setForeground(QColor("#6b7280"))

        self.table.setVerticalHeaderItem(row, label)

    def _on_verification_click(self, logical_index: int) -> None:
        """Handle click on vertical header to set verification date to today.

        Args:
            logical_index: Row index that was clicked
        """
        # Find the product corresponding to this row
        filtered = self._filtered_produits()
        if 0 <= logical_index < len(filtered):
            produit = filtered[logical_index]
            produit_id = produit.get("id")
            if produit_id is not None:
                today_str = date.today().isoformat()
                # Update local data
                produit["derniere_verification"] = today_str
                # Emit signal for controller to persist
                self.verification_change.emit(int(produit_id), today_str)
                # Refresh header display
                self._set_verification_header(logical_index, today_str)

    # --- Utilitaires ---
    def _add_button_style(self, active: bool) -> str:
        """Get add button style using design tokens.

        Args:
            active: Whether the button should appear active/enabled.

        Returns:
            CSS stylesheet string for the add button.
        """
        return f"""
            QPushButton {{
                background-color: #0d47a1;
                color: white;
                border: none;
                font-weight: bold;
                font-size: 20px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #1565c0;
            }}
            QPushButton:pressed {{
                background-color: #0a2f6a;
            }}
            QPushButton:disabled {{
                background-color: {TOKENS['bg_button_disabled']};
                color: {TOKENS['text_muted']};
                border-radius: 6px;
            }}
        """

    def _emit_add_to_cart(self, produit):
        payload = dict(produit)
        # Use promo price as effective PV when product is on promotion
        if payload.get("en_promo"):
            payload["pv"] = payload.get("prix_promo", payload.get("pv", 0))
        payload["prix"] = payload.get("pv", payload.get("prix", 0))
        self.produit_ajoute.emit(payload)

    def _format_dlv_dlc(self, value: str) -> str:
        return format_dlv_dlc_date(value)

    def _is_dlv_expired(self, value: str) -> bool:
        parsed = parse_dlv_dlc_date(value)
        if parsed is None:
            return False
        return parsed < date.today()

    def _apply_dlv_color(self, item: QTableWidgetItem, value: str) -> None:
        """Colorise la cellule DLV/DLC selon l'echeance."""
        parsed = parse_dlv_dlc_date(value)
        if parsed is None:
            return

        today = date.today()
        if parsed < today:
            item.setForeground(QColor("#dc2626"))  # Expire
        elif parsed <= today + timedelta(days=7):
            item.setForeground(QColor("#ea580c"))  # Tres proche
        elif parsed <= today + timedelta(days=30):
            item.setForeground(QColor("#ca8a04"))  # A surveiller
        else:
            item.setForeground(QColor("#16a34a"))  # OK

    def get_produits(self) -> list[dict]:
        """Return a copy of the current list of produits for external access."""
        return list(self.produits)

    def update_produit(self, produit: dict) -> None:
        """Update a single product in the list and refresh the table display.

        Args:
            produit: Product dict with 'id' field to identify which product to update.
        """
        target_id = produit.get("id")
        if target_id is None:
            return
        for i, row in enumerate(self.produits):
            if row.get("id") == target_id:
                self.produits[i] = dict(produit)
                self._refresh_table()
                return
