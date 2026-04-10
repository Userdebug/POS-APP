"""Base table mixin for common QTableWidget setup patterns."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem


class BaseTableMixin:
    """Mixin providing common QTableWidget setup methods."""

    @staticmethod
    def setup_readonly_table(
        table: QTableWidget,
        headers: list[str],
        rows: int = 0,
    ) -> None:
        """Configure a table for read-only display.

        Args:
            table: The QTableWidget to configure
            headers: List of column header labels
            rows: Initial number of rows (default 0)
        """
        if rows > 0:
            table.setRowCount(rows)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

    @staticmethod
    def create_styled_item(text: str, align_right: bool = False) -> QTableWidgetItem:
        """Create a styled QTableWidgetItem.

        Args:
            text: Text content
            align_right: Whether to align text to the right

        Returns:
            Configured QTableWidgetItem
        """
        item = QTableWidgetItem(str(text))
        if align_right:
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        else:
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
