"""NFR Report Dialog - Rapport des marges par catégorie (NFR style)."""

import logging
from datetime import datetime
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtPrintSupport import QPrinter
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

from core.database import DatabaseManager
from services.analyse_journaliere_service import AnalyseJournaliereService
from ui.dialogs.report_table_dialog import TableReportDialog


class NFRReportDialog(TableReportDialog):
    """Dialog for displaying NFR (Marges par Catégorie) report with month/year selection."""

    data_loaded = pyqtSignal(list)

    def __init__(self, parent: QWidget | None = None, db_manager: DatabaseManager | None = None):
        # Column headers for the standard table view
        headers = [
            "Catégorie",
            "CA HT",
            "CA TTC",
        ]
        super().__init__(
            title="Rapport NFR (Chiffre d'Affaires Mensuel)",
            headers=headers,
            parent=parent,
            allow_import=True,
        )

        self.db_manager = db_manager or DatabaseManager()
        self.analyse_service = AnalyseJournaliereService(self.db_manager)

        # Store raw data for PDF export
        self._report_data: list[dict[str, Any]] = []

        # Setup month/year selection controls
        self._setup_month_year_controls()

        # Setup the NFR-style table (marges par catégorie)
        self._setup_nfr_table()

        # Load initial data
        self._load_data()

    def _setup_month_year_controls(self) -> None:
        """Setup month and year selection controls."""
        # Month selection
        month_label = QLabel("Mois:")
        self.month_spin = QSpinBox()
        self.month_spin.setMinimum(1)
        self.month_spin.setMaximum(12)
        self.month_spin.setValue(datetime.now().month)

        # Year selection
        year_label = QLabel("Année:")
        self.year_spin = QSpinBox()
        self.year_spin.setMinimum(2020)
        self.year_spin.setMaximum(2100)
        self.year_spin.setValue(datetime.now().year)

        # Refresh button
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.clicked.connect(self._load_data)

        # PDF Export button
        btn_pdf = QPushButton("Imprimer PDF")
        btn_pdf.clicked.connect(self._export_pdf)

        # Add controls to layout
        self.controls_layout.addWidget(month_label)
        self.controls_layout.addWidget(self.month_spin)
        self.controls_layout.addWidget(year_label)
        self.controls_layout.addWidget(self.year_spin)
        self.controls_layout.addWidget(btn_refresh)
        self.controls_layout.addWidget(btn_pdf)
        self.controls_layout.addStretch()

    def _setup_nfr_table(self) -> None:
        """Setup the NFR-style table for marges par catégorie display."""
        # This is an alternative display mode showing:
        # - First row: "Date début" (user can select a start date)
        # - Second+ rows: Each category as a row with its margin data
        # - Last column: Current date as "date fin"

        # Remove the standard table from parent layout
        root = self.layout()
        if root and self.table:
            root.removeWidget(self.table)
            self.table.hide()

        # Create NFR-style table
        # Structure:
        # - Row 0: Date selection (start date input)
        # - Row 1+: Category data rows
        # - Last column: End date (current date)

        self.nfr_table = QTableWidget()
        self.nfr_table.setMinimumHeight(400)
        self.nfr_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.nfr_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        # Insert after controls layout
        root.insertWidget(1, self.nfr_table, 1)

    def _load_data(self) -> None:
        """Load NFR report data based on selected month/year."""
        year = self.year_spin.value()
        month = self.month_spin.value()

        try:
            data = self.analyse_service.get_nfr_report(year, month)
            self._report_data = data
            self._populate_nfr_table(data, year, month)
            self.data_loaded.emit(data)
        except Exception as e:
            logging.getLogger(__name__).warning("Failed to load NFR report: %s", e)
            self._report_data = []
            self._populate_nfr_table([], year, month)

    def _populate_nfr_table(self, data: list[dict[str, Any]], year: int, month: int) -> None:
        """Populate the NFR-style table with margin data.

        Structure:
        - Column 0: Labels (Date début, Category names, Date fin)
        - Column 1+: Each category as a separate column with its margin value
        """
        if not data:
            # Clear table if no data
            self.nfr_table.setRowCount(0)
            self.nfr_table.setColumnCount(0)
            return

        # Number of categories
        num_categories = len(data)

        # Table structure:
        # - Row 0: Headers (Category names)
        # - Row 1: Date début label + input field in first cell
        # - Row 2+: Each category's margin data
        # - Last row: Date fin (current date)

        # Create columns: Label column + one column per category
        self.nfr_table.setColumnCount(num_categories + 1)
        self.nfr_table.setRowCount(3)  # Header row, Data row, Date fin row

        # Set header labels (category names)
        category_names = [item.get("categorie", "") for item in data]
        headers = [""] + category_names  # Empty first column for row labels
        self.nfr_table.setHorizontalHeaderLabels(headers)

        # Row 0: Header row - Category names displayed as first column
        # We'll use the vertical header for row labels instead

        # Set vertical headers
        self.nfr_table.setVerticalHeaderLabels(["Catégories", "CA TTC (€)", "Date fin"])

        # Row 1: Category columns with category names
        for col_idx, item in enumerate(data):
            cat_name = item.get("categorie", "")
            cat_item = QTableWidgetItem(cat_name)
            cat_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.nfr_table.setItem(0, col_idx + 1, cat_item)

        # Row 2: CA TTC values for each category
        for col_idx, item in enumerate(data):
            ca_ttc = item.get("ca_ttc", 0)
            ca_item = QTableWidgetItem(f"{ca_ttc:,} €")
            ca_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.nfr_table.setItem(1, col_idx + 1, ca_item)

        # Row 3 (index 2): Date fin - current date in last column
        current_date = datetime.now().strftime("%d/%m/%y")
        date_fin_item = QTableWidgetItem(current_date)
        date_fin_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.nfr_table.setItem(2, num_categories, date_fin_item)

        # Also populate the standard table for CSV import compatibility
        self._populate_standard_table(data)

    def _populate_standard_table(self, data: list[dict[str, Any]]) -> None:
        """Populate the standard table view (for CSV import compatibility)."""
        if not data:
            self.set_rows([])
            return

        rows = []
        for item in data:
            row = [
                item.get("categorie", ""),
                f"{item.get('ca_ht', 0):,}",
                f"{item.get('ca_ttc', 0):,}",
            ]
            rows.append(row)

        self.set_rows(rows)

    def _export_pdf(self) -> None:
        """Export the NFR report to PDF."""
        if not self._report_data:
            QMessageBox.warning(
                self,
                "Aucune donnée",
                "Aucune donnée à exporter. Veuillez d'abord charger les données.",
            )
            return

        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog

            # Create printer
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setPageSize(QPrinter.PageSize.A4)
            printer.setOrientation(QPrinter.Orientation.Landscape)

            # Create preview dialog
            preview = QPrintPreviewDialog(printer, self)
            preview.setWindowTitle("Aperçu NFR - Marges par Catégorie")
            preview.paintRequested.connect(lambda p: self._render_pdf(p))
            preview.exec()
        except Exception as e:
            logging.getLogger(__name__).warning("PDF export failed: %s", e)
            QMessageBox.critical(
                self,
                "Erreur d'export",
                f"Échec de l'export PDF: {str(e)}",
            )

    def _render_pdf(self, printer: QPrinter) -> None:
        """Render the report to the printer."""

        painter = QPainter(printer)
        painter.setPen(Qt.GlobalColor.black)

        # Get page margins
        margin = 50
        page_width = printer.pageRect(QPrinter.Unit.Point).width()

        # Title
        year = self.year_spin.value()
        month = self.month_spin.value()
        title = f"NFR - Chiffre d'Affaires Mensuel - {month:02d}/{year}"
        painter.drawText(margin, margin, title)

        # Draw table header
        y_pos = margin + 40
        col_width = (page_width - 2 * margin) / (len(self._report_data) + 1)

        # Header row
        painter.drawText(margin, y_pos, "Catégorie")
        x_pos = margin + col_width
        for item in self._report_data:
            painter.drawText(int(x_pos), y_pos, item.get("categorie", ""))
            x_pos += col_width

        # Draw line
        y_pos += 10
        painter.drawLine(margin, y_pos, page_width - margin, y_pos)

        # Data row - CA TTC
        y_pos += 20
        painter.drawText(margin, y_pos, "CA TTC (€)")
        x_pos = margin + col_width
        for item in self._report_data:
            ca_ttc = item.get("ca_ttc", 0)
            painter.drawText(int(x_pos), y_pos, f"{ca_ttc:,} €")
            x_pos += col_width

        # Date fin
        y_pos += 30
        current_date = datetime.now().strftime("%d/%m/%y")
        painter.drawText(margin, y_pos, "Date fin:")
        painter.drawText(int(margin + col_width), y_pos, current_date)

        painter.end()
