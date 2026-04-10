import csv
import logging

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from styles.dialog_styles import (
    DIALOG_BASE,
    REPORT_TABLE,
    SECONDARY_BUTTON,
)


class TableReportDialog(QDialog):
    def __init__(
        self,
        title: str,
        headers: list[str],
        parent: QWidget | None = None,
        allow_import: bool = False,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(980, 560)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.setStyleSheet(DIALOG_BASE)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        self.controls_layout = QHBoxLayout()
        self.controls_layout.setSpacing(8)
        root.addLayout(self.controls_layout)

        # Table
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setStyleSheet(REPORT_TABLE)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        if allow_import:
            btn_import = QPushButton("Importer")
            btn_import.setStyleSheet(SECONDARY_BUTTON)
            btn_import.clicked.connect(self._import_csv)
            actions.addWidget(btn_import)
        btn_close = QPushButton("Fermer")
        btn_close.setStyleSheet(SECONDARY_BUTTON)
        btn_close.clicked.connect(self.accept)
        actions.addWidget(btn_close)
        root.addLayout(actions)

    def set_rows(self, rows: list[list[str]]) -> None:
        self.table.setRowCount(0)
        for row_values in rows:
            row = self.table.rowCount()
            self.table.insertRow(row)
            for col, value in enumerate(row_values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

    def _import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Importer un fichier", "", "CSV (*.csv);;Tous les fichiers (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                sample = fh.read(2048)
                fh.seek(0)
                dialect = csv.Sniffer().sniff(sample, delimiters=",;|\t")
                reader = csv.reader(fh, dialect)
                rows = [r for r in reader if any(str(c).strip() for c in r)]
        except (OSError, UnicodeDecodeError, csv.Error) as exc:
            logging.getLogger(__name__).warning("import CSV ignore (%s): %s", path, exc)
            return
        if not rows:
            return
        col_count = max(len(r) for r in rows)
        self.table.setColumnCount(col_count)
        self.table.setHorizontalHeaderLabels([f"Col {i + 1}" for i in range(col_count)])
        self.set_rows(rows)
