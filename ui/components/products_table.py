"""Table des produits pour l'ecran mouvements."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from core.formatters import format_dlv_dlc_date, format_grouped_int


class ProduitsTable(QGroupBox):
    """Widget de liste produits avec recherche et selection."""

    produit_selectionne = pyqtSignal(dict)

    def __init__(self) -> None:
        super().__init__("Produits")
        self._produits = []
        self._categorie_active = "Tous"
        self._recherche = ""
        self._category_buttons = []
        # Correction: La map des catégories était manquante, causant un crash au démarrage.
        # On l'initialise avec les sous-catégories connues.
        # Ces catégories correspondent aux `categorie_code` du fichier d'import
        # et aux noms dans la table `categories` de la base de données.
        self._categories_map = {
            cat: cat
            for cat in [
                "BA",
                "BSA",
                "Confi",
                "EPI",
                "HS",
                "Tabac",
                "Baz",
                "GL",
                "Gaz",
                "PF",
                "Zoth",
                "Lub",
                "Pea",
                "Solaires",
            ]
        }

        self._build_ui()
        self.set_produits(self._default_produits())

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        self.table = QTableWidget(0, 11)
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Nom produit",
                "Categorie",
                "PA",
                "PRC",
                "PV",
                "Btq",
                "Rv",
                "Tot",
                "DLV/DLC",
                "",
            ]
        )
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nom
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Categorie
        for index in (3, 4, 5, 6, 7, 8, 9, 10):
            header.setSectionResizeMode(index, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        footer.setContentsMargins(0, 0, 0, 0)
        footer.addWidget(QLabel("Categorie :"))
        self.footer_categories = QHBoxLayout()
        self.footer_categories.setSpacing(4)
        footer.addLayout(self.footer_categories, 1)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Recherche fuzzy...")
        self.search_input.setMaximumHeight(28)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        footer.addWidget(self.search_input, 1)
        layout.addLayout(footer)

        # No timer - search applied immediately

    def set_produits(self, produits: list[dict]) -> None:
        self._produits = [dict(p) for p in (produits or [])]
        self._categorie_active = "Tous"
        self._search_text = ""
        if hasattr(self, "search_input"):
            self.search_input.clear()
        self._build_category_buttons()
        self.refresh()

    def get_produits(self) -> list[dict]:
        return self._produits

    def refresh(self) -> None:
        self._refresh_table_incremental()

    def update_produit(self, produit: dict) -> None:
        """Update a single product row in the table without full refresh."""
        produit_id = produit.get("id")
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.text() == str(produit_id):
                self._update_table_row(row, produit)
                return
        # If not found, do full refresh
        self._refresh_table_incremental()

    def _refresh_table_incremental(self) -> None:
        """Optimized refresh that only updates changed rows."""
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
        pa = int(produit.get("pa", produit.get("prc", 0)))
        prc = int(produit.get("prc", round(pa * 1.2)))
        values = [
            str(produit.get("id", "")),
            str(produit.get("nom", "")),
            str(produit.get("categorie", "Sans categorie")),
            format_grouped_int(pa),
            format_grouped_int(prc),
            format_grouped_int(produit.get("pv", 0)),
            format_grouped_int(b),
            format_grouped_int(r),
            format_grouped_int(b + r),
            format_dlv_dlc_date(str(produit.get("dlv_dlc", ""))),
        ]
        for col, value in enumerate(values):
            item = self.table.item(row, col)
            if item is None:
                item = QTableWidgetItem(value)
                self.table.setItem(row, col, item)
                if col in (0, 1, 3, 4, 5, 6, 7, 8, 9):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
            else:
                item.setText(value)

    def _insert_table_row(self, row: int, produit: dict) -> None:
        """Insert a new table row with cached button."""
        self.table.insertRow(row)

        b = int(produit.get("b", 0))
        r = int(produit.get("r", 0))
        pa = int(produit.get("pa", produit.get("prc", 0)))
        prc = int(produit.get("prc", round(pa * 1.2)))
        values = [
            str(produit.get("id", "")),
            str(produit.get("nom", "")),
            str(produit.get("categorie", "Sans categorie")),
            format_grouped_int(pa),
            format_grouped_int(prc),
            format_grouped_int(produit.get("pv", 0)),
            format_grouped_int(b),
            format_grouped_int(r),
            format_grouped_int(b + r),
            format_dlv_dlc_date(str(produit.get("dlv_dlc", ""))),
        ]
        for col, value in enumerate(values):
            item = QTableWidgetItem(value)
            if col in (0, 1, 3, 4, 5, 6, 7, 8, 9):
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(row, col, item)

        # Use a static cached button instead of creating new one each time
        btn_select = self._get_cached_button()
        try:
            btn_select.clicked.disconnect()
        except TypeError:
            pass  # No connections to disconnect
        btn_select.clicked.connect(lambda _, p=produit: self._select_produit(p))
        self.table.setCellWidget(row, 10, btn_select)

    def _get_cached_button(self) -> QPushButton:
        """Get or create a cached button widget."""
        if not hasattr(self, "_button_cache"):
            self._button_cache = []
        if self._button_cache:
            return self._button_cache.pop()
        btn = QPushButton("Choisir")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def _recycle_button(self, btn: QPushButton) -> None:
        """Recycle a button back to the cache."""
        if not hasattr(self, "_button_cache"):
            self._button_cache = []
        btn.clicked.disconnect()
        self._button_cache.append(btn)

    def _build_category_buttons(self) -> None:
        while self.footer_categories.count():
            item = self.footer_categories.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._category_buttons.clear()

        categories = ["Tous"] + sorted(self._categories_map.keys())
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setMaximumHeight(24)
            btn.setStyleSheet("padding: 1px 8px;")
            btn.setChecked(cat == self._categorie_active)
            btn.clicked.connect(lambda _, c=cat: self._set_category(c))
            self.footer_categories.addWidget(btn)
            self._category_buttons.append(btn)
        self.footer_categories.addStretch()

    def _set_category(self, categorie: str) -> None:
        self._categorie_active = categorie
        for btn in self._category_buttons:
            btn.setChecked(btn.text() == categorie)
        self.refresh()

    def _on_search_text_changed(self) -> None:
        """Applique le filtre de recherche immédiatement."""
        self._apply_search_filter()

    def _apply_search_filter(self) -> None:
        """Applique le filtre de recherche apres le delai du timer."""
        text = self.search_input.text().strip().lower()

        # Regle: bloque la recherche pour les repetitions (ex: 'aaaa', '1111')
        if len(text) > 3 and len(set(text)) == 1:
            return

        # Regle: recherche activee a partir de 2 caracteres
        if len(text) < 2:
            text = ""

        if text == self._search_text:
            return

        self._search_text = text
        self.refresh()

    def _matches_search(self, produit: dict) -> bool:
        if not self._search_text:
            return True
        nom = str(produit.get("nom", "")).lower()
        categorie = str(produit.get("categorie", "")).lower()
        base_search = f"{nom} {categorie}"
        # Verifie que tous les mots de la recherche sont presents
        return all(term in base_search for term in self._search_text.split())

    def _filtered_produits(self) -> list[dict]:
        resultat = []

        cat_prefix = self._categories_map.get(self._categorie_active)

        for produit in self._produits:
            categorie = produit.get("categorie", "Sans categorie")
            if cat_prefix and not categorie.startswith(cat_prefix):
                continue
            if not self._matches_search(produit):
                continue
            resultat.append(produit)
        return resultat

    def _select_produit(self, produit: dict) -> None:
        self.produit_selectionne.emit(dict(produit))

    def _default_produits(self) -> list[dict]:
        return []
