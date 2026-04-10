"""Header information section displaying user, transaction count, and metrics."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class HeaderInfoWidget(QWidget):
    """Displays session info: user (top), transactions (top), metrics (bottom)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._main_layout = QHBoxLayout(self)
        self._main_layout.setContentsMargins(10, 4, 10, 4)
        self._main_layout.setSpacing(20)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)

        self.lbl_user = QLabel("Utilisateur: —")
        self.lbl_user.setStyleSheet("color: #e5e7eb; font-size: 14px; font-weight: bold;")
        left_layout.addWidget(self.lbl_user)

        self.lbl_transactions = QLabel("Transactions: 0")
        self.lbl_transactions.setStyleSheet("color: #9ca3af; font-size: 13px;")
        left_layout.addWidget(self.lbl_transactions)

        self._main_layout.addWidget(left_container, 0)

        self._main_layout.addStretch()

        metrics_container = QWidget()
        metrics_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        metrics_layout = QHBoxLayout(metrics_container)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(10)

        # Vente metric - 2 rows with background
        self.vente_container = QWidget()
        self.vente_container.setStyleSheet(
            "background-color: #292929; border-radius: 6px; padding: 10px 12px;"
        )
        self.vente_inner_layout = QVBoxLayout(self.vente_container)
        self.vente_inner_layout.setSpacing(0)
        self.vente_inner_layout.setContentsMargins(0, 6, 0, 6)
        self.lbl_vente_label = QLabel("Vente")
        self.lbl_vente_label.setStyleSheet("color: #eab308; font-size: 12px; font-weight: bold;")
        self.lbl_vente_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.vente_inner_layout.addWidget(self.lbl_vente_label)
        self.lbl_vente = QLabel("0 Ar")
        self.lbl_vente.setStyleSheet("color: #eab308; font-size: 18px; font-weight: bold;")
        self.lbl_vente.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.vente_inner_layout.addWidget(self.lbl_vente)

        # Depenses metric - 2 rows with background
        self.depenses_container = QWidget()
        self.depenses_container.setStyleSheet(
            "background-color: #292929; border-radius: 6px; padding: 10px 12px;"
        )
        self.depenses_inner_layout = QVBoxLayout(self.depenses_container)
        self.depenses_inner_layout.setSpacing(0)
        self.depenses_inner_layout.setContentsMargins(0, 6, 0, 6)
        self.lbl_depenses_label = QLabel("Dépenses")
        self.lbl_depenses_label.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
        self.lbl_depenses_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.depenses_inner_layout.addWidget(self.lbl_depenses_label)
        self.lbl_depenses = QLabel("0 Ar")
        self.lbl_depenses.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: bold;")
        self.lbl_depenses.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.depenses_inner_layout.addWidget(self.lbl_depenses)

        # Caisse metric - 2 rows with background
        self.caisse_container = QWidget()
        self.caisse_container.setStyleSheet(
            "background-color: #292929; border-radius: 6px; padding: 10px 12px;"
        )
        self.caisse_inner_layout = QVBoxLayout(self.caisse_container)
        self.caisse_inner_layout.setSpacing(0)
        self.caisse_inner_layout.setContentsMargins(0, 6, 0, 6)
        self.lbl_caisse_label = QLabel("Caisse")
        self.lbl_caisse_label.setStyleSheet("color: #22c55e; font-size: 12px; font-weight: bold;")
        self.lbl_caisse_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.caisse_inner_layout.addWidget(self.lbl_caisse_label)
        self.lbl_caisse = QLabel("0 Ar")
        self.lbl_caisse.setStyleSheet("color: #22c55e; font-size: 18px; font-weight: bold;")
        self.lbl_caisse.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.caisse_inner_layout.addWidget(self.lbl_caisse)

        metrics_layout.addWidget(self.vente_container, 1)
        metrics_layout.addWidget(self.depenses_container, 1)
        metrics_layout.addWidget(self.caisse_container, 1)

        self._main_layout.addWidget(metrics_container, 1)

    def update_data(self, user: str, transaction_count: int) -> None:
        """Passive update: set labels with provided data.

        Args:
            user: User name
            transaction_count: Number of transactions
        """
        self.lbl_user.setText(f"Utilisateur: {user}")
        self.lbl_transactions.setText(f"Transactions: {transaction_count}")

    def update_metrics(self, vente: int, depenses: int, caisse: int) -> None:
        """Update metrics display.

        Args:
            vente: Total sales amount
            depenses: Total expenses amount
            caisse: Total cash in register
        """
        from core.formatters import format_grouped_int

        self.lbl_vente.setText(f"{format_grouped_int(vente)} Ar")
        self.lbl_depenses.setText(f"{format_grouped_int(depenses)} Ar")
        self.lbl_caisse.setText(f"{format_grouped_int(caisse)} Ar")
