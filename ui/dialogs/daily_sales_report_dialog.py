"""Dialog for displaying the complete daily report (Journalier Complet).

This dialog is shown after cloture and contains an Exporter PDF button that:
1. Exports the report to PDF
2. Opens the PDF with the default system viewer
3. Closes the application
"""

import logging
import os
import subprocess
import sys
from typing import Any

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.formatters import format_grouped_int
from styles.dialog_styles import (
    DIALOG_BASE,
    HEADER_LABEL,
    PRIMARY_BUTTON,
    REPORT_TABLE,
    SECONDARY_BUTTON,
)

logger = logging.getLogger(__name__)


class RapportVenteJourDialog(QDialog):
    """Dialog for displaying the complete daily report during cloture workflow.

    Shows 3 sections: Sales, Expenses, Invoices. Has an Exporter PDF button.
    """

    # Signal emitted when user clicks Exporter PDF (to close the app)
    importer_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None, jour: str, rapport_data: Any | None = None) -> None:
        """Initialize the complete daily report dialog.

        Args:
            parent: Parent widget.
            jour: Date in ISO format (YYYY-MM-DD).
            rapport_data: JournalierCompletData with sales, expenses, receptions.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Journalier - {jour}")
        self.setMinimumSize(780, 620)
        self.resize(780, 620)

        self._jour = jour
        self._data = rapport_data

        self.setStyleSheet(DIALOG_BASE)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Title
        title = QLabel(f"Journal des ventes - {jour}")
        title.setStyleSheet(HEADER_LABEL)
        content_layout.addWidget(title)

        # Section 1: Sales
        grp_sales = QGroupBox("Resume des ventes par categorie")
        grp_sales.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay_sales = QVBoxLayout(grp_sales)
        lay_sales.setContentsMargins(8, 8, 8, 8)

        self.table_sales = QTableWidget(0, 5)
        self.table_sales.setHorizontalHeaderLabels(
            ["Categorie", "Produit", "Qté vendue", "Total", "Stock final"]
        )
        self.table_sales.setStyleSheet(REPORT_TABLE)
        self.table_sales.setAlternatingRowColors(True)
        self.table_sales.verticalHeader().setVisible(False)
        self.table_sales.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_sales.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table_sales.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay_sales.addWidget(self.table_sales)

        self.lbl_total_ventes = QLabel("Total ventes: 0 Ar")
        self.lbl_total_ventes.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #7c3aed; border-radius: 6px; padding: 6px 12px;"
        )
        lay_sales.addWidget(self.lbl_total_ventes)
        content_layout.addWidget(grp_sales)

        # Section 2: Expenses
        grp_depenses = QGroupBox("Resume des depenses")
        grp_depenses.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay_depenses = QVBoxLayout(grp_depenses)
        lay_depenses.setContentsMargins(8, 8, 8, 8)

        self.table_depenses = QTableWidget(0, 3)
        self.table_depenses.setHorizontalHeaderLabels(["Designation", "Valeur", "Remarque"])
        self.table_depenses.setStyleSheet(REPORT_TABLE)
        self.table_depenses.setAlternatingRowColors(True)
        self.table_depenses.verticalHeader().setVisible(False)
        self.table_depenses.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_depenses.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table_depenses.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        lay_depenses.addWidget(self.table_depenses)

        self.lbl_total_depenses = QLabel("Total depenses: 0 Ar")
        self.lbl_total_depenses.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #dc2626; border-radius: 6px; padding: 6px 12px;"
        )
        lay_depenses.addWidget(self.lbl_total_depenses)
        content_layout.addWidget(grp_depenses)

        # Section 3: Receptions (Invoices)
        grp_factures = QGroupBox("Resume des factures")
        grp_factures.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay_factures = QVBoxLayout(grp_factures)
        lay_factures.setContentsMargins(8, 8, 8, 8)

        self.table_factures = QTableWidget(0, 3)
        self.table_factures.setHorizontalHeaderLabels(["N° Facture", "Fournisseur", "Total TTC"])
        self.table_factures.setStyleSheet(REPORT_TABLE)
        self.table_factures.setAlternatingRowColors(True)
        self.table_factures.verticalHeader().setVisible(False)
        self.table_factures.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_factures.horizontalHeader()
        if header is not None:
            header.setStretchLastSection(True)
        self.table_factures.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        lay_factures.addWidget(self.table_factures)

        self.lbl_total_factures = QLabel("Total factures: 0 Ar")
        self.lbl_total_factures.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #2563eb; border-radius: 6px; padding: 6px 12px;"
        )
        lay_factures.addWidget(self.lbl_total_factures)
        content_layout.addWidget(grp_factures)

        scroll.setWidget(content_widget)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll, 1)

        # Buttons
        button_container = QHBoxLayout()
        button_container.setContentsMargins(16, 8, 16, 16)
        button_container.setSpacing(12)

        btn_fermer = QPushButton("Fermer")
        btn_fermer.setStyleSheet(SECONDARY_BUTTON)
        btn_fermer.setMinimumSize(120, 42)
        btn_fermer.clicked.connect(self.reject)
        button_container.addWidget(btn_fermer)

        button_container.addStretch(1)

        btn_exporter = QPushButton("Exporter PDF")
        btn_exporter.setStyleSheet(PRIMARY_BUTTON)
        btn_exporter.setMinimumSize(160, 42)
        btn_exporter.clicked.connect(self._on_exporter_clicked)
        button_container.addWidget(btn_exporter)

        root.addLayout(button_container)

        # Populate tables
        self._populate_all()

    def _populate_all(self) -> None:
        """Populate all three tables from the data."""
        if self._data is None:
            return

        # Sales table
        sales = getattr(self._data, "sales", [])
        self.table_sales.setRowCount(len(sales))
        for i, row in enumerate(sales):
            self.table_sales.setItem(i, 0, QTableWidgetItem(row.categorie))
            self.table_sales.setItem(i, 1, QTableWidgetItem(row.produit))
            self.table_sales.setItem(i, 2, QTableWidgetItem(str(row.quantite_vendue)))
            item_total = QTableWidgetItem(format_grouped_int(row.total_vente))
            item_total.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_sales.setItem(i, 3, item_total)
            item_stock = QTableWidgetItem(str(row.stock_final))
            item_stock.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_sales.setItem(i, 4, item_stock)

        total_ventes = getattr(self._data, "total_ventes", 0)
        self.lbl_total_ventes.setText(f"Total ventes: {format_grouped_int(total_ventes)} Ar")

        # Expenses table
        expenses = getattr(self._data, "expenses", [])
        self.table_depenses.setRowCount(len(expenses))
        for i, row in enumerate(expenses):
            self.table_depenses.setItem(i, 0, QTableWidgetItem(row.designation))
            item_val = QTableWidgetItem(format_grouped_int(row.valeur))
            item_val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_depenses.setItem(i, 1, item_val)
            self.table_depenses.setItem(i, 2, QTableWidgetItem(row.remarque))

        total_depenses = getattr(self._data, "total_depenses", 0)
        self.lbl_total_depenses.setText(f"Total depenses: {format_grouped_int(total_depenses)} Ar")

        # Receptions table
        receptions = getattr(self._data, "receptions", [])
        self.table_factures.setRowCount(len(receptions))
        for i, row in enumerate(receptions):
            self.table_factures.setItem(i, 0, QTableWidgetItem(row.numero_facture))
            self.table_factures.setItem(i, 1, QTableWidgetItem(row.fournisseur))
            item_ttc = QTableWidgetItem(format_grouped_int(row.total_ttc))
            item_ttc.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table_factures.setItem(i, 2, item_ttc)

        total_receptions = getattr(self._data, "total_receptions", 0)
        total_text = f"Total factures: {format_grouped_int(total_receptions)} Ar"
        self.lbl_total_factures.setText(total_text)

    def _on_exporter_clicked(self) -> None:
        """Handle Exporter PDF button click."""
        logger.info("Exporter PDF clicked - generating report for %s", self._jour)

        try:
            pdf_path = self._generate_pdf()
            if pdf_path and os.path.exists(pdf_path):
                self._open_pdf(pdf_path)
        except Exception as exc:
            logger.error("Failed to generate/open PDF: %s", exc)

        self.importer_clicked.emit()
        self.accept()

    def _generate_pdf(self) -> str:
        """Generate a PDF report from the current data.

        Returns:
            Path to the generated PDF file.
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import cm
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            filename = f"Journalier-{self._jour}.pdf"
            filepath = os.path.join(os.path.expanduser("~"), "Documents", filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            doc = SimpleDocTemplate(filepath, pagesize=A4)
            story = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                "CustomTitle", parent=styles["Title"], fontSize=16, spaceAfter=20
            )
            story.append(Paragraph(f"Journal des ventes - {self._jour}", title_style))
            story.append(Spacer(1, 0.5 * cm))

            # Section 1: Sales
            story.append(Paragraph("Resume des ventes par categorie", styles["Heading2"]))
            if self._data and hasattr(self._data, "sales"):
                sales_data = [["Categorie", "Produit", "Qté", "Total", "Stock"]]
                for row in self._data.sales:
                    sales_data.append(
                        [
                            row.categorie,
                            row.produit,
                            str(row.quantite_vendue),
                            format_grouped_int(row.total_vente),
                            str(row.stock_final),
                        ]
                    )
                sales_data.append(
                    ["", "", "TOTAL", format_grouped_int(self._data.total_ventes), ""]
                )
                table = Table(sales_data, colWidths=[3 * cm, 4 * cm, 2 * cm, 3 * cm, 2 * cm])
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3b82f6")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ]
                    )
                )
                story.append(table)
            story.append(Spacer(1, 0.5 * cm))

            # Section 2: Expenses
            story.append(Paragraph("Resume des depenses", styles["Heading2"]))
            if self._data and hasattr(self._data, "expenses"):
                dep_data = [["Designation", "Valeur", "Remarque"]]
                for row in self._data.expenses:
                    dep_data.append([row.designation, format_grouped_int(row.valeur), row.remarque])
                dep_data.append(["TOTAL", format_grouped_int(self._data.total_depenses), ""])
                table = Table(dep_data, colWidths=[6 * cm, 3 * cm, 5 * cm])
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dc2626")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ]
                    )
                )
                story.append(table)
            story.append(Spacer(1, 0.5 * cm))

            # Section 3: Receptions
            story.append(Paragraph("Resume des factures", styles["Heading2"]))
            if self._data and hasattr(self._data, "receptions"):
                fac_data = [["N° Facture", "Fournisseur", "Total TTC"]]
                for row in self._data.receptions:
                    fac_data.append(
                        [
                            row.numero_facture,
                            row.fournisseur,
                            format_grouped_int(row.total_ttc),
                        ]
                    )
                fac_data.append(["", "TOTAL", format_grouped_int(self._data.total_receptions)])
                table = Table(fac_data, colWidths=[4 * cm, 6 * cm, 3 * cm])
                table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                            ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")),
                            ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ]
                    )
                )
                story.append(table)

            doc.build(story)
            logger.info("PDF generated: %s", filepath)
            return filepath

        except ImportError:
            logger.warning("reportlab not installed - skipping PDF generation")
            return ""

    def _open_pdf(self, filepath: str) -> None:
        """Open the PDF with the default system viewer.

        Args:
            filepath: Path to the PDF file.
        """
        try:
            if sys.platform == "win32":
                os.startfile(filepath)
            elif sys.platform == "darwin":
                subprocess.run(["open", filepath], check=False)
            else:
                subprocess.run(["xdg-open", filepath], check=False)
            logger.info("PDF opened: %s", filepath)
        except Exception as exc:
            logger.error("Failed to open PDF: %s", exc)
