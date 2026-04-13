"""Admin authentication dialog for enabling privileged features."""

from __future__ import annotations

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class AdminAuthDialog(QDialog):
    """Dialog for admin authentication."""

    def __init__(self, db_manager, parent: QWidget | None = None) -> None:
        """Initialize admin auth dialog.

        Args:
            db_manager: Database manager for PIN verification
            parent: Parent widget
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self._admin_authenticated = False
        self.setWindowTitle("Authentification Administrateur")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build dialog UI."""
        layout = QVBoxLayout(self)

        title = QLabel("Entrez le code PIN administrateur")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Code PIN")
        self.password_input.returnPressed.connect(self._verify_password)
        layout.addWidget(self.password_input)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(cancel_btn)

        self.verify_btn = QPushButton("Vérifier")
        self.verify_btn.clicked.connect(self._verify_password)
        self.verify_btn.setDefault(True)
        buttons.addWidget(self.verify_btn)

        layout.addLayout(buttons)

    def _verify_password(self) -> None:
        """Verify entered password against stored PIN."""
        entered_password = self.password_input.text()

        if not entered_password:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez entrer un code PIN.",
            )
            return

        if self.db_manager.verify_admin_pin(entered_password):
            self._admin_authenticated = True
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Erreur",
                "Code PIN incorrect.",
            )
            self.password_input.clear()
            self.password_input.setFocus()

    def is_authenticated(self) -> bool:
        """Check if authentication was successful.

        Returns:
            True if authenticated, False otherwise
        """
        return self._admin_authenticated
