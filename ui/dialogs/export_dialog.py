"""Export dialog for exporting data to JSON."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.data_export_service import DataExportService
from styles.design_tokens import TOKENS
from styles.dialog_styles import (
    DIALOG_BASE,
    HEADER_LABEL,
    INPUT_FIELD,
    PRIMARY_BUTTON,
    SECONDARY_BUTTON,
    SEPARATOR,
)

logger = logging.getLogger(__name__)


class ExportDialog(QDialog):
    """Dialog for exporting data to JSON."""

    def __init__(self, parent: QWidget | None, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Exporter les données")
        self.resize(480, 280)

        self.setStyleSheet(DIALOG_BASE + INPUT_FIELD)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header
        header = QLabel("Exporter les données")
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        # Info text
        info = QLabel(
            "Exportez les produits, ventes et dépenses du jour vers un fichier JSON. "
            "Les données peuvent être restaurées ultérieurement."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {TOKENS['text_muted']};")
        root.addWidget(info)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet(SEPARATOR)
        separator.setFixedHeight(1)
        root.addWidget(separator)

        # Date selection
        date_layout = QHBoxLayout()
        date_layout.addWidget(QLabel("Date:"))
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        date_layout.addWidget(self.date_edit)
        date_layout.addStretch()
        root.addLayout(date_layout)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {TOKENS['text_muted']};")
        root.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_cancel = QPushButton("Annuler")
        btn_cancel.setStyleSheet(SECONDARY_BUTTON)
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        btn_export = QPushButton("Exporter")
        btn_export.setStyleSheet(PRIMARY_BUTTON)
        btn_export.setFixedWidth(100)
        btn_export.clicked.connect(self._do_export)
        button_layout.addWidget(btn_export)

        root.addLayout(button_layout)

    def _do_export(self) -> None:
        """Execute the export."""
        date = self.date_edit.date().toString("yyyy-MM-dd")

        # Ask for file location
        default_name = f"export_{date}.json"
        workdir = Path.cwd()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer l'export",
            str(workdir / default_name),
            "JSON (*.json);;Tous les fichiers (*)",
        )

        if not file_path:
            return

        try:
            export_service = DataExportService(self.db_manager)
            counts = export_service.export_all(file_path, day=date)

            self.status_label.setText(
                f"Exporté: {counts.get('produits', 0)} produits, "
                f"{counts.get('ventes', 0)} ventes, "
                f"{counts.get('depenses', 0)} dépenses"
            )

            QMessageBox.information(
                self,
                "Export terminé",
                f"Les données ont été exportées vers:\n{file_path}",
                QMessageBox.StandardButton.Ok,
            )
            self.accept()

        except Exception as e:
            logger.exception("Export failed")
            QMessageBox.critical(
                self,
                "Erreur d'export",
                f"Échec de l'export: {e}",
                QMessageBox.StandardButton.Ok,
            )
