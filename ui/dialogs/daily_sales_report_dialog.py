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
            rapport_data: JournalierCompletData with sales, expenses, achats.
        """
        super().__init__(parent)
        self.setWindowTitle(f"Journalier - {jour}")
        self.setMinimumSize(800, 700)
        self.resize(800, 700)

        self._jour = jour
        self._data = rapport_data
        self._rows_per_page = 10

        self._sales_page = 0
        self._expenses_page = 0
        self._achats_page = 0

        self.setStyleSheet(DIALOG_BASE)

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

        self.table_sales = QTableWidget(self._rows_per_page, 5)
        self.table_sales.setHorizontalHeaderLabels(
            ["Categorie", "Produit", "Qté vendeuse", "Total", "Stock final"]
        )
        self.table_sales.setStyleSheet(REPORT_TABLE)
        self.table_sales.setAlternatingRowColors(True)
        self.table_sales.verticalHeader().setVisible(False)
        self.table_sales.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_sales.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table_sales.setMaximumHeight(
            self.table_sales.horizontalHeader().height()
            + self.table_sales.rowHeight(0) * (self._rows_per_page + 1)
        )
        lay_sales.addWidget(self.table_sales)

        self._sales_nav = QHBoxLayout()
        self._sales_nav.setSpacing(8)
        btn_prev_sales = QPushButton("<")
        btn_prev_sales.setStyleSheet(SECONDARY_BUTTON)
        btn_prev_sales.setFixedSize(40, 30)
        btn_prev_sales.clicked.connect(lambda: self._change_page("sales", -1))
        self._sales_nav.addWidget(btn_prev_sales)
        self.lbl_page_sales = QLabel("Page 1/1")
        self.lbl_page_sales.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._sales_nav.addWidget(self.lbl_page_sales)
        btn_next_sales = QPushButton(">")
        btn_next_sales.setStyleSheet(SECONDARY_BUTTON)
        btn_next_sales.setFixedSize(40, 30)
        btn_next_sales.clicked.connect(lambda: self._change_page("sales", 1))
        self._sales_nav.addWidget(btn_next_sales)
        self._sales_nav.addStretch(1)
        lay_sales.addLayout(self._sales_nav)

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

        self.table_depenses = QTableWidget(self._rows_per_page, 3)
        self.table_depenses.setHorizontalHeaderLabels(["Designation", "Valeur", "Remarque"])
        self.table_depenses.setStyleSheet(REPORT_TABLE)
        self.table_depenses.setAlternatingRowColors(True)
        self.table_depenses.verticalHeader().setVisible(False)
        self.table_depenses.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_depenses.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table_depenses.setMaximumHeight(
            self.table_depenses.horizontalHeader().height()
            + self.table_depenses.rowHeight(0) * (self._rows_per_page + 1)
        )
        lay_depenses.addWidget(self.table_depenses)

        self._expenses_nav = QHBoxLayout()
        self._expenses_nav.setSpacing(8)
        btn_prev_exp = QPushButton("<")
        btn_prev_exp.setStyleSheet(SECONDARY_BUTTON)
        btn_prev_exp.setFixedSize(40, 30)
        btn_prev_exp.clicked.connect(lambda: self._change_page("expenses", -1))
        self._expenses_nav.addWidget(btn_prev_exp)
        self.lbl_page_expenses = QLabel("Page 1/1")
        self.lbl_page_expenses.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._expenses_nav.addWidget(self.lbl_page_expenses)
        btn_next_exp = QPushButton(">")
        btn_next_exp.setStyleSheet(SECONDARY_BUTTON)
        btn_next_exp.setFixedSize(40, 30)
        btn_next_exp.clicked.connect(lambda: self._change_page("expenses", 1))
        self._expenses_nav.addWidget(btn_next_exp)
        self._expenses_nav.addStretch(1)
        lay_depenses.addLayout(self._expenses_nav)

        self.lbl_total_depenses = QLabel("Total depenses: 0 Ar")
        self.lbl_total_depenses.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #dc2626; border-radius: 6px; padding: 6px 12px;"
        )
        lay_depenses.addWidget(self.lbl_total_depenses)
        content_layout.addWidget(grp_depenses)

        # Section 3: Receptions (Invoices)
        grp_achats = QGroupBox("Resume des achats")
        grp_achats.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        lay_achats = QVBoxLayout(grp_achats)
        lay_achats.setContentsMargins(8, 8, 8, 8)

        self.table_achats = QTableWidget(self._rows_per_page, 3)
        self.table_achats.setHorizontalHeaderLabels(["N° Facture", "Fournisseur", "Total TTC"])
        self.table_achats.setStyleSheet(REPORT_TABLE)
        self.table_achats.setAlternatingRowColors(True)
        self.table_achats.verticalHeader().setVisible(False)
        self.table_achats.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_achats.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.table_achats.setMaximumHeight(
            self.table_achats.horizontalHeader().height()
            + self.table_achats.rowHeight(0) * (self._rows_per_page + 1)
        )
        lay_achats.addWidget(self.table_achats)

        self._achats_nav = QHBoxLayout()
        self._achats_nav.setSpacing(8)
        btn_prev_rec = QPushButton("<")
        btn_prev_rec.setStyleSheet(SECONDARY_BUTTON)
        btn_prev_rec.setFixedSize(40, 30)
        btn_prev_rec.clicked.connect(lambda: self._change_page("achats", -1))
        self._achats_nav.addWidget(btn_prev_rec)
        self.lbl_page_achats = QLabel("Page 1/1")
        self.lbl_page_achats.setStyleSheet("color: #6b7280; font-size: 12px;")
        self._achats_nav.addWidget(self.lbl_page_achats)
        btn_next_rec = QPushButton(">")
        btn_next_rec.setStyleSheet(SECONDARY_BUTTON)
        btn_next_rec.setFixedSize(40, 30)
        btn_next_rec.clicked.connect(lambda: self._change_page("achats", 1))
        self._achats_nav.addWidget(btn_next_rec)
        self._achats_nav.addStretch(1)
        lay_achats.addLayout(self._achats_nav)

        self.lbl_total_achats = QLabel("Total achats: 0 Ar")
        self.lbl_total_achats.setStyleSheet(
            "font-size: 15px; font-weight: 700; color: #f5f3ff;"
            "background-color: #2563eb; border-radius: 6px; padding: 6px 12px;"
        )
        lay_achats.addWidget(self.lbl_total_achats)
        content_layout.addWidget(grp_achats)

        # Root layout
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.addWidget(content_widget, 1)

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

        sales = getattr(self._data, "sales", [])
        expenses = getattr(self._data, "expenses", [])
        achats = getattr(self._data, "achats", [])

        total_ventes = getattr(self._data, "total_ventes", 0)
        total_depenses = getattr(self._data, "total_depenses", 0)
        total_achats = getattr(self._data, "total_achats", 0)

        self._sales_page = 0
        self._expenses_page = 0
        self._achats_page = 0

        self._sales_data = sales
        self._expenses_data = expenses
        self._achats_data = achats

        self._render_page("sales")
        self._render_page("expenses")
        self._render_page("achats")

        self.lbl_total_ventes.setText(f"Total ventes: {format_grouped_int(total_ventes)} Ar")
        self.lbl_total_depenses.setText(f"Total depenses: {format_grouped_int(total_depenses)} Ar")
        self.lbl_total_achats.setText(f"Total achats: {format_grouped_int(total_achats)} Ar")

    def _change_page(self, table: str, delta: int) -> None:
        """Change page for a table."""
        if table == "sales":
            total = len(self._sales_data)
            current = self._sales_page
        elif table == "expenses":
            total = len(self._expenses_data)
            current = self._expenses_page
        else:
            total = len(self._achats_data)
            current = self._achats_page

        max_page = max(0, (total - 1) // self._rows_per_page)
        new_page = current + delta

        if new_page < 0 or new_page > max_page:
            return

        if table == "sales":
            self._sales_page = new_page
        elif table == "expenses":
            self._expenses_page = new_page
        else:
            self._achats_page = new_page

        self._render_page(table)

    def _render_page(self, table: str) -> None:
        """Render a single page of data for a table."""
        if table == "sales":
            data = getattr(self, "_sales_data", [])
            page = self._sales_page
            tbl = self.table_sales
            lbl = self.lbl_page_sales
        elif table == "expenses":
            data = getattr(self, "_expenses_data", [])
            page = self._expenses_page
            tbl = self.table_depenses
            lbl = self.lbl_page_expenses
        else:
            data = getattr(self, "_achats_data", [])
            page = self._achats_page
            tbl = self.table_achats
            lbl = self.lbl_page_achats

        max_page = max(0, (len(data) - 1) // self._rows_per_page) if data else 0
        lbl.setText(f"Page {page + 1}/{max_page + 1}")

        start = page * self._rows_per_page
        end = min(start + self._rows_per_page, len(data))
        page_data = data[start:end] if data else []

        tbl.clearContents()
        tbl.setRowCount(self._rows_per_page)

        for i, row in enumerate(page_data):
            if table == "sales":
                tbl.setItem(i, 0, QTableWidgetItem(row.categorie))
                tbl.setItem(i, 1, QTableWidgetItem(row.produit))
                tbl.setItem(i, 2, QTableWidgetItem(str(row.quantite_vendue)))
                item_total = QTableWidgetItem(format_grouped_int(row.total_vente))
                item_total.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                tbl.setItem(i, 3, item_total)
                item_stock = QTableWidgetItem(str(row.stock_final))
                item_stock.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                tbl.setItem(i, 4, item_stock)
            elif table == "expenses":
                tbl.setItem(i, 0, QTableWidgetItem(row.designation))
                item_val = QTableWidgetItem(format_grouped_int(row.valeur))
                item_val.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                tbl.setItem(i, 1, item_val)
                tbl.setItem(i, 2, QTableWidgetItem(row.remarque))
            else:
                tbl.setItem(i, 0, QTableWidgetItem(row.numero_facture))
                tbl.setItem(i, 1, QTableWidgetItem(row.fournisseur))
                item_ttc = QTableWidgetItem(format_grouped_int(row.total_ttc))
                item_ttc.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                )
                tbl.setItem(i, 2, item_ttc)

        for i in range(len(page_data), self._rows_per_page):
            for j in range(tbl.columnCount()):
                tbl.setItem(i, j, QTableWidgetItem(""))

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

            # Section 3: Achats
            story.append(Paragraph("Resume des achats", styles["Heading2"]))
            if self._data and hasattr(self._data, "achats"):
                fac_data = [["N° Facture", "Fournisseur", "Total TTC"]]
                for row in self._data.achats:
                    fac_data.append(
                        [
                            row.numero_facture,
                            row.fournisseur,
                            format_grouped_int(row.total_ttc),
                        ]
                    )
                fac_data.append(["", "TOTAL", format_grouped_int(self._data.total_achats)])
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
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)
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
