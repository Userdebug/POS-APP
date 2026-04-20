"""Table des produits pour l'ecran mouvements."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_dlv_dlc_date, format_grouped_int
from ui.components.search_bar import SearchBar


class _CategoryButtonGrid(QWidget):
    """Widget that organizes category buttons in a flexible 2-row grid layout."""

    MAX_BUTTONS_PER_ROW = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._buttons: list[QPushButton] = []
        self._grid_layout = QGridLayout(self)
        self._grid_layout.setSpacing(4)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._grid_layout)

    def clear(self) -> None:
        """Remove all buttons from the grid."""
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._buttons.clear()

    def add_button(self, btn: QPushButton) -> None:
        """Add a button to the grid in a 2-row wrapping layout."""
        self._buttons.append(btn)
        row = len(self._buttons) // self.MAX_BUTTONS_PER_ROW
        col = len(self._buttons) % self.MAX_BUTTONS_PER_ROW
        self._grid_layout.addWidget(btn, row, col)

    def add_stretch_after_row(self, row: int) -> None:
        """Add stretch after a specific row."""
        self._grid_layout.setColumnStretch(row, 1)

    def count(self) -> int:
        """Return the number of buttons in the grid."""
        return len(self._buttons)


class ProduitsTable(QGroupBox):
    """Widget de liste produits avec recherche et selection."""

    produit_selectionne = pyqtSignal(dict)
    categories_modifiees = pyqtSignal(dict)

    def __init__(self, db_manager=None) -> None:
        super().__init__("Produits")
        self._db_manager = db_manager
        self._produits = []
        self._categorie_active = "Tous"
        self._search_text = ""
        self._category_buttons = []
        self._categories_map: dict[str, str] = {}
        self._button_grid: _CategoryButtonGrid | None = None

        self._build_ui()
        self._load_categories_from_db()
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

        self._button_grid = _CategoryButtonGrid()
        footer.addWidget(self._button_grid, 1)

        self.search_input = SearchBar(
            placeholder="Recherche fuzzy...",
            debounce_ms=300,
            min_chars=2,
        )
        self.search_input.search_changed.connect(self._on_search_changed)
        self.search_input.setMinimumWidth(150)
        self.search_input.setMaximumWidth(250)
        footer.addWidget(self.search_input, 0)
        layout.addLayout(footer)

    def _load_categories_from_db(self) -> None:
        """Load categories dynamically from database (only subcategories)."""
        if self._db_manager is None:
            self._init_default_categories()
            return
        try:
            # Get only subcategories (categories with a parent_id)
            all_categories = self._db_manager.categories.get_all_categories()
            subcategories = [c for c in all_categories if c.parent_id is not None]
            if subcategories:
                # Build map from category objects (use nom as key)
                self._categories_map = {cat.nom: cat.nom for cat in subcategories}
                self._build_category_buttons()
                self.categories_modifiees.emit(self._categories_map)
            else:
                # Fall back to defaults if no subcategories
                self._init_default_categories()
        except Exception:
            # Fall back to defaults if DB query fails
            self._init_default_categories()

    def _init_default_categories(self) -> None:
        """Initialize with default hardcoded categories (fallback)."""
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
        self._build_category_buttons()

    def set_categories(self, categories: list[str] | dict[str, str]) -> None:
        """Set categories dynamically from external source.

        Args:
            categories: List of category names OR dict mapping prefix to full name.
        """
        if isinstance(categories, list):
            self._categories_map = {cat: cat for cat in categories}
        else:
            self._categories_map = dict(categories)
        self._build_category_buttons()
        self.categories_modifiees.emit(self._categories_map)

    def get_categories(self) -> dict[str, str]:
        """Return the current categories map."""
        return dict(self._categories_map)

    def update_category_buttons(self) -> None:
        """Rebuild category buttons after external categories have changed."""
        self._build_category_buttons()
        self.categories_modifiees.emit(self._categories_map)

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

    def refresh(self, full_rebuild: bool = False) -> None:
        """Refresh table with UI update protection.

        Args:
            full_rebuild: If True, force complete table rebuild.
                         Use sparingly - only when product list changes.
        """
        self.table.setUpdatesEnabled(False)
        try:
            if full_rebuild:
                self._refresh_table_full()
            else:
                self._refresh_table_incremental()
        finally:
            self.table.setUpdatesEnabled(True)

    def _refresh_table_full(self) -> None:
        """Full table rebuild - only call when product list changes."""
        self.table.setRowCount(0)
        filtered = self._filtered_produits()
        self.table.setRowCount(len(filtered))
        for row_idx, produit in enumerate(filtered):
            self._populate_table_row(row_idx, produit)

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

        self._update_row_button(row, produit.get("id"))

    def _populate_table_row(self, row: int, produit: dict) -> None:
        """Populate a table row (for full rebuild)."""
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
        self._create_row_button(row, produit.get("id"))

    def _update_row_button(self, row: int, produit_id) -> None:
        """Update button in a row without recreation."""
        old_btn = self.table.cellWidget(row, 10)
        if old_btn is not None:
            old_btn.deleteLater()
        self._create_row_button(row, produit_id)

    def _create_row_button(self, row: int, produit_id) -> None:
        """Create a selection button for a row."""
        btn_select = QPushButton("Choisir")
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setProperty("produit_id", produit_id)
        btn_select.clicked.connect(lambda r=row: self._on_row_button_clicked(r))
        self.table.setCellWidget(row, 10, btn_select)

    def _on_row_button_clicked(self, row: int) -> None:
        """Handle button click by looking up product from the filtered list."""
        # Use product ID lookup instead of row index to handle search filtering
        btn = self.sender()
        if btn is None:
            return
        produit_id = btn.property("produit_id")
        if produit_id is None:
            return

        # Find product by ID in the original products list
        for produit in self._produits:
            if str(produit.get("id")) == str(produit_id):
                self.produit_selectionne.emit(dict(produit))
                return

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

        # Create button using product ID lookup to avoid closure issues
        btn_select = QPushButton("Choisir")
        btn_select.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select.setProperty("produit_id", produit.get("id"))
        btn_select.clicked.connect(lambda r=row: self._on_row_button_clicked(r))
        self.table.setCellWidget(row, 10, btn_select)

    def _set_category(self, categorie: str) -> None:
        self._categorie_active = categorie
        for btn in self._category_buttons:
            btn.setChecked(btn.text() == categorie)
        if categorie != "Tous" or self._search_text != "":
            self.refresh()

    def _build_category_buttons(self) -> None:
        if not self._button_grid:
            return

        self._button_grid.clear()
        self._category_buttons.clear()

        categories = ["Tous"] + sorted(self._categories_map.keys())
        for cat in categories:
            btn = QPushButton(cat)
            btn.setCheckable(True)
            btn.setMaximumHeight(24)
            btn.setStyleSheet("padding: 1px 8px;")
            btn.setChecked(cat == self._categorie_active)
            btn.clicked.connect(lambda _, c=cat: self._set_category(c))
            self._button_grid.add_button(btn)
            self._category_buttons.append(btn)

    def _on_search_changed(self, text: str) -> None:
        """Handle debounced search text from SearchBar."""
        if text != self._search_text:
            self._search_text = text
            if text == "" and self._categorie_active == "Tous":
                return
            self.refresh()

    def _matches_search(self, produit: dict) -> bool:
        if not self._search_text:
            return True
        nom = str(produit.get("nom", "")).lower()
        categorie = str(produit.get("categorie", "")).lower()
        base_search = f"{nom} {categorie}"
        # Verifie que tous les mots de la recherche sont presents
        return all(term in base_search for term in self._search_text.split())

    def _has_quantity(self, produit: dict) -> bool:
        """Check if product has quantity (b + r > 0)."""
        return (int(produit.get("b", 0)) + int(produit.get("r", 0))) > 0

    def _filtered_produits(self) -> list[dict]:
        resultat = []

        cat_prefix = self._categories_map.get(self._categorie_active)

        for produit in self._produits:
            # Filter out products with zero quantity
            if not self._has_quantity(produit):
                continue
            categorie = produit.get("categorie", "Sans categorie")
            if cat_prefix and not categorie.startswith(cat_prefix):
                continue
            if not self._matches_search(produit):
                continue
            resultat.append(produit)

        resultat.sort(key=self._sort_by_dlv_dlc)
        return resultat

    def _sort_by_dlv_dlc(self, produit: dict) -> tuple:
        dlv_dlc = str(produit.get("dlv_dlc", "")).strip()
        if not dlv_dlc:
            return (1, "")  # Empty dates last
        # Parse date for sorting (format: DD/MM/YYYY)
        parts = dlv_dlc.split("/")
        if len(parts) == 3:
            try:
                day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                return (0, year * 10000 + month * 100 + day)  # Sort ascending (nearest first)
            except ValueError:
                return (1, "")
        return (1, "")

    def _default_produits(self) -> list[dict]:
        return []
