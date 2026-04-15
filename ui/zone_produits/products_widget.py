from datetime import date, timedelta

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QAbstractScrollArea,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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
from ui.components.search_bar import SearchBar


class ZoneProduits(QWidget):
    """Zone affichant la liste des produits avec recherche et ajout au panier."""

    produit_ajoute = pyqtSignal(dict)
    verification_change = pyqtSignal(int, str)

    def __init__(self):
        super().__init__()
        self.produits = []
        self.search_text = ""
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

        # Footer avec SearchBar (debounce integre)
        footer = QHBoxLayout()
        footer.setSpacing(10)

        self.search_input = SearchBar(
            placeholder="Rechercher un produit...",
            debounce_ms=300,
            min_chars=2,
        )
        self.search_input.search_changed.connect(self._on_search_changed)
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

        # Fast path: if data is identical, skip refresh entirely
        if new_produits == self.produits:
            return

        # Check if product IDs are the same - if so, use incremental update
        old_ids = {p.get("id") for p in self.produits}
        new_ids = {p.get("id") for p in new_produits}

        if old_ids == new_ids and len(new_produits) == len(self.produits):
            # Same products, just different data - update in place
            self._update_products_incremental(new_produits)
            return

        # Full replacement needed
        self.produits = new_produits
        self.search_text = ""
        self.search_input.clear()
        self._refresh_table()

    def _update_products_incremental(self, new_produits: list) -> None:
        """Update products in-place without full table rebuild.

        Only updates rows that changed, preserving table structure.
        """
        # Create a lookup map for new product data
        new_map = {p.get("id"): p for p in new_produits}

        # Update existing rows
        for i, row in enumerate(self.produits):
            prod_id = row.get("id")
            if prod_id in new_map:
                self.produits[i] = new_map[prod_id]

        # Re-apply search filter if active
        if self.search_text:
            self._refresh_table()

    def _on_search_changed(self, text: str) -> None:
        """Handle debounced search text from SearchBar."""
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
        filtered = [p for p in self.produits if self._matches_search(p)]
        return sorted(filtered, key=self._dlv_sort_key)

    def _dlv_sort_key(self, produit: dict) -> tuple:
        """Sort key for DLV/DLC ordering - nearly expired first, no date last."""
        dlv_value = str(produit.get("dlv_dlc", ""))
        parsed = parse_dlv_dlc_date(dlv_value)
        if parsed is None:
            return (1, date.max)  # No date = lowest priority
        return (0, parsed)  # Has date = higher priority, sorted by date

    def _refresh_table(self):
        """Refresh table with UI update protection to prevent lag."""
        self.table.setUpdatesEnabled(False)
        try:
            self._refresh_table_incremental()
        finally:
            self.table.setUpdatesEnabled(True)

    def _refresh_table_incremental(self) -> None:
        """Optimized refresh that only updates changed rows.

        Updates existing rows in-place, adds new rows, and removes excess rows.
        This avoids the performance penalty of full table rebuilds.
        """
        filtered = self._filtered_produits()
        current_rows = self.table.rowCount()
        new_rows = len(filtered)

        # Remove excess rows
        while current_rows > new_rows:
            self.table.removeRow(current_rows - 1)
            current_rows -= 1

        # Update existing rows or add new ones
        for row_idx, produit in enumerate(filtered):
            if row_idx < self.table.rowCount():
                # Update existing row
                self._update_table_row(row_idx, produit)
            else:
                # Add new row
                self._insert_table_row(row_idx, produit)

    def _update_table_row(self, row: int, produit: dict) -> None:
        """Update a single table row without recreating widgets."""
        b = int(produit.get("b", 0))
        r = int(produit.get("r", 0))
        pa = int(produit.get("pa", produit.get("prix", 0)))
        qte_min = int(produit.get("min_qte", 2))
        total_qte = b + r
        pa_100 = int(pa / 100)
        nom = str(produit.get("nom", ""))
        is_promo = bool(produit.get("en_promo", 0))

        # Update verification header
        verification_str = str(produit.get("derniere_verification", ""))
        self._set_verification_header(row, verification_str)

        # Update col 0 - Nom & Infos (QLabel widget)
        promo_badge = (
            " <span style='color:#22c55e; font-weight:bold;'>[P]</span>" if is_promo else ""
        )
        html_text = (
            f"<b style='color:{TOKENS['text_primary']};'>{nom}</b><br>"
            f"<span style='color:#22c55e;'>B: {format_grouped_int(b)}</span> | "
            f"<span style='color:#f59e0b;'>R: {format_grouped_int(r)}</span> | "
            f"<span style='color:#a855f7;'>Idx: {format_grouped_int(pa_100)}</span>{promo_badge}"
        )
        existing_widget = self.table.cellWidget(row, 0)
        if existing_widget and isinstance(existing_widget, QLabel):
            existing_widget.setText(html_text)
        else:
            lbl = QLabel(html_text)
            lbl.setContentsMargins(2, 2, 2, 2)
            lbl.setWordWrap(True)
            self.table.setCellWidget(row, 0, lbl)
            self.table.setItem(row, 0, QTableWidgetItem(""))

        # Update col 1 - Total Qté
        item_qte = self.table.item(row, 1)
        if item_qte:
            item_qte.setText(format_grouped_int(total_qte))
            if total_qte < qte_min:
                item_qte.setForeground(QColor("#dc2626"))
            else:
                item_qte.setForeground(QColor())

        # Update col 2 - PV
        pv = int(produit.get("pv", 0))
        if is_promo:
            pv = int(produit.get("prix_promo", pv))
        item_pv = self.table.item(row, 2)
        if item_pv:
            item_pv.setText(format_grouped_int(pv))

        # Update col 3 - DLV/DLC
        dlv_value = str(produit.get("dlv_dlc", ""))
        item_dlv = self.table.item(row, 3)
        if item_dlv:
            item_dlv.setText(self._format_dlv_dlc(dlv_value))
            self._apply_dlv_color(item_dlv, dlv_value)

        # Update col 4 - Add button
        self._update_add_button(row, produit)

    def _update_add_button(self, row: int, produit: dict) -> None:
        """Update the add button for a row - always recreate to ensure correct closure."""
        # Always recreate button to ensure closure captures correct product reference
        self._recreate_add_button(row, produit)

    def _recreate_add_button(self, row: int, produit: dict) -> None:
        """Recreate the add button container and button for a row."""
        b = int(produit.get("b", 0))
        r = int(produit.get("r", 0))
        total_qte = b + r

        dlv_value = str(produit.get("dlv_dlc", ""))
        has_dlv = parse_dlv_dlc_date(dlv_value) is not None
        is_expired = self._is_dlv_expired(dlv_value)

        is_vente = self._mode == "vente"
        if is_vente:
            can_add = total_qte > 0 and (not has_dlv or not is_expired)
        else:
            can_add = True

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        btn_add = QPushButton("+")
        btn_add.setMinimumHeight(20)
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.setStyleSheet(self._add_button_style(can_add))
        btn_add.setEnabled(can_add)

        if not can_add:
            msg = "Stock épuisé" if total_qte <= 0 else "DLV/DLC dépassée"
            btn_add.setToolTip(f"{msg}: ajout désactivé")
        else:
            btn_add.setToolTip("Ajouter au panier")

        # Store reference to product dict - closure captures this specific product
        produit_ref = dict(produit)

        def on_add_clicked():
            # Re-fetch from filtered list to get latest data (prices, stock, etc.)
            filtered = self._filtered_produits()
            prod_id = produit_ref.get("id")
            for p in filtered:
                if p.get("id") == prod_id:
                    self._emit_add_to_cart(p)
                    break

        btn_add.clicked.connect(on_add_clicked)

        layout.addWidget(btn_add)
        self.table.setCellWidget(row, 4, container)

    def _insert_table_row(self, row: int, produit: dict) -> None:
        """Insert a new table row."""
        self.table.insertRow(row)

        b = int(produit.get("b", 0))
        r = int(produit.get("r", 0))
        pa = int(produit.get("pa", produit.get("prix", 0)))
        qte_min = int(produit.get("min_qte", 2))
        total_qte = b + r
        pa_100 = int(pa / 100)
        nom = str(produit.get("nom", ""))
        is_promo = bool(produit.get("en_promo", 0))

        # Verification header
        verification_str = str(produit.get("derniere_verification", ""))
        self._set_verification_header(row, verification_str)

        # Col 0 - Nom & Infos
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
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setCellWidget(row, 0, lbl)

        # Get PV
        pv = int(produit.get("pv", 0))
        if is_promo:
            pv = int(produit.get("prix_promo", pv))

        dlv_value = str(produit.get("dlv_dlc", ""))

        # Col 1 - Qté
        item_qte = QTableWidgetItem(format_grouped_int(total_qte))
        item_qte.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if total_qte < qte_min:
            item_qte.setForeground(QColor("#dc2626"))
        self.table.setItem(row, 1, item_qte)

        # Col 2 - PV
        item_pv = QTableWidgetItem(format_grouped_int(pv))
        item_pv.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, 2, item_pv)

        # Col 3 - DLV/DLC
        item_dlv = QTableWidgetItem(self._format_dlv_dlc(dlv_value))
        item_dlv.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._apply_dlv_color(item_dlv, dlv_value)
        self.table.setItem(row, 3, item_dlv)

        # Col 4 - Add button
        self._recreate_add_button(row, produit)

    def _refresh_table_intern(self):
        """Legacy method - now redirects to incremental refresh."""
        self._refresh_table_incremental()

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
                background-color: {TOKENS["bg_button_disabled"]};
                color: {TOKENS["text_muted"]};
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

    def update_single_product(self, produit: dict) -> None:
        """Update a single product in the list without full table refresh.

        Args:
            produit: Product dict with 'id' field to identify which product to update.
        """
        target_id = produit.get("id")
        if target_id is None:
            return

        # Ensure target_id is int for consistent comparison
        try:
            target_id = int(target_id)
        except (ValueError, TypeError):
            return

        # Find and update the product in our list
        updated = False
        for i, row in enumerate(self.produits):
            row_id = row.get("id")
            # Handle both int and string IDs for comparison
            try:
                row_id = int(row_id) if row_id is not None else None
            except (ValueError, TypeError):
                pass
            if row_id == target_id:
                self.produits[i] = dict(produit)
                # Ensure ID is int
                self.produits[i]["id"] = target_id
                updated = True
                break

        if not updated:
            # Product not in list, add it
            new_prod = dict(produit)
            new_prod["id"] = target_id
            self.produits.append(new_prod)

        # Check if product passes current filters
        if self.search_text:
            if not self._matches_search(produit):
                # Product no longer matches filter, check if it needs removal
                if target_id == produit.get("id"):
                    # Just update in place, user can refresh to see removal
                    pass

        # Only refresh if the product is visible in the current filtered view
        if self._matches_search(produit):
            self._refresh_table()

    # Keep update_produit as alias for backward compatibility
    update_produit = update_single_product
