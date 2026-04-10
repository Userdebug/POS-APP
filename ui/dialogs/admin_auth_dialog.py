"""Admin authentication dialog for enabling privileged features."""

from __future__ import annotations

import hashlib
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

ADMIN_PASSWORD_KEY = "admin_password_hash"


class AdminAuthDialog(QDialog):
    """Dialog for admin authentication."""

    def __init__(self, settings_service, parent: QWidget | None = None) -> None:
        """Initialize admin auth dialog.

        Args:
            settings_service: Settings service for password validation
            parent: Parent widget
        """
        super().__init__(parent)
        self.settings_service = settings_service
        self._admin_authenticated = False
        self.setWindowTitle("Authentification Administrateur")
        self.setModal(True)
        self._build_ui()

    def _build_ui(self) -> None:
        """Build dialog UI."""
        layout = QVBoxLayout(self)

        title = QLabel("Entrez le mot de passe administrateur")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Mot de passe")
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
        """Verify entered password against stored hash."""
        entered_password = self.password_input.text()

        if not entered_password:
            QMessageBox.warning(
                self,
                "Erreur",
                "Veuillez entrer un mot de passe.",
            )
            return

        entered_hash = hashlib.sha256(entered_password.encode()).hexdigest()
        stored_hash = self.settings_service.get_item_value(ADMIN_PASSWORD_KEY, None, "string")

        if stored_hash is None:
            QMessageBox.warning(
                self,
                "Erreur",
                "Aucun mot de passe administrateur n'est configuré.\n"
                "Veuillez configurer un mot de passe dans les paramètres.",
            )
            return

        if entered_hash == stored_hash:
            self._admin_authenticated = True
            self.accept()
        else:
            QMessageBox.warning(
                self,
                "Erreur",
                "Mot de passe incorrect.",
            )
            self.password_input.clear()
            self.password_input.setFocus()

    def is_authenticated(self) -> bool:
        """Check if authentication was successful.

        Returns:
            True if authenticated, False otherwise
        """
        return self._admin_authenticated
