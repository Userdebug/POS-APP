"""Dialog for cash closure with editable table by category."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
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


class CashClosureDialog(QDialog):
    """Dialog for entering cash closure amounts by category."""

    ROW_HEIGHT = 32
    HEADER_HEIGHT = 34
    BUTTON_HEIGHT = 36
    DIALOG_PADDING = 20

    def __init__(self, parent: QWidget | None, jour: str, db_manager=None):
        super().__init__(parent)

        # Format title: "Clôture du dd/mm/yy" from ISO date
        date_display = self._format_date_short(jour)
        self.setWindowTitle(f"Cl\u00f4ture du {date_display}")
        self.setStyleSheet(DIALOG_BASE)

        self._db_manager = db_manager

        root = QVBoxLayout(self)
        root.setContentsMargins(self.DIALOG_PADDING, 16, self.DIALOG_PADDING, 16)
        root.setSpacing(10)

        # ==================== Table ====================
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Cat\u00e9gorie", "CA TTC"])
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

        # Disable vertical scrollbar to prevent scrolling
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        header_view = self.table.horizontalHeader()
        if header_view is not None:
            header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
            header_view.resizeSection(1, 150)
            header_view.setFixedHeight(self.HEADER_HEIGHT)

        root.addWidget(self.table)

        # ==================== Separator ====================
        root.addWidget(self._make_separator())

        # ==================== Total ====================
        total_container = QHBoxLayout()
        total_container.addStretch()
        self.lbl_total = QLabel("Total: 0")
        self.lbl_total.setStyleSheet(
            f"font-size: 18px; font-weight: 700; color: {TOKENS['total_caisse_text']};"
            f"background-color: {TOKENS['total_caisse_bg']};"
            f"border: 2px solid {TOKENS['total_caisse_border']};"
            "border-radius: 8px; padding: 8px 18px;"
        )
        self.lbl_total.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        total_container.addWidget(self.lbl_total)
        total_container.addStretch()
        root.addLayout(total_container)

        # ==================== Buttons ====================
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        button_layout.addStretch()

        self._btn_cancel = QPushButton("Annuler")
        self._btn_cancel.setStyleSheet(SECONDARY_BUTTON)
        self._btn_cancel.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_cancel.setFixedWidth(100)
        self._btn_cancel.setFixedHeight(self.BUTTON_HEIGHT)
        self._btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(self._btn_cancel)

        self._btn_ok = QPushButton("Valider")
        self._btn_ok.setStyleSheet(PRIMARY_BUTTON)
        self._btn_ok.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._btn_ok.setFixedWidth(100)
        self._btn_ok.setFixedHeight(self.BUTTON_HEIGHT)
        self._btn_ok.clicked.connect(self.accept)
        button_layout.addWidget(self._btn_ok)

        button_layout.addStretch()

        root.addLayout(button_layout)

        self.table.cellChanged.connect(self._on_cell_changed)

        # Load sous-categories from database
        self._load_sous_categories()

        self._refresh_total()
        self._fit_to_content()
        self._ensure_no_scroll()

    def _ensure_no_scroll(self) -> None:
        """Ensure the table displays all rows without scrollbar."""
        row_count = self.table.rowCount()
        if row_count == 0:
            return
        # Calculate minimum height to fit all rows + header
        header_height = self.HEADER_HEIGHT
        rows_height = row_count * self.ROW_HEIGHT
        min_height = header_height + rows_height + 4
        self.table.setMinimumHeight(min_height)

    def _load_sous_categories(self) -> None:
        """Load sous-categories from database for Catégorie 1."""
        if self._db_manager is None:
            return

        try:
            with self._db_manager._connect() as conn:
                query = """
                    SELECT c.nom AS sous_categorie
                    FROM categories c
                    INNER JOIN categories parent ON c.parent_id = parent.id
                    WHERE parent.nom = ?
                    ORDER BY c.nom
                """
                rows = conn.execute(query, (CATEGORY_1_NAME,)).fetchall()
                sous_categories = [str(row["sous_categorie"]) for row in rows]

                # Add rows with initial value 0
                self.table.blockSignals(True)
                for cat in sous_categories:
                    self._add_row(self.table.rowCount(), {"categorie": cat, "ca_ttc_final": 0})
                self.table.blockSignals(False)
        except Exception:
            pass

    @staticmethod
    def _format_date_short(iso_date: str) -> str:
        """Convert ISO date (yyyy-MM-dd) to short format (dd/MM/yy).

        Args:
            iso_date: Date string in ISO format.

        Returns:
            Formatted date string or original if parsing fails.
        """
        try:
            parts = iso_date.split("-")
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0][2:]}"
        except (IndexError, ValueError):
            pass
        return iso_date

    def _fit_to_content(self) -> None:
        """Size the dialog to fit all content without scrolling."""
        row_count = self.table.rowCount()
        # Calculate table height: rows only
        table_height = row_count * self.ROW_HEIGHT + 4

        # Calculate total dialog height
        # table + total ~60 + buttons ~50 + margins ~30
        total_height = table_height + 140

        # Minimum width
        if self.width() < 320:
            self.setMinimumWidth(320)

        self.resize(320, max(total_height, 200))

    @staticmethod
    def _make_separator() -> QFrame:
        """Create a styled horizontal separator.

        Returns:
            Configured QFrame separator.
        """
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(SEPARATOR)
        sep.setFixedHeight(1)
        sep.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return sep

    def _add_row(self, row_idx: int, row_data: dict) -> None:
        """Add a row to the table with proper formatting.

        Args:
            row_idx: Row index to insert at.
            row_data: Dictionary with 'categorie' and 'ca_ttc_final' keys.
        """
        self.table.insertRow(row_idx)

        # Category item (read-only)
        cat_item = QTableWidgetItem(str(row_data.get("categorie", "")))
        cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row_idx, 0, cat_item)

        # Value item (editable)
        value = int(row_data.get("ca_ttc_final", 0) or 0)
        value_item = QTableWidgetItem(format_grouped_int(value))
        value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row_idx, 1, value_item)

        self.table.setRowHeight(row_idx, self.ROW_HEIGHT)

    def _on_cell_changed(self, row: int, col: int):
        """Handle cell value changes."""
        if col != 1:
            return
        item = self.table.item(row, col)
        if item is None:
            return
        value = max(0, parse_grouped_int(item.text(), default=0))
        self.table.blockSignals(True)
        item.setText(format_grouped_int(value))
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.blockSignals(False)
        self._refresh_total()

    def _refresh_total(self):
        """Refresh the total display."""
        total = 0
        for row in range(self.table.rowCount()):
            value_item = self.table.item(row, 1)
            total += max(
                0, parse_grouped_int("" if value_item is None else value_item.text(), default=0)
            )
        self.lbl_total.setText(f"Total: {format_grouped_int(total)}")

    def values(self) -> list[dict]:
        """Get the current values from the table.

        Returns:
            List of dictionaries with 'categorie' and 'ca_ttc_final' keys.
        """
        data: list[dict] = []
        for row in range(self.table.rowCount()):
            cat_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            categorie = "" if cat_item is None else str(cat_item.text()).strip()
            if not categorie:
                continue
            data.append(
                {
                    "categorie": categorie,
                    "ca_ttc_final": max(
                        0,
                        parse_grouped_int(
                            "" if value_item is None else value_item.text(), default=0
                        ),
                    ),
                }
            )
        return data
