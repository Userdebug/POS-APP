"""Composite widget displaying Oasis, Guest and Ventes Jour reports.

This widget encapsulates all report table UI and update logic, reducing
orchestration weight in the main window.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QSizePolicy,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_grouped_int
from presenters.reports_presenter import ReportsPresenter
from ui.dialogs.user_confirm_delete_dialog import UserConfirmDeleteDialog
from ui.main.sales_model import SalesModel

logger = logging.getLogger(__name__)

# ==================== Constants ====================

_COMPACT_TABLE_STYLE = (
    "QTableWidget {"
    "  border: none;"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
    " QTableWidget::item {"
    "  padding: 1px 4px;"
    "}"
    " QTableCornerButton {"
    "  border: none;"
    "  background-color: #1a1c23;"
    "}"
    " QHeaderView::section:horizontal {"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
    " QHeaderView::section:vertical {"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
)

_TABLE_VIEW_STYLE = (
    "QTableView {"
    "  border: none;"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
    " QHeaderView::section:horizontal {"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
    " QHeaderView::section:vertical {"
    "  background-color: #1a1c23;"
    "  color: #e5e7eb;"
    "  font-size: 8pt;"
    "}"
    " QTableCornerButton::section {"
    "  border: none;"
    "  background-color: #1a1c23;"
    "}"
)

_ROW_HEIGHT = 20


class ReportsWidget(QWidget):
    """Widget containing report tables (Oasis, Guest, Ventes Jour)."""

    def __init__(
        self,
        db_manager: Any,
        reports_presenter: ReportsPresenter,
        operateur_id: int | None,
        user_name: str,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize reports widget.

        Args:
            db_manager: DatabaseManager instance for data access.
            reports_presenter: ReportsPresenter for report data computation.
            operateur_id: ID of the current operator/user.
            user_name: Name of the current user.
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.reports_presenter = reports_presenter
        self._operateur_id = operateur_id
        self._user_name = user_name
        self._current_jour: str = ""

        self.table_oasis: QTableWidget | None = None
        self.table_guest: QTableWidget | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        """Build the UI layout with three report tables (Oasis, Guest, Ventes Jour)."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        layout.addWidget(self._build_ventes_group(), 2)
        layout.addWidget(self._build_oasis_group(), 1)
        layout.addWidget(self._build_guest_group(), 2)

    # ==================== Table Builders ====================

    def _build_oasis_group(self) -> QGroupBox:
        """Build Oasis report group box."""
        grp = QGroupBox("Oasis")
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(0)

        self.table_oasis = QTableWidget(0, 2)
        self.table_oasis.setHorizontalHeaderLabels(["Catégorie", "Total PRC"])
        self._configure_qtablewidget(self.table_oasis, stretch_col=0)
        lay.addWidget(self.table_oasis)
        return grp

    def _build_guest_group(self) -> QGroupBox:
        """Build Guest report group box."""
        grp = QGroupBox("Guest")
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(0)

        self.table_guest = QTableWidget(0, 3)
        self.table_guest.setHorizontalHeaderLabels(["Produit", "Qté", "Valeur"])
        self._configure_qtablewidget(self.table_guest, stretch_col=0)
        lay.addWidget(self.table_guest)
        return grp

    def _build_ventes_group(self) -> QGroupBox:
        """Build Ventes Jour report group box."""
        grp = QGroupBox("Ventes Jour")
        grp.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        lay = QVBoxLayout(grp)
        lay.setContentsMargins(2, 1, 2, 1)
        lay.setSpacing(0)

        self.sales_model = SalesModel([])
        self.liste_ventes_table = QTableView()
        self.liste_ventes_table.setModel(self.sales_model)
        self.liste_ventes_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.liste_ventes_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.liste_ventes_table.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        vertical_header = self.liste_ventes_table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(True)
            vertical_header.setDefaultSectionSize(_ROW_HEIGHT)
            vertical_header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            vertical_header.sectionClicked.connect(self._on_sale_row_delete_clicked)
            vertical_header.setStyleSheet(
                "QHeaderView::section:vertical {"
                "  background-color: #1a1c23; color: #e5e7eb; font-size: 8pt;"
                "}"
            )

        horizontal_header = self.liste_ventes_table.horizontalHeader()
        if horizontal_header:
            horizontal_header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            horizontal_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            horizontal_header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            horizontal_header.setStyleSheet(
                "QHeaderView::section:horizontal {"
                "  background-color: #1a1c23; color: #e5e7eb; font-size: 8pt;"
                "}"
            )

        self.liste_ventes_table.setStyleSheet(_TABLE_VIEW_STYLE)
        lay.addWidget(self.liste_ventes_table)
        return grp

    # ==================== Shared Config ====================

    def _configure_qtablewidget(self, table: QTableWidget, stretch_col: int) -> None:
        """Apply compact dense configuration to a QTableWidget.

        Args:
            table: The QTableWidget to configure.
            stretch_col: Column index that should stretch.
        """
        vertical_header = table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)
            vertical_header.setDefaultSectionSize(_ROW_HEIGHT)
            vertical_header.setMinimumSectionSize(_ROW_HEIGHT)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        table.setWordWrap(False)

        header = table.horizontalHeader()
        if header:
            for col in range(table.columnCount()):
                if col == stretch_col:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
                else:
                    header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
            header.setStyleSheet(
                "QHeaderView::section:horizontal {"
                "  background-color: #1a1c23; color: #e5e7eb; font-size: 8pt;"
                "}"
            )

        vertical_header = table.verticalHeader()
        if vertical_header:
            vertical_header.setStyleSheet(
                "QHeaderView::section:vertical {"
                "  background-color: #1a1c23; color: #e5e7eb; font-size: 8pt;"
                "}"
            )

        table.setStyleSheet(_COMPACT_TABLE_STYLE)

    # ==================== Public API ====================

    def update_reports(self, jour: str | date) -> None:
        """Update all report tables for the given day.

        Args:
            jour: Date in ISO format (YYYY-MM-DD) or date object.
        """
        jour_str = jour if isinstance(jour, str) else jour.isoformat()
        self._current_jour = jour_str
        self._update_oasis_report(jour_str)
        self._update_guest_report(jour_str)
        self._update_ventes_jour_report(jour_str)

    def update_sales_history(self, sales: list[dict[str, Any]]) -> None:
        """Update Ventes Jour sales history table.

        Args:
            sales: List of sale records.
        """
        self.sales_model.beginResetModel()
        self.sales_model.sales = sales
        self.sales_model.endResetModel()

    # ==================== Update Methods ====================

    def _update_oasis_report(self, jour: str) -> None:
        """Update Oasis report table."""
        if self.table_oasis is None:
            return

        try:
            oasis_data = self.db_manager.get_oasis_stats(jour)
        except Exception as exc:
            logger.warning("Failed to get Oasis stats: %s", exc)
            oasis_data = []

        self.table_oasis.setRowCount(0)
        for row_data in oasis_data:
            row = self.table_oasis.rowCount()
            self.table_oasis.insertRow(row)
            self.table_oasis.setItem(row, 0, QTableWidgetItem(str(row_data.get("categorie", ""))))
            val_item = QTableWidgetItem(format_grouped_int(int(row_data.get("total_prc", 0) or 0)))
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_oasis.setItem(row, 1, val_item)
        # Ensure vertical header stays hidden after populating
        self.table_oasis.verticalHeader().setVisible(False)  # type: ignore[union-attr]

    def _update_ventes_jour_report(self, jour: str) -> None:
        """Update Ventes Jour report table with daily sales data."""
        self._current_jour = jour
        try:
            sales = self.db_manager.list_daily_sales(jour)
        except Exception as exc:
            logger.warning("Failed to get daily sales: %s", exc)
            sales = []

        self.sales_model.beginResetModel()
        self.sales_model.sales = sales
        self.sales_model.endResetModel()

    def _update_guest_report(self, jour: str) -> None:
        """Update Guest report table with details and subtotals."""
        if self.table_guest is None:
            return

        guest_details, guest_subtotals = self.reports_presenter.get_guest_report(jour)
        self.table_guest.setRowCount(0)

        current_cat = None
        cat_total_val = 0

        for row_data in guest_details:
            cat = row_data.categorie
            if current_cat is not None and cat != current_cat:
                self._add_guest_subtotal_row(current_cat, cat_total_val)
                cat_total_val = 0

            current_cat = cat
            row = self.table_guest.rowCount()
            self.table_guest.insertRow(row)
            self.table_guest.setItem(row, 0, QTableWidgetItem(str(row_data.produit)))

            qte_item = QTableWidgetItem(str(row_data.qte))
            qte_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_guest.setItem(row, 1, qte_item)

            val = int(row_data.val)
            cat_total_val += val
            val_item = QTableWidgetItem(format_grouped_int(val))
            val_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_guest.setItem(row, 2, val_item)

        if current_cat is not None:
            self._add_guest_subtotal_row(current_cat, cat_total_val)

    def _add_guest_subtotal_row(self, category: str, total: int) -> None:
        """Add a subtotal row to the Guest table."""
        if self.table_guest is None:
            return

        row = self.table_guest.rowCount()
        self.table_guest.insertRow(row)
        self.table_guest.setItem(
            row,
            0,
            self._styled_item(
                f"Total {category}",
                bg=QColor("#2d3038"),
                fg=QColor("#e5e7eb"),
                bold=True,
            ),
        )
        self.table_guest.setSpan(row, 0, 1, 2)
        self.table_guest.setItem(
            row,
            2,
            self._styled_item(
                format_grouped_int(total),
                bg=QColor("#2d3038"),
                fg=QColor("#e5e7eb"),
                bold=True,
                align_right=True,
            ),
        )

    # ==================== Handlers ====================

    def _on_sale_row_delete_clicked(self, row: int) -> None:
        """Handle click on vertical header to delete a sale.

        Args:
            row: Row index that was clicked.
        """
        if row < 0 or row >= len(self.sales_model.sales):
            return

        sale_info = self.sales_model.sales[row]
        vente_id = sale_info.get("id")
        if not vente_id:
            logger.warning("No sale ID found for row %d", row)
            return

        if self._operateur_id is None:
            logger.warning("Cannot delete sale: no operator ID available")
            return

        dialog = UserConfirmDeleteDialog(
            self, sale_info, self.db_manager, self._operateur_id, self._user_name
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        if self.db_manager.delete_sale(vente_id, self._operateur_id):
            logger.info("Sale %s deleted by admin", vente_id)
            if self._current_jour:
                self._update_ventes_jour_report(self._current_jour)
                # Recompute live CA and refresh Tsf to reflect deletion
                self.db_manager.daily_tracking.sync_unclosed_day(self._current_jour)
        else:
            logger.warning("Failed to delete sale %s", vente_id)

    # ==================== Utilities ====================

    def _styled_item(
        self,
        text: str,
        *,
        bg: QColor | Qt.GlobalColor | None = None,
        fg: QColor | Qt.GlobalColor | None = None,
        bold: bool = False,
        align_right: bool = False,
    ) -> QTableWidgetItem:
        """Create a styled table widget item.

        Args:
            text: Display text.
            bg: Background color.
            fg: Foreground color.
            bold: Whether to use bold font.
            align_right: Whether to align text to the right.

        Returns:
            QTableWidgetItem with applied styling.
        """
        item = QTableWidgetItem(text)
        if bg is not None:
            item.setBackground(bg)
        if fg is not None:
            item.setForeground(fg)
        if bold:
            font = item.font()
            font.setBold(True)
            item.setFont(font)
        if align_right:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item
