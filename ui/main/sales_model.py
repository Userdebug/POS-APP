"""Qt model for the day's sales table."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PyQt6.QtGui import QColor, QIcon, QPainter
from PyQt6.QtWidgets import QApplication, QStyle


class SalesModel(QAbstractTableModel):
    """Expose a list of sales in tabular form."""

    _HEADERS = ("Heure", "Produit", "Qte")
    _trash_icon: QIcon | None = None

    def __init__(self, sales: list[dict[str, Any]] | None = None) -> None:
        super().__init__()
        self.sales = sales or []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self.sales)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        if parent.isValid():
            return 0
        return len(self._HEADERS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        sale = self.sales[index.row()]
        is_deleted = bool(sale.get("deleted", 0))

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return str(sale.get("heure", ""))
            if index.column() == 1:
                produit = str(sale.get("produit", ""))
                return f"{produit} (SUPPRIMÉ)" if is_deleted else produit
            if index.column() == 2:
                return str(sale.get("quantite", ""))

        if role == Qt.ItemDataRole.FontRole and is_deleted:
            font = self.createIndex(0, 0).data(Qt.ItemDataRole.FontRole)
            if font:
                font.setStrikeOut(True)
                return font

        if role == Qt.ItemDataRole.ForegroundRole and is_deleted:
            return QColor("#888b94")

        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> str | QIcon | None:  # noqa: N802
        # Vertical header (left selector column) - return trash icon
        if orientation == Qt.Orientation.Vertical:
            if role == Qt.ItemDataRole.DecorationRole:
                return self._get_trash_icon()
            if role == Qt.ItemDataRole.DisplayRole:
                return None  # Empty text, just show icon

        # Horizontal header (column labels)
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        if 0 <= section < len(self._HEADERS):
            return self._HEADERS[section]
        return None

    @classmethod
    def _get_trash_icon(cls) -> QIcon:
        """Get or create the reusable red trash icon."""
        if cls._trash_icon is not None:
            return cls._trash_icon

        style = QApplication.style()
        if not style:
            return QIcon()
        base_icon = style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)
        pixmap = base_icon.pixmap(16, 16)
        if pixmap.isNull():
            cls._trash_icon = base_icon
            return cls._trash_icon

        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), QColor("#c62828"))
        painter.end()
        cls._trash_icon = QIcon(pixmap)
        return cls._trash_icon
