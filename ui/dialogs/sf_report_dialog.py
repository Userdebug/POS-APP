"""SF Report Dialog - Rapport de Stock Flux sur une période."""

from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QPageSize, QPainter
from PyQt6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (
    QDateEdit,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from core.database import DatabaseManager
from services.analyse_journaliere_service import AnalyseJournaliereService
from ui.dialogs.report_table_dialog import TableReportDialog


class SFReportDialog(TableReportDialog):
    """Dialog for displaying SF (Stock Flux) report with date range selection."""

    _SF_DATE_DEBUT_PARAM_KEY = "SF_DATE_DEBUT_DEFAULT"

    data_loaded = pyqtSignal(list)

    def __init__(
        self,
        parent: QWidget | None = None,
        db_manager: DatabaseManager | None = None,
        start_date: QDate | None = None,
        end_date: QDate | None = None,
    ):
        # Column headers: category, SI from date debut, purchases, SF from date fin, demarque
        headers = [
            "Catégorie",
            "SI (début) HT",
            "Achats HT",
            "SF (fin) HT",
            "Démarque HT",
        ]
        super().__init__(
            title="Rapport SF (Stock Flux)",
            headers=headers,
            parent=parent,
            allow_import=False,
        )

        self.db_manager = db_manager or DatabaseManager()
        self.analyse_service = AnalyseJournaliereService(self.db_manager)
        self._current_rows: list = []  # Store data for import/print

        self.start_date = start_date or QDate.currentDate().addMonths(-1)
        self.end_date = end_date or QDate.currentDate()

        # Validate dates
        if self.start_date >= self.end_date:
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self, "Erreur", "La date de début doit être antérieure à la date de fin."
            )
            return

        # Setup date range controls
        self._setup_date_controls()

        # Load initial data
        self._load_data()

    def _setup_date_controls(self) -> None:
        """Setup date range selection controls."""
        # Date début
        date_debut_label = QLabel("Date début:")
        self.date_debut = QDateEdit()
        self.date_debut.setCalendarPopup(True)
        self.date_debut.setDisplayFormat("yyyy-MM-dd")
        self.date_debut.setDate(self.start_date)
        self.date_debut.setReadOnly(True)  # Make readonly since set externally

        # Date fin
        date_fin_label = QLabel("Date fin:")
        self.date_fin = QDateEdit()
        self.date_fin.setCalendarPopup(True)
        self.date_fin.setDisplayFormat("yyyy-MM-dd")
        self.date_fin.setDate(self.end_date)
        self.date_fin.setReadOnly(True)  # Make readonly since set to current date

        # Actualiser button
        btn_refresh = QPushButton("Actualiser")
        btn_refresh.clicked.connect(self._load_data)

        # Import button
        btn_import = QPushButton("Importer")
        btn_import.clicked.connect(self._import_data)

        # Print button
        btn_print = QPushButton("Imprimer")
        btn_print.clicked.connect(self._print_report)

        # Add controls to layout
        self.controls_layout.addWidget(date_debut_label)
        self.controls_layout.addWidget(self.date_debut)
        self.controls_layout.addWidget(date_fin_label)
        self.controls_layout.addWidget(self.date_fin)
        self.controls_layout.addWidget(btn_refresh)
        self.controls_layout.addWidget(btn_import)
        self.controls_layout.addWidget(btn_print)
        self.controls_layout.addStretch()

    def _load_data(self) -> None:
        """Load SF report data based on selected date range."""
        date_debut = self.start_date.toString("yyyy-MM-dd")
        date_fin = self.end_date.toString("yyyy-MM-dd")

        try:
            data = self.analyse_service.get_sf_report(date_debut, date_fin)
            self._populate_table(data)
            self.data_loaded.emit(data)
        except Exception:
            # Handle error gracefully - table will remain empty
            self.set_rows([])

    def _populate_table(self, data: list[dict]) -> None:
        """Populate the table with SF report data."""
        if not data:
            self.set_rows([])
            return

        rows = []
        for item in data:
            # Convert TTC to HT (divide by 1.2 for TVA 20%)
            si_ht = int(item.get("si_ttc", 0) / 1.2)
            achats_ht = int(item.get("achats_ttc", 0) / 1.2)
            sf_ht = int(item.get("sf_ttc", 0) / 1.2)
            demarque_ht = int(item.get("demarque_ttc", 0) / 1.2)

            row = [
                item.get("sous_categorie", ""),
                f"{si_ht:,}",
                f"{achats_ht:,}",
                f"{sf_ht:,}",
                f"{demarque_ht:,}",
            ]
            rows.append(row)

        self._current_rows = rows  # Store for import/print
        self.set_rows(rows)

    def _import_data(self) -> None:
        """Import SF report data to CSV."""
        import csv

        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter SF Rapport",
            f"sf_rapport_{self.date_debut.date().toString('yyyy-MM-dd')}_{self.date_fin.date().toString('yyyy-MM-dd')}.csv",
            "CSV Files (*.csv)",
        )

        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # Write headers
                writer.writerow(
                    ["Catégorie", "SI (début) HT", "Achats HT", "SF (fin) HT", "Démarque HT"]
                )
                # Write data rows
                for row in self._current_rows:
                    writer.writerow(row)
            QMessageBox.information(self, "Succès", "Données exportées avec succès!")
        except Exception as e:
            QMessageBox.critical(self, "Erreur", f"Échec de l'export: {str(e)}")

    def _print_report(self) -> None:
        """Print SF report."""
        from PyQt6.QtPrintSupport import QPrinter

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        preview = QPrintPreviewDialog(printer, self)
        preview.setWindowTitle("Aperçu SF Rapport")
        preview.paintRequested.connect(lambda p: self._render_print(p))
        preview.exec()

    def _render_print(self, printer: QPrinter) -> None:
        """Render the report for printing."""

        painter = QPainter(printer)
        painter.setPen(Qt.GlobalColor.black)

        # Title
        date_start = self.date_debut.date().toString("yyyy-MM-dd")
        date_end = self.date_fin.date().toString("yyyy-MM-dd")
        title = f"Rapport SF (Stock Flux) - HT\n{date_start} au {date_end}"
        painter.drawText(50, 50, title)

        # Table header
        y_pos = 100
        headers = ["Catégorie", "SI (début) HT", "Achats HT", "SF (fin) HT", "Démarque HT"]
        x_pos = 50
        for header in headers:
            painter.drawText(x_pos, y_pos, header)
            x_pos += 120

        # Draw line
        y_pos += 10
        painter.drawLine(50, y_pos, 700, y_pos)

        # Data rows
        y_pos += 20
        for row in self._current_rows:
            x_pos = 50
            for cell in row:
                painter.drawText(x_pos, y_pos, str(cell))
                x_pos += 120
            y_pos += 20

        painter.end()
