"""SF (Stock Flux) margin table widget for main window."""

from __future__ import annotations

from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import DatabaseManager
from presenters.reports_presenter import ReportsPresenter, SFTableData


class SFTableWidget(QWidget):
    """2-row table displaying SF margin percentages by category.

    Row 0 (header): Categories from SF report
    Row 1 (data): Margin percentages with color coding
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        reports_presenter: ReportsPresenter,
        parent: QWidget | None = None,
    ):
        """Initialize SF margin table widget.

        Args:
            db_manager: Database manager for data access.
            reports_presenter: Reports presenter for business logic.
            parent: Parent widget.
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.reports_presenter = reports_presenter

        # Default date: 1 month ago
        self._date_debut = QDate.currentDate().addMonths(-1)
        self._date_fin = QDate.currentDate()

        # Set compact size
        self.setMaximumHeight(70)  # Compact height to fit content
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._build_ui()
        self._refresh_table()

    # ==================== UI ==================== #

    def _build_ui(self) -> None:
        """Build the table UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Main container with horizontal layout for date picker + table
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        # Date picker for date debut
        self._date_edit = QDateEdit(self._date_debut)
        self._date_edit.setCalendarPopup(True)
        self._date_edit.setDisplayFormat("dd/MM/yyyy")
        self._date_edit.setFixedWidth(100)
        self._date_edit.setStyleSheet("""
            QDateEdit {
                background-color: #1f2937;
                color: #e5e7eb;
                border: 1px solid #374151;
                padding: 4px 8px;
                font-size: 10px;
            }
            QDateEdit::drop-down {
                width: 16px;
                border: none;
            }
            QDateEdit::down-arrow {
                image: none;
                border-left: 3px solid transparent;
                border-right: 3px solid transparent;
                border-top: 5px solid #9ca3af;
            }
        """)
        self._date_edit.dateChanged.connect(self._on_date_changed)
        container_layout.addWidget(self._date_edit, 0)

        # Table widget
        self._table = QTableWidget()
        self._table.setRowCount(2)
        self._table.setColumnCount(1)  # Will expand based on data
        self._table.horizontalHeader().hide()  # type: ignore
        self._table.verticalHeader().hide()  # type: ignore
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setShowGrid(True)
        self._table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._table.setMaximumHeight(65)  # Compact height for 2 rows
        self._table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #374151;
                background-color: #1f2937;
            }
            QTableWidget::item {
                border: 1px solid #374151;
                background-color: #1f2937;
                color: #e5e7eb;
                padding: 4px 8px;
            }
            QTableWidget::item:selected {
                background-color: #374151;
                color: #ffffff;
            }
        """)
        container_layout.addWidget(self._table, 1)

        layout.addWidget(container)

    # ==================== Signals ==================== #

    def _on_date_changed(self, date: QDate) -> None:
        """Handle date change and refresh table."""
        self._date_debut = date
        self._refresh_table()

    # ---------------- Data ---------------- #

    # ==================== Data ==================== #

    def _refresh_table(self) -> None:
        """Refresh table with SF data for selected date range."""
        try:
            date_debut = self._date_debut.toString("yyyy-MM-dd")
            date_fin = self._date_fin.toString("yyyy-MM-dd")

            sf_data = self.reports_presenter.get_sf_table_data(date_debut, date_fin)
            self._populate_table(sf_data)

        except Exception:
            # On error, show empty table with error message
            self._table.clearContents()
            self._table.setColumnCount(2)
            self._table.setItem(0, 1, self._item("Erreur", bold=True))

    def _populate_table(self, sf_data: SFTableData) -> None:
        """Populate table with SF data.

        Args:
            sf_data: SF table data with categories and margins.
        """
        categories = sf_data.categories
        data_by_category = sf_data.data_by_category

        if not categories:
            self._table.clearContents()
            self._table.setColumnCount(2)
            self._table.setItem(0, 1, self._item("Pas de donnees", bold=True))
            self._table.setSpan(0, 1, 2, 1)
            return

        # Set table dimensions
        col_count = len(categories) + 1  # +1 for date column
        self._table.setColumnCount(col_count)
        self._table.setRowCount(2)

        # Date picker spans both rows in column 0
        self._table.setSpan(0, 0, 2, 1)
        self._table.setCellWidget(0, 0, self._date_edit)

        # Row 0: Category headers
        for col, cat in enumerate(categories, 1):
            self._table.setItem(0, col, self._item(cat, bold=True))

        # Row 1: Margin percentages
        for col, cat in enumerate(categories, 1):
            item_data = data_by_category.get(cat)
            margin_pct = self._calculate_margin(item_data)
            margin_text = self._format_margin(margin_pct)

            margin_item = self._item(margin_text)
            bg_color = self._margin_bg_color(margin_pct)
            if bg_color:
                margin_item.setBackground(QBrush(bg_color))

            self._table.setItem(1, col, margin_item)

        # Column sizing
        h_header = self._table.horizontalHeader()  # type: ignore
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # type: ignore
        self._table.setColumnWidth(0, 110)
        for i in range(1, col_count):
            h_header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)  # type: ignore

    # ==================== Helpers ==================== #

    @staticmethod
    def _calculate_margin(item: dict | None) -> float:
        """Calculate margin percentage from SF data item.

        Args:
            item: Dictionary with 'marge_ttc' and 'vente_theo_ttc' keys.

        Returns:
            Margin percentage as float.
        """
        if item is None:
            return 0.0
        marge = float(item.get("marge_ttc", 0) or 0)
        vente_theo = float(item.get("vente_theo_ttc", 0) or 0)
        if vente_theo <= 0:
            return 0.0
        return (marge / vente_theo) * 100

    @staticmethod
    def _format_margin(pct: float) -> str:
        """Format margin percentage for display.

        Args:
            pct: Margin percentage.

        Returns:
            Formatted string (e.g., "25.5%").
        """
        return f"{pct:.1f}%"

    @staticmethod
    def _margin_bg_color(pct: float) -> QColor | None:
        """Get background color based on margin percentage.

        Args:
            pct: Margin percentage.

        Returns:
            QColor for background, or None for default.
        """
        if pct < 15:
            return QColor("#fca5a5")  # Red
        if pct < 20:
            return QColor("#93c5fd")  # Blue
        return QColor("#86efac")  # Green

    @staticmethod
    def _item(text: str, bold: bool = False) -> QTableWidgetItem:
        """Create table item with proper styling.

        Args:
            text: Item text.
            bold: Whether to use bold font.

        Returns:
            Styled QTableWidgetItem.
        """
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        font = QFont()
        font.setPointSize(10)
        if bold:
            font.setBold(True)
        item.setFont(font)

        return item
