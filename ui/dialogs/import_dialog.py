"""Import dialog for importing data from JSON."""

from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.data_import_service import DataImportService
from styles.design_tokens import TOKENS
from styles.dialog_styles import (
    DIALOG_BASE,
    HEADER_LABEL,
    INPUT_FIELD,
    PRIMARY_BUTTON,
    REPORT_TABLE,
    SECONDARY_BUTTON,
    SEPARATOR,
)

logger = logging.getLogger(__name__)


class ImportDialog(QDialog):
    """Dialog for importing data from JSON."""

    def __init__(self, parent: QWidget | None, db_manager):
        super().__init__(parent)
        self.db_manager = db_manager
        self.setWindowTitle("Importer les données")
        self.resize(600, 450)

        self.setStyleSheet(DIALOG_BASE + INPUT_FIELD)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header
        header = QLabel("Importer les données")
        header.setStyleSheet(HEADER_LABEL)
        root.addWidget(header)

        # Info text
        info = QLabel(
            "Importez les produits, ventes et dépenses depuis un fichier JSON exporté précédemment. "
            "Les produits seront mis à jour, les ventes et dépenses seront ajoutées."
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

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Fichier:"))
        self.file_label = QLabel("Aucun fichier sélectionné")
        self.file_label.setStyleSheet(f"color: {TOKENS['text_muted']};")
        file_layout.addWidget(self.file_label, 1)
        btn_browse = QPushButton("Parcourir...")
        btn_browse.setStyleSheet(SECONDARY_BUTTON)
        btn_browse.clicked.connect(self._browse_file)
        file_layout.addWidget(btn_browse)
        root.addLayout(file_layout)

        # Preview table
        preview_label = QLabel("Aperçu:")
        preview_label.setStyleSheet(f"font-weight: 700; color: {TOKENS['text_default']};")
        root.addWidget(preview_label)

        self.preview_table = QTableWidget(0, 3)
        self.preview_table.setHorizontalHeaderLabels(["Type", "Nombre", "Exemple"])
        self.preview_table.setStyleSheet(REPORT_TABLE)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setMaximumHeight(150)
        root.addWidget(self.preview_table)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet(f"color: {TOKENS['text_muted']};")
        root.addWidget(self.status_label)

        # Error label
        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #dc2626;")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        btn_cancel = QPushButton("Annuler")
        btn_cancel.setStyleSheet(SECONDARY_BUTTON)
        btn_cancel.setFixedWidth(100)
        btn_cancel.clicked.connect(self.reject)
        button_layout.addWidget(btn_cancel)

        btn_import = QPushButton("Importer")
        btn_import.setStyleSheet(PRIMARY_BUTTON)
        btn_import.setFixedWidth(100)
        btn_import.clicked.connect(self._do_import)
        btn_import.setEnabled(False)
        self.btn_import = btn_import
        button_layout.addWidget(btn_import)

        root.addLayout(button_layout)

        self.file_path = None

    def _browse_file(self) -> None:
        """Browse for JSON file."""
        workdir = Path.cwd()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner un fichier JSON",
            str(workdir),
            "JSON (*.json);;Tous les fichiers (*)",
        )

        if not file_path:
            return

        self.file_path = file_path
        self.file_label.setText(Path(file_path).name)
        self._preview_file()

    def _preview_file(self) -> None:
        """Preview the file contents."""
        if not self.file_path:
            return

        try:
            import_service = DataImportService(self.db_manager)
            preview = import_service.preview_import(self.file_path)

            counts = preview.get("counts", {})
            self.preview_table.setRowCount(0)

            row = 0
            for data_type, count in [
                ("Produits", counts.get("produits", 0)),
                ("Ventes", counts.get("ventes", 0)),
                ("Dépenses", counts.get("depenses", 0)),
                ("Clôtures", counts.get("clotures", 0)),
            ]:
                self.preview_table.insertRow(row)
                self.preview_table.setItem(row, 0, QTableWidgetItem(data_type))
                self.preview_table.setItem(row, 1, QTableWidgetItem(str(count)))
                self.preview_table.setItem(row, 2, QTableWidgetItem(""))
                row += 1

            self.status_label.setText(f"Prêt à importer: {count} enregistrements")
            self.btn_import.setEnabled(True)

        except Exception as e:
            logger.exception("Preview failed")
            self.error_label.setText(f"Erreur: {e}")
            self.error_label.setVisible(True)
            self.btn_import.setEnabled(False)

    def _do_import(self) -> None:
        """Execute the import."""
        if not self.file_path:
            return

        # Confirm
        response = QMessageBox.question(
            self,
            "Confirmer l'import",
            "Les données seront importées. Les produits existants seront mis à jour. "
            "Voulez-vous continuer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if response != QMessageBox.StandardButton.Yes:
            return

        try:
            import_service = DataImportService(self.db_manager)
            result = import_service.import_all(self.file_path)

            imported = result.get("imported", {})
            errors = result.get("errors", [])

            if errors:
                error_text = "\n".join(errors)
                self.error_label.setText(f"Erreurs: {error_text}")
                self.error_label.setVisible(True)

            self.status_label.setText(
                f"Importé: {imported.get('produits', 0)} produits, "
                f"{imported.get('ventes', 0)} ventes, "
                f"{imported.get('depenses', 0)} dépenses"
            )

            QMessageBox.information(
                self,
                "Import terminé",
                self.status_label.text(),
                QMessageBox.StandardButton.Ok,
            )
            self.accept()

        except Exception as e:
            logger.exception("Import failed")
            QMessageBox.critical(
                self,
                "Erreur d'import",
                f"Échec de l'import: {e}",
                QMessageBox.StandardButton.Ok,
            )
