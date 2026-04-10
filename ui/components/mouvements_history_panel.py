"""Historique des mouvements (haut droite)."""

from datetime import datetime

from PyQt6.QtWidgets import QGroupBox, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout


class MouvementsHistoryPanel(QGroupBox):
    """Panel affichant l'historique des mouvements."""

    def __init__(self) -> None:
        super().__init__()
        self.setTitle("Derniers Mouvements")
        self.setStyleSheet("""
            QGroupBox {
                border: 1px solid #2a3142;
                border-radius: 10px;
                margin-top: 12px;
                padding: 10px;
                font-weight: 700;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #e2e8f0;
            }
            """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 10)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Date", "Produit", "Type", "Qte"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)

    def add_movement(self, produit_nom: str, type_mouvement: str, qte: int) -> None:
        row = 0
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%d/%m/%y %H:%M")))
        self.table.setItem(row, 1, QTableWidgetItem(produit_nom))
        self.table.setItem(row, 2, QTableWidgetItem(type_mouvement))
        self.table.setItem(row, 3, QTableWidgetItem(str(qte)))
