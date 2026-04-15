"""Historique des mouvements (haut droite)."""

from datetime import datetime

from PyQt6.QtWidgets import QGroupBox, QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout

from services.mouvements_service import MOUVEMENT_LABELS


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
        self._db_manager = None

    def set_db_manager(self, db_manager) -> None:
        self._db_manager = db_manager

    def load_for_product(self, produit_id: int, produit_nom: str) -> None:
        self.table.setRowCount(0)
        if self._db_manager is None:
            return
        mouvements = self._db_manager.get_mouvements_par_produit(produit_id)
        for m in mouvements:
            row = self.table.rowCount()
            self.table.insertRow(row)
            jour = m.get("jour", "")
            try:
                dt = datetime.fromisoformat(jour.replace("Z", "+00:00"))
                date_str = dt.strftime("%d/%m/%y %H:%M")
            except Exception:
                date_str = jour[:16] if jour else "-"
            type_label = MOUVEMENT_LABELS.get(
                m.get("type_mouvement", ""), m.get("type_mouvement", "")
            )
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            self.table.setItem(row, 1, QTableWidgetItem(produit_nom))
            self.table.setItem(row, 2, QTableWidgetItem(type_label))
            self.table.setItem(row, 3, QTableWidgetItem(str(m.get("quantite", 0))))

    def add_movement(self, produit_nom: str, type_mouvement: str, qte: int) -> None:
        row = 0
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(datetime.now().strftime("%d/%m/%y %H:%M")))
        self.table.setItem(row, 1, QTableWidgetItem(produit_nom))
        self.table.setItem(row, 2, QTableWidgetItem(type_mouvement))
        self.table.setItem(row, 3, QTableWidgetItem(str(qte)))
