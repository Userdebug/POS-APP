"""Dialog for displaying daily purchases (achats) resume.

Shows the list of invoices/receptions for the current day with totals.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.database import DatabaseManager
from core.formatters import format_grouped_int
from styles.dialog_styles import (
    DIALOG_BASE,
    HEADER_LABEL,
    REPORT_TABLE,
    SECONDARY_BUTTON,
)


class AchatsResumeDialog(QDialog):
    """Dialog displaying the daily purchases (invoices) summary."""

    def __init__(self, parent: QWidget | None, db_manager: DatabaseManager, jour: str) -> None:
        """Initialize the daily purchases resume dialog.

        Args:
            parent: Parent widget.
            db_manager: Database manager for data access.
            jour: Date in ISO format (YYYY-MM-DD).
        """
        super().__init__(parent)
        self.setWindowTitle(f"Resume des achats - {jour}")
        self.setMinimumSize(600, 450)
        self.resize(650, 500)

        self._db_manager = db_manager
        self._jour = jour

        self.setStyleSheet(DIALOG_BASE)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # Title
        title = QLabel(f"Resume des achats - {jour}")
        title.setStyleSheet(HEADER_LABEL)
        root.addWidget(title)

        # Invoices table
        self.table_factures = QTableWidget(0, 4)
        self.table_factures.setHorizontalHeaderLabels(
            ["N° Facture", "Fournisseur", "Total TTC", "Statut"]
        )
        self.table_factures.setStyleSheet(REPORT_TABLE)
        self.table_factures.setAlternatingRowColors(True)
        self.table_factures.verticalHeader().setVisible(False)
        self.table_factures.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_factures.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        root.addWidget(self.table_factures)

        # Total
        self.lbl_total = QLabel("Total: 0 Ar")
        self.lbl_total.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #2563eb; border-radius: 6px; padding: 6px 12px;"
        )
        root.addWidget(self.lbl_total)

        # Buttons
        button_container = QHBoxLayout()
        button_container.setSpacing(12)

        button_container.addStretch(1)

        btn_fermer = QPushButton("Fermer")
        btn_fermer.setStyleSheet(SECONDARY_BUTTON)
        btn_fermer.setMinimumSize(120, 42)
        btn_fermer.clicked.connect(self.reject)
        button_container.addWidget(btn_fermer)

        root.addLayout(button_container)

        # Populate table
        self._populate()

    def _populate(self) -> None:
        """Populate the invoices table from database."""
        try:
            rows = self._db_manager.list_daily_achats(self._jour)
        except Exception:
            rows = []

        self.table_factures.setRowCount(len(rows))
        total = 0

        for i, row in enumerate(rows):
            num_facture = str(row.get("numero_facture", "-"))
            fournisseur = str(row.get("fournisseur", "-"))
            total_ttc = int(row.get("total_ttc", 0) or 0)
            statut = str(row.get("statut", "-"))

            total += total_ttc

            self.table_factures.setItem(i, 0, QTableWidgetItem(num_facture))
            self.table_factures.setItem(i, 1, QTableWidgetItem(fournisseur))

            item_ttc = QTableWidgetItem(format_grouped_int(total_ttc))
            item_ttc.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_factures.setItem(i, 2, item_ttc)

            self.table_factures.setItem(i, 3, QTableWidgetItem(statut))

        self.lbl_total.setText(f"Total: {format_grouped_int(total)} Ar")
