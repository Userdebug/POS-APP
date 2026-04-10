"""Suivi Analyse Dialog - Analyse des CA et Achats par catégorie."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFrame,
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

from core.database import DatabaseManager
from core.formatters import format_grouped_int, parse_grouped_int
from styles.design_tokens import TOKENS
from styles.dialog_styles import (
    DIALOG_BASE,
    PRIMARY_BUTTON,
    REPORT_TABLE,
    SECONDARY_BUTTON,
    SEPARATOR,
)

CATEGORY_1_NAME = "Catégorie 1 - OW (Owners)"


class SuiviAnalyseDialog(QDialog):
    """Dialog for displaying CA final and Achats by category for a selected date."""

    ROW_HEIGHT = 32
    HEADER_HEIGHT = 34
    BUTTON_HEIGHT = 36
    DIALOG_PADDING = 20

    def __init__(self, parent: QWidget | None = None, db_manager: DatabaseManager | None = None):
        super().__init__(parent)

        self.setWindowTitle("Suivi Analyse - CA et Achats")
        self.setStyleSheet(DIALOG_BASE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.db_manager = db_manager or DatabaseManager()
        self._current_date = None
        self._original_data: dict[str, dict[str, int]] = {}
        self._edit_mode = False

        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(self.DIALOG_PADDING, 16, self.DIALOG_PADDING, 16)
        root.setSpacing(10)

        # ==================== Date Selector ====================
        date_layout = QHBoxLayout()
        date_layout.setSpacing(12)

        date_label = QLabel("Date:")
        date_label.setStyleSheet("font-weight: 600;")
        date_layout.addWidget(date_label)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd/MM/yy")
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self._on_date_changed)
        date_layout.addWidget(self.date_edit)

        date_layout.addStretch()
        root.addLayout(date_layout)

        # ==================== Separator ====================
        root.addWidget(self._make_separator())

        # ==================== Table ====================
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Cat\u00e9gorie", "CA (Ar)", "Achats (Ar)"])
        self.table.setStyleSheet(REPORT_TABLE + """
            QTableWidget::item {
                padding: 0px 4px;
            }
        """)
        self.table.setAlternatingRowColors(True)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setShowGrid(True)

        vh = self.table.verticalHeader()
        if vh is not None:
            vh.setDefaultSectionSize(self.ROW_HEIGHT)
            vh.setVisible(False)

        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header_view = self.table.horizontalHeader()
        if header_view is not None:
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header_view.resizeSection(1, 130)
            header_view.resizeSection(2, 130)
            header_view.setFixedHeight(self.HEADER_HEIGHT)

        root.addWidget(self.table)

        # ==================== Separator ====================
        root.addWidget(self._make_separator())

        # ==================== Total ====================
        total_container = QHBoxLayout()
        total_container.addStretch()

        self.lbl_total_ca = QLabel("Total CA: 0")
        self.lbl_total_ca.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TOKENS['total_caisse_text']};"
            f"background-color: {TOKENS['total_caisse_bg']};"
            f"border: 1px solid {TOKENS['total_caisse_border']};"
            "border-radius: 4px; padding: 4px 12px;"
        )
        self.lbl_total_ca.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        total_container.addWidget(self.lbl_total_ca)

        self.lbl_total_achats = QLabel("Total Achats: 0")
        self.lbl_total_achats.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {TOKENS['total_caisse_text']};"
            f"background-color: {TOKENS['total_caisse_bg']};"
            f"border: 1px solid {TOKENS['total_caisse_border']};"
            "border-radius: 4px; padding: 4px 12px;"
        )
        self.lbl_total_achats.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        total_container.addWidget(self.lbl_total_achats)

        total_container.addStretch()
        root.addLayout(total_container)

        # ==================== Buttons ====================
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        button_layout.addStretch()

        self._btn_edit = QPushButton("Modifier")
        self._btn_edit.setStyleSheet(SECONDARY_BUTTON)
        self._btn_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_edit.setFixedWidth(100)
        self._btn_edit.setFixedHeight(self.BUTTON_HEIGHT)
        self._btn_edit.clicked.connect(self._toggle_edit_mode)
        button_layout.addWidget(self._btn_edit)

        self._btn_save = QPushButton("Enregistrer")
        self._btn_save.setStyleSheet(PRIMARY_BUTTON)
        self._btn_save.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_save.setFixedWidth(100)
        self._btn_save.setFixedHeight(self.BUTTON_HEIGHT)
        self._btn_save.setEnabled(False)
        self._btn_save.clicked.connect(self._save_changes)
        button_layout.addWidget(self._btn_save)

        self._btn_close = QPushButton("Fermer")
        self._btn_close.setStyleSheet(SECONDARY_BUTTON)
        self._btn_close.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_close.setFixedWidth(100)
        self._btn_close.setFixedHeight(self.BUTTON_HEIGHT)
        self._btn_close.clicked.connect(self.accept)
        button_layout.addWidget(self._btn_close)

        button_layout.addStretch()

        root.addLayout(button_layout)

        self.table.cellChanged.connect(self._on_cell_changed)

    def _make_separator(self) -> QFrame:
        """Create a styled horizontal separator."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return sep

    def _on_date_changed(self) -> None:
        self._load_data()

    def _load_data(self) -> None:
        """Load data for the selected date."""
        jour = self.date_edit.date().toString("yyyy-MM-dd")
        self._current_date = jour

        # Load sous-categories for Catégorie 1 with their data
        with self.db_manager._connect() as conn:
            # Get subcategories with existing CA and Achats data
            query = """
                SELECT 
                    c.nom AS sous_categorie,
                    COALESCE(a.ca, 0) AS ca_final,
                    COALESCE(a.achats, 0) AS achats
                FROM categories c
                INNER JOIN categories parent ON c.parent_id = parent.id
                LEFT JOIN analyse_journaliere_categories a 
                    ON a.categorie_id = c.id AND a.jour = ?
                WHERE parent.nom = ?
                ORDER BY c.nom
            """
            rows = conn.execute(query, (jour, CATEGORY_1_NAME)).fetchall()

        # Build map for original data
        existing_map = {
            str(row["sous_categorie"]): {
                "ca_final_ttc": int(row["ca_final"] or 0),
                "achats_ttc": int(row["achats_ttc"] or 0),
            }
            for row in rows
        }
        self._original_data = dict(existing_map)

        # Build table data with all categories
        table_data: list[dict] = []
        for row in rows:
            cat = str(row["sous_categorie"])
            existing = existing_map.get(cat, {"ca_final_ttc": 0, "achats_ttc": 0})
            table_data.append(
                {
                    "categorie": cat,
                    "ca_final_ttc": existing["ca_final_ttc"],
                    "achats_ttc": existing["achats_ttc"],
                }
            )

        # Populate table
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for row_data in table_data:
            self._add_row(row_data)

        self.table.blockSignals(False)

        # Update headers to include both columns
        self.table.setHorizontalHeaderLabels(["Cat\u00e9gorie", "CA (Ar)", "Achats (Ar)"])

        self._refresh_totals()
        self._fit_to_content()

    def _add_row(self, row_data: dict) -> None:
        """Add a row to the table."""
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)

        # Category item (read-only)
        cat_item = QTableWidgetItem(str(row_data.get("categorie", "")))
        cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row_idx, 0, cat_item)

        # CA value item (editable)
        ca_value = int(row_data.get("ca_final_ttc", 0) or 0)
        ca_item = QTableWidgetItem(format_grouped_int(ca_value))
        ca_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        ca_item.setFlags(ca_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row_idx, 1, ca_item)

        # Achats value item (editable)
        achats_value = int(row_data.get("achats_ttc", 0) or 0)
        achats_item = QTableWidgetItem(format_grouped_int(achats_value))
        achats_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        achats_item.setFlags(achats_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row_idx, 2, achats_item)

        self.table.setRowHeight(row_idx, self.ROW_HEIGHT)

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value changes."""
        if col not in (1, 2):
            return
        item = self.table.item(row, col)
        if item is None:
            return
        value = max(0, parse_grouped_int(item.text(), default=0))
        self.table.blockSignals(True)
        item.setText(format_grouped_int(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.blockSignals(False)
        self._refresh_totals()

    def _refresh_totals(self):
        """Refresh the total displays."""
        total_ca = 0
        total_achats = 0
        for row in range(self.table.rowCount()):
            ca_item = self.table.item(row, 1)
            achats_item = self.table.item(row, 2)
            total_ca += max(
                0, parse_grouped_int("" if ca_item is None else ca_item.text(), default=0)
            )
            total_achats += max(
                0, parse_grouped_int("" if achats_item is None else achats_item.text(), default=0)
            )

        self.lbl_total_ca.setText(f"Total CA: {format_grouped_int(total_ca)}")
        self.lbl_total_achats.setText(f"Total Achats: {format_grouped_int(total_achats)}")

    def _toggle_edit_mode(self) -> None:
        """Toggle edit mode for the table."""
        self._edit_mode = not self._edit_mode
        self._btn_save.setEnabled(self._edit_mode)
        self._btn_edit.setText("Annuler" if self._edit_mode else "Modifier")

        # Make CA and Achats columns editable
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if self._edit_mode:
            flags |= Qt.ItemFlag.ItemIsEditable

        for row in range(self.table.rowCount()):
            ca_item = self.table.item(row, 1)
            achats_item = self.table.item(row, 2)
            if ca_item:
                ca_item.setFlags(flags)
            if achats_item:
                achats_item.setFlags(flags)

    def _save_changes(self) -> None:
        """Save changes to the database."""
        if not self._current_date:
            return

        saved = False
        with self.db_manager._connect() as conn:
            for row in range(self.table.rowCount()):
                cat_item = self.table.item(row, 0)
                ca_item = self.table.item(row, 1)
                achats_item = self.table.item(row, 2)

                if cat_item is None or ca_item is None or achats_item is None:
                    continue

                categorie = str(cat_item.text()).strip()
                if not categorie:
                    continue

                ca_value = parse_grouped_int(ca_item.text(), default=0)
                achats_value = parse_grouped_int(achats_item.text(), default=0)

                original = self._original_data.get(categorie)
                if (
                    original is not None
                    and original["ca_final_ttc"] == ca_value
                    and original["achats_ttc"] == achats_value
                ):
                    continue

                try:
                    # Get category_id from categories table
                    cat_id_row = conn.execute(
                        "SELECT id FROM categories WHERE nom = ?",
                        (categorie,),
                    ).fetchone()

                    if not cat_id_row:
                        continue

                    categorie_id = cat_id_row["id"]

                    # Check if row exists in analyse_journaliere_categories
                    existing = conn.execute(
                        "SELECT id FROM analyse_journaliere_categories WHERE jour = ? AND categorie_id = ?",
                        (self._current_date, categorie_id),
                    ).fetchone()

                    if existing:
                        conn.execute(
                            "UPDATE analyse_journaliere_categories SET ca = ?, achats = ? WHERE jour = ? AND categorie_id = ?",
                            (ca_value, achats_value, self._current_date, categorie_id),
                        )
                    else:
                        conn.execute(
                            "INSERT INTO analyse_journaliere_categories (jour, categorie_id, ca, achats) VALUES (?, ?, ?, ?)",
                            (self._current_date, categorie_id, ca_value, achats_value),
                        )
                    saved = True
                except Exception:
                    pass

            if saved:
                conn.commit()

        if saved:
            self._edit_mode = False
            self._btn_save.setEnabled(False)
            self._btn_edit.setText("Modifier")
            self._load_data()

    def _fit_to_content(self) -> None:
        """Size the dialog to fit all content without scrolling."""
        row_count = self.table.rowCount()
        if row_count == 0:
            return

        # Calculate width from table columns
        table_width = 0
        for col in range(self.table.columnCount()):
            table_width += self.table.columnWidth(col)
        # Add margins
        width = table_width + 40

        # Calculate height: rows + header + padding
        table_height = row_count * self.ROW_HEIGHT + self.HEADER_HEIGHT + 20
        # Total height includes date selector, separators, table, totals, buttons
        total_height = table_height + 180

        self.setFixedSize(width, total_height)
